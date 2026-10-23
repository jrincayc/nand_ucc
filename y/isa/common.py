"""Machine memory map for Hack-vN-AB (trimmed copy of nandgen/y/isa/common.py: constants + Machine only).
AB-bit address bus (env HACK_AB, default 14), ROM_BASE = 2**(AB-1): RAM below ARM_BASE = ROM_BASE-16, the 16 ARM
registers (write-only window) just below ROM_BASE, ROM from ROM_BASE up.  Reset PC = ROM_BASE."""
import os
AB = int(os.environ.get('HACK_AB', 14))
assert 13 <= AB <= 15
ROM_BASE = 1 << (AB - 1)
ARM_BASE = ROM_BASE - 16
AMASK = (1 << AB) - 1
ROM_BYTES = ROM_BASE


class Machine:
    def __init__(self):
        self.ram = bytearray(ARM_BASE)
        self.rom = bytearray(ROM_BYTES)
        self.armlog = []
        self.fetch = self.dread = self.dwrite = 0

    def load_rom(self, off, data):
        self.rom[off:off + len(data)] = data

    def peek(self, a):
        a &= AMASK
        if a < ARM_BASE:
            return self.ram[a]
        return 0 if a < ROM_BASE else self.rom[a - ROM_BASE]

    def rd(self, a, kind='d'):
        if kind == 'f': self.fetch += 1
        else: self.dread += 1
        return self.peek(a)

    def wr(self, a, v):
        a &= AMASK; v &= 255
        self.dwrite += 1
        if a < ARM_BASE: self.ram[a] = v
        elif a < ROM_BASE: self.armlog.append((a - ARM_BASE, v))

    @property
    def accesses(self):
        return self.fetch + self.dread + self.dwrite
