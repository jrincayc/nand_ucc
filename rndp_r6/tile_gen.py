#!/usr/bin/env python3
"""R6 RAM tile: one 8-bit word (58 gates: 8 DFF + 50 NAND), placed by a fixed rule and routed ONCE with the R5 mrouter; the result is a pattern replicated by translation
(ramblock_gen.py).  Inputs: WE, SEL, DIN0-7 (left-edge pads), CI0-7 (top-edge pads, chain from the previous tile); outputs CO0-7 (bottom-edge pads) = inverted OR chain.
usage: tile_gen.py OUT.json"""
import sys, json, subprocess, collections
OUT = sys.argv[1]
PITCH = int(sys.argv[2]) if len(sys.argv) > 2 else 6
gates = []      # (kind 'N'|'D', ins, x, y, name)
nets = collections.OrderedDict()
def net(n): return nets.setdefault(n, dict(drv=None, sinks=[]))
pads = {}
def add(kind, ins, x, y, name):
    gates.append((kind, ins, x, y, name))
    net(name)['drv'] = (x + 1, y, 0); pads[(x + 1, y)] = name
    for p, s in enumerate(ins):
        net(s)['sinks'].append((x, y + p, 0)); pads[(x, y + p)] = s
        if kind == 'D': break
X = [12 + 5 * i for i in range(7)]
y0 = 6
add('N', ['WE', 'SEL'], X[0], 2, 'g0'); add('N', ['g0', 'g0'], X[1], 2, 'g1')
for b in range(8):
    y = y0 + PITCH * b
    add('D', ['g7_%d' % b], X[0], y, 'q%d' % b)
    add('N', ['q%d' % b, 'g0'], X[1], y, 'g5_%d' % b)
    add('N', ['DIN%d' % b, 'g1'], X[2], y, 'g6_%d' % b)
    add('N', ['g5_%d' % b, 'g6_%d' % b], X[3], y, 'g7_%d' % b)
    add('N', ['SEL', 'q%d' % b], X[4], y, 'g8_%d' % b)
    add('N', ['CI%d' % b, 'g8_%d' % b], X[5], y, 'g9_%d' % b)
    add('N', ['g9_%d' % b, 'g9_%d' % b], X[6], y, 'CO%d' % b)
H = y0 + PITCH * 8 + 2; W = X[6] + 8
ports = {}
ext_rows = {'WE': 1, 'SEL': 3}
for b in range(8): ext_rows['DIN%d' % b] = 5 + b
for n, r in ext_rows.items():
    ports[n] = (2, r); net(n)['drv'] = (2, r, 0); pads[(2, r)] = n
# left ports are rows 1,3,5..12: distinct rows; din rows 5..12 ; keep them out of gate region (gates start at x=12)
for b in range(8):
    xc = X[1] + 4 * b + 0
    ports['CI%d' % b] = (xc, 0); net('CI%d' % b)['drv'] = (xc, 0, 0); pads[(xc, 0)] = 'CI%d' % b
    ports['CO%d' % b] = (xc, H - 1); net('CO%d' % b)['sinks'].append((xc, H - 1, 0)); pads[(xc, H - 1)] = 'CO%d' % b
ids = {n: i for i, n in enumerate(nets)}
prob = [f'grid 0 0 {W} {H}']
for (x, y), n in pads.items(): prob.append(f'pad {x} {y} {ids[n]}')
for n, d in nets.items():
    if not d['sinks']: continue
    prob.append(f'net {ids[n]} {len(d["sinks"])}'); prob.append('d %d %d %d' % d['drv'])
    for s in d['sinks']: prob.append('s %d %d %d' % s)
open('/tmp/tile.prob', 'w').write('\n'.join(prob) + '\n')
r = subprocess.run(['/home/claude/r5/e4/mrouter/mrouter', '/tmp/tile.prob', '/tmp/tile.out', '--iters', '80'], capture_output=True, text=True)
print(r.stderr[-200:])
trk = []; vias = []; fails = 0
for l in open('/tmp/tile.out'):
    t = l.split()
    if t[2] == 'FAIL': fails += 1
    elif t[2] == 'T': trk.append([int(t[4]), int(t[5]), int(t[6]), int(t[7]), int(t[8])])
    elif t[2] == 'V': vias.append([int(t[4]), int(t[5])])
print(f'tile {W}x{H}, {len(gates)} gates, fails {fails}, {len(trk)} tracks, {len(vias)} vias')
json.dump(dict(W=W, H=H, gates=[[k, i, x, y, n] for k, i, x, y, n in gates], tracks=trk, vias=vias, ports=ports, fails=fails), open(OUT, 'w'))
