"""M1 check of the *core* netlist (CPU + address decode, RAM/ROM/ARM outside) against the behavioural model.
The memory map is exercised in full: RAM (2**ram_abits bytes), the ARM window, the gap, ROM, wrap-around.
usage: HACK_AB=14 python3 coretest.py [RAM_ABITS] [FUZZ_SEEDS]"""
import random, sys
import common, isahack as H
from nl_core import build_core
from fastsim import Fast
from fuzz_hack import gen
from test_hackvn import ref_state

RAB = int(sys.argv[1]) if len(sys.argv) > 1 else 10
NSEED = int(sys.argv[2]) if len(sys.argv) > 2 else 20
RAMN = 1 << RAB


class M(common.Machine):
    """Same machine, but RAM is only 2**RAB bytes (reads above it, below the ARM window, return 0)."""
    def __init__(self):
        super().__init__(); self.ram = bytearray(RAMN)
    def peek(self, a):
        a &= common.AMASK
        if a < RAMN: return self.ram[a]
        return 0 if a < common.ROM_BASE else self.rom[a - common.ROM_BASE]
    def wr(self, a, v):
        a &= common.AMASK; v &= 255; self.dwrite += 1
        if a < RAMN: self.ram[a] = v
        elif common.ARM_BASE <= a < common.ROM_BASE: self.armlog.append((a - common.ARM_BASE, v))


core = build_core(2, RAB)
import os
if os.environ.get('COREMUT'):                      # negative control: rewire one random gate input
    import mutate
    rr = random.Random(int(os.environ['COREMUT']))
    while True:
        c2, g = mutate.mutate(core, rr)
        if not os.environ.get('COREMUTD') or 'decode' in str(core.gate_tags[g]): break
    core, MUTGATE = c2, g
Fast.boundary = lambda self: self.st('st') & 1
def net_state(f): return (f.st('pc'), f.st('a'), f.st('d'))


def run(ref_m, net_m, code_len, max_instr=100000, tag=''):
    ref = H.CPU(ref_m); fs = Fast(core, 'addr')
    fs.setbus('run', 0); fs.setbus('romdata', 0); fs.setbus('ramrd', 0); fs.evaluate(); fs.tick()
    fs.setbus('run', 1)
    instrs = ticks = 0
    while instrs < max_instr:
        alive = ref.step(); instrs += 1
        while True:
            fs.setbus('romdata', 0); fs.setbus('ramrd', 0); fs.evaluate()
            a = fs.out('addr')
            fs.setbus('romdata', net_m.rom[a & (common.ROM_BASE - 1)])
            fs.setbus('ramrd', net_m.ram[a & (RAMN - 1)]); fs.evaluate()
            # the model's view of this address must equal what the decode delivers to the CPU
            if fs.out('ram_we'): net_m.ram[fs.out('ram_addr')] = fs.out('wdata')
            if fs.out('arm_en'): net_m.armlog.append((fs.out('arm_addr'), fs.out('wdata')))
            fs.tick(); ticks += 1
            if fs.boundary(): break
            assert ticks < 40 * (instrs + 10), 'stuck'
        if not alive: break
        assert ref_state(ref) == net_state(fs), f'{tag} instr {instrs}: ref {ref_state(ref)} net {net_state(fs)}'
        assert ref_m.ram == net_m.ram, f'{tag} RAM differs after instr {instrs}'
        assert ref_m.armlog == net_m.armlog, f'{tag} armlog differs after instr {instrs}'
    return instrs, ticks


def boundary_image():
    """Directed: for every address just below/above each region boundary do  D=D+1 ; @t ; M=D ; @t ; D=M ; then
    store D into RAM[0x10+i] so reads of the gap/ROM/ARM window are observable; also reads through the wrap."""
    R, A_, B_ = RAMN, common.ARM_BASE, common.ROM_BASE
    ts = sorted({0, 1, R - 1, R, R + 1, A_ - 1, A_, A_ + 1, A_ + 7, A_ + 15, B_ - 1, B_, B_ + 1, B_ + 0x100,
                 2 * B_ - 1, (1 << common.AB) - 1} | {1 << b for b in range(4, common.AB)} | {(1 << b) - 1 for b in range(4, common.AB + 1)})
    w = []
    C = lambda a, comp, d, j=0: 7 << 13 | a << 12 | H.COMP[comp] << 6 | d << 3 | j
    for i, t in enumerate(ts):
        w += [C(0, 'D+1', 2), t, C(0, 'D', 1), t, C(1, 'A', 2) if False else C(1, 'A', 2), 0x40 + i, C(0, 'D', 1)]
    # note: C(1,'A',2) = D=M (a=1 selects M)
    base = B_
    h = base + 2 * len(w)
    w += [h, 7 << 13 | 0b101010 << 6 | 7]
    return b''.join(bytes([x & 255, x >> 8]) for x in w)


