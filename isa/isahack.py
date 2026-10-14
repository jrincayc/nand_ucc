"""Hack-derived von Neumann machine.  16-bit instructions fetched as two bytes (little endian) from
the unified 13-bit memory.  Registers: D (8 bit), A (13 bit), PC (13 bit).  M = mem[A].
  A-instruction  0vvvvvvvvvvvvvvv   A = v[12:0]
  C-instruction  111 a cccccc ddd jjj  standard Hack comp/dest/jump, 8-bit ALU, signed jump tests;
                 dest A writes A[7:0] only (A[12:8] unchanged)
  AP instruction 110 xxxxxxxxxxxxx   A = {mem[A+1][4:0], mem[A]}   (indirect A load; the one addition
                 to Hack: it makes 13-bit pointers in memory usable; 2 data reads)
Jumps go to A (value before the instruction).  No carry flag, no shifts (only D+D / D+M).
"""
import common
from common import ARM_BASE as ARM, ROM_BASE

NAME = 'Hack-vN'
COMP = {'0': 0b101010, '1': 0b111111, '-1': 0b111010, 'D': 0b001100, 'A': 0b110000, '!D': 0b001101,
        '!A': 0b110001, '-D': 0b001111, '-A': 0b110011, 'D+1': 0b011111, 'A+1': 0b110111,
        'D-1': 0b001110, 'A-1': 0b110010, 'D+A': 0b000010, 'D-A': 0b010011, 'A-D': 0b000111,
        'D&A': 0b000000, 'D|A': 0b010101}
FN = {'0': lambda d, y: 0, '1': lambda d, y: 1, '-1': lambda d, y: -1, 'D': lambda d, y: d,
      'A': lambda d, y: y, '!D': lambda d, y: ~d, '!A': lambda d, y: ~y, '-D': lambda d, y: -d,
      '-A': lambda d, y: -y, 'D+1': lambda d, y: d + 1, 'A+1': lambda d, y: y + 1,
      'D-1': lambda d, y: d - 1, 'A-1': lambda d, y: y - 1, 'D+A': lambda d, y: d + y,
      'D-A': lambda d, y: d - y, 'A-D': lambda d, y: y - d, 'D&A': lambda d, y: d & y,
      'D|A': lambda d, y: d | y}
BYCODE = {v: FN[k] for k, v in COMP.items()}
JUMP = {'': 0, 'JGT': 1, 'JEQ': 2, 'JGE': 3, 'JLT': 4, 'JNE': 5, 'JLE': 6, 'JMP': 7}


class Asm:
    def __init__(self):
        self.items = []

    def label(self, n): self.items.append(('L', n))
    def A(self, v): self.items.append(('A', v))
    def AP(self): self.items.append(('W', 6 << 13))
    def data(self, b): self.items.append(('B', bytes(b)))
    def data_label(self, lab): self.items.append(('LA', lab))
    def C(self, dest, comp, jump=''):
        a = 0
        if 'M' in comp:
            a, comp = 1, comp.replace('M', 'A')
        d = ('A' in dest) << 2 | ('D' in dest) << 1 | ('M' in dest)
        self.items.append(('W', 7 << 13 | a << 12 | COMP[comp] << 6 | d << 3 | JUMP[jump]))

    def assemble(self):
        labels, pc = {}, ROM_BASE
        for it in self.items:
            if it[0] == 'L': labels[it[1]] = pc
            elif it[0] == 'B': pc += len(it[1])
            elif it[0] == 'LA': pc += 2
            else: pc += 2
        out = bytearray()
        for it in self.items:
            if it[0] == 'L': continue
            if it[0] == 'B': out += it[1]; continue
            if it[0] == 'LA': v = labels[it[1]]; out += bytes([v & 255, v >> 8]); continue
            v = it[1]
            if it[0] == 'A':
                if isinstance(v, tuple) and v[0] == 'tab':
                    v = (labels['rettab'] & 255) + 2 * v[1]; assert v < 256, 'return table crosses a page'
                elif isinstance(v, tuple) and v[0] == 'page': v = labels['rettab'] & ~255
                elif isinstance(v, tuple): v = labels[v[1]] & 255 if v[0] == 'lo' else labels[v[1]] >> 8
                else: v = labels[v] if isinstance(v, str) else v
                assert 0 <= v < 0x2000, v
            out += bytes([v & 255, v >> 8])
        return bytes(out)

    # --- macros -------------------------------------------------------------
    def setc(self, var, k):
        self.A(var)
        if k in (0, 1, 255): self.C('M', {0: '0', 1: '1', 255: '-1'}[k])
        else:
            self.A(k); self.C('D', 'A'); self.A(var); self.C('M', 'D')
    def ldD(self, var): self.A(var); self.C('D', 'M')
    def stD(self, var): self.A(var); self.C('M', 'D')
    def ldDc(self, k): self.A(k); self.C('D', 'A')
    def jump(self, lab, cond='JMP', comp='0'): self.A(lab); self.C('', comp, cond)
    def inc16(self, lo, tag):
        self.A(lo); self.C('M', 'M+1'); self.C('D', 'M'); self.jump(tag, 'JNE', 'D')
        self.A(lo + 1); self.C('M', 'M+1'); self.label(tag)
    def dec_loop(self, var, lab):            # var -= 1; if var != 0 goto lab
        self.A(var); self.C('M', 'M-1'); self.C('D', 'M'); self.jump(lab, 'JNE', 'D')


