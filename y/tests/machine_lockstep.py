"""Run a flattened HD machine (CPU + RAM tiles, ROM external) in lockstep with the behavioural model isahack.CPU."""
import os, sys, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, '..', 'tools'), os.path.join(HERE, '..', 'isa')]
import common, isahack as H
from fastsim import Fast


class MR(common.Machine):
    """Behavioural machine with a RAM of ramn bytes (reads between RAM and the ARM window are 0)."""
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


def run_flat(c, image, ramn, ram_init=None, max_instr=20000, check_every=1):
    """image: ROM bytes.  Returns (instructions, ticks).  Raises AssertionError on the first difference."""
    mr, mn = MR(ramn), MR(ramn)
    for m in (mr, mn): m.load_rom(0, image)
    if ram_init is not None: mr.ram[:] = ram_init
    ref = H.CPU(mr)
    Fast.boundary = lambda self: self.st('st') & 1
    fs = Fast(c, 'rom_addr')
    if ram_init is not None:
        for k in range(ramn):
            for j in range(8): fs.v[c.ram_q[k][j]] = (ram_init[k] >> j) & 1
    def ram_now(): return bytes(sum(fs.v[c.ram_q[k][j]] << j for j in range(8)) for k in range(ramn))
    fs.setbus('tie', 1); fs.setbus('run', 0); fs.setbus('romdata', 0); fs.evaluate(); fs.tick()
    fs.setbus('run', 1)
    armlog = []
    instrs = ticks = 0
    while instrs < max_instr:
        alive = ref.step(); instrs += 1
        while True:
            fs.setbus('romdata', 0); fs.evaluate()
            a13 = fs.out('rom_addr')
            fs.setbus('romdata', mn.rom[a13 & (common.ROM_BASE - 1)] if (a13 & (common.ROM_BASE - 1)) < len(mn.rom) else 0)
            fs.evaluate()
            if fs.out('arm_en'): armlog.append((fs.out('arm_addr'), fs.out('wdata')))
            fs.tick(); ticks += 1
            if fs.boundary(): break
            assert ticks < 40 * (instrs + 10), 'machine stuck'
        if not alive: break
        want = (ref.pc, ref.A, ref.D); got = (fs.st('pc'), fs.st('a'), fs.st('d'))
        assert want == got, f'instr {instrs}: model {want} machine {got}'
        if instrs % check_every == 0:
            assert bytes(mr.ram) == ram_now(), f'RAM differs after instr {instrs}'
            assert mr.armlog == armlog, f'arm log differs after instr {instrs}'
    assert bytes(mr.ram) == ram_now() and mr.armlog == armlog
    return instrs, ticks


if __name__ == '__main__':
    import hd as HDM, ref_flatten as RF
    hd = HDM.read(open(sys.argv[1]).read()); f = RF.flatten(hd); c = RF.to_compiled(f)
    img = open(sys.argv[2], 'rb').read()
    print(run_flat(c, img, f.W))
