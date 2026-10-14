"""6502-lite: real NMOS 6502 opcodes, a regular subset.  Registers A, X, Y, PC; flags N Z C.
No stack, no decimal mode, no V flag, no (zp,X) or zp,X modes.
  group 01 (LDA STA ADC SBC AND ORA EOR CMP): imm zp abs abs,X abs,Y (zp),Y   (STA: no imm)
  group 10: ASL LSR ROL ROR (A, zp, abs), INC DEC (zp, abs), LDX (imm zp abs), STX (zp abs)
  group 00: LDY CPX CPY (imm zp abs), STY (zp abs)
  implied: TAX TXA TAY TYA INX DEX INY DEY CLC SEC NOP; branches BEQ BNE BCC BCS BMI BPL; JMP abs
"""
from common import ARM_BASE, ROM_BASE

NAME = '6502-lite'
SIZE = {'imm': 2, 'zp': 2, 'izy': 2, 'rel': 2, 'abs': 3, 'absx': 3, 'absy': 3, 'acc': 1, 'impl': 1}

OPS = {}   # (mnemonic, mode) -> opcode
G1 = {'ORA': 0, 'AND': 1, 'EOR': 2, 'ADC': 3, 'STA': 4, 'LDA': 5, 'CMP': 6, 'SBC': 7}
M1 = {'zp': 1, 'imm': 2, 'abs': 3, 'izy': 4, 'absy': 6, 'absx': 7}
for m, a in G1.items():
    for md, b in M1.items():
        if not (m == 'STA' and md == 'imm'):
            OPS[(m, md)] = a << 5 | b << 2 | 1
G2 = {'ASL': 0, 'ROL': 1, 'LSR': 2, 'ROR': 3, 'STX': 4, 'LDX': 5, 'DEC': 6, 'INC': 7}
for m in ('ASL', 'ROL', 'LSR', 'ROR'):
    for md, b in (('zp', 1), ('acc', 2), ('abs', 3)):
        OPS[(m, md)] = G2[m] << 5 | b << 2 | 2
for m in ('INC', 'DEC', 'STX'):
    for md, b in (('zp', 1), ('abs', 3)):
        OPS[(m, md)] = G2[m] << 5 | b << 2 | 2
for md, b in (('imm', 0), ('zp', 1), ('abs', 3)):
    OPS[('LDX', md)] = G2['LDX'] << 5 | b << 2 | 2
G0 = {'STY': 4, 'LDY': 5, 'CPY': 6, 'CPX': 7}
for m, a in G0.items():
    for md, b in (('imm', 0), ('zp', 1), ('abs', 3)):
        if not (m == 'STY' and md == 'imm'):
            OPS[(m, md)] = a << 5 | b << 2
for m, o in (('TAX', 0xAA), ('TXA', 0x8A), ('TAY', 0xA8), ('TYA', 0x98), ('INX', 0xE8), ('DEX', 0xCA),
             ('INY', 0xC8), ('DEY', 0x88), ('CLC', 0x18), ('SEC', 0x38), ('NOP', 0xEA)):
    OPS[(m, 'impl')] = o
for m, o in (('BPL', 0x10), ('BMI', 0x30), ('BCC', 0x90), ('BCS', 0xB0), ('BNE', 0xD0), ('BEQ', 0xF0)):
    OPS[(m, 'rel')] = o
OPS[('JMP', 'abs')] = 0x4C
DEC = {v: k for k, v in OPS.items()}
OPCODE_COUNT = len(OPS)


class Asm:
    def __init__(self, base=ROM_BASE):
        self.base, self.items = base, []

    def label(self, n):
        self.items.append(('L', n))

    def __getattr__(self, name):
        mn, _, md = name.partition('_')
        md = md or ('rel' if mn.startswith('B') else 'impl')
        if mn in ('ASL', 'LSR', 'ROL', 'ROR') and md == 'impl':
            md = 'acc'
        if (mn, md) not in OPS:
            raise AttributeError(f'no such instruction {mn} {md}')

        def emit(arg=None):
            self.items.append(('I', mn, md, arg))
        return emit

    def assemble(self):
        labels, pc = {}, self.base
        for it in self.items:
            if it[0] == 'L':
                labels[it[1]] = pc
            else:
                pc += SIZE[it[2]]
        out, pc = bytearray(), self.base
        for it in self.items:
            if it[0] == 'L':
                continue
            _, mn, md, arg = it
            val = labels[arg] if isinstance(arg, str) else arg
            out.append(OPS[(mn, md)])
            pc += SIZE[md]
            if md == 'rel':
                d = val - pc
                assert -128 <= d <= 127, f'branch to {arg} out of range ({d})'
                out.append(d & 255)
            elif SIZE[md] == 2:
                assert 0 <= val < 256, (mn, md, val)
                out.append(val)
            elif SIZE[md] == 3:
                out += bytes([val & 255, (val >> 8) & 255])
        return bytes(out)


