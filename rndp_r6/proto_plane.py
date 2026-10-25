#!/usr/bin/env python3
"""R6 prototype: strip-placed grid ROM plane for a random ROM, routed with the R5 mrouter.  usage: proto_plane.py R C seed MODE(slot|pack) [pitch]
Gates: NAND pads A(x,y) B(x,y+1) Y(x+1,y).  Signals: hi[h] (driver pad at strip left edge), lo[l] (driver pad at bottom edge), 8 outputs (sink pads at top edge)."""
import sys, random, subprocess, collections, os
R, C, seed, MODE = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
P = int(sys.argv[5]) if len(sys.argv) > 5 else 5
MODE0 = MODE
rnd = random.Random(seed)
def rbyte():
    if rnd.random() > 0.46: return 0
    while True:
        b = sum(1 << j for j in range(8) if rnd.random() < 0.43)
        if b: return b
words = [rbyte() for _ in range(R * C)]
if os.environ.get('ROMFILE'):
    _d = open(os.environ['ROMFILE'], 'rb').read()[int(os.environ.get('OFFSET', '0')):]
    words = list(_d[:R * C]) + [0] * max(0, R * C - len(_d))
gates = []      # (name, ins[2] names), names: 'hi3','lo5' (external) or gate ids 'g12'
ext = set()
def G(a, b):
    gates.append((a, b)); return 'g%d' % (len(gates) - 1)
def NOT(a): return G(a, a)
strip_gates = collections.defaultdict(list)      # h -> list of (gate id, lane j or -1, l)
rowres = [[None] * 8 for _ in range(R)]
for h in range(R):
    for j in range(8):
        acc = None
        for l in range(C):
            if (words[h * C + l] >> j) & 1:
                w = cellout = None
                key = ('cell', h, l)
                if key not in globals().setdefault('_cells', {}):
                    _cells[key] = G('hi%d' % h, 'lo%d' % l); strip_gates[h].append((_cells[key], -1, l))
                w = _cells[key]
                if acc is None:
                    acc = G(w, w); strip_gates[h].append((acc, j, l))
                else:
                    t = NOT(acc); strip_gates[h].append((t, j, l)); acc = G(t, w); strip_gates[h].append((acc, j, l))
        rowres[h][j] = acc
outs = []
for j in range(8):
    acc = None
    for h in range(R):
        r = rowres[h][j]
        if r is None: continue
        if acc is None: acc = r
        else:
            nr = G(r, r); na = NOT(acc); acc = G(na, nr); strip_gates['col'].append((nr, j, h)); strip_gates['col'].append((na, j, h)); strip_gates['col'].append((acc, j, h))
    outs.append(acc)
ngate = len(gates)
band = {}
for h in range(R):
    k = 0
    for l in range(C):
        if words[h*C+l]: band[(h,l)] = k; k += 1
BL = (lambda h,l: band[(h,l)]) if MODE == 'cpack' else (lambda h,l: l)
if MODE == 'cpack': MODE = 'slot'
# ---- placement
pos = {}
X0 = 8; SW = 2 * P if MODE == 'slot' else P
STRIP = (1 + 8) * P + 2
colx = X0 + C * SW + 2 * P if MODE == 'slot' else None
for h in range(R):
    base = 2 + h * STRIP
    if MODE == 'slot':
        for g, j, l in strip_gates[h]:
            if j < 0: pos[g] = (X0 + BL(h,l) * SW, base)
            else:
                # first gate of a pair at slot x, second at +P : NOT before NAND; first-ones' NOT-less 'acc' sits at slot x
                pos[g] = (0, 0)
    else:
        nxt = [0] * 9
        for g, j, l in strip_gates[h]:
            if j < 0: pos[g] = (X0 + l * P, base)
            else:
                k = nxt[j]; nxt[j] += 1; pos[g] = (X0 + k * P, base + (1 + j) * P)
