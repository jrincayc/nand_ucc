"""ACC8: custom byte accumulator machine, designed for small hardware.  Registers: ACC (8), P (13-bit
data pointer with post-increment), PC (13), flags Z C.  Zero page (0x00-0xFF) is the operand space.
  2-byte zp ops : LDZ STZ ADDZ ADCZ SUBZ SBCZ ANDZ ORZ XORZ INCZ DECZ     (INCZ/DECZ: in-memory, set Z)
  2-byte imm ops: LDI ADDI SUBI ANDI XORI
  3-byte abs    : LDA STA (13-bit address), LPA (P = imm13), JMP
  pointer       : LDX STX LDX+ STX+ (1 byte; mem[P], optional P+=1)   LPZ z: P={mem[z+1],mem[z]}
                  SPZ z: mem[z]=P[7:0], mem[z+1]=P[12:8]
  1-byte acc    : SHL SHR ROL ROR CPL CLC SEC NOP
  2-byte branch : JZ JNZ JC JNC (signed 8-bit relative)
Loads and ALU ops set Z; ADD/SUB/shifts set C (SUB: C = borrow).
"""
from common import ARM_BASE as ARM, ROM_BASE

NAME = 'ACC8'
FUNCS = ['LD', 'ADD', 'ADC', 'SUB', 'SBC', 'AND', 'OR', 'XOR']
SPEC = []                                   # (mnemonic, operand kind, opcode)
for i, f in enumerate(FUNCS):
    SPEC.append((f + 'I', 'i', 0x40 + i))
for i, f in enumerate(FUNCS):
    SPEC.append((f + 'Z', 'z', 0x48 + i))
SPEC += [('STZ', 'z', 0x50), ('INCZ', 'z', 0x51), ('DECZ', 'z', 0x52), ('LPZ', 'z', 0x53), ('SPZ', 'z', 0x54),
         ('JZ', 'r', 0x58), ('JNZ', 'r', 0x59), ('JC', 'r', 0x5A), ('JNC', 'r', 0x5B),
         ('LDA', 'a', 0x80), ('STA', 'a', 0x81), ('LPA', 'a', 0x82), ('JMP', 'a', 0x83),
         ('NOP', '', 0x00), ('CLC', '', 0x01), ('SEC', '', 0x02), ('CPL', '', 0x03), ('SHL', '', 0x04),
         ('SHR', '', 0x05), ('ROL', '', 0x06), ('ROR', '', 0x07), ('LDX', '', 0x08), ('STX', '', 0x09),
         ('LDXP', '', 0x0A), ('STXP', '', 0x0B)]
OP = {n: (c, k) for n, k, c in SPEC}
BYCODE = {c: (n, k) for n, k, c in SPEC}
OPCODE_COUNT = len(SPEC)
SZ = {'z': 2, 'i': 2, 'a': 3, '': 1, 'r': 2}


class Asm:
    def __init__(self): self.items = []
    def label(self, n): self.items.append(('L', n))
    def __getattr__(self, name):
        if name not in OP: raise AttributeError(name)
        return lambda arg=None: self.items.append(('I', name, arg))
    def assemble(self):
        labels, pc = {}, ROM_BASE
        for it in self.items:
            if it[0] == 'L': labels[it[1]] = pc
            else: pc += SZ[OP[it[1]][1]]
        out, pc = bytearray(), ROM_BASE
        for it in self.items:
            if it[0] == 'L': continue
            _, n, arg = it
            code, k = OP[n]
            pc += SZ[k]
            out.append(code)
            v = labels[arg] if isinstance(arg, str) else arg
            if k == 'r':
                assert v >> 8 == pc >> 8, f'{n} {arg}: target {v:#x} not in the page of the next instruction {pc:#x}'
                out.append(v & 255)
            elif k and k in 'zi':
                assert 0 <= v < 256, (n, v); out.append(v)
            elif k == 'a':
                out += bytes([v & 255, v >> 8])
        return bytes(out)


