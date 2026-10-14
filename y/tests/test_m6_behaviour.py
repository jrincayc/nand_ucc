#!/usr/bin/env python3
"""test_m6_behaviour.py -- V7: the improved child (ram_abits 8, 256 B RAM; the machine the ROM builds, which test_m5 / the RNDW run prove equal to
flatten(improved HD)) runs the demo program and 30 random Hack-vN-AB programs in lockstep with the behavioural model isahack.py."""
import os, sys, random
HERE = os.path.dirname(os.path.abspath(__file__))
for d in ('tools', 'isa', 'tests', '.'):
    sys.path.insert(0, os.path.join(HERE, '..', d))
import hd as H, ref_flatten as RF, ref_improve as R, machine_lockstep as ML, isahack as IH, common
hd0 = H.read(open(os.path.join(HERE, '..', 'hd', 'core_r8.hd')).read()); hd1 = R.improve_hd(hd0)[0]
f1 = RF.flatten(hd1); print('improved r8', RF.counts(f1)); c1 = RF.to_compiled(f1)

def gen(rng, n):
    COMPS = list(IH.COMP.values()); words = []
    while len(words) < n:
        r = rng.random()
        if r < 0.25: words.append(rng.getrandbits(15))
        elif r < 0.33: words.append(6 << 13)
        elif r < 0.43:
            words.append(common.ROM_BASE + 2 * (len(words) + 3))
            words.append(7 << 13 | rng.getrandbits(1) << 12 | rng.choice(COMPS) << 6 | rng.getrandbits(3) << 3 | rng.randrange(1, 8))
            words.append(7 << 13 | rng.getrandbits(1) << 12 | rng.choice(COMPS) << 6 | rng.getrandbits(3) << 3)
        else: words.append(7 << 13 | rng.getrandbits(1) << 12 | rng.choice(COMPS) << 6 | rng.getrandbits(3) << 3)
    words += [common.ROM_BASE + 2 * len(words), 7 << 13 | 0b101010 << 6 | 7]
    return b''.join(bytes([w & 255, w >> 8]) for w in words)

os.system(f'python3 {HERE}/../tools/asm.py -o {HERE}/_asm {HERE}/../examples/demo.asm > /dev/null')
img = open(f'{HERE}/_asm/rom.bin', 'rb').read(); ok = True
r = ML.run_flat(c1, img, f1.W); print('demo', r); ok &= r == (131, 336)
rr = random.Random(11); bad = 0
for k in range(30):
    im = gen(rr, 40); ri = bytes(rr.getrandbits(8) for _ in range(f1.W))
    try: ML.run_flat(c1, im, f1.W, ram_init=ri, max_instr=400)
    except AssertionError as e: bad += 1; print('  ', k, e)
print(f'random programs: {30 - bad}/30 in lockstep')
print('PASS' if ok and not bad else 'FAIL'); sys.exit(0 if ok and not bad else 1)
