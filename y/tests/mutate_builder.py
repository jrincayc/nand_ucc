#!/usr/bin/env python3
"""mutate_builder.py -- mutation check of the builder: single-field changes to random instructions of src/builder.asm's image;
a mutant is KILLED if the decoded command set differs from the reference (or the run crashes / does not halt in time).
usage: mutate_builder.py N [seed]"""
import os, sys, random, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
for d in ('tools', 'isa', 'tests', '.'):
    sys.path.insert(0, os.path.join(HERE, '..', d))
import run_builder as RB, hd as HDM, ref_flatten as RF, isahack as H, hd2asm
from machine_lockstep import MR

ROOT = os.path.join(HERE, '..')
hd = HDM.read(open(os.path.join(ROOT, 'hd', 'core.hd')).read())
out = tempfile.mkdtemp(); data = os.path.join(out, 'd.asm'); open(data, 'w').write(hd2asm.Enc(hd).encode().text())
img = RB.assemble([os.path.join(ROOT, 'src', 'macros.asm'), os.path.join(ROOT, 'src', 'builder.asm'), data], out)
ref = set(RF.commands(RF.flatten(hd), img, 0, RF.STRIDE))
code_end = int(open(os.path.join(out, 'symbols.txt')).read().split('hd_header = ')[1].split()[0]) - 0x2000 if False else 0x1000
n, seed = int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 1
rng = random.Random(seed); killed = 0; surv = []
for t in range(n):
    im = bytearray(img)
    while True:
        a = rng.randrange(0, code_end, 2); w = im[a] | im[a + 1] << 8
        if w == 0: continue
        if w >> 15 == 0:                                   # A-instruction: change the value by +-1 or flip a low bit
            nw = (w ^ (1 << rng.randrange(0, 8))) & 0x7FFF
        elif w >> 13 == 7:                                 # C-instruction: flip one bit of comp, dest or jump
            nw = w ^ (1 << rng.choice(list(range(0, 12))))
        else: continue
        if nw != w: break
    im[a], im[a + 1] = nw & 255, nw >> 8
    m = MR(128); m.load_rom(0, bytes(im)); cpu = H.CPU(m); cnt = 0; why = ''
    try:
        while cnt < 8_000_000:
            if not cpu.step(): break
            cnt += 1
        else: why = 'no halt'
        if not why:
            why = '' if set(RB.decode_arm(m.armlog)) == ref and len(RB.decode_arm(m.armlog)) == len(ref) else 'output differs'
    except Exception as e: why = 'crash ' + type(e).__name__
    if why: killed += 1
    else: surv.append((hex(0x2000 + a), hex(w), hex(nw)))
    print(f'mutant {t}: addr {0x2000 + a:#x} {w:#06x} -> {nw:#06x}: {"killed (" + why + ")" if why else "SURVIVED"}', flush=True)
print(f'{killed}/{n} killed; survivors: {surv}')