class CPU:
    def __init__(self, m):
        self.m, self.pc, self.acc, self.p, self.z, self.c = m, ROM_BASE, 0, 0, 0, 0

    def f8(self):
        v = self.m.rd(self.pc, 'f'); self.pc = (self.pc + 1) & 0x1FFF; return v

    def setz(self, v):
        v &= 255; self.z = int(v == 0); return v

    def step(self):
        i0 = self.pc
        n, k = BYCODE[self.f8()]
        arg = None
        if k and k in 'zir': arg = self.f8()
        elif k == 'a': arg = self.f8(); arg |= self.f8() << 8
        m, a = self.m, self.acc
        rd = lambda: m.rd(arg)
        if n[-1] in 'IZ' and n[:-1] in FUNCS:
            f = FUNCS.index(n[:-1]); v = arg if n[-1] == 'I' else rd()
            if f == 0: t = v
            elif f in (1, 2): t = a + v + (self.c if f == 2 else 0); self.c = t >> 8
            elif f in (3, 4): t = a - v - (self.c if f == 4 else 0); self.c = int(t < 0)
            elif f == 5: t = a & v
            elif f == 6: t = a | v
            else: t = a ^ v
            self.acc = self.setz(t)
        elif n == 'STZ': m.wr(arg, a)
        elif n in ('INCZ', 'DECZ'):
            v = self.setz(rd() + (1 if n == 'INCZ' else -1)); m.wr(arg, v)
        elif n == 'LDA': self.acc = self.setz(m.rd(arg))
        elif n == 'STA': m.wr(arg, a)
        elif n == 'LPA': self.p = arg & 0x1FFF
        elif n == 'JMP':
            if arg == i0: return False
            self.pc = arg
        elif n == 'LDX': self.acc = self.setz(m.rd(self.p))
        elif n == 'LDXP': self.acc = self.setz(m.rd(self.p)); self.p = (self.p + 1) & 0x1FFF
        elif n == 'STX': m.wr(self.p, a)
        elif n == 'STXP': m.wr(self.p, a); self.p = (self.p + 1) & 0x1FFF
        elif n == 'LPZ': lo = m.rd(arg); hi = m.rd(arg + 1); self.p = (lo | hi << 8) & 0x1FFF
        elif n == 'SPZ': m.wr(arg, self.p & 255); m.wr(arg + 1, self.p >> 8)
        elif n == 'SHL': self.c = a >> 7; self.acc = self.setz(a << 1)
        elif n == 'SHR': self.c = a & 1; self.acc = self.setz(a >> 1)
        elif n == 'ROL': c = self.c; self.c = a >> 7; self.acc = self.setz(a << 1 | c)
        elif n == 'ROR': c = self.c; self.c = a & 1; self.acc = self.setz(a >> 1 | c << 7)
        elif n == 'CPL': self.acc = self.setz(~a)
        elif n == 'CLC': self.c = 0
        elif n == 'SEC': self.c = 1
        elif n == 'NOP': pass
        elif n in ('JZ', 'JNZ', 'JC', 'JNC'):
            t = {'JZ': self.z, 'JNZ': not self.z, 'JC': self.c, 'JNC': not self.c}[n]
            if t: self.pc = (self.pc & ~255) | arg
        else: raise ValueError(n)
        return True