if MODE == 'slot':
    # fix overlaps: gates in the same lane/strip with the same l: place sequentially by (l, idx)
    used = collections.defaultdict(int)
    for h in range(R):
        for g, j, l in strip_gates[h]:
            if j < 0: continue
            k = used[(h, j, l)]; used[(h, j, l)] += 1
            pos[g] = (X0 + BL(h,l) * SW + k * P, 2 + h * STRIP + (1 + j) * P)
# column reduction gates: stacked at the right, one lane per bit
NB = (max(band.values()) + 1 if MODE0 == 'cpack' else C)
cx0 = X0 + (NB * SW if MODE == 'slot' else max(len(strip_gates[h]) for h in range(R)) * P) + 3 * P
nxtc = collections.defaultdict(int)
for g, j, h in strip_gates['col']:
    k = nxtc[j]; nxtc[j] += 1; pos[g] = (cx0 + j * P, 2 + k * P)
W = max(x for x, y in pos.values()) + 8 + 4 * P; Hh = max(max(y for x, y in pos.values()), 2 + R * STRIP) + 8 + 2 * P
# ---- nets
nets = collections.OrderedDict(); pads = {}
def net(n): return nets.setdefault(n, dict(drv=None, sinks=[]))
for g, (a, b) in enumerate(gates):
    x, y = pos['g%d' % g]
    net('g%d' % g)['drv'] = (x + 1, y, 0); pads[(x + 1, y)] = 'g%d' % g
    for p, s in enumerate((a, b)):
        if p == 1 and b == a: continue                 # both pins of a NOT tie to the same net: sink both
        pass
    for p, s in enumerate((a, b)):
        net(s)['sinks'].append((x, y + p, 0)); pads[(x, y + p)] = s
for h in range(R): net('hi%d' % h)['drv'] = (0, 2 + h * STRIP + 1, 1); pads[(0, 2 + h * STRIP + 1)] = 'hi%d' % h
LX = (lambda l: X0 + l * P) if MODE0 == 'cpack' else (lambda l: X0 + l * SW)
for l in range(C): net('lo%d' % l)['drv'] = (LX(l), 0, 1); pads[(LX(l), 0)] = 'lo%d' % l
for j in range(8):
    if outs[j] is not None:
        net(outs[j])['sinks'].append((cx0 + j * P, Hh - 2, 0)); pads[(cx0 + j * P, Hh - 2)] = outs[j]
for n in list(nets):
    if nets[n]['drv'] is None: raise SystemExit('undriven ' + n)
ids = {n: i for i, n in enumerate(nets)}
prob = [f'grid 0 0 {W} {Hh}']
for (x, y), n in pads.items(): prob.append(f'pad {x} {y} {ids[n]}')
for n, d in nets.items():
    if not d['sinks']: continue
    prob.append(f'net {ids[n]} {len(d["sinks"])}'); prob.append('d %d %d %d' % d['drv'])
    for s in d['sinks']: prob.append('s %d %d %d' % s)
tag = f'proto_{R}_{C}_{seed}_{MODE0}'
open(f'/tmp/{tag}.prob', 'w').write('\n'.join(prob) + '\n')
print(f'{MODE} R={R} C={C} P={P}: {ngate} gates, ones={sum(bin(w).count("1") for w in words)}, grid {W} x {Hh} = {W*Hh} cells ({W*Hh/ngate:.0f}/gate), nets {len(nets)}', flush=True)
r = subprocess.run(['/home/claude/r5/e4/mrouter/mrouter', f'/tmp/{tag}.prob', f'/tmp/{tag}.out', '--iters', '60'], capture_output=True, text=True)
print(r.stderr[-300:])
fails = tr = vi = 0
for line in open(f'/tmp/{tag}.out'):
    t = line.split()
    if t[2] == 'FAIL': fails += 1
    elif t[2] == 'T': tr += abs(int(t[6]) - int(t[4])) + abs(int(t[7]) - int(t[5])) if False else abs(int(t[7]) - int(t[5])) + abs(int(t[8]) - int(t[6]))
    elif t[2] == 'V': vi += 1
print(f'fails {fails} track-steps {tr} ({tr/ngate:.1f}/gate) vias {vi}')
