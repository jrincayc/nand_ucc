#!/usr/bin/env python3
"""chk_full.py PREFIX [OX OY] -- load PREFIX.build in rndp, compare every dumped pin's world net to the expected key (PREFIX.keys.json)."""
import sys, json, subprocess, collections, time
pre = sys.argv[1]; OX, OY = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (260, 40)
RNDP = '/home/claude/rndp/target/release/rndp'
t0 = time.time()
r = subprocess.run([RNDP, '--build', pre + '.build', '--rom', 'off', '--ram', 'off', '--layers', '2', '--width', '2048', '--height', '8192', '--steps', '0', '--dump-pads', pre + '.pads'], capture_output=True, text=True)
o = r.stdout + r.stderr
print('\n'.join(l for l in o.splitlines() if any(k in l for k in ('build:', 'faults', 'bounding', 'segments', 'nets', 'refused', 'error', 'rror'))), f'({time.time()-t0:.0f}s)')
ex = {(x, y): tuple(k) for x, y, k in json.load(open(pre + '.keys.json'))}
worlds = collections.defaultdict(set); logical = collections.defaultdict(set); unm = 0; seen = set()
for l in open(pre + '.pads'):
    pi, kind, pin, x, y, net = l.split(); k = (int(x) - OX, int(y) - OY)
    key = ex.get(k)
    if key is None: unm += 1; print('unmapped', kind, pin, k) if unm < 6 else None; continue
    seen.add(k); worlds[int(net)].add(key); logical[key].add(int(net))
opens = {n: s for n, s in logical.items() if len(s) > 1}; shorts = {n: s for n, s in worlds.items() if len(s) > 1}
print(f'expected pins {len(ex)} dumped-and-mapped {len(seen)} unmapped {unm} opens {len(opens)} shorts {len(shorts)}')
miss = [k for k in ex if k not in seen]; print('expected but not dumped', len(miss), miss[:5])
for n, s in list(opens.items())[:5]: print('OPEN', n, sorted(s)[:8])
for n, s in list(shorts.items())[:5]: print('SHORT', n, sorted(s, key=str)[:8])
