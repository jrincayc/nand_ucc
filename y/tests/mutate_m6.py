#!/usr/bin/env python3
"""mutate_m6.py -- mutation check of the whole ROM program (builder + improver) on the seed r5 build.
Only instructions that the clean run executes are mutated (a never-executed word cannot change a run).  A mutant is KILLED when its
arm-register write log differs from the clean run's log (checked online: the run is aborted at the first difference), it crashes, or it
does not halt within twice the clean instruction count.  usage: mutate_m6.py N [seed]"""
import os, sys, random, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
for d in ('tools', 'isa', 'tests', '.'):
    sys.path.insert(0, os.path.join(HERE, '..', d))
import run_builder as RB, hd as HDM, ref_flatten as RF, isahack as H, hd2asm, common
from machine_lockstep import MR

ROOT = os.path.join(HERE, '..')
hd = HDM.read(open(os.path.join(ROOT, 'hd', 'core.hd')).read())
out = tempfile.mkdtemp(); data = os.path.join(out, 'd.asm'); open(data, 'w').write(hd2asm.Enc(hd).encode().text())
img = RB.assemble([os.path.join(ROOT, 'src', f) for f in ('macros.asm', 'ram.asm', 'builder.asm', 'improver.asm')] + [data], out)

def fresh():
    m = MR(256); m.load_rom(0, img); return m

# clean run: the arm log and the set of executed instruction addresses
m = fresh(); cpu = H.CPU(m); seen = set(); cnt = 0
while True:
    seen.add(cpu.pc)
    if not cpu.step(): break
    cnt += 1
clean = list(m.armlog); words = sorted(a - common.ROM_BASE for a in seen if 0 <= a - common.ROM_BASE < len(img) - 1)
print(f'clean run: {cnt:,} instructions, {len(clean)} arm writes, {len(words)} distinct executed words', flush=True)

n, seed = int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 1
rng = random.Random(seed); killed = 0; surv = []
for t in range(n):
    im = bytearray(img)
    while True:
        a = rng.choice(words); w = im[a] | im[a + 1] << 8
        if w >> 15 == 0: nw = (w ^ (1 << rng.randrange(0, 8))) & 0x7FFF      # A-instruction: flip a low bit of the value
        elif w >> 13 == 7: nw = w ^ (1 << rng.randrange(0, 12))               # C-instruction: flip one bit of comp / dest / jump
        else: continue
        if nw != w: break
    im[a], im[a + 1] = nw & 255, nw >> 8
    m = MR(256); m.load_rom(0, bytes(im)); cpu = H.CPU(m); c = 0; why = ''
    ow = m.wr; k = [0]
    class Diff(Exception): pass
    def wr(ad, v, ow=ow, m=m):
        ow(ad, v)
        if common.ARM_BASE <= (ad & common.AMASK) < common.ROM_BASE:
            i = len(m.armlog) - 1
            if i >= len(clean) or m.armlog[i] != clean[i]: raise Diff()
    m.wr = wr
    try:
        while c < 2 * cnt:
            if not cpu.step(): break
            c += 1
        else: why = 'no halt'
        if not why and m.armlog != clean: why = 'log differs'
    except Diff: why = 'log differs'
    except Exception as e: why = 'crash ' + type(e).__name__
    if why: killed += 1
    else: surv.append((hex(common.ROM_BASE + a), hex(w), hex(nw)))
    print(f'mutant {t}: addr {common.ROM_BASE + a:#x} {w:#06x} -> {nw:#06x}: {"killed (" + why + ")" if why else "SURVIVED"}', flush=True)
print(f'{killed}/{n} killed; survivors: {surv}')
