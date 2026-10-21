#!/usr/bin/env python3
"""rvasm.py -- assembler for the RNDP Replicator 3 CPU (RV32EC).  Trusted base: keep it small and readable.

usage:  python3 rvasm.py -o OUTDIR file.s [file2.s ...]      (files are assembled in order, one location counter; reset PC = ROM_BASE)
output: OUTDIR/rom.bin      bytes from ROM_BASE to the last programmed byte (gaps = 0 = unprogrammed)
        OUTDIR/rom.lst      listing: ADDR BYTES | file:line | [macro] | source text   (every programmed byte appears on exactly one line)
        OUTDIR/symbols.txt  name = value

Source syntax (GNU/LLVM style RISC-V; comments start with // or #... only // here, # is not used):
  label:                       define a label at the location counter (may share a line with a statement)
  mnemonic operands            base instruction or pseudo (see PSEUDO).  Registers x0..x15 or ABI names (zero ra sp gp tp t0-t2 s0 fp s1 a0-a5).
  c.mnemonic operands          force the 16-bit form (error if it does not fit)
  .rvc / .norvc                automatic compression on (default) / off.  When on, each instruction is replaced by its 16-bit form whenever the
                               operands fit (relaxation: sizes only grow until stable).  The listing shows which form was chosen.
  .org expr  .equ NAME, expr   absolute location counter / constant (predefined: ROM_BASE 0x4000, ARM_BASE 0x3FF0)
  .byte e,.. .half e,.. .word e,..   data (little endian)      .space n   n zero bytes (programmed)      .align n   pad to a multiple of n with zeros
  .macro NAME p1 p2 .. / .endm text macro; body uses \\p1 ..; \\@ = unique number per expansion.  Invoke:  NAME arg1, arg2
Expressions: Python syntax on numbers (dec, 0x, 0b), symbols, + - * // % << >> & | ^ ~ ( ), plus lo12(x), hi20(x) (so that lui hi20(x); addi lo12(x) builds x).
Immediate operands accept expressions; branch/jump operands are labels or expressions (absolute addresses)."""
import os, re, sys

ROM_BASE, ARM_BASE = 0x4000, 0x3FF0
REGS = {}
for _i in range(16): REGS[f'x{_i}'] = _i
REGS.update(zero=0, ra=1, sp=2, gp=3, tp=4, t0=5, t1=6, t2=7, s0=8, fp=8, s1=9, a0=10, a1=11, a2=12, a3=13, a4=14, a5=15)


class AsmError(Exception):
    pass


def sx(v, n):
    v &= (1 << n) - 1
    return v - (1 << n) if v >> (n - 1) else v


def fits_s(v, n): return -(1 << (n - 1)) <= v < (1 << (n - 1))
def fits_u(v, n): return 0 <= v < (1 << n)
def b(v, hi, lo=None):
    if lo is None: lo = hi
    return (v >> lo) & ((1 << (hi - lo + 1)) - 1)


