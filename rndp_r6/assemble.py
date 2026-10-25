#!/usr/bin/env python3
"""assemble.py LAY NL PLANE.build RAM.build OUT_PREFIX -- whole R6-B board: R2c core (vp pins) + ROM plane + RAM block + formula interface wires.
Writes OUT.build (global coords, shifted by OFS) , OUT.keys.json (pin -> expected net key) and prints stats."""
import sys, json, collections, os
sys.path.insert(0, '/home/claude/c3/tools')
import lay
layf, nlf, planef, ramf, out = sys.argv[1:6]
OFS = tuple(int(v) for v in os.environ.get('OFS', '260,40').split(','))
L = lay.read_lay(layf); nl = lay.read_nl(nlf)
vp = {}
for line in open(layf):
    w = line.split()
    if w[0] == 'vp': vp[w[1]] = tuple(map(int, w[2:5]))        # S pinx0 pinrow
S, PX0, ROMROW = vp['rom']; _, _, RAMROW = vp['ram']
XP = lambda idx: PX0 + S * idx
CW_, CH_ = L.W, L.H
PX, PY = 292, 0                 # plane origin
MX, MY = -204, 304              # RAM block origin
B = []                          # global commands (kind, ...)
def trk(l, x0, y0, x1, y1):
    if (x0, y0) != (x1, y1): B.append(('track', l, x0, y0, x1, y1))
def via(x, y): B.append(('via', x, y))
# ---------------- core
for (x, y, k, o) in L.sites:
    if k != 'E': B.append(('place', 1 if k == 'D' else 0, x, y, 0, 0))
ax, ay, arot, aab = L.parts['arm']; B.append(('place', 3, ax, ay, arot, aab))
order = sorted(range(len(L.sinks)), key=lambda i: (L.sinks[i][1], i))
RUNB = []
for i in order:
    pts = L.sinks[i][3]
    for a, b in zip(pts, pts[1:]):
        tgt = RUNB if L.sinks[i][1] == 2 else B
        if a[2] == b[2]:
            if a[:2] != b[:2]: tgt.append(('track', a[2], a[0], a[1], b[0], b[1]))
        else: tgt.append(('via', a[0], a[1]))
ncore = len(B)
# ---------------- blocks
def load(path, ox, oy):
    n = 0
    for l in open(path):
        t = l.split()
        if t[0] == 'place': B.append(('place', int(t[1]), int(t[2]) + ox, int(t[3]) + oy, int(t[4]), int(t[5])))
        elif t[0] == 'track': B.append(('track', int(t[1]), int(t[2]) + ox, int(t[3]) + oy, int(t[4]) + ox, int(t[5]) + oy))
        else: B.append(('via', int(t[1]) + ox, int(t[2]) + oy))
load(planef, PX, PY); P = json.load(open(planef + '.pins.json'))
load(ramf, MX, MY); R = json.load(open(ramf + '.pins.json'))
nblk = len(B) - ncore
# ---------------- interface wires (each wire = list of ops; ('p',x,y) start, ('s',layer,x,y) segment to, ('v',) via at current point)
NA = nl.rom if hasattr(nl, 'rom') else 14
WIRES = []
class Wire:
    def __init__(s, x, y): s.ops = [('p', x, y)]; s.x, s.y = x, y; s.layer = None; WIRES.append(s)
    def v(s): s.ops.append(('v',)); s.layer = None if s.layer is None else 1 - s.layer; return s
    def go(s, l, x, y):
        if (x, y) != (s.x, s.y): s.ops.append(('s', l, x, y)); s.x, s.y = x, y
        return s
def flush(w):
    x, y = w.ops[0][1:]; lay_ = None
    for o in w.ops[1:]:
        if o[0] == 'v': via(x, y)
        else: trk(o[1], x, y, o[2], o[3]); x, y = o[2], o[3]
    via(*w.ops[0][1:]) if False else None
rows = {}
for i in range(14):
    m = i; x = XP(m); yr = -2 - m
    cx = PX + P['abitpos'][i][0]; cy = PY + P['abitpos'][i][1]
    (Wire(x, ROMROW).v().go(1, x, yr).v().go(0, cx, yr).v().go(1, cx, cy))
for j in range(8):
    m = 14 + j; x = XP(m); yr = -2 - m
    ox, oy = PX + P['outpos'][j][0], PY + P['outpos'][j][1]
    q = PX + P['size'][0] + 4 + 2 * j
    (Wire(ox, oy).go(0, q, oy).v().go(1, q, yr).v().go(0, x, yr).v().go(1, x, ROMROW).v())
