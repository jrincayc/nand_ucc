#!/usr/bin/env python3
"""test_hd_seed.py -- HD round trip: export the module seed, read it back, flatten it with hdflat and require the result to be
gate-for-gate identical to ModNet.flatten(); also read/write is a fixed point."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools')]
import hdmod_export, hdflat, hd as hdlib
out = os.path.join(HERE, '..', 'hd', 'cpu_mod.hd')
m, ports, state, roots = hdmod_export.export(out)
text = open(out).read(); h = hdlib.read(text)
assert hdlib.write(h) == text, 'HD write(read(x)) != x'
F, fports, fstate = m.flatten(roots, ports, state)
G, gports = hdflat.flatten(h)
ok = F.kind == G.kind and fports == gports
byt, fl, dff, gates = m.counts(roots)
print(f'body {len(h.body)} instances; flatten: {sum(1 for k in G.kind[2:] if k[0] == "nand")} NAND {sum(1 for k in G.kind[2:] if k[0] == "dff")} DFF; HD flatten == ModNet flatten: {ok}')
print('RESULT', 'PASS' if ok else 'FAIL'); sys.exit(0 if ok else 1)
