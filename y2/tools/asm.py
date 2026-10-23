#!/usr/bin/env python3
"""asm.py -- text assembler for Hack-vN-AB (Y project, M2).  Copy of nandgen/y/tools/asm.py.  Trusted base: keep it small and readable.

usage:  python3 asm.py -o OUTDIR file.asm [file2.asm ...]      (files are assembled in order, one location counter)
output: OUTDIR/rom.bin   bytes from ROM_BASE to the last programmed byte (gaps = 0 = unprogrammed)
        OUTDIR/rom.lst   listing: one line per emitted item   ADDR  BYTES | file:line | [macro] | source text
        OUTDIR/symbols.txt   name = value

Source syntax (Hack style; comments start with //):
  label:                      define a label at the location counter (may share a line with a statement)
  @expr                       A-instruction (0 <= expr <= AMASK)
  [dest=]comp[;jump]          C-instruction, Hack syntax: dest in A,D,M,AM,AD,MD,AMD
  AP                          indirect A load  A = {mem[A+1][AB-9:0], mem[A]}
  .org expr                   set the location counter (absolute address; skipped bytes stay unprogrammed)
  .equ NAME, expr             constant   (predefined: ROM_BASE, ARM_BASE, AB)
  .byte e,e,...  .word e,...  data (little endian words)    .space n   n zero bytes (programmed)
  .macro NAME p1 p2 ... / .endm   text macro; body uses \\p1 ...; \\@ = unique number per expansion
Expressions: numbers (dec, 0x, 0b), symbols, + - *, parentheses, lo(x), hi(x).
"""
import os, re, sys, json

AB = int(os.environ.get('HACK_AB', 14))
ROM_BASE = 1 << (AB - 1)
AMASK = (1 << AB) - 1

COMP = {'0': 0b101010, '1': 0b111111, '-1': 0b111010, 'D': 0b001100, 'A': 0b110000, '!D': 0b001101,
        '!A': 0b110001, '-D': 0b001111, '-A': 0b110011, 'D+1': 0b011111, 'A+1': 0b110111,
        'D-1': 0b001110, 'A-1': 0b110010, 'D+A': 0b000010, 'D-A': 0b010011, 'A-D': 0b000111,
        'D&A': 0b000000, 'D|A': 0b010101}
JUMP = {'': 0, 'JGT': 1, 'JEQ': 2, 'JGE': 3, 'JLT': 4, 'JNE': 5, 'JLE': 6, 'JMP': 7}
DEST = {'': 0, 'M': 1, 'D': 2, 'MD': 3, 'A': 4, 'AM': 5, 'AD': 6, 'AMD': 7}


class AsmError(Exception):
    pass


def split_comment(text):
    i = text.find('//')
    return (text[:i], text[i + 2:].strip()) if i >= 0 else (text, '')


TOK = re.compile(r'\s*(0x[0-9a-fA-F]+|0b[01]+|\d+|[A-Za-z_.][A-Za-z_0-9.]*|[-+*(),])')


def tokens(s):
    out, pos = [], 0
    s = s.strip()
    while pos < len(s):
        m = TOK.match(s, pos)
        if not m:
            raise AsmError(f'bad character in expression {s!r} at {s[pos:]!r}')
        out.append(m.group(1)); pos = m.end()
        while pos < len(s) and s[pos].isspace(): pos += 1
    return out


def evaluate(expr, syms):
    t = tokens(expr)
    pos = [0]

    def peek(): return t[pos[0]] if pos[0] < len(t) else None
    def take(): pos[0] += 1; return t[pos[0] - 1]

    def atom():
        x = take()
        if x == '(':
            v = add()
            if take() != ')': raise AsmError('missing )')
            return v
        if x == '-': return -atom()
        if x in ('lo', 'hi') and peek() == '(':
            take(); v = add()
            if take() != ')': raise AsmError('missing )')
            return v & 255 if x == 'lo' else (v >> 8) & 255
        if re.fullmatch(r'0x[0-9a-fA-F]+|0b[01]+|\d+', x): return int(x, 0)
        if x in syms: return syms[x]
        raise AsmError(f'undefined symbol {x!r}')

    def mul():
        v = atom()
        while peek() == '*': take(); v *= atom()
        return v

    def add():
        v = mul()
        while peek() in ('+', '-'): v = v + mul() if take() == '+' else v - mul()
        return v

    v = add()
    if pos[0] != len(t): raise AsmError(f'junk after expression {expr!r}')
    return v


def split_args(s):
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch == '(': depth += 1
        if ch == ')': depth -= 1
        if ch == ',' and depth == 0: out.append(cur.strip()); cur = ''
        else: cur += ch
    if cur.strip(): out.append(cur.strip())
    return out


