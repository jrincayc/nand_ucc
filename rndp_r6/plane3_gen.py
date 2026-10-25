#!/usr/bin/env python3
"""R6 plane v3: uniform, state-free ROM plane.  usage: plane3_gen.py ROMFILE OFFSET OUT.build [R=128 C=128]
Every strip exists (R strips of C cells).  Lane j of strip s is ONE snake wire: pass slots / gadget slots left to right, then right end -> return row (y+3) -> left region
-> down to lane row of strip s+1.  The chain starts floating (reads 0) at slot 0 of strip 0; the last strip's right end is the lane output.
A slot is a gadget (T=NOT(acc), N=NAND(T,w)) if the ROM bit is 1, else a straight wire.  No data-dependent geometry except which slots are gadgets/cells."""
import sys, json
rom, off, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
R = int(sys.argv[4]) if len(sys.argv) > 4 else 128; C = int(sys.argv[5]) if len(sys.argv) > 5 else 128
data = list(open(rom, 'rb').read()[off:off + R * C]); data += [0] * (R * C - len(data))
LP, CW, LANE0 = 5, 8, 9
B = []; pins = {}
def trk(L, x0, y0, x1, y1):
    if (x0, y0) != (x1, y1): B.append(f'track {L} {x0} {y0} {x1} {y1}')
def via(x, y): B.append(f'via {x} {y}')
nid = [0]
def newnet(): nid[0] += 1; return nid[0]
def pin(x, y, net): assert (x, y) not in pins, (x, y); pins[(x, y)] = net
def place(x, y, ins):
    B.append(f'place 0 {x} {y} 0 0'); n = newnet(); pin(x, y, ins[0]); pin(x, y + 1, ins[1]); pin(x + 1, y, n); return n
NB = (C - 1).bit_length(); NBH = (R - 1).bit_length()
XL0 = 2; XB = XL0 + 16 + 6; XG = XB + 4 * (NB + NBH) + 4; X0 = XG + 8 * 6 + 6; XEND = X0 + C * CW + 2
INVY = 2; PY0 = INVY + 4 + 8 * C + 8; STRIPH = LANE0 + LP * 8 + 3 + 1
base = lambda s: PY0 + 3 + s * STRIPH
yj = lambda s, j: base(s) + LANE0 + LP * j
TOP = base(R - 1) + 8
# ---- address inputs, inverters, buses
abit = [newnet() for _ in range(NB + NBH)]; nabit = []
busx = lambda i, neg: XB + 4 * i + (1 if neg else -1)
for i in range(NB + NBH):
    x = XB + 4 * i
    B.append(f'place 0 {x} {INVY} 0 0'); pin(x, INVY, abit[i]); pin(x, INVY + 1, abit[i]); n = newnet(); pin(x + 1, INVY, n); nabit.append(n)
    via(x - 1, INVY + 1); trk(0, x - 1, INVY + 1, x - 1, INVY); trk(0, x - 1, INVY, x, INVY); trk(0, x - 1, INVY + 1, x, INVY + 1)
def lit(i, bit):
    return busx(i, bit == 0), (nabit[i] if bit == 0 else abit[i])
def line(y, v, i0, nbits):
    lits = [lit(i0 + k, (v >> k) & 1) for k in range(nbits)]
    prev = None
    for k in range(nbits - 1):
        Xk = XG + 8 * k
        if k == 0:
            (xb0, n0), (xb1, n1) = lits[0], lits[1]
            via(xb0, y); trk(0, xb0, y, Xk, y)
            via(xb1, y + 2); trk(0, xb1, y + 2, Xk, y + 2); trk(0, Xk, y + 2, Xk, y + 1)
            ins = [n0, n1]
        else:
            xb, n1 = lits[k + 1]
            trk(0, Xk - 3, y, Xk, y)
            via(xb, y + 2 + k); trk(0, xb, y + 2 + k, Xk, y + 2 + k); trk(0, Xk, y + 2 + k, Xk, y + 1)
            ins = [prev, n1]
        nd = place(Xk, y, ins)
        trk(0, Xk + 1, y, Xk + 4, y); trk(0, Xk + 3, y, Xk + 3, y + 1); trk(0, Xk + 3, y + 1, Xk + 4, y + 1)
        prev = place(Xk + 4, y, [nd, nd])
    return prev, XG + 8 * (nbits - 2) + 5