class CPU:
    def __init__(self, m):
        self.m, self.pc = m, ROM_BASE
        self.a = self.x = self.y = 0
        self.n = self.z = self.c = 0

    def f8(self):
        v = self.m.rd(self.pc, 'f')
        self.pc = (self.pc + 1) & 0x1FFF
        return v

    def nz(self, v):
        v &= 255
        self.n, self.z = v >> 7, int(v == 0)
        return v

    def addr(self, md):
        m = self.m
        if md in ('zp',):
            return self.f8()
        if md == 'abs':
            lo = self.f8()
            return lo | self.f8() << 8
        if md in ('absx', 'absy'):
            lo = self.f8()
            return ((lo | self.f8() << 8) + (self.x if md == 'absx' else self.y)) & 0xFFFF
        if md == 'izy':
            zp = self.f8()
            lo = m.rd(zp)
            hi = m.rd((zp + 1) & 255)
            return ((lo | hi << 8) + self.y) & 0xFFFF
        raise ValueError(md)

    def step(self):
        start = self.pc
        op = self.f8()
        mn, md = DEC[op]
        m = self.m
        if md == 'rel':
            off = self.f8()
            off -= 256 if off > 127 else 0
            cond = {'BEQ': self.z, 'BNE': not self.z, 'BCC': not self.c, 'BCS': self.c,
                    'BMI': self.n, 'BPL': not self.n}[mn]
            if cond:
                self.pc = (self.pc + off) & 0x1FFF
            return self.pc != start
        if mn == 'JMP':
            lo = self.f8()
            self.pc = (lo | self.f8() << 8) & 0x1FFF
            return self.pc != start
        if md == 'impl':
            if mn == 'TAX': self.x = self.nz(self.a)
            elif mn == 'TXA': self.a = self.nz(self.x)
            elif mn == 'TAY': self.y = self.nz(self.a)
            elif mn == 'TYA': self.a = self.nz(self.y)
            elif mn == 'INX': self.x = self.nz(self.x + 1)
            elif mn == 'DEX': self.x = self.nz(self.x - 1)
            elif mn == 'INY': self.y = self.nz(self.y + 1)
            elif mn == 'DEY': self.y = self.nz(self.y - 1)
            elif mn == 'CLC': self.c = 0
            elif mn == 'SEC': self.c = 1
            return True
        if md == 'acc' or mn in ('ASL', 'LSR', 'ROL', 'ROR', 'INC', 'DEC') and md != 'acc':
            if md == 'acc':
                v, ea = self.a, None
            else:
                ea = self.addr(md)
                v = m.rd(ea)
            if mn == 'INC': r = self.nz(v + 1)
            elif mn == 'DEC': r = self.nz(v - 1)
            else:
                if mn == 'ASL': self.c, r = v >> 7, (v << 1) & 255
                elif mn == 'LSR': self.c, r = v & 1, v >> 1
                elif mn == 'ROL': self.c, r = v >> 7, ((v << 1) | self.c) & 255
                else: self.c, r = v & 1, (v >> 1) | self.c << 7
                r = self.nz(r)
            if ea is None:
                self.a = r
            else:
                m.wr(ea, r)
            return True
        if mn in ('STA', 'STX', 'STY'):
            ea = self.addr(md)
            m.wr(ea, {'STA': self.a, 'STX': self.x, 'STY': self.y}[mn])
            return True
        v = self.f8() if md == 'imm' else m.rd(self.addr(md))
        if mn == 'LDA': self.a = self.nz(v)
        elif mn == 'LDX': self.x = self.nz(v)
        elif mn == 'LDY': self.y = self.nz(v)
        elif mn == 'AND': self.a = self.nz(self.a & v)
        elif mn == 'ORA': self.a = self.nz(self.a | v)
        elif mn == 'EOR': self.a = self.nz(self.a ^ v)
        elif mn in ('ADC', 'SBC'):
            if mn == 'SBC':
                v ^= 255
            s = self.a + v + self.c
            self.c = int(s > 255)
            self.a = self.nz(s)
        else:
            r = {'CMP': self.a, 'CPX': self.x, 'CPY': self.y}[mn]
            self.c = int(r >= v)
            self.nz(r - v)
        return True


ARM = ARM_BASE