def encode_c(text):
    s = text.replace(' ', '')
    dest, jump = '', ''
    if '=' in s: dest, s = s.split('=', 1)
    if ';' in s: s, jump = s.split(';', 1)
    if jump not in JUMP: raise AsmError(f'bad jump {jump!r}')
    if any(c not in 'AMD' for c in dest) or len(set(dest)) != len(dest):
        raise AsmError(f'bad destination {dest!r}')
    dkey = ''.join(sorted(dest, key='AMD'.index))
    comp = s
    if 'M' in comp and 'A' in comp: raise AsmError(f'comp {s!r} mixes A and M')
    a = 1 if 'M' in comp else 0
    comp = comp.replace('M', 'A')
    for sep in '+&|':
        if sep in comp[1:]:
            x, y = comp.split(sep, 1)
            if (x, y) == ('A', 'D'): comp = 'D' + sep + 'A'
    if comp not in COMP: raise AsmError(f'unknown comp {s!r}')
    return 7 << 13 | a << 12 | COMP[comp] << 6 | DEST[dkey] << 3 | JUMP[jump]


class Item:
    def __init__(self, kind, addr, size, file, line, text, macro=None):
        self.kind, self.addr, self.size, self.file, self.line, self.text, self.macro = kind, addr, size, file, line, text, macro
        self.data = b''; self.stmt = ''


def read_lines(paths):
    for p in paths:
        with open(p) as f:
            for n, raw in enumerate(f, 1):
                yield p, n, raw.rstrip('\n'), None


def expand_macros(lines):
    macros, out, cur, uid = {}, [], None, 0
    for f, n, text, _ in lines:
        code, _c = split_comment(text)
        w = code.split()
        if cur is not None:
            if w and w[0] == '.endm': cur = None
            else: macros[cur][1].append((f, n, text))
            continue
        if w and w[0] == '.macro':
            if len(w) < 2: raise AsmError(f'{f}:{n}: .macro needs a name')
            cur = w[1]; macros[cur] = (w[2:], [])
            continue
        out.append((f, n, text))
    if cur is not None: raise AsmError(f'unterminated .macro {cur}')
    res = []

    def expand(f, n, text, depth=0, info=None):
        nonlocal uid
        code, comment = split_comment(text)
        c = code.strip()
        m = re.match(r'^((?:[A-Za-z_.][A-Za-z_0-9.]*:\s*)*)([A-Za-z_][A-Za-z_0-9]*)\b(.*)$', c)
        if m and m.group(2) in macros and not c.startswith('@'):
            name, argstr = m.group(2), m.group(3)
            params, body = macros[name]
            args = split_args(argstr)
            if len(args) != len(params): raise AsmError(f'{f}:{n}: macro {name} takes {len(params)} arguments')
            if depth > 8: raise AsmError('macro nesting too deep')
            uid += 1; myid = uid
            if m.group(1).strip(): res.append((f, n, m.group(1).strip() + '  ' + ('//' + comment if comment else ''), None))
            res.append((f, n, (name + ' ' + argstr.strip()).strip() + ('  // ' + comment if comment else ''), ('@call', name)))
            for bf, bn, bt in body:
                t = bt
                for p, a in zip(params, args): t = t.replace('\\' + p, a)
                t = t.replace('\\@', str(myid))
                expand(bf, bn, t, depth + 1, (name, f, n))
            return
        res.append((f, n, text, info))

    for f, n, text in out: expand(f, n, text)
    return res


