#!/usr/bin/env python3
"""test_rowchan.py [R [Z [iters]]] -- g1 netlist -> 2-D refined placement (tools/refine.py) -> row-and-channel layout (tools/rowchan.py) -> build in rndp
(no shorts / opens); prints the board size.  Defaults R=22 Z=14 6M iterations (about 70 s)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools'), HERE]
import lay, rowchan, refine, validate_layout as V
R = int(sys.argv[1]) if len(sys.argv) > 1 else 22; Z = int(sys.argv[2]) if len(sys.argv) > 2 else 14; it = int(sys.argv[3]) if len(sys.argv) > 3 else 6000000
nl = lay.read_nl(os.path.join(HERE, '..', 'hd', 'cpu_g1.nl'))
rc, a, b = refine.refine(nl, R, iters=it, alpha=18.0, seed=2)
text, st = rowchan.layout(nl, R, Z, rc); open('/tmp/test_rowchan.lay', 'w').write(text)
print(f'board {st["W"]} x {st["H"]} = {st["area"]} cells, {st["tracks"]} track rows, {st["lanes"]} lane columns')
bad = V.check(nl, lay.read_lay('/tmp/test_rowchan.lay'), quiet=True); print('RESULT', 'PASS' if not bad else 'FAIL'); sys.exit(1 if bad else 0)
