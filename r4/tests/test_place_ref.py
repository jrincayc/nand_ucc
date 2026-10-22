#!/usr/bin/env python3
"""test_place_ref.py -- normative integer placement (tools/place_ref.py, no inherited order: gate numbers randomly permuted) -> serpentine fold ->
row-and-channel layout (R=22, Z=14) -> build in rndp (no shorts / opens); also checks determinism."""
import os, random, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools'), HERE]
import lay, rowchan, place_ref, validate_layout as V
nl = lay.read_nl(os.environ.get('NL', os.path.join(HERE, '..', 'hd', 'cpu_g1.nl'))); N = len(nl.nodes); R = 22
perm = list(range(N)); random.Random(12).shuffle(perm)
def rn(t):
    m = re.match(r'^n(\d+)(.*)$', t); return f'n{perm[int(m.group(1))]}{m.group(2)}' if m else t
new = [None] * N
for k, (kind, ins) in enumerate(nl.nodes): new[perm[k]] = (kind, [rn(t) for t in ins])
nl.nodes = new; nl.ports = [(n, rn(t)) for n, t in nl.ports]
o = place_ref.order(nl, seed=1); assert o == place_ref.order(nl, seed=1) and sorted(o) == list(range(N))
cols = -(-N // R); rc = [None] * N
for rank, k in enumerate(o): r = rank // cols; j = rank % cols; rc[k] = (r, cols - 1 - j if r % 2 else j)
text, st = rowchan.layout(nl, R, 14, rc); open('/tmp/test_place_ref.lay', 'w').write(text)
print(f'board {st["W"]} x {st["H"]} = {st["area"]} cells')
bad = V.check(nl, lay.read_lay('/tmp/test_place_ref.lay'), quiet=True); print('RESULT', 'PASS' if not bad else 'FAIL'); sys.exit(1 if bad else 0)