class CPU:
    def __init__(self, m):
        self.m, self.pc, self.A, self.D = m, ROM_BASE, 0, 0

    def f16(self):
        lo = self.m.rd(self.pc, 'f'); hi = self.m.rd(self.pc + 1, 'f')
        self.pc = (self.pc + 2) & common.AMASK
        return lo | hi << 8

    def step(self):
        i0 = self.pc
        ins = self.f16()
        if ins >> 15 == 0:
            self.A = ins & common.AMASK
            return True
        top = ins >> 13
        if top == 6:
            lo = self.m.rd(self.A); hi = self.m.rd(self.A + 1)
            self.A = (lo | (hi & (common.AMASK >> 8)) << 8)
            return True
        assert top == 7, hex(ins)
        a, c, d, j = ins >> 12 & 1, ins >> 6 & 63, ins >> 3 & 7, ins & 7
        y = self.m.rd(self.A) if a else self.A & 255
        out = BYCODE[c](self.D, y) & 255
        s = out - 256 if out > 127 else out
        oldA = self.A
        if d & 1: self.m.wr(oldA, out)
        if d & 2: self.D = out
        if d & 4: self.A = (self.A & ~255) | out
        if (j & 1 and s > 0) or (j & 2 and s == 0) or (j & 4 and s < 0):
            if oldA == i0 - 2: return False
            self.pc = oldA
        return True