for k in range(24): rows[k] = (XP(k), RAMROW + 3 + k)
for k in range(7):
    x, yr = rows[k]; cx = MX + R['ABPOS'][k][0]; cy = MY + R['ABPOS'][k][1]
    (Wire(x, RAMROW).v().go(1, x, yr).v().go(0, cx, yr).v().go(1, cx, cy))
for idx in range(9):
    x, yr = rows[7 + idx]; cx = MX + R['BUSPOS'][idx][0]; cy = MY + R['BUSPOS'][idx][1]
    (Wire(x, RAMROW).v().go(1, x, yr).v().go(0, cx, yr).v().go(1, cx, cy))
for c in range(8):
    x, yr = rows[16 + c]; px_, py_ = MX + R['DPOS'][c][0], MY + R['DPOS'][c][1]
    rail = MX + R['SIZE'][0] + 6 + 2 * c; ry = py_ + 3 + c
    (Wire(px_, py_).go(1, px_, ry).v().go(0, rail, ry).v().go(1, rail, yr).v().go(0, x, yr).v().go(1, x, RAMROW).v())
for w in WIRES:
    x, y = w.ops[0][1:]
    for o in w.ops[1:]:
        if o[0] == 'v': via(x, y)
        else: trk(o[1], x, y, o[2], o[3]); x, y = o[2], o[3]
# ---------------- expected keys
def key(s):
    s = s.split('@')[0]
    if s.startswith('ramo'): return ('ramo', int(s[4:]))
    if s.startswith('rom'): return ('rom', int(s[3:]))
    return ('n', int(s[1:]))
port = dict(nl.ports)
ex = {}
for (x, y, k, o) in L.sites:
    if k == 'E': continue
    kind, ins = nl.nodes[o]
    ex[(x + 1, y)] = ('n', o)
    for p, s in enumerate(ins): ex[(x, y + p)] = ('open', o, p) if s == 'open' else key(s)
for name, s in nl.ports:
    if name.startswith('rom_') or name.startswith('ram_'): continue
    ex[lay.port_cell(L, nl, name)] = key(s)
for i in range(4): ex.setdefault(lay.pcell(L, 'arm', 0, i), ('unusedarm', i))
ex.setdefault(lay.pcell(L, 'arm', 0, 4), ('unusedarm', 4))
for j in range(8): ex.setdefault(lay.pcell(L, 'arm', 1, j), ('unusedarm', 5 + j))
def merge(pins, ox, oy, canon, tag):
    for x, y, n in pins:
        k = (x + ox, y + oy); assert k not in ex, (tag, k)
        ex[k] = canon.get(n, (tag, n))
canonP = {P['abit'][i]: key(port[f'rom_addr{i}']) for i in range(14)}
canonP.update({P['outs'][j]: ('rom', j) for j in range(8)})
canonR = {R['abit'][i]: key(port[f'ram_addr{i}']) for i in range(7)}
canonR[R['WE']] = key(port['ram_we'])
for b in range(8): canonR[R['DIN'][b]] = key(port[f'ram_din{b}']); canonR[R['DOUT'][b]] = ('ramo', b)
merge(P['pins'], PX, PY, canonP, 'P'); merge(R['pins'], MX, MY, canonR, 'M')
json.dump([[x, y, list(k)] for (x, y), k in ex.items()], open(out + '.keys.json', 'w'))
def emit(path, cmds):
  with open(path, 'w') as fh:
    for c in cmds:
        if c[0] == 'place': fh.write(f'place {c[1]} {c[2] + OFS[0]} {c[3] + OFS[1]} {c[4]} {c[5]}\n')
        elif c[0] == 'track': fh.write(f'track {c[1]} {c[2] + OFS[0]} {c[3] + OFS[1]} {c[4] + OFS[0]} {c[5] + OFS[1]}\n')
        else: fh.write(f'via {c[1] + OFS[0]} {c[2] + OFS[1]}\n')
import pickle; pickle.dump([w.ops for w in WIRES], open(out + '.wires.pkl', 'wb'))
emit(out + '.seed.build', B); emit(out + '.run.build', RUNB); emit(out + '.build', B + RUNB)
xs = [c[2] for c in B if c[0] == 'track'] + [c[4] for c in B if c[0] == 'track']; ys = [c[3] for c in B if c[0] == 'track'] + [c[5] for c in B if c[0] == 'track']
print(f'commands {len(B)} (core {ncore}, blocks {nblk}, iface {len(B) - ncore - nblk}); x {min(xs)}..{max(xs)} y {min(ys)}..{max(ys)}; OFS {OFS}')
