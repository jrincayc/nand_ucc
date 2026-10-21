"""Behavioural machine with a RAM of ramn bytes (reads between RAM and the ARM window are 0)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, '..', 'tools'), os.path.join(HERE, '..', 'isa')]
import common


class MR(common.Machine):
    def __init__(self, ramn):
        super().__init__(); self.ramn = ramn; self.ram = bytearray(ramn)
    def peek(self, a):
        a &= common.AMASK
        if a < self.ramn: return self.ram[a]
        return 0 if a < common.ROM_BASE else self.rom[a - common.ROM_BASE]
    def wr(self, a, v):
        a &= common.AMASK; v &= 255; self.dwrite += 1
        if a < self.ramn: self.ram[a] = v
        elif common.ARM_BASE <= a < common.ROM_BASE: self.armlog.append((a - common.ARM_BASE, v))