def assemble(kernel, P):
    a = Asm()
    lo, hi = (lambda v: v & 255), (lambda v: v >> 8)
    V = list(range(0x10, 0x40, 2))             # 16-bit vars at even addresses (lo, lo+1)
    if kernel == 'K1':
        n = P['K1_N']
        PV, IV = V[0], V[1]
        a.setc(PV, lo(ROM_BASE)); a.setc(PV + 1, hi(ROM_BASE)); a.setc(IV, 0); a.setc(IV + 1, 0)
        a.label('loop')
        a.A(PV); a.AP(); a.C('D', 'M'); a.stD(ARM + 10)
        a.ldD(IV); a.stD(ARM + 4); a.ldD(IV + 1); a.stD(ARM + 5)
        a.ldDc(3); a.stD(ARM + 15)
        a.inc16(PV, 'c1'); a.inc16(IV, 'c2')
        a.ldD(IV); a.A(lo(n)); a.C('D', 'D-A'); a.jump('loop', 'JNE', 'D')
        a.ldD(IV + 1); a.A(hi(n)); a.C('D', 'D-A'); a.jump('loop', 'JNE', 'D')
    elif kernel == 'K2':
        PV, OV, BM, OM, VL, VH, I, K = V[0], V[1], 0x30, 0x31, 0x32, 0x33, 0x34, 0x35
        a.setc(PV, lo(P['K2_S'])); a.setc(PV + 1, hi(P['K2_S']))
        a.setc(OV, lo(P['K2_OUT'])); a.setc(OV + 1, hi(P['K2_OUT']))
        a.setc(K, P['K2_M']); a.setc(BM, 1)
        a.label('field')
        a.setc(VL, 0); a.setc(VH, 0); a.setc(OM, 1); a.setc(I, 9)
        a.label('bit')
        a.A(PV); a.AP(); a.C('D', 'M'); a.A(BM); a.C('D', 'D&M'); a.jump('skip', 'JEQ', 'D')
        a.ldD(OM); a.jump('hib', 'JEQ', 'D')
        a.A(VL); a.C('M', 'D|M'); a.jump('skip')
        a.label('hib'); a.setc(VH, 1)
        a.label('skip')
        a.ldD(OM); a.C('M', 'D+M')
        a.ldD(BM); a.C('M', 'D+M'); a.C('D', 'M'); a.jump('nb', 'JNE', 'D')
        a.setc(BM, 1); a.inc16(PV, 'p')
        a.label('nb')
        a.dec_loop(I, 'bit')
        a.ldD(VL); a.A(OV); a.AP(); a.C('M', 'D'); a.inc16(OV, 'o1')
        a.ldD(VH); a.A(OV); a.AP(); a.C('M', 'D'); a.inc16(OV, 'o2')
        a.dec_loop(K, 'field')
    elif kernel == 'K3':
        TV, OV, TMP, K = V[0], V[1], 0x30, 0x31
        a.setc(TV, lo(P['K3_TBL'])); a.setc(TV + 1, hi(P['K3_TBL']))
        o = P['K3_VAL'] + P['K3_NIN']
        a.setc(OV, lo(o)); a.setc(OV + 1, hi(o)); a.setc(K, P['K3_G'])
        a.label('loop')
        a.A(TV); a.AP(); a.AP(); a.C('D', 'M'); a.stD(TMP)
        a.inc16(TV, 't1'); a.inc16(TV, 't2')
        a.A(TV); a.AP(); a.AP(); a.C('D', 'M'); a.A(TMP); a.C('D', 'D&M'); a.C('D', '!D')
        a.A(OV); a.AP(); a.C('M', 'D')
        a.inc16(TV, 't3'); a.inc16(TV, 't4'); a.inc16(OV, 't5')
        a.dec_loop(K, 'loop')
    elif kernel == 'K4':
        XV, YV, J, WL, NW = V[0], 0x30, 0x31, 0x32, 0x33
        a.setc(ARM + 8, 1); a.setc(ARM + 9, 0)
        a.setc(YV, P['K4_Y0']); a.setc(XV, lo(P['K4_X0'])); a.setc(XV + 1, hi(P['K4_X0']))
        a.setc(WL, 0); a.setc(NW, P['K4_NW'])
        a.label('word'); a.setc(J, 8)
        a.label('cell')
        a.ldD(XV); a.stD(ARM + 0); a.ldD(XV + 1); a.stD(ARM + 1); a.ldD(YV); a.stD(ARM + 2)
        a.setc(ARM + 3, 0); a.setc(ARM + 15, 1)
        a.ldD(XV); a.jump('neg', 'JLT', 'D')
        a.A(3); a.C('D', 'D+A'); a.stD(XV); a.jump('xd')
        a.label('neg'); a.A(3); a.C('D', 'D+A'); a.stD(XV); a.jump('xd', 'JLT', 'D')
        a.A(XV + 1); a.C('M', 'M+1')
        a.label('xd')
        a.dec_loop(J, 'cell')
        a.A(WL); a.C('M', 'M+1'); a.C('D', 'M'); a.A(64); a.C('D', 'D-A'); a.jump('nw', 'JNE', 'D')
        a.setc(WL, 0); a.setc(XV, lo(P['K4_X0'])); a.setc(XV + 1, hi(P['K4_X0']))
        a.ldD(YV); a.A(4); a.C('D', 'D+A'); a.stD(YV)
        a.label('nw')
        a.dec_loop(NW, 'word')
    else:
        raise KeyError(kernel)
    a.label('halt'); a.jump('halt')
    return a.assemble()


if __name__ == '__main__':
    import common, sys
    for row in common.report(sys.modules[__name__]):
        print(row)