def assemble(paths):
    lines = expand_macros(read_lines(paths))
    syms, items, pc = {'ROM_BASE': ROM_BASE, 'ARM_BASE': ROM_BASE - 16, 'AB': AB}, [], ROM_BASE
    for f, n, text, mac in lines:
        if mac and mac[0] == '@call':
            it = Item('call', pc, 0, f, n, text.strip()); it.stmt = ''; items.append(it); continue
        code, comment = split_comment(text)
        c = code.strip()
        while True:
            m = re.match(r'^([A-Za-z_.][A-Za-z_0-9.]*):\s*(.*)$', c)
            if not m: break
            name = m.group(1)
            if name in syms: raise AsmError(f'{f}:{n}: duplicate symbol {name}')
            syms[name] = pc; c = m.group(2)
        if not c: continue
        macinfo = mac
        w = c.split(None, 1)
        d = w[0]
        arg = w[1] if len(w) > 1 else ''
        if d == '.equ':
            a = split_args(arg)
            if len(a) != 2: raise AsmError(f'{f}:{n}: .equ NAME, expr')
            syms[a[0]] = evaluate(a[1], syms); continue
        if d == '.org':
            pc = evaluate(arg, syms); continue
        if d == '.byte': size = len(split_args(arg))
        elif d == '.word': size = 2 * len(split_args(arg))
        elif d == '.space': size = evaluate(arg, syms)
        elif d.startswith('.'): raise AsmError(f'{f}:{n}: unknown directive {d}')
        else: size = 2
        it = Item('data' if d.startswith('.') else 'instr', pc, size, f, n, text.strip(), macinfo)
        it.stmt = c
        items.append(it); pc += size
    mem = {}
    for it in items:
        c = it.stmt
        if it.kind == 'call': continue
        try:
            w = c.split(None, 1); d = w[0]; arg = w[1] if len(w) > 1 else ''
            if d == '.byte':
                vals = [evaluate(a, syms) for a in split_args(arg)]
                if any(not -128 <= v <= 255 for v in vals): raise AsmError(f'.byte value out of range {vals}')
                it.data = bytes(v & 255 for v in vals)
            elif d == '.word':
                vals = [evaluate(a, syms) for a in split_args(arg)]
                if any(not -32768 <= v <= 65535 for v in vals): raise AsmError(f'.word value out of range {vals}')
                it.data = b''.join(bytes([v & 255, (v >> 8) & 255]) for v in vals)
            elif d == '.space':
                it.data = bytes(it.size)
            elif c.startswith('@'):
                v = evaluate(c[1:], syms)
                if not 0 <= v <= AMASK: raise AsmError(f'A-instruction value {v:#x} outside 0..{AMASK:#x}')
                it.data = bytes([v & 255, v >> 8])
            elif c.replace(' ', '') == 'AP':
                it.data = bytes([0, 6 << 5])
            else:
                v = encode_c(c); it.data = bytes([v & 255, v >> 8])
        except AsmError as e:
            raise AsmError(f'{it.file}:{it.line}: {e}   [{it.text}]')
        for k, b in enumerate(it.data):
            a = it.addr + k
            if not ROM_BASE <= a <= AMASK: raise AsmError(f'{it.file}:{it.line}: address {a:#x} outside ROM {ROM_BASE:#x}..{AMASK:#x}')
            if a in mem: raise AsmError(f'{it.file}:{it.line}: address {a:#x} already used by {mem[a][1]}')
            mem[a] = (b, f'{it.file}:{it.line}')
    return items, syms, mem


def write_outputs(outdir, items, syms, mem):
    os.makedirs(outdir, exist_ok=True)
    top = max(mem) if mem else ROM_BASE
    rom = bytearray(top - ROM_BASE + 1)
    for a, (b, _) in mem.items(): rom[a - ROM_BASE] = b
    open(os.path.join(outdir, 'rom.bin'), 'wb').write(bytes(rom))
    lines, last = [], ROM_BASE
    for it in sorted(items, key=lambda i: i.addr):
        if it.addr > last:
            lines.append(f'{last:04X}  {"":<24}| gap | | [{it.addr - last} unprogrammed bytes]')
        mac = f'macro {it.macro[0]} @{it.macro[1]}:{it.macro[2]}' if it.macro and it.macro[0] != '@call' else ''
        chunks = [it.data[k:k + 8] for k in range(0, len(it.data), 8)] or [b'']
        for k, ch in enumerate(chunks):
            hexb = ' '.join(f'{b:02X}' for b in ch)
            if k == 0: lines.append(f'{it.addr:04X}  {hexb:<24}| {it.file}:{it.line} | {mac} | {it.text}')
            else: lines.append(f'{it.addr + 8 * k:04X}  {hexb:<24}|  |  |')
        last = it.addr + len(it.data)
    open(os.path.join(outdir, 'rom.lst'), 'w').write('\n'.join(lines) + '\n')
    open(os.path.join(outdir, 'symbols.txt'), 'w').write(''.join(f'{k} = {v}\n' for k, v in sorted(syms.items())))
    return bytes(rom)


def main(argv):
    if '-o' not in argv or argv.index('-o') + 1 >= len(argv): print(__doc__); return 2
    k = argv.index('-o'); outdir = argv[k + 1]; files = argv[:k] + argv[k + 2:]
    try:
        items, syms, mem = assemble(files)
    except AsmError as e:
        print('asm error:', e, file=sys.stderr); return 1
    rom = write_outputs(outdir, items, syms, mem)
    print(f'{len(items)} items, {len(rom)} ROM bytes from {ROM_BASE:#x} (AB={AB}), {len(syms)} symbols')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