def assemble(kernel, P):
    a = Asm()
    lo, hi = (lambda v: v & 255), (lambda v: v >> 8)
    if kernel == 'K1':
        n = P['K1_N']; IL, IH = 0x10, 0x11
        a.LPA(ROM_BASE); a.LDI(0); a.STZ(IL); a.STZ(IH)
        a.label('loop')
        a.LDXP(); a.STA(ARM + 10); a.LDZ(IL); a.STA(ARM + 4); a.LDZ(IH); a.STA(ARM + 5)
        a.LDI(3); a.STA(ARM + 15)
        a.INCZ(IL); a.JNZ('c'); a.INCZ(IH); a.label('c')
        a.LDZ(IL); a.XORI(lo(n)); a.JNZ('loop'); a.LDZ(IH); a.XORI(hi(n)); a.JNZ('loop')
    elif kernel == 'K2':
        PV, OV, T0, T1, OFF, CNT, SC = 0x10, 0x12, 0x14, 0x15, 0x16, 0x17, 0x18
        a.LPA(P['K2_OUT']); a.SPZ(OV); a.LPA(P['K2_S'])
        a.LDI(P['K2_M']); a.STZ(CNT); a.LDI(0); a.STZ(OFF)
        a.label('loop')
        a.LDXP(); a.STZ(T0); a.LDX(); a.STZ(T1)
        a.LDZ(OFF); a.JZ('ns'); a.STZ(SC)
        a.label('sh'); a.LDZ(T1); a.SHR(); a.STZ(T1); a.LDZ(T0); a.ROR(); a.STZ(T0); a.DECZ(SC); a.JNZ('sh')
        a.label('ns')
        a.SPZ(PV); a.LPZ(OV); a.LDZ(T0); a.STXP(); a.LDZ(T1); a.ANDI(1); a.STXP(); a.SPZ(OV); a.LPZ(PV)
        a.INCZ(OFF); a.LDZ(OFF); a.XORI(8); a.JNZ('s2'); a.LDI(0); a.STZ(OFF); a.LDXP()
        a.label('s2'); a.DECZ(CNT); a.JNZ('loop')
    elif kernel == 'K3':
        TV, OV, A, B, T, CNT = 0x10, 0x12, 0x14, 0x16, 0x18, 0x19
        a.LPA(P['K3_VAL'] + P['K3_NIN']); a.SPZ(OV); a.LPA(P['K3_TBL'])
        a.LDI(P['K3_G']); a.STZ(CNT)
        a.label('loop')
        a.LDXP(); a.STZ(A); a.LDXP(); a.STZ(A + 1); a.LDXP(); a.STZ(B); a.LDXP(); a.STZ(B + 1)
        a.SPZ(TV); a.LPZ(A); a.LDX(); a.STZ(T); a.LPZ(B); a.LDX(); a.ANDZ(T); a.CPL(); a.STZ(T)
        a.LPZ(OV); a.LDZ(T); a.STXP(); a.SPZ(OV); a.LPZ(TV)
        a.DECZ(CNT); a.JNZ('loop')
    elif kernel == 'K4':
        XL, XH, YV, WL, NW, J = 0x10, 0x11, 0x12, 0x13, 0x14, 0x15
        a.LDI(1); a.STA(ARM + 8); a.LDI(0); a.STA(ARM + 9)
        a.LDI(P['K4_Y0']); a.STZ(YV); a.LDI(lo(P['K4_X0'])); a.STZ(XL); a.LDI(hi(P['K4_X0'])); a.STZ(XH)
        a.LDI(0); a.STZ(WL); a.LDI(P['K4_NW']); a.STZ(NW)
        a.label('word'); a.LDI(8); a.STZ(J)
        a.label('cell')
        a.LDZ(XL); a.STA(ARM + 0); a.LDZ(XH); a.STA(ARM + 1); a.LDZ(YV); a.STA(ARM + 2)
        a.LDI(0); a.STA(ARM + 3); a.LDI(1); a.STA(ARM + 15)
        a.LDZ(XL); a.ADDI(3); a.STZ(XL); a.JNC('nc'); a.INCZ(XH); a.label('nc')
        a.DECZ(J); a.JNZ('cell')
        a.INCZ(WL); a.LDZ(WL); a.XORI(64); a.JNZ('nw')
        a.LDI(0); a.STZ(WL); a.LDI(lo(P['K4_X0'])); a.STZ(XL); a.LDI(hi(P['K4_X0'])); a.STZ(XH)
        a.LDZ(YV); a.ADDI(4); a.STZ(YV)
        a.label('nw'); a.DECZ(NW); a.JNZ('word')
    else:
        raise KeyError(kernel)
    a.label('halt'); a.JMP('halt')
    return a.assemble()


if __name__ == '__main__':
    import common, sys
    for row in common.report(sys.modules[__name__]):
        print(row)
