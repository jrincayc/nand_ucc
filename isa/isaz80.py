"""Z80-lite: real Z80 opcodes, subset.  Registers A B C D E H L, flags Z C (plus S for none), PC.
No stack/CALL/RET, no IX/IY, no ED-prefix.  Included:
  LD r,r' / LD r,n / LD r,(HL) / LD (HL),r / LD A,(BC|DE) / LD (BC|DE),A / LD A,(nn) / LD (nn),A
  LD rr,nn (BC DE HL) / INC DE|HL|BC / DEC rr / INC r / DEC r / ADD HL,rr / EX DE,HL
  ADD A,r|n  SUB n  AND r|n  OR r  XOR r|n  CP n  CPL  CB: SRL SLA RR RL r
  JP nn, JR e, JR NZ|Z|NC|C e, DJNZ e
"""
from common import ARM_BASE as ARM, ROM_BASE

NAME = 'Z80-lite'
R = {'B': 0, 'C': 1, 'D': 2, 'E': 3, 'H': 4, 'L': 5, 'M': 6, 'A': 7}
RR = {'BC': 0, 'DE': 1, 'HL': 2}
JRC = {'NZ': 0x20, 'Z': 0x28, 'NC': 0x30, 'C': 0x38, '': 0x18, 'DJNZ': 0x10}


class Asm:
    def __init__(self):
        self.items, self.used = [], set()

    def label(self, n): self.items.append(('L', n))
    def raw(self, *b, key=None):
        self.items.append(('B', bytes(b)))
        self.used.add(b[0])
    def ld(self, d, s):            # register/register/(HL)
        self.raw(0x40 | R[d] << 3 | R[s])
    def ldn(self, d, n):
        self.raw(0x06 | R[d] << 3, n & 255)
    def ldrr(self, rr, nn):
        self.raw(0x01 | RR[rr] << 4, nn & 255, nn >> 8 & 255)
    def lda_nn(self, nn): self.raw(0x3A, nn & 255, nn >> 8)
    def sta_nn(self, nn): self.raw(0x32, nn & 255, nn >> 8)
    def lda_bc(self): self.raw(0x0A)
    def lda_de(self): self.raw(0x1A)
    def sta_de(self): self.raw(0x12)
    def incr(self, r): self.raw(0x04 | R[r] << 3)
    def decr(self, r): self.raw(0x05 | R[r] << 3)
    def inc16(self, rr): self.raw(0x03 | RR[rr] << 4)
    def dec16(self, rr): self.raw(0x0B | RR[rr] << 4)
    def addhl(self, rr): self.raw(0x09 | RR[rr] << 4)
    def exde(self): self.raw(0xEB)
    def adda_n(self, n): self.raw(0xC6, n & 255)
    def adda(self, r): self.raw(0x80 | R[r])
    def sub_n(self, n): self.raw(0xD6, n & 255)
    def and_n(self, n): self.raw(0xE6, n & 255)
    def and_(self, r): self.raw(0xA0 | R[r])
    def or_(self, r): self.raw(0xB0 | R[r])
    def xor_(self, r): self.raw(0xA8 | R[r])
    def xor_n(self, n): self.raw(0xEE, n & 255)
    def cp_n(self, n): self.raw(0xFE, n & 255)
    def cpl(self): self.raw(0x2F)
    def cb(self, kind, r):         # RL 0x10 RR 0x18 SLA 0x20 SRL 0x38
        self.raw(0xCB, {'RL': 0x10, 'RR': 0x18, 'SLA': 0x20, 'SRL': 0x38}[kind] | R[r])
    def jr(self, cond, lab): self.items.append(('J', JRC[cond], lab))
    def jp(self, lab): self.items.append(('P', lab))

    def assemble(self):
        def size(it): return len(it[1]) if it[0] == 'B' else 2 if it[0] == 'J' else 3 if it[0] == 'P' else 0
        labels, pc = {}, ROM_BASE
        for it in self.items:
            if it[0] == 'L': labels[it[1]] = pc
            pc += size(it)
        out, pc = bytearray(), ROM_BASE
        for it in self.items:
            pc += size(it)
            if it[0] == 'B': out += it[1]
            elif it[0] == 'J':
                d = labels[it[2]] - pc
                assert -128 <= d <= 127, (it, d)
                out += bytes([it[1], d & 255])
            elif it[0] == 'P':
                out += bytes([0xC3, labels[it[1]] & 255, labels[it[1]] >> 8])
        return bytes(out)