def assemble(kernel, P):
    a = Asm()
    lo, hi = (lambda v: v & 255), (lambda v: v >> 8)

    def inc16(zl, zh, lab):
        a.INC_zp(zl); a.BNE(lab); a.INC_zp(zh); a.label(lab)

    def add16(zl, zh, k, lab):
        a.LDA_zp(zl); a.CLC(); a.ADC_imm(k); a.STA_zp(zl); a.BCC(lab); a.INC_zp(zh); a.label(lab)

    def dec_count(cl, ch, loop, tag):
        a.LDA_zp(cl); a.BNE(tag); a.DEC_zp(ch); a.label(tag)
        a.DEC_zp(cl); a.LDA_zp(cl); a.ORA_zp(ch); a.BNE(loop)

    def setw(zl, zh, v):
        a.LDA_imm(lo(v)); a.STA_zp(zl)
        a.LDA_imm(hi(v)); a.STA_zp(zh)

    if kernel == 'K1':
        n = P['K1_N']
        PL, PH, IH = 0x10, 0x11, 0x12
        a.LDA_imm(0); a.STA_zp(PL); a.STA_zp(IH)
        a.LDA_imm(hi(ROM_BASE)); a.STA_zp(PH)
        a.LDY_imm(0)
        a.label('loop')
        a.LDA_izy(PL); a.STA_abs(ARM + 10)
        a.TYA(); a.STA_abs(ARM + 4)
        a.LDA_zp(IH); a.STA_abs(ARM + 5)
        a.LDA_imm(3); a.STA_abs(ARM + 15)
        a.INY(); a.BNE('cont'); a.INC_zp(IH); a.INC_zp(PH)
        a.label('cont')
        a.CPY_imm(lo(n)); a.BNE('loop'); a.LDA_zp(IH); a.CMP_imm(hi(n)); a.BNE('loop')
    elif kernel == 'K2':
        PL, PH, OL, OH, OFF, KL, KH, T0, T1 = range(0x10, 0x19)
        setw(PL, PH, P['K2_S']); setw(OL, OH, P['K2_OUT']); setw(KL, KH, P['K2_M'])
        a.LDA_imm(0); a.STA_zp(OFF)
        a.label('loop')
        a.LDY_imm(0); a.LDA_izy(PL); a.STA_zp(T0); a.INY(); a.LDA_izy(PL); a.STA_zp(T1)
        a.LDX_zp(OFF); a.BEQ('ns')
        a.label('sh'); a.LSR_zp(T1); a.ROR_zp(T0); a.DEX(); a.BNE('sh')
        a.label('ns')
        a.LDY_imm(0); a.LDA_zp(T0); a.STA_izy(OL); a.INY(); a.LDA_zp(T1); a.AND_imm(1); a.STA_izy(OL)
        add16(OL, OH, 2, 's0')
        inc16(PL, PH, 's1')
        a.INC_zp(OFF); a.LDA_zp(OFF); a.CMP_imm(8); a.BNE('s2')
        a.LDA_imm(0); a.STA_zp(OFF); inc16(PL, PH, 's3')
        a.label('s2')
        dec_count(KL, KH, 'loop', 'd')
    elif kernel == 'K3':
        TL, TH, OL, OH, AL, AH, BL, BH, GL, GH = range(0x10, 0x1A)
        setw(TL, TH, P['K3_TBL']); setw(OL, OH, P['K3_VAL'] + P['K3_NIN']); setw(GL, GH, P['K3_G'])
        a.label('loop')
        a.LDY_imm(0)
        for z in (AL, AH, BL, BH):
            a.LDA_izy(TL); a.STA_zp(z)
            if z != BH:
                a.INY()
        a.LDY_imm(0)
        a.LDA_izy(AL); a.AND_izy(BL); a.EOR_imm(255); a.STA_izy(OL)
        add16(TL, TH, 4, 't1')
        inc16(OL, OH, 't2')
        dec_count(GL, GH, 'loop', 't3')
    elif kernel == 'K4':
        XL, XH, YL, YH, C, WL, WH, TL, TH = range(0x10, 0x19)
        a.LDA_imm(1); a.STA_abs(ARM + 8); a.LDA_imm(0); a.STA_abs(ARM + 9)
        setw(XL, XH, P['K4_X0']); setw(YL, YH, P['K4_Y0']); setw(WL, WH, P['K4_NW'])
        a.LDA_imm(0); a.STA_zp(C)
        a.label('wloop')
        a.LDA_zp(XL); a.STA_zp(TL); a.LDA_zp(XH); a.STA_zp(TH)
        a.LDX_imm(8)
        a.label('jloop')
        a.LDA_zp(TL); a.STA_abs(ARM + 0); a.LDA_zp(TH); a.STA_abs(ARM + 1)
        a.LDA_zp(YL); a.STA_abs(ARM + 2); a.LDA_zp(YH); a.STA_abs(ARM + 3)
        a.LDA_imm(1); a.STA_abs(ARM + 15)
        add16(TL, TH, 3, 'n1')
        a.DEX(); a.BNE('jloop')
        add16(XL, XH, 24, 'n2')
        a.INC_zp(C); a.LDA_zp(C); a.CMP_imm(64); a.BNE('n3')
        a.LDA_imm(0); a.STA_zp(C); setw(XL, XH, P['K4_X0'])
        add16(YL, YH, 4, 'n4')
        a.label('n3')
        dec_count(WL, WH, 'wloop', 'd')
    else:
        raise KeyError(kernel)
    a.label('halt'); a.JMP_abs('halt')
    return a.assemble()


if __name__ == '__main__':
    import common
    print(NAME, 'opcodes:', OPCODE_COUNT)
    for row in common.report(__import__('isa6502')):
        print(row)
