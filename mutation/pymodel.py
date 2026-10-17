"""Python port of isahack.CPU + common.Machine/MR (copied semantics), for differential testing of libhack.so."""
class MR:
    def __init__(self, ab, ramn, rom, ram_fill=255):
        self.ab = ab; self.amask = (1 << ab) - 1; self.rom_base = 1 << (ab - 1); self.arm_base = self.rom_base - 16
        self.ramn = ramn; self.ram = bytearray([ram_fill]) * ramn
        self.rom = bytearray(self.rom_base); self.rom[:len(rom)] = rom; self.armlog = []
    def peek(self, a):
        a &= self.amask
        if a < self.ramn: return self.ram[a]
        return 0 if a < self.rom_base else self.rom[a - self.rom_base]
    def rd(self, a, kind='d'): return self.peek(a)
    def wr(self, a, v):
        a &= self.amask; v &= 255
        if a < self.ramn: self.ram[a] = v
        elif self.arm_base <= a < self.rom_base: self.armlog.append((a - self.arm_base, v))
COMP = {'0': 0b101010, '1': 0b111111, '-1': 0b111010, 'D': 0b001100, 'A': 0b110000, '!D': 0b001101, '!A': 0b110001, '-D': 0b001111,
        '-A': 0b110011, 'D+1': 0b011111, 'A+1': 0b110111, 'D-1': 0b001110, 'A-1': 0b110010, 'D+A': 0b000010, 'D-A': 0b010011,
        'A-D': 0b000111, 'D&A': 0b000000, 'D|A': 0b010101}
FN = {'0': lambda d, y: 0, '1': lambda d, y: 1, '-1': lambda d, y: -1, 'D': lambda d, y: d, 'A': lambda d, y: y, '!D': lambda d, y: ~d,
      '!A': lambda d, y: ~y, '-D': lambda d, y: -d, '-A': lambda d, y: -y, 'D+1': lambda d, y: d + 1, 'A+1': lambda d, y: y + 1,
      'D-1': lambda d, y: d - 1, 'A-1': lambda d, y: y - 1, 'D+A': lambda d, y: d + y, 'D-A': lambda d, y: d - y,
      'A-D': lambda d, y: y - d, 'D&A': lambda d, y: d & y, 'D|A': lambda d, y: d | y}
BYCODE = {v: FN[k] for k, v in COMP.items()}
class CPU:
    def __init__(self, m): self.m, self.pc, self.A, self.D = m, m.rom_base, 0, 0
    def f16(self):
        lo = self.m.rd(self.pc); hi = self.m.rd(self.pc + 1); self.pc = (self.pc + 2) & self.m.amask
        return lo | hi << 8
    def step(self):
        i0 = self.pc; ins = self.f16(); am = self.m.amask
        if ins >> 15 == 0: self.A = ins & am; return True
        top = ins >> 13
        if top == 6:
            lo = self.m.rd(self.A); hi = self.m.rd(self.A + 1); self.A = lo | (hi & (am >> 8)) << 8; return True
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
def decode(armlog):
    regs = [0] * 16; cmds = []; rom = []
    s16 = lambda lo, hi: (lo | hi << 8) - (65536 if hi & 128 else 0)
    for r, v in armlog:
        regs[r] = v
        if r != 15: continue
        ax, ay = s16(regs[0], regs[1]), s16(regs[2], regs[3])
        if v == 1:
            if regs[8] > 3: raise KeyError('kind')
            cmds.append((1, regs[8], regs[9], ax, ay, 0, 0))
        elif v == 2: cmds.append((2, 0, 0, ax, ay, s16(regs[4], regs[5]), s16(regs[6], regs[7])))
        elif v == 3: rom.append((ax, ay, regs[4] | regs[5] << 8, regs[10]))
        else: raise AssertionError('bad cmd')
    return cmds, rom
def run(ab, ramn, rom, max_instr, ram_fill=255):
    m = MR(ab, ramn, rom, ram_fill); cpu = CPU(m); n = 0; status = 'timeout'
    try:
        while n < max_instr:
            n += 1
            if not cpu.step(): status = 'halt'; break
    except (AssertionError, KeyError): status = 'illegal'
    return status, n, m
