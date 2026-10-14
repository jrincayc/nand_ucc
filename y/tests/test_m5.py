#!/usr/bin/env python3
"""test_m5.py -- M5 integration: the assembly builder with the improver (src/builder.asm + src/improver.asm) builds the IMPROVED child.
g0 (seed HD) -> run -> arm writes; expected = ref_flatten.commands(flatten(improved HD), image of the improved machine).
g1 (improved HD) -> run -> the same machine again (fixed point).  RAM is 256 bytes preloaded with random bytes."""
import os, sys, random, tempfile, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
for d in ('tools', 'isa', 'tests', '.'):
    sys.path.insert(0, os.path.join(HERE, '..', d))
import run_builder as RB, hd as HDM, ref_flatten as RF, isahack as H, hd2asm, ref_improve as RI
from machine_lockstep import MR

ROOT = os.path.join(HERE, '..'); fails = []
SRC = [os.path.join(ROOT, 'src', f) for f in ('macros.asm', 'ram.asm', 'builder.asm', 'improver.asm')]
def check(name, ok, extra=''):
    print(('PASS ' if ok else 'FAIL ') + name + (' ' + extra if extra else ''), flush=True)
    if not ok: fails.append(name)

def image_of(hd, tag):
    out = tempfile.mkdtemp(); data = os.path.join(out, tag + '_data.asm')
    open(data, 'w').write(hd2asm.Enc(hd).encode().text())
    return RB.assemble(SRC + [data], out), out, SRC + [data]

def run(img, ramn=256, seed=7):
    m = MR(ramn); m.load_rom(0, img); rng = random.Random(seed); m.ram[:] = bytes(rng.getrandbits(8) for _ in range(ramn))
    hw = set(); orig = m.wr
    def wr(a, v):
        if a < ramn: hw.add(a)
        orig(a, v)
    m.wr = wr; cpu = H.CPU(m); n = 0
    while cpu.step(): n += 1
    return RB.decode_arm(m.armlog), n, max(hw)

def seed_hd(ra):
    hd = __import__('hd_export').build_hd(ra); return hd[0] if isinstance(hd, tuple) else hd

cases = [('seed r5', 5, False), ('improved r5', 5, True), ('seed r6', 6, False)]
if '--big' in sys.argv: cases += [('seed r7', 7, False), ('improved r7', 7, True), ('seed r8', 8, False), ('improved r8', 8, True)]
for tag, ra, imp in cases:
    hd = seed_hd(ra)
    if imp: hd = RI.improve_hd(hd)[0]
    g0img, out, srcs = image_of(hd, tag.replace(' ', '_'))
    child = RI.improve_hd(hd)[0]                        # what the improver must produce (a fixed point for improved input)
    g1img, _, _ = image_of(child, tag.replace(' ', '_') + '_child')
    ref = RF.commands(RF.flatten(child), g1img, 0, RF.STRIDE)
    c, n, hw = run(g0img)
    same = len(c) == len(set(c)) and set(c) == set(ref) and c[-3:] == ref[-3:]
    kinds = [x[0] for x in c]
    order = kinds.index('wire') > len(kinds) - 1 - kinds[::-1].index('rom') and kinds.index('rom') > kinds.index('place')
    check(f'{tag}: commands equal the reference for the improved child', same, f'{len(c)} commands, {n:,} instructions, image {len(g0img)} B; missing {len(set(ref) - set(c))}, extra {len(set(c) - set(ref))}')
    check(f'{tag}: every PROGRAM_ROM precedes the first WIRE', order)
    check(f'{tag}: RAM high-water mark below 256', hw < 256, f'(highest byte written {hw})')
    tc = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'trace_check.py'), out] + srcs, capture_output=True, text=True)
    check(f'{tag}: trace_check passes', tc.returncode == 0, tc.stdout.strip().splitlines()[-1] if tc.stdout.strip() else tc.stderr[-200:])
    if imp: check(f'{tag}: fixed point (child image == own image)', g1img == g0img)
print('FAILED: ' + ', '.join(fails) if fails else 'ALL M5 INTEGRATION TESTS PASSED'); sys.exit(1 if fails else 0)
