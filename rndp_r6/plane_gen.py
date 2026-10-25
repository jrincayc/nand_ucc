#!/usr/bin/env python3
"""R6: router-free ROM plane generator.  Every wire is a fixed formula of (strip, column, bit).  usage: plane_gen.py ROMFILE OFFSET R C OUT.build [LP] [CW]
Cell (h,l) = NAND(hi[h], lo[l]) at (cx, base); lane j (one per output bit) is ONE OR-chain over all cells in (h,l) order (serpentine-free: the chain returns from
a strip's right end to the next strip's left end on the free row yj+3).  chain: first one: N=NAND(w,w); later: T=NOT(acc), N=NAND(T,w).
Layer 0 horizontal, layer 1 vertical.  Emits place/track/via lines and the logical pin->net map (JSON)."""
import sys, json, collections
rom, off, R, C, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
LP = int(sys.argv[6]) if len(sys.argv) > 6 else 5
CW = int(sys.argv[7]) if len(sys.argv) > 7 else 8
data = open(rom, 'rb').read()[off:off + R * C]; data = list(data) + [0] * (R * C - len(data))
B = []; pins = {}; gates = []         # gates: (x, y, kind, ins[2], name)
def trk(L, x0, y0, x1, y1):
    if (x0, y0) != (x1, y1): B.append(f'track {L} {x0} {y0} {x1} {y1}')
def via(x, y): B.append(f'via {x} {y}')
rows = [h for h in range(R) if any(data[h * C:(h + 1) * C])]
XL0 = 2; X0 = XL0 + 2 * 8 + 4; XEND = X0 + C * CW + 2
STRIPH = 3 + 8 * LP + 3
base_of = {h: 2 + s * STRIPH for s, h in enumerate(rows)}
yj = lambda b, j: b + 3 + LP * j
last = {}                              # lane -> (x_out, y_out, strip base) of chain end ; None
nid = [0]
def newnet(): nid[0] += 1; return nid[0]
def pin(x, y, net): assert (x, y) not in pins, (x, y); pins[(x, y)] = net
lonet = {l: newnet() for l in range(C)}; hinet = {h: newnet() for h in rows}
lo_top = {}; hi_right = {}
def place(x, y, ins):
    B.append(f'place 0 {x} {y} 0 0'); n = newnet(); pin(x, y, ins[0]); pin(x, y + 1, ins[1]); pin(x + 1, y, n); return n
lanes_started = [False] * 8; chain_net = [None] * 8; chain_end = [None] * 8       # chain_end: (x, y, base)
for h in rows:
    b = base_of[h]
    for l in range(C):
        v = data[h * C + l]
        if not v: continue
        cx = X0 + l * CW
        w = place(cx, b, [hinet[h], lonet[l]])
        # hi: trunk on row b-1 (drawn later up to hi_right), stub down to A
        hi_right[h] = cx; trk(0, cx, b - 1, cx, b)
        # lo: layer-1 vertical at cx-1, via to layer 0 at (cx-1, b+1), stub to B
        lo_top[l] = max(lo_top.get(l, 0), b + 1); via(cx - 1, b + 1); trk(0, cx - 1, b + 1, cx, b + 1)
        js = [j for j in range(8) if (v >> j) & 1]
        trk(0, cx + 1, b, cx + 3, b); via(cx + 3, b); trk(1, cx + 3, b, cx + 3, yj(b, js[-1]) + 1)
        for j in js:
            y = yj(b, j); via(cx + 3, y + 1); trk(0, cx + 3, y + 1, cx + 5, y + 1)
            if chain_net[j] is None:                       # very first one of lane j: N = NAND(w, w)
                trk(0, cx + 4, y + 1, cx + 4, y); trk(0, cx + 4, y, cx + 5, y)
                n = place(cx + 5, y, [w, w])
                chain_net[j] = n; chain_end[j] = (cx + 6, y, b)
            else:
                xe, ye, be = chain_end[j]
                if be == b:                                # same strip: straight along the lane row
                    trk(0, xe, ye, cx, y)
                else:                                      # return path: right end -> row ye+3 -> left region -> row y
                    XE = XEND + 2 * j; XL = XL0 + 2 * j
                    trk(0, xe, ye, XE, ye); via(XE, ye); trk(1, XE, ye, XE, ye + 3); via(XE, ye + 3)
                    trk(0, XE, ye + 3, XL, ye + 3); via(XL, ye + 3); trk(1, XL, ye + 3, XL, y); via(XL, y)
                    trk(0, XL, y, cx, y)
                trk(0, cx - 1, y, cx - 1, y + 1); trk(0, cx - 1, y + 1, cx, y + 1)
                t = place(cx, y, [chain_net[j], chain_net[j]])
                trk(0, cx + 1, y, cx + 5, y)
                n = place(cx + 5, y, [t, w])
                chain_net[j] = n; chain_end[j] = (cx + 6, y, b)
    if h in hi_right: trk(0, 0, b - 1, hi_right[h], b - 1)
# NOTE: when a T gate's A pin is reached by trk(0, xe, ye, cx, y) the net is the previous chain output; both T pins (cx,y),(cx,y+1) were registered with that net.
for l, top in lo_top.items(): trk(1, X0 + l * CW - 1, 0, X0 + l * CW - 1, top)
# chain outputs: extend to the right end
for j in range(8):
    if chain_end[j]: xe, ye, be = chain_end[j]; trk(0, xe, ye, XEND + 2 * j, ye)
open(out, 'w').write('\n'.join(B) + '\n')
json.dump({'pins': [[x, y, n] for (x, y), n in pins.items()], 'rows': rows, 'XEND': XEND, 'outs': chain_net, 'hi': {str(h): n for h, n in hinet.items()}, 'lo': {str(l): n for l, n in lonet.items()}, 'C': C, 'LP': LP, 'CW': CW}, open(out + '.pins.json', 'w'))
ng = sum(1 for l in B if l.startswith('place'))
xs = [int(t[2]) for t in (l.split() for l in B) if t[0] == 'place']; maxx = XEND + 20; maxy = 2 + len(rows) * STRIPH
print(f'strips {len(rows)} gates {ng} board {maxx} x {maxy} = {maxx * maxy} cells ({maxx * maxy / ng:.0f}/gate)')
