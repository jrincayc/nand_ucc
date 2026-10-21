"""Hack-derived von Neumann CPU model (trimmed copy of nandgen/y/isa/isahack.py: the CPU only).
16-bit instructions fetched as two bytes (little endian).  Registers D (8 bit), A (AB bit), PC (AB bit).  M = mem[A].
  A-instruction  0vvvvvvvvvvvvvvv   A = v[AB-1:0]
  C-instruction  111 a cccccc ddd jjj  standard Hack comp/dest/jump, 8-bit ALU, signed jump tests; dest A writes A[7:0] only
  AP instruction 110 xxxxxxxxxxxxx   A = {mem[A+1][AB-9:0], mem[A]}
Jumps go to A (value before the instruction).  A jump to itself halts."""
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
