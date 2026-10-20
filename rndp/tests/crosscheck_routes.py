#!/usr/bin/env python3
"""Cross-check the Rust simulator's connectivity against the netlist, using router output.

usage: crosscheck_routes.py CORE_BODY_HD routes.json RNDP_BINARY WORKDIR
Converts routes.json (from nandgen/rndp/analysis/slice_router.py or glue_router.py) into an rndp-state
file (NAND parts + segments + vias), loads it in the simulator, dumps pad net ids, and checks that two
pads share a simulator net iff they share a netlist net.  Router bookkeeping is never consulted.
"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, '/home/claude/rndp_analysis')
import analyze_hd_routing as A

core, jpath, binp, work = sys.argv[1:5]
os.makedirs(work, exist_ok=True)
d = json.load(open(jpath))
gates = {g[0]: g for g in A.expand(*A.parse(core)[:2])}
lines = ['rndp-state 1', f'cfg {max(d["W"],16)} {max(d["H"],16)} {d["L"]} 1 1 16 16 5000000', 'tick 0']
gid_idx = {}
for i, g in enumerate(d['gates']):
    gid_idx[g['gid']] = i
    lines.append(f'part {i} 0 {g["origin"][0]} {g["origin"][1]} 0 0')
for n in d['nets']:
    for (l, x1, y1, x2, y2) in n['segs']:
        lines.append(f'seg {l} {x1} {y1} {x2} {y2}')
    for (x, y) in n['vias']:
        lines.append(f'via {x} {y}')
st = os.path.join(work, 'routes.state')
open(st, 'w').write('\n'.join(lines) + '\n')
pads = os.path.join(work, 'pads.txt')
p = subprocess.run([binp, '--world', st, '--dump-pads', pads], capture_output=True, text=True)
if p.returncode:
    print('simulator refused the layout:\n', p.stdout, p.stderr); sys.exit(1)
print(p.stdout.split('\n')[0:0] or '', end='')
pin_name = {'in0': '0', 'in1': '1', 'out0': 'Y'}
sim_net, nl_net = {}, {}
for ln in open(pads):
    pi, kind, nm, x, y, net = ln.split()
    gid = d['gates'][int(pi)]['gid']
    g = gates[gid]
    key = (gid, pin_name[nm])
    sim_net[key] = int(net)
    nl_net[key] = {'0': g[2][0], '1': g[2][1], 'Y': g[3]}[pin_name[nm]]
from collections import defaultdict
by_sim, by_nl = defaultdict(set), defaultdict(set)
for k in sim_net:
    by_sim[sim_net[k]].add(nl_net[k]); by_nl[nl_net[k]].add(sim_net[k])
shorts = {s: v for s, v in by_sim.items() if len(v) > 1}
opens = {n: v for n, v in by_nl.items() if len(v) > 1}
print(f'{len(sim_net)} pads, {len(by_nl)} netlist nets, {len(by_sim)} simulator nets; shorts {len(shorts)}, opens {len(opens)}')
for s, v in list(shorts.items())[:5]: print('  SHORT', sorted(v))
for n, v in list(opens.items())[:8]: print('  OPEN', n, len(v), 'pieces')
sys.exit(1 if shorts or opens else 0)