def decode_exhaustive():
    """Every address 0..2**AB-1 through the decode: state X, A=address, IR = 'M=M' store word.  Checks
    wdata (= the value the CPU reads), ram_we, arm_en and the ram/arm/rom address outputs."""
    word = 7 << 13 | 1 << 12 | H.COMP['A'] << 6 | 1 << 3          # M = M  (comp passes M through, store)
    fs = Fast(core, 'addr'); rnd = random.Random(7)
    def setw(name, val):
        for i, w in enumerate(core.outs[name]): fs.v[w] = (val >> i) & 1
    setw('st', 0b00100); setw('ir', word & 0x1FFF)           # sX only; IR = lo 8 + hi 5
    fs.setbus('run', 1)
    n = 0
    for mode in ('X', 'F0', 'F1', 'AP0'):
        setw('st', {'X': 0b00100, 'F0': 0b00001, 'F1': 0b00010, 'AP0': 0b01000}[mode])
        for a in range(1 << common.AB):
            other = rnd.getrandbits(common.AB)
            if mode == 'X': setw('a', a); setw('pc', other)
            else: setw('pc', a if mode in ('F0', 'F1') else other); setw('a', a if mode == 'AP0' else other)
            setw('d', rnd.getrandbits(8)); setw('ir', word & 0x1FFF)
            rv, mv = rnd.getrandbits(8), rnd.getrandbits(8)
            fs.setbus('romdata', rv); fs.setbus('ramrd', mv); fs.evaluate()
            exp = mv if a < RAMN else (0 if a < common.ROM_BASE else rv)
            got = (fs.out('wdata'), fs.out('ram_we'), fs.out('arm_en'), fs.out('ram_addr'), fs.out('arm_addr'), fs.out('rom_addr'))
            we = mode == 'X'
            want = (exp, int(we and a < RAMN), int(we and common.ARM_BASE <= a < common.ROM_BASE), a & (RAMN - 1), a & 15, a & (common.ROM_BASE - 1))
            assert got == want, f'decode {mode} addr {a:#x}: got {got} want {want}'
            n += 1
    return n


print('decode exhaustive ok,', decode_exhaustive(), 'addresses', flush=True)
tot = 0
mr, mn = M(), M()
img = boundary_image()
for m in (mr, mn): m.load_rom(0, img)
i, t = run(mr, mn, len(img), tag='boundary'); tot += i
print('boundary ok', i, 'instrs')
for k in common.KERNELS:
    rng1, rng2 = random.Random(f'1-{k}'), random.Random(f'1-{k}')
    code = H.assemble(k, common.P)
    mr, mn = M(), M()
    for m in (mr, mn): m.load_rom(0, code)
    common.prepare(k, mr, rng1); check = common.prepare(k, mn, rng2)
    i, t = run(mr, mn, len(code), tag=k); tot += i
    assert check(mn) is None and mr.ram == mn.ram and mr.armlog == mn.armlog
    print(k, 'ok', i, 'instrs', t, 'ticks', flush=True)
for seed in range(NSEED):
    img = gen(random.Random(seed), 800)
    rng = random.Random(seed); ram = bytes(rng.getrandbits(8) for _ in range(RAMN))
    mr, mn = M(), M()
    for m in (mr, mn): m.ram[:] = ram; m.load_rom(0, img)
    i, t = run(mr, mn, len(img), max_instr=20000, tag=f'fuzz{seed}'); tot += i
print(f'core AB={common.AB} ram_abits={RAB}: all ok, {tot} instructions compared; core NAND {len(core.gates)} DFF {core.n_dff}')
