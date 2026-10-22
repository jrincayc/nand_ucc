#!/usr/bin/env python3
"""test_strip.py -- M3 pipeline check: seed HD (ordered) -> improver -> g1 HD -> netlist -> strip layout -> build in rndp (no shorts / opens),
for the unimproved seed g0 and the improved g1; prints the board sizes."""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); T = os.path.join(HERE, '..', 'tools'); sys.path[:0] = [T, HERE]
import hd as hdlib, hd2nl, strip, lay, ref_improve, validate_layout as V
os.environ.setdefault('ROM_BITS', '15')
seed = hdlib.read(open(os.path.join(HERE, '..', 'hd', 'cpu_seed.hd')).read()); g1, _ = ref_improve.improve_hd(seed)
assert hdlib.write(g1) == open(os.path.join(HERE, '..', 'hd', 'cpu_g1.hd')).read(), 'hd/cpu_g1.hd is not the improver output for hd/cpu_seed.hd'
bad = 0
for name, h in (('g0 (seed)', seed), ('g1 (improved)', g1)):
    text, n = hd2nl.convert(h); p = f'/tmp/test_strip_{name[:2]}'
    open(p + '.nl', 'w').write(text); nl = lay.read_nl(p + '.nl')
    lt, st = strip.layout(nl); open(p + '.lay', 'w').write(lt)
    print(f'{name}: {n} nodes, board {st["W"]} x {st["H"]} = {st["area"]} cells, {st["tracks"]} tracks, {st["nets"]} nets')
    bad += V.check(nl, lay.read_lay(p + '.lay'), quiet=True)
print('RESULT', 'PASS' if not bad else 'FAIL'); sys.exit(1 if bad else 0)