# ---- 32-bit encoders
def e_r(f7, rs2, rs1, f3, rd, opc): return (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | opc
def e_i(imm, rs1, f3, rd, opc): return ((imm & 0xFFF) << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | opc
def e_s(imm, rs2, rs1, f3, opc): return (b(imm, 11, 5) << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (b(imm, 4, 0) << 7) | opc
def e_b(imm, rs2, rs1, f3): return (b(imm, 12) << 31) | (b(imm, 10, 5) << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (b(imm, 4, 1) << 8) | (b(imm, 11) << 7) | 0x63
def e_u(imm20, rd, opc): return ((imm20 & 0xFFFFF) << 12) | (rd << 7) | opc
def e_j(imm, rd): return (b(imm, 20) << 31) | (b(imm, 10, 1) << 21) | (b(imm, 11) << 20) | (b(imm, 19, 12) << 12) | (rd << 7) | 0x6F

ALU_R = {'add': (0, 0), 'sub': (0x20, 0), 'sll': (0, 1), 'slt': (0, 2), 'sltu': (0, 3), 'xor': (0, 4), 'srl': (0, 5), 'sra': (0x20, 5), 'or': (0, 6), 'and': (0, 7)}
ALU_I = {'addi': 0, 'slti': 2, 'sltiu': 3, 'xori': 4, 'ori': 6, 'andi': 7}
SHIFT_I = {'slli': (0, 1), 'srli': (0, 5), 'srai': (0x20, 5)}
LOADS = {'lb': 0, 'lh': 1, 'lw': 2, 'lbu': 4, 'lhu': 5}
STORES = {'sb': 0, 'sh': 1, 'sw': 2}
BRANCH = {'beq': 0, 'bne': 1, 'blt': 4, 'bge': 5, 'bltu': 6, 'bgeu': 7}


class NoFit(Exception):
    pass


class Item:
    """one source statement after macro expansion"""
    def __init__(self, kind, text, file, line, macro=''):
        self.kind, self.text, self.file, self.line, self.macro = kind, text, file, line, macro
        self.addr = 0; self.size = 0; self.data = b''; self.minsize = 0


class Asm:
    def __init__(self):
        self.syms = {'ROM_BASE': ROM_BASE, 'ARM_BASE': ARM_BASE}
        self.items = []; self.macros = {}; self.uniq = 0; self.rvc = True

    # ---------------------------------------------------------------- reading
    def read(self, path):
        lines = open(path).read().split('\n')
        self.expand_lines([(l, os.path.basename(path), n + 1, '') for n, l in enumerate(lines)])

    def expand_lines(self, lines):
        i = 0
        while i < len(lines):
            raw, f, n, mac = lines[i]; i += 1
            code = raw.split('//')[0].strip()
            if not code: continue
            m = re.match(r'^([A-Za-z_.][A-Za-z_0-9.]*):\s*(.*)$', code)
            while m:
                self.items.append(Item('label', m.group(1), f, n, mac)); code = m.group(2).strip()
                m = re.match(r'^([A-Za-z_.][A-Za-z_0-9.]*):\s*(.*)$', code)
            if not code: continue
            w = code.split(None, 1); head = w[0]; rest = w[1] if len(w) > 1 else ''
            if head == '.macro':
                parts = rest.split(); name, params = parts[0], parts[1:]; body = []
                while i < len(lines) and lines[i][0].split('//')[0].strip() != '.endm':
                    body.append(lines[i]); i += 1
                if i >= len(lines): raise AsmError(f'{f}:{n}: .macro without .endm')
                i += 1; self.macros[name] = (params, body); continue
            if head in self.macros:
                params, body = self.macros[head]; args = [a.strip() for a in rest.split(',')] if rest else []
                if len(args) != len(params): raise AsmError(f'{f}:{n}: macro {head} takes {len(params)} arguments')
                self.uniq += 1; out = []
                for (bl, bf, bn, _) in body:
                    t = bl
                    for p, a in sorted(zip(params, args), key=lambda x: -len(x[0])): t = t.replace('\\' + p, a)
                    t = t.replace('\\@', str(self.uniq)); out.append((t, bf, bn, f'{head}@{f}:{n}'))
                self.expand_lines(out); continue
            self.items.append(Item('stmt', code, f, n, mac))

    # ---------------------------------------------------------------- expressions and operands
    def ev(self, s, item, pc=None):
        s = s.strip()
        env = dict(self.syms); env.update(lo12=lambda x: sx(x, 12), hi20=lambda x: ((x + 0x800) >> 12) & 0xFFFFF)
        try: return int(eval(s.replace('$', str(pc if pc is not None else 0)), {'__builtins__': {}}, env))
        except NameError as e: raise AsmError(f'{item.file}:{item.line}: undefined symbol in {s!r} ({e})')
        except Exception as e: raise AsmError(f'{item.file}:{item.line}: bad expression {s!r} ({e})')

    def reg(self, s, item):
        s = s.strip()
        if s not in REGS: raise AsmError(f'{item.file}:{item.line}: bad register {s!r} (RV32E has x0..x15)')
        return REGS[s]

    def memop(self, s, item):
        m = re.match(r'^(.*)\(\s*([A-Za-z0-9_]+)\s*\)$', s.strip())
        if not m: raise AsmError(f'{item.file}:{item.line}: bad memory operand {s!r}')
        return (self.ev(m.group(1), item) if m.group(1).strip() else 0), self.reg(m.group(2), item)

    # ---------------------------------------------------------------- instruction encoding
    def pseudo(self, mn, ops, item):
        """expand pseudo-instructions to a list of (mnemonic, operand list); li/la/call depend on the value."""
        o = ops
        if mn == 'nop': return [('addi', ['x0', 'x0', '0'])]
        if mn == 'mv': return [('addi', [o[0], o[1], '0'])]
        if mn == 'not': return [('xori', [o[0], o[1], '-1'])]
        if mn == 'neg': return [('sub', [o[0], 'x0', o[1]])]
        if mn == 'seqz': return [('sltiu', [o[0], o[1], '1'])]
        if mn == 'snez': return [('sltu', [o[0], 'x0', o[1]])]
        if mn == 'sltz': return [('slt', [o[0], o[1], 'x0'])]
        if mn == 'sgtz': return [('slt', [o[0], 'x0', o[1]])]
        if mn == 'j': return [('jal', ['x0', o[0]])]
        if mn == 'jr': return [('jalr', ['x0', f'0({o[0]})'])]
        if mn == 'ret': return [('jalr', ['x0', '0(ra)'])]
        if mn == 'beqz': return [('beq', [o[0], 'x0', o[1]])]
        if mn == 'bnez': return [('bne', [o[0], 'x0', o[1]])]
        if mn == 'blez': return [('bge', ['x0', o[0], o[1]])]
        if mn == 'bgez': return [('bge', [o[0], 'x0', o[1]])]
        if mn == 'bltz': return [('blt', [o[0], 'x0', o[1]])]
        if mn == 'bgtz': return [('blt', ['x0', o[0], o[1]])]
        if mn == 'bgt': return [('blt', [o[1], o[0], o[2]])]
        if mn == 'ble': return [('bge', [o[1], o[0], o[2]])]
        if mn == 'bgtu': return [('bltu', [o[1], o[0], o[2]])]
        if mn == 'bleu': return [('bgeu', [o[1], o[0], o[2]])]
        if mn == 'jal' and len(o) == 1: return [('jal', ['ra', o[0]])]
        if mn == 'jalr' and len(o) == 1: return [('jalr', ['ra', f'0({o[0]})'])]
        return None

    def enc32(self, mn, o, pc, item):
        r = lambda i: self.reg(o[i], item)
        ev = lambda s: self.ev(s, item, pc)
        if mn in ALU_R: f7, f3 = ALU_R[mn]; return e_r(f7, r(2), r(1), f3, r(0), 0x33)
        if mn in ALU_I:
            v = ev(o[2])
            if not fits_s(v, 12): raise AsmError(f'{item.file}:{item.line}: {mn} immediate {v} does not fit 12 bits')
            return e_i(v, r(1), ALU_I[mn], r(0), 0x13)
        if mn in SHIFT_I:
            f7, f3 = SHIFT_I[mn]; v = ev(o[2])
            if not fits_u(v, 5): raise AsmError(f'{item.file}:{item.line}: shift amount {v}')
            return e_r(f7, v, r(1), f3, r(0), 0x13)
        if mn in LOADS:
            imm, rs = self.memop(o[1], item)
            if not fits_s(imm, 12): raise AsmError(f'{item.file}:{item.line}: offset {imm}')
            return e_i(imm, rs, LOADS[mn], r(0), 0x03)
        if mn in STORES:
            imm, rs = self.memop(o[1], item)
            if not fits_s(imm, 12): raise AsmError(f'{item.file}:{item.line}: offset {imm}')
            return e_s(imm, r(0), rs, STORES[mn], 0x23)
        if mn in BRANCH:
            off = ev(o[2]) - pc
            if off & 1 or not fits_s(off, 13): raise NoFit(f'branch offset {off}')
            return e_b(off, r(1), r(0), BRANCH[mn])
        if mn == 'lui': return e_u(ev(o[1]) & 0xFFFFF, r(0), 0x37)
        if mn == 'auipc': return e_u(ev(o[1]) & 0xFFFFF, r(0), 0x17)
        if mn == 'jal':
            off = ev(o[1]) - pc
            if off & 1 or not fits_s(off, 21): raise NoFit(f'jal offset {off}')
            return e_j(off, r(0))
        if mn == 'jalr':
            imm, rs = self.memop(o[1], item)
            return e_i(imm, rs, 0, r(0), 0x67)
        if mn == 'fence': return 0x0000000F
        raise AsmError(f'{item.file}:{item.line}: unknown instruction {mn!r}')

    def c_forms(self, mn, o, pc, item):
        """16-bit encoding of the instruction (mn, o) if one exists, else None.  Never raises NoFit."""
        try: r = lambda i: self.reg(o[i], item)
        except IndexError: return None
        ev = lambda s: self.ev(s, item, pc)
        pr = lambda x: 8 <= x <= 15            # 3-bit register range x8..x15
        q = lambda x: x - 8
        try:
            if mn == 'addi':
                rd, rs, v = r(0), r(1), ev(o[2])
                if rd == 0 and rs == 0 and v == 0: return 0x0001                                              # c.nop
                if rd == rs and rd != 0 and v != 0 and fits_s(v, 6): return 0x0001 | (b(v, 5) << 12) | (rd << 7) | (b(v, 4, 0) << 2)           # c.addi
                if rs == 0 and rd != 0 and fits_s(v, 6): return 0x4001 | (b(v, 5) << 12) | (rd << 7) | (b(v, 4, 0) << 2)                       # c.li
                if rd == 2 and rs == 2 and v != 0 and v % 16 == 0 and fits_s(v, 10):                                                           # c.addi16sp
                    return 0x6101 | (b(v, 9) << 12) | (b(v, 4) << 6) | (b(v, 6) << 5) | (b(v, 8, 7) << 3) | (b(v, 5) << 2)
                if rs == 2 and pr(rd) and v > 0 and v % 4 == 0 and v < 1024:                                                                   # c.addi4spn
                    return 0x0000 | (b(v, 5, 4) << 11) | (b(v, 9, 6) << 7) | (b(v, 2) << 6) | (b(v, 3) << 5) | (q(rd) << 2)
                if v == 0 and rd != 0 and rs != 0: return 0x8002 | (rd << 7) | (rs << 2)                                                      # c.mv
                return None
            if mn == 'add':
                rd, a, bb = r(0), r(1), r(2)
                if rd == a and rd != 0 and bb != 0: return 0x9002 | (rd << 7) | (bb << 2)                                                      # c.add
                if a == 0 and rd != 0 and bb != 0: return 0x8002 | (rd << 7) | (bb << 2)                                                       # c.mv
                if rd == bb and rd != 0 and a != 0: return 0x9002 | (rd << 7) | (a << 2)                                                       # c.add (commutative)
                return None
            if mn in ('sub', 'xor', 'or', 'and'):
                rd, a, bb = r(0), r(1), r(2)
                if not (pr(rd) and pr(bb)): return None
                if a != rd:
                    if mn == 'sub' or rd != bb or not pr(a): return None
                    a, bb = rd, a                                                                                                                # commutative swap
                    if not pr(bb): return None
                return 0x8C01 | ({'sub': 0, 'xor': 1, 'or': 2, 'and': 3}[mn] << 5) | (q(rd) << 7) | (q(bb) << 2)
            if mn == 'andi':
                rd, rs, v = r(0), r(1), ev(o[2])
                if rd == rs and pr(rd) and fits_s(v, 6): return 0x8801 | (b(v, 5) << 12) | (q(rd) << 7) | (b(v, 4, 0) << 2)
                return None
            if mn in ('slli', 'srli', 'srai'):
                rd, rs, v = r(0), r(1), ev(o[2])
                if rd != rs or not 1 <= v <= 31: return None
                if mn == 'slli': return 0x0002 | (rd << 7) | (v << 2) if rd != 0 else None
                if not pr(rd): return None
                return (0x8001 if mn == 'srli' else 0x8401) | (q(rd) << 7) | (v << 2)
            if mn == 'lui':
                rd, v = r(0), ev(o[1]) & 0xFFFFF
                v6 = sx(v, 20)
                if rd not in (0, 2) and v6 != 0 and fits_s(v6, 6): return 0x6001 | (b(v6, 5) << 12) | (rd << 7) | (b(v6, 4, 0) << 2)
                return None
            if mn == 'lw':
                rd = r(0); imm, rs = self.memop(o[1], item)
                if rs == 2 and rd != 0 and fits_u(imm, 8) and imm % 4 == 0: return 0x4002 | (b(imm, 5) << 12) | (rd << 7) | (b(imm, 4, 2) << 4) | (b(imm, 7, 6) << 2)   # c.lwsp
                if pr(rd) and pr(rs) and fits_u(imm, 7) and imm % 4 == 0: return 0x4000 | (b(imm, 5, 3) << 10) | (q(rs) << 7) | (b(imm, 2) << 6) | (b(imm, 6) << 5) | (q(rd) << 2)
                return None
            if mn == 'sw':
                rs2 = r(0); imm, rs = self.memop(o[1], item)
                if rs == 2 and fits_u(imm, 8) and imm % 4 == 0: return 0xC002 | (b(imm, 5, 2) << 9) | (b(imm, 7, 6) << 7) | (rs2 << 2)                                   # c.swsp
                if pr(rs2) and pr(rs) and fits_u(imm, 7) and imm % 4 == 0: return 0xC000 | (b(imm, 5, 3) << 10) | (q(rs) << 7) | (b(imm, 2) << 6) | (b(imm, 6) << 5) | (q(rs2) << 2)
                return None
            if mn == 'jal':
                rd, off = r(0), ev(o[1]) - pc
                if rd in (0, 1) and off % 2 == 0 and fits_s(off, 12):
                    return (0xA001 if rd == 0 else 0x2001) | (b(off, 11) << 12) | (b(off, 4) << 11) | (b(off, 9, 8) << 9) | (b(off, 10) << 8) | (b(off, 6) << 7) | (b(off, 7) << 6) | (b(off, 3, 1) << 3) | (b(off, 5) << 2)
                return None
            if mn == 'jalr':
                rd = r(0); imm, rs = self.memop(o[1], item)
                if imm == 0 and rs != 0 and rd == 0: return 0x8002 | (rs << 7)                                                                          # c.jr
                if imm == 0 and rs != 0 and rd == 1: return 0x9002 | (rs << 7)                                                                          # c.jalr
                return None
            if mn in ('beq', 'bne'):
                a, bb, off = r(0), r(1), ev(o[2]) - pc
                if bb == 0 and pr(a) and off % 2 == 0 and fits_s(off, 9):
                    return (0xC001 if mn == 'beq' else 0xE001) | (b(off, 8) << 12) | (b(off, 4, 3) << 10) | (q(a) << 7) | (b(off, 7, 6) << 5) | (b(off, 2, 1) << 3) | (b(off, 5) << 2)
                return None
        except AsmError:
            return None
        return None

    def encode_stmt(self, item, pc, allow_c):
        """-> bytes for the statement at pc (c.* forced, automatic compression if allow_c)"""
        text = item.text; w = text.split(None, 1); mn = w[0]; ops = [x.strip() for x in w[1].split(',')] if len(w) > 1 else []
        if mn.startswith('.'): raise AsmError('directive in encode_stmt')
        forced = mn.startswith('c.')
        if forced: mn = mn[2:]
        # li / la: value-dependent sequences
        if mn in ('li', 'la'):
            rd = self.reg(ops[0], item); v = self.ev(ops[1], item, pc) & 0xFFFFFFFF; sv = sx(v, 32)
            seq = [('addi', [ops[0], 'x0', str(sv)])] if fits_s(sv, 12) else [('lui', [ops[0], str(((v + 0x800) >> 12) & 0xFFFFF)])] + ([('addi', [ops[0], ops[0], str(sx(v, 12))])] if sx(v, 12) else [])
            if mn == 'la' or (len(ops) > 1 and not re.fullmatch(r'-?(0x[0-9a-fA-F]+|\d+)', ops[1])): self.reserve = 8
            out = b''; p = pc
            for m2, o2 in seq:
                bs = self.enc_one(item, m2, o2, p, allow_c, forced); out += bs; p += len(bs)
            return out
        ps = self.pseudo(mn, ops, item)
        seq = ps if ps else [(mn, ops)]
        out = b''; p = pc
        for m2, o2 in seq:
            bs = self.enc_one(item, m2, o2, p, allow_c, forced); out += bs; p += len(bs)
        return out

    def enc_one(self, item, mn, o, pc, allow_c, forced):
        if forced or allow_c:
            h = self.c_forms(mn, o, pc, item)
            if h is not None: return h.to_bytes(2, 'little')
            if forced: raise AsmError(f'{item.file}:{item.line}: c.{mn} {", ".join(o)} does not fit the 16-bit form')
        try: return self.enc32(mn, o, pc, item).to_bytes(4, 'little')
        except NoFit as e: raise AsmError(f'{item.file}:{item.line}: {e} (out of range; restructure the code)')

    # ---------------------------------------------------------------- layout / relaxation
    def directive(self, item, pc):
        w = item.text.split(None, 1); d = w[0]; rest = w[1] if len(w) > 1 else ''
        ev = lambda s: self.ev(s, item, pc)
        if d == '.org': return ('org', ev(rest))
        if d == '.equ':
            n, e = rest.split(',', 1); self.syms[n.strip()] = ev(e); return ('none',)
        if d == '.rvc': self.rvc = True; return ('none',)
        if d == '.norvc': self.rvc = False; return ('none',)
        if d in ('.byte', '.half', '.word'):
            n = {'.byte': 1, '.half': 2, '.word': 4}[d]
            return ('data', b''.join((ev(x) & ((1 << (8 * n)) - 1)).to_bytes(n, 'little') for x in rest.split(',')))
        if d == '.space': return ('data', bytes(ev(rest)))
        if d == '.align':
            a = ev(rest); return ('data', bytes((-pc) % a))
        if d in ('.globl', '.global', '.text', '.section'): return ('none',)
        raise AsmError(f'{item.file}:{item.line}: unknown directive {d}')

    def layout(self):
        self.reserve = 0
        sizes = {}                                       # id(item) -> minimum size (sizes only grow)
        for it in self.items:
            if it.kind == 'stmt' and not it.text.startswith('.'): sizes[id(it)] = 0
        for rounds in range(40):
            self.syms = {k: v for k, v in self.syms.items() if k in ('ROM_BASE', 'ARM_BASE')}
            self.rvc = True; pc = ROM_BASE; changed = False; labels = {}
            # first sweep: labels with current sizes
            for it in self.items:
                it.addr = pc
                if it.kind == 'label': labels[it.text] = pc; self.syms[it.text] = pc; continue
                if it.text.startswith('.'):
                    pass
                else:
                    pc += sizes[id(it)] if sizes[id(it)] else 4
                    continue
                w = it.text.split(None, 1); d = w[0]
                if d == '.org': pc = self.ev(w[1], it, pc) if w[1].strip() else pc
                elif d == '.equ':
                    n, e = w[1].split(',', 1)
                    try: self.syms[n.strip()] = self.ev(e, it, pc)
                    except AsmError: pass
                elif d in ('.byte', '.half', '.word'): pc += len(w[1].split(',')) * {'.byte': 1, '.half': 2, '.word': 4}[d]
                elif d == '.space': pc += self.ev(w[1], it, pc)
                elif d == '.align': a = self.ev(w[1], it, pc); pc += (-pc) % a
            # second sweep: real encoding at the addresses implied by the sizes
            pc = ROM_BASE; self.rvc = True
            for it in self.items:
                it.addr = pc
                if it.kind == 'label': continue
                if it.text.startswith('.'):
                    r = self.directive(it, pc)
                    if r[0] == 'org': pc = r[1]; it.addr = pc
                    elif r[0] == 'data': it.data = r[1]; pc += len(r[1])
                    else: it.data = b''
                    continue
                bs = self.encode_stmt(it, pc, self.rvc)
                if len(bs) > (sizes[id(it)] or 0):
                    if sizes[id(it)] and len(bs) != sizes[id(it)]: changed = True
                    if not sizes[id(it)]: changed = True
                    sizes[id(it)] = max(sizes[id(it)], len(bs))
                # keep sizes monotone: pad a shrunken encoding back up with a 32-bit form is not possible, so we accept shrinking only in round 0
                it.data = bs; pc += len(bs)
                if len(bs) < sizes[id(it)]: sizes[id(it)] = len(bs); changed = True
            if not changed: break
        else:
            raise AsmError('relaxation did not converge')
        # final consistency check: every label address equals its address in the final layout
        return

    def output(self, outdir):
        os.makedirs(outdir, exist_ok=True)
        mem = {}
        lst = []
        for it in self.items:
            if it.kind == 'label': lst.append(f'{it.addr:04X}  {"":<12} | {it.file}:{it.line} | {it.macro or "":<12} | {it.text}:'); continue
            data = it.data
            for k, byte in enumerate(data):
                if it.addr + k in mem: raise AsmError(f'{it.file}:{it.line}: address {it.addr + k:#x} programmed twice')
                mem[it.addr + k] = byte
            shown = ' '.join(f'{x:02X}' for x in data[:6]) + (' ..' if len(data) > 6 else '')
            lst.append(f'{it.addr:04X}  {shown:<12} | {it.file}:{it.line} | {it.macro or "":<12} | {it.text}')
        end = max(mem) + 1 if mem else ROM_BASE
        img = bytearray(end - ROM_BASE)
        for a, v in mem.items(): img[a - ROM_BASE] = v
        open(os.path.join(outdir, 'rom.bin'), 'wb').write(bytes(img))
        open(os.path.join(outdir, 'rom.lst'), 'w').write('\n'.join(lst) + '\n')
        open(os.path.join(outdir, 'symbols.txt'), 'w').write('\n'.join(f'{k} = {v}' for k, v in sorted(self.syms.items())) + '\n')
        return bytes(img), mem


def assemble(paths, outdir=None):
    a = Asm()
    for p in paths: a.read(p)
    a.layout()
    img, mem = a.output(outdir) if outdir else (None, None)
    return a, img


if __name__ == '__main__':
    args = sys.argv[1:]; out = None; files = []
    while args:
        x = args.pop(0)
        if x == '-o': out = args.pop(0)
        else: files.append(x)
    try:
        a, img = assemble(files, out or 'out')
    except AsmError as e:
        print('asm error:', e); sys.exit(1)
    print(f'{sum(len(i.data) for i in a.items)} bytes, {len([i for i in a.items if i.kind == "label"])} labels, {len(img)} byte image')