class CPU:
    def __init__(self, m):
        self.m, self.pc = m, ROM_BASE
        self.r = [0] * 8          # B C D E H L (M unused) A
        self.z = self.c = 0

    f8 = lambda s: s._f8()
    def _f8(self):
        v = self.m.rd(self.pc, 'f'); self.pc = (self.pc + 1) & 0x1FFF; return v
    def f16(self):
        lo = self._f8(); return lo | self._f8() << 8
    def hl(self): return self.r[4] << 8 | self.r[5]
    def get(self, i): return self.m.rd(self.hl()) if i == 6 else self.r[i]
    def put(self, i, v):
        v &= 255
        if i == 6: self.m.wr(self.hl(), v)
        else: self.r[i] = v
    def rr(self, k): return (self.r[2 * k] << 8 | self.r[2 * k + 1]) if k < 3 else None
    def setrr(self, k, v):
        v &= 0xFFFF; self.r[2 * k], self.r[2 * k + 1] = v >> 8, v & 255
    def alu(self, op, v):
        a = self.r[7]
        if op == 0: t = a + v; self.c = t >> 8
        elif op in (2, 7): t = a - v; self.c = int(t < 0)
        elif op == 4: t = a & v; self.c = 0
        elif op == 5: t = a ^ v; self.c = 0
        elif op == 6: t = a | v; self.c = 0
        else: raise ValueError(op)
        t &= 255; self.z = int(t == 0)
        if op != 7: self.r[7] = t

    def step(self):
        o = self._f8()
        if o == 0xCB:
            o2 = self._f8(); i = o2 & 7; k = o2 & 0xF8; v = self.get(i)
            if k == 0x38: self.c, v = v & 1, v >> 1
            elif k == 0x20: self.c, v = v >> 7, v << 1
            elif k == 0x18: c = self.c; self.c, v = v & 1, v >> 1 | c << 7
            elif k == 0x10: c = self.c; self.c, v = v >> 7, v << 1 | c
            else: raise ValueError(hex(o2))
            v &= 255; self.put(i, v); self.z = int(v == 0); return True
        if o & 0xC0 == 0x40:
            if o == 0x76: raise ValueError('HALT unused')
            self.put(o >> 3 & 7, self.get(o & 7)); return True
        if o & 0xC7 == 0x06: self.put(o >> 3 & 7, self._f8()); return True
        if o & 0xC7 == 0x04:
            i = o >> 3 & 7; v = (self.get(i) + 1) & 255; self.put(i, v); self.z = int(v == 0); return True
        if o & 0xC7 == 0x05:
            i = o >> 3 & 7; v = (self.get(i) - 1) & 255; self.put(i, v); self.z = int(v == 0); return True
        if o & 0xC0 == 0x80: self.alu(o >> 3 & 7, self.get(o & 7)); return True
        if o & 0xC7 == 0xC6: self.alu(o >> 3 & 7, self._f8()); return True
        if o & 0xCF == 0x01 and o >> 4 < 3: self.setrr(o >> 4, self.f16()); return True
        if o & 0xCF == 0x03 and o >> 4 < 3: self.setrr(o >> 4, self.rr(o >> 4) + 1); return True
        if o & 0xCF == 0x0B and o >> 4 < 3: self.setrr(o >> 4, self.rr(o >> 4) - 1); return True
        if o & 0xCF == 0x09 and o >> 4 < 3:
            t = self.hl() + self.rr(o >> 4); self.c = t >> 16; self.setrr(2, t); return True
        m = self.m
        if o == 0x3A: self.r[7] = m.rd(self.f16()); return True
        if o == 0x32: m.wr(self.f16(), self.r[7]); return True
        if o == 0x0A: self.r[7] = m.rd(self.rr(0)); return True
        if o == 0x1A: self.r[7] = m.rd(self.rr(1)); return True
        if o == 0x02: m.wr(self.rr(0), self.r[7]); return True
        if o == 0x12: m.wr(self.rr(1), self.r[7]); return True
        if o == 0xEB:
            d, h = self.rr(1), self.hl(); self.setrr(1, h); self.setrr(2, d); return True
        if o == 0x2F: self.r[7] ^= 255; return True
        if o == 0xC3: self.pc = self.f16(); return True
        if o in (0x18, 0x20, 0x28, 0x30, 0x38, 0x10):
            e = self._f8(); e -= 256 if e > 127 else 0
            if o == 0x10:
                self.r[0] = (self.r[0] - 1) & 255; t = self.r[0] != 0
            else:
                t = {0x18: True, 0x20: not self.z, 0x28: self.z, 0x30: not self.c, 0x38: self.c}[o]
            if t:
                if e == -2: return False
                self.pc = (self.pc + e) & 0x1FFF
            return True
        raise ValueError(f'illegal opcode {o:#x} at {self.pc - 1:#x}')


