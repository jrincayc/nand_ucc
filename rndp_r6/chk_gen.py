#!/usr/bin/env python3
"""chk_gen.py BUILD -- load plane_gen output in rndp; every gate pin must lie on the world net of its logical net (no opens, no shorts)."""
import sys, json, subprocess, collections
bf = sys.argv[1]; RNDP = '/home/claude/rndp/target/release/rndp'; OX = OY = 8
lines = []
for l in open(bf):
    t = l.split()
    if t[0] == 'place': lines.append(f'place {t[1]} {int(t[2])+OX} {int(t[3])+OY} {t[4]} {t[5]}')
    elif t[0] == 'track': lines.append(f'track {t[1]} {int(t[2])+OX} {int(t[3])+OY} {int(t[4])+OX} {int(t[5])+OY}')
    else: lines.append(f'via {int(t[1])+OX} {int(t[2])+OY}')
open(bf + '.sh', 'w').write('\n'.join(lines) + '\n')
r = subprocess.run([RNDP, '--build', bf + '.sh', '--rom', 'off', '--ram', 'off', '--layers', '2', '--width', '4096', '--height', '8192', '--steps', '0', '--dump-pads', bf + '.pads'], capture_output=True, text=True)
o = r.stdout + r.stderr
print('\n'.join(l for l in o.splitlines() if any(k in l for k in ('build:', 'faults', 'bounding', 'segments', 'nets', 'refused', 'error'))))
pins = {(x, y): n for x, y, n in json.load(open(bf + '.pins.json'))['pins']}
worlds = collections.defaultdict(set); logical = collections.defaultdict(set); bad = 0
for l in open(bf + '.pads'):
    pi, kind, pin, x, y, net = l.split(); k = (int(x) - OX, int(y) - OY)
    if k not in pins: bad += 1; continue
    worlds[int(net)].add(pins[k]); logical[pins[k]].add(int(net))
opens = {n: s for n, s in logical.items() if len(s) > 1}; shorts = {n: s for n, s in worlds.items() if len(s) > 1}
print(f'pins {len(pins)} dumped {sum(len(v) for v in logical.values())} undeclared {bad} opens {len(opens)} shorts {len(shorts)}')
for n, s in list(opens.items())[:3]: print('OPEN lognet', n, sorted(s)[:6])
for n, s in list(shorts.items())[:3]: print('SHORT world', n, sorted(s)[:6])
