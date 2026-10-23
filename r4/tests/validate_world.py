#!/usr/bin/env python3
"""validate_world.py NL BUILD PADS [SEED] -- S6: the world rndp built from the emulator's arm commands (BUILD, offset 32) must have exactly the netlist's connectivity.
PADS = rndp --dump-pads output.  Part k (k-th 'place' of kind NAND/DFF) is node k (route_ref emits places in node order).  For every node pin the rndp net must equal the net of
its driver (outputs: own net); two different expected keys on one net = SHORT, one key on two nets = OPEN.  ROM/RAM/ARM pins are not mapped (limitation)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools')]
import lay
nl = lay.read_nl(sys.argv[1]); seed = int(sys.argv[4]) if len(sys.argv) > 4 else 1
OFS = 32
parts = [l.split() for l in open(sys.argv[2]) if l.startswith('place')]
parts = [(int(p[1]), int(p[2]) - OFS, int(p[3]) - OFS) for p in parts if p[1] in ('0', '1')]
assert len(parts) == len(nl.nodes), (len(parts), len(order), len(nl.nodes))
ex = {}
for (k, x, y), o in zip(parts, range(len(parts))):
    kind, ins = nl.nodes[o]
    assert (k == 1) == (kind == 'D'), ('kind mismatch', o, kind, k)
    ex[(x + 1, y)] = ('n', o)
    for p, s in enumerate(ins):
        ex[(x, y + p)] = ('open', o, p) if s == 'open' else lay.key(s)
netkeys = {}; keynets = {}; unm = 0; n = 0
for l in open(sys.argv[3]):
    pi, kind, pin, x, y, net = l.split(); k = ex.get((int(x) - OFS, int(y) - OFS))
    if kind in ('ARM', 'ROM', 'RAM'): continue
    if k is None: unm += 1; continue
    n += 1; netkeys.setdefault(int(net), set()).add(k); keynets.setdefault(k, set()).add(int(net))
bad = 0
for net, ks in netkeys.items():
    if len(ks) > 1:
        bad += 1
        if bad < 10: print('SHORT net', net, sorted(ks, key=str)[:5])
for k, ns in keynets.items():
    if len(ns) > 1 and k[0] not in ('rom', 'ramo'):
        bad += 1
        if bad < 10: print('OPEN', k, sorted(ns)[:5])
print(f'node pins checked {n}, nets {len(netkeys)}, unmapped pins {unm}, problems {bad}'); sys.exit(1 if bad or unm else 0)