def assemble(kernel, P):
    a = Asm()
    lo, hi = (lambda v: v & 255), (lambda v: v >> 8)
    if kernel == 'K1':
        n = P['K1_N']
        a.ldrr('HL', ROM_BASE); a.ldrr('DE', 0)
        a.label('loop')
        a.ld('A', 'M'); a.sta_nn(ARM + 10)
        a.ld('A', 'E'); a.sta_nn(ARM + 4)
        a.ld('A', 'D'); a.sta_nn(ARM + 5)
        a.ldn('A', 3); a.sta_nn(ARM + 15)
        a.inc16('HL'); a.inc16('DE')
        a.ld('A', 'E'); a.xor_n(lo(n)); a.jr('NZ', 'loop')
        a.ld('A', 'D'); a.xor_n(hi(n)); a.jr('NZ', 'loop')
    elif kernel == 'K2':
        CNT, OFF = 0x10, 0x11
        a.ldrr('HL', P['K2_S']); a.ldrr('DE', P['K2_OUT'])
        a.ldn('A', P['K2_M']); a.sta_nn(CNT); a.ldn('A', 0); a.sta_nn(OFF)
        a.label('loop')
        a.ld('C', 'M'); a.inc16('HL'); a.ld('B', 'M'); a.dec16('HL')
        a.lda_nn(OFF); a.or_('A'); a.jr('Z', 'ns')
        a.label('sh'); a.cb('SRL', 'B'); a.cb('RR', 'C'); a.decr('A'); a.jr('NZ', 'sh')
        a.label('ns')
        a.ld('A', 'C'); a.sta_de(); a.inc16('DE')
        a.ld('A', 'B'); a.and_n(1); a.sta_de(); a.inc16('DE')
        a.inc16('HL')
        a.lda_nn(OFF); a.incr('A'); a.cp_n(8); a.jr('NZ', 's2')
        a.xor_('A'); a.inc16('HL')
        a.label('s2'); a.sta_nn(OFF)
        a.lda_nn(CNT); a.decr('A'); a.sta_nn(CNT); a.jr('NZ', 'loop')
    elif kernel == 'K3':
        CNT = 0x10
        a.ldrr('HL', P['K3_TBL']); a.ldrr('DE', P['K3_VAL'] + P['K3_NIN'])
        a.ldn('A', P['K3_G']); a.sta_nn(CNT)
        a.label('loop')
        a.ld('C', 'M'); a.inc16('HL'); a.ld('B', 'M'); a.inc16('HL')
        a.lda_bc(); a.sta_de()
        a.ld('C', 'M'); a.inc16('HL'); a.ld('B', 'M'); a.inc16('HL')
        a.lda_bc(); a.ld('C', 'A'); a.lda_de(); a.and_('C'); a.cpl(); a.sta_de(); a.inc16('DE')
        a.lda_nn(CNT); a.decr('A'); a.sta_nn(CNT); a.jr('NZ', 'loop')
    elif kernel == 'K4':
        YV = 0x10
        a.ldn('A', 1); a.sta_nn(ARM + 8); a.xor_('A'); a.sta_nn(ARM + 9)
        a.ldn('A', P['K4_Y0']); a.sta_nn(YV)
        a.ldrr('HL', P['K4_X0']); a.ldn('D', 0); a.ldn('E', P['K4_NW'])
        a.label('word'); a.ldn('B', 8)
        a.label('cell')
        a.ld('A', 'L'); a.sta_nn(ARM + 0); a.ld('A', 'H'); a.sta_nn(ARM + 1)
        a.lda_nn(YV); a.sta_nn(ARM + 2); a.xor_('A'); a.sta_nn(ARM + 3)
        a.ldn('A', 1); a.sta_nn(ARM + 15)
        a.inc16('HL'); a.inc16('HL'); a.inc16('HL')
        a.jr('DJNZ', 'cell')
        a.incr('D'); a.ld('A', 'D'); a.cp_n(64); a.jr('NZ', 'nw')
        a.ldn('D', 0); a.ldrr('HL', P['K4_X0'])
        a.lda_nn(YV); a.adda_n(4); a.sta_nn(YV)
        a.label('nw'); a.decr('E'); a.jr('NZ', 'word')
    else:
        raise KeyError(kernel)
    a.label('halt'); a.jr('', 'halt')
    return a.assemble()


if __name__ == '__main__':
    import common
    for row in common.report(__import__(__name__)):
        print(row)
