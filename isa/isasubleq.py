"""SUBLEQ (flavor b: program lives in RAM, copied from ROM by a hardware boot loader before reset).
8-bit cells, 13-bit operand addresses; instruction a,b,c = 6 bytes (a_lo a_hi b_lo b_hi c_lo c_hi):
  mem[b] -= mem[a]; if the signed 8-bit result <= 0 goto c, else goto next.   Reads of the ARM window give 0,
so an ARM register is set with  T=-v; reg = 0 - T.   Only K1 is implemented (a faithful program);
K2-K4 need bitwise ops / carry tests that 8-bit signed SUBLEQ makes very expensive -- see estimates in
the write-up (marked as estimates, not measured).
"""
from common import ARM_BASE as ARM, ROM_BASE

NAME = 'SUBLEQ(b)'
BASE = 0x0800          # RAM address the boot loader copies the image to
LOADED = [0]


class Asm:
    def __init__(self): self.code, self.data, self.labels = [], [], {}
    def label(self, n): self.code.append(('L', n))
    def var(self, n, v=0): self.data.append((n, v))
    def sub(self, a, b, c=None, lab=None):
        if lab: self.label(lab)
        self.code.append(('I', a, b, c))
    def jmp(self, c, lab=None): self.sub('Z', 'Z', c, lab)
    def mov(self, dst, src):
        self.sub(dst, dst); self.sub(src, 'T'); self.sub('T', dst); self.sub('T', 'T')
    def assemble(self):
        ni = sum(1 for x in self.code if x[0] == 'I')
        addr, pc, sym = {}, BASE, {}
        for x in self.code:
            if x[0] == 'L': sym[x[1]] = pc
            else: pc += 6
        for n, v in self.data:
            sym[n] = pc; pc += 1
        def res(o, nxt):
            if o is None: return nxt
            if isinstance(o, int): return o
            if isinstance(o, tuple):          # field cell of a labelled instruction
                return sym[o[0]] + {'a_lo': 0, 'a_hi': 1, 'b_lo': 2, 'b_hi': 3}[o[1]]
            return sym[o]
        out, pc = bytearray(), BASE
        for x in self.code:
            if x[0] == 'L': continue
            _, a, b, c = x
            for v in (res(a, 0), res(b, 0), res(c, pc + 6)):
                out += bytes([v & 255, v >> 8])
            pc += 6
        for n, v in self.data: out.append(v & 255)
        return bytes(out)


class CPU:
    def __init__(self, m):
        self.m, self.pc = m, BASE
        n = LOADED[0]
        m.ram[BASE:BASE + n] = m.rom[:n]       # boot loader (not counted in kernel accesses)
        self.loader_accesses = 2 * n

    def step(self):
        m, i0 = self.m, self.pc
        f = [m.rd(i0 + k, 'f') for k in range(6)]
        a, b, c = f[0] | f[1] << 8, f[2] | f[3] << 8, f[4] | f[5] << 8
        r = (m.rd(b) - m.rd(a)) & 255
        m.wr(b, r)
        if r == 0 or r > 127:
            if c == i0: return False
            self.pc = c
        else:
            self.pc = i0 + 6
        return True


def assemble(kernel, P):
    if kernel != 'K1':
        raise NotImplementedError(kernel)
    a = Asm()
    for n, v in (('Z', 0), ('T', 0), ('ONE', 1), ('N3', 253), ('M1', 255), ('PLO', ROM_BASE & 255),
                 ('PHI', ROM_BASE >> 8), ('IL', 0), ('IH', 0), ('C', 64), ('CN', 64), ('OC', 4), ('FL', 2), ('K44', P['K1_N'] - 256)):
        a.var(n, v)
    A = lambda r: ARM + r
    a.mov('C', 'CN') if False else None
    a.label('start'); a.mov('C', 'CN')
    a.label('loop')
    a.mov(('LD', 'a_lo'), 'PLO'); a.mov(('LD', 'a_hi'), 'PHI')
    a.sub(0, 'T', lab='LD'); a.sub('T', A(10)); a.sub('T', 'T')
    a.sub('IL', 'T'); a.sub('T', A(4)); a.sub('T', 'T')
    a.sub('IH', 'T'); a.sub('T', A(5)); a.sub('T', 'T')
    a.sub('N3', A(15))
    a.sub('M1', 'PLO'); a.sub('M1', 'IL')
    a.sub('ONE', 'C', 'cend'); a.jmp('loop')
    a.sub('ONE', 'OC', 'ph2', lab='cend'); a.jmp('start')
    a.sub('ONE', 'FL', 'halt', lab='ph2')
    a.sub('M1', 'PHI'); a.sub('M1', 'IH'); a.mov('CN', 'K44'); a.jmp('start')
    a.jmp('halt', lab='halt')
    img = a.assemble()
    LOADED[0] = len(img)
    return img


if __name__ == '__main__':
    import common, sys
    r = common.run(sys.modules[__name__], 'K1', 1)
    print(r)
