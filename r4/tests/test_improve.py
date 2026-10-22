#!/usr/bin/env python3
"""test_improve.py -- M2: run the normative improver (ref_improve.py) over the module seed HD.
Checks: every improved module computes the same truth tables (asserted inside improve_hd), improving the improved HD changes nothing
(fixed point), the improved HD flattens, and its gate counts are reported.  The tick-for-tick lockstep is run with
CPU_HD=hd/cpu_mod_improved.hd python3 tests/gate_vs_rtl.py."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools')]
import hd as hdlib, hdflat, ref_improve
HD = os.path.join(HERE, '..', 'hd', os.environ.get('HDDIR', '')); src = os.path.join(HD, 'cpu_mod.hd'); dst = os.path.join(HD, 'cpu_mod_improved.hd')
h0 = hdlib.read(open(src).read()); h1, rep = ref_improve.improve_hd(h0)
open(dst, 'w').write(hdlib.write(h1))
for r in rep: print('%-5s %3d -> %3d NAND' % r[:3])
h1r = hdlib.read(open(dst).read()); assert hdlib.write(h1r) == open(dst).read(), 'write(read(x)) != x'
h2, rep2 = ref_improve.improve_hd(h1r)
fixed = all(a == b for _, a, b, _ in rep2) and hdlib.write(h2) == hdlib.write(h1r)
print('fixed point (improving the improved HD changes nothing):', fixed)
def count(h):
    F, _ = hdflat.flatten(h)
    return sum(1 for k in F.kind[2:] if k[0] == 'nand'), sum(1 for k in F.kind[2:] if k[0] == 'dff')
n0, d0 = count(h0); n1, d1 = count(h1r)
print(f'seed {n0} NAND + {d0} DFF  ->  improved {n1} NAND + {d1} DFF  (saved {n0 - n1}, {100 * (n0 - n1) / n0:.1f}%)')
ok = fixed and d0 == d1
print('RESULT', 'PASS' if ok else 'FAIL'); sys.exit(0 if ok else 1)