# ---- lo lines
lonet = {}
for l in range(C):
    y = INVY + 4 + 8 * l
    o_, xo = line(y, l, 0, NB); lonet[l] = o_
    cxl = X0 + l * CW - 1
    trk(0, xo, y, cxl, y); via(cxl, y); trk(1, cxl, y, cxl, base(R - 1) + 1)
# ---- lanes: floating start
cur = [newnet() for _ in range(8)]; floating = list(cur)
XE = lambda j: XEND + 2 * j; XL = lambda j: XL0 + 2 * j
for s in range(R):
    b = base(s)
    hnet, xo = line(b - 1, s, NB, NBH)
    trk(0, xo, b - 1, X0 + (C - 1) * CW, b - 1)                       # hi trunk, whole strip
    for l in range(C):
        v = data[s * C + l]; cx = X0 + l * CW
        if v:
            w = place(cx, b, [hnet, lonet[l]])
            trk(0, cx, b - 1, cx, b)
            via(cx - 1, b + 1); trk(0, cx - 1, b + 1, cx, b + 1)
            trk(0, cx + 1, b, cx + 3, b); via(cx + 3, b); trk(1, cx + 3, b, cx + 3, yj(s, 7) + 1)
        for j in range(8):
            y = yj(s, j)
            if (v >> j) & 1:
                trk(0, cx - 1, y, cx, y); trk(0, cx - 1, y, cx - 1, y + 1); trk(0, cx - 1, y + 1, cx, y + 1)
                t = place(cx, y, [cur[j], cur[j]])
                trk(0, cx + 1, y, cx + 5, y)
                via(cx + 3, y + 1); trk(0, cx + 3, y + 1, cx + 5, y + 1)
                n = place(cx + 5, y, [t, w])
                trk(0, cx + 6, y, cx + 7, y)
                cur[j] = n
            else:
                trk(0, cx - 1, y, cx + 7, y)
    for j in range(8):
        y = yj(s, j)
        trk(0, X0 + (C - 1) * CW + 7, y, XE(j), y)
        if s < R - 1:
            via(XE(j), y); trk(1, XE(j), y, XE(j), y + 3); via(XE(j), y + 3); trk(0, XE(j), y + 3, XL(j), y + 3)
            via(XL(j), y + 3); trk(1, XL(j), y + 3, XL(j), yj(s + 1, j)); via(XL(j), yj(s + 1, j)); trk(0, XL(j), yj(s + 1, j), X0 - 1, yj(s + 1, j))
# ---- buses, all to the top
for i in range(NB + NBH):
    x = XB + 4 * i
    trk(1, x - 1, INVY + 1, x - 1, TOP); trk(1, x + 1, INVY, x + 1, TOP)
open(out, 'w').write('\n'.join(B) + '\n')
json.dump({'outpos': [[XE(j), yj(R - 1, j)] for j in range(8)], 'abitpos': [[XB + 4 * i - 1, INVY + 1] for i in range(NB + NBH)], 'size': [XEND + 20, base(R - 1) + STRIPH],
           'pins': [[x, y, n] for (x, y), n in pins.items()], 'XEND': XEND, 'outs': cur, 'abit': abit, 'NB': NB, 'NBH': NBH, 'C': C, 'R': R, 'floating': floating}, open(out + '.pins.json', 'w'))
ng = sum(1 for l in B if l.startswith('place'))
print(f'gates {ng} commands {len(B)} board {XEND + 20} x {base(R - 1) + STRIPH} = {(XEND + 20) * (base(R - 1) + STRIPH)} cells')
