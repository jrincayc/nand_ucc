#!/usr/bin/env python3
"""check_plane.py PLANE_JSON PADS -- every pin the generator declared must sit on the world net its logical net implies (no shorts, no opens); pins not declared must be unmapped."""
import sys, json
from plane import logical_nets
d = json.load(open(sys.argv[1])); pins = logical_nets(d['bits'], d['X0'], d['Y0'])
net_of = {}; lognets = {}; worldnets = {}; unm = 0
for l in open(sys.argv[2]):
    pi, kind, pin, x, y, net = l.split(); k = (int(x), int(y))
    if k not in pins: unm += 1; print('undeclared pin', kind, pin, k, 'net', net); continue
    lognets.setdefault(pins[k], set()).add(int(net)); worldnets.setdefault(int(net), set()).add(pins[k])
seen = {k for k in pins}; got = {(int(l.split()[3]), int(l.split()[4])) for l in open(sys.argv[2])}
missing = [k for k in seen if k not in got]
opens = {n: s for n, s in lognets.items() if len(s) > 1}; shorts = {n: s for n, s in worldnets.items() if len(s) > 1 and not (len(s) == 1)}
for n, s in list(opens.items())[:8]: print('OPEN', n, sorted(s))
for n, s in list(shorts.items())[:8]: print('SHORT world net', n, sorted(s))
print(f'declared {len(pins)} pin cells, dumped {len(got)}, missing {len(missing)}, undeclared {unm}, opens {len(opens)}, shorts {len(shorts)}')
sys.exit(1 if (opens or shorts or missing or unm) else 0)
