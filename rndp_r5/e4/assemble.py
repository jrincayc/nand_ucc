#!/usr/bin/env python3
"""assemble.py W SEED -- builds the E4 ring (rows) and the parent world command list (arm-relative frame P, arm part at (0,0)).
Outputs /tmp/e4_rows.json (rows, W, geometry), /tmp/e4_parent.build (rndp build file, board offset applied), /tmp/e4_child_expect.pkl (parent cmds shifted by DX)."""
import sys, os, pickle, json, collections
import spec2 as S, pattern as PT, plane as PL, fmt3
def conv_pat(x):
    if x.get("cen", 0): return S.pack_int(d=x["d"], reg=x["reg"], src=x["src"], D=0, cpol=x["cpol"], ccol=x["ccol"], ph=S.PH_P)
    return S.pack_int(d=x["d"], reg=x["reg"], src=x["src"], D=0, cpol=1, ccol=S.CC_ALWAYS, ph=S.PH_P)
W = int(sys.argv[1]); SEED = sys.argv[2]; M = 16255; X0, RX, DX = 150, 144, 900
BX = X0 - 26                                   # block x -> P x
AYP = 4 * (M + 1) - 32768                      # block y 0 -> P y
Y0P = AYP - 4 * W
CX, CY = (DX + BX) >> 8, 0x7E
assert (DX + BX) % 512 == 0 and CX % 2 == 0 and AYP >> 8 == CY, (DX + BX, CX, AYP)
cmds, words = pickle.load(open(f'/tmp/fp_{W}_{SEED}.pkl', 'rb'))
body = [c for c, l in cmds if l == 0]
late = {k: [c for c, l in cmds if l == k] for k in (1, 2, 3)}
# ---- geometry of the block
RXb = 20; gx0 = RXb - 8; gy0 = 30; gridx0 = max(0, gx0 - 10)
names = [f'arm_addr{i}' for i in range(4)] + ['arm_en'] + [f'wdata{j}' for j in range(8)]
portpad = {nm: (gridx0, gy0 + 2 + 3 * i) for i, nm in enumerate(names + ['ram_addr0'])}
pin = {}      # arm pin cell (relative to arm origin)
for i in range(4): pin[f'arm_addr{i}'] = (0, i)
pin['arm_en'] = (0, 4)
for j in range(8): pin[f'wdata{j}'] = (1, j)
lane = {}
for i in range(4): lane[f'arm_addr{i}'] = -3 - i
lane['arm_en'] = -7
for j in range(8): lane[f'wdata{j}'] = 3 + j
def blk(c):                                    # block-coordinate command -> P frame
    if c[0] == 'place': return ('place', c[1], c[2] + BX, c[3] + AYP, c[4], c[5])
    if c[0] == 'track': return ('track', c[1], c[2] + BX, c[3] + AYP, c[4] + BX, c[5] + AYP)
    return ('via', c[1] + BX, c[2] + AYP)
def longwire(nm):
    px, py = portpad[nm]; px += BX; py += AYP; lx = lane[nm]; ax, ay = pin[nm]
    return [('via', px, py), ('track', 0, px, py, lx, py), ('via', lx, py), ('track', 1, lx, py, lx, ay), ('via', lx, ay), ('track', 0, lx, ay, ax, ay)]
# ---- C commands (P frame, parent coordinates): arm part, D0 wire, long wires (not EN), late1, EN wire, late2
armplace = [('place', 3, 0, 0, 0, 0)]
D0LANE = 110
_px, _py = portpad['ram_addr0']; _px += BX; _py += AYP
d0 = [('via', _px, _py), ('track', 0, _px, _py, D0LANE, _py), ('via', D0LANE, _py), ('track', 1, D0LANE, _py, D0LANE, Y0P), ('via', D0LANE, Y0P), ('track', 0, D0LANE, Y0P, RX, Y0P)]
lw = [c for nm in names if nm != 'arm_en' for c in longwire(nm)]
cC = armplace + d0 + lw + [blk(c) for c in late[1]] + longwire('arm_en') + [blk(c) for c in late[2]]
def shift(cs, dx): return [(c[0], c[1], c[2] + dx, c[3], c[4] + dx, c[5]) if c[0] == 'track' else (c[0], c[1], c[2] + dx, c[3], c[4], c[5]) if c[0] == 'place' else (c[0], c[1] + dx, c[2]) for c in cs]
def regs_of(c, dx):
    if c[0] == 'place': _, k, x, y, r, v = c; return {0: (x + dx) & 255, 1: ((x + dx) >> 8) & 255, 2: y & 255, 3: (y >> 8) & 255, 8: k, 9: r, 10: v, 15: 1}
    if c[0] == 'track': _, l, x0, y0, x1, y1 = c; return {0: (x0 + dx) & 255, 1: ((x0 + dx) >> 8) & 255, 2: y0 & 255, 3: (y0 >> 8) & 255, 4: (x1 + dx) & 255, 5: ((x1 + dx) >> 8) & 255, 6: y1 & 255, 7: (y1 >> 8) & 255, 10: l, 15: 4}
    _, x, y = c; return {0: (x + dx) & 255, 1: ((x + dx) >> 8) & 255, 2: y & 255, 3: (y >> 8) & 255, 15: 5}
C_rows = []; st = {}
for c in cC:
    for r, v in regs_of(c, DX).items():
        if r != 15 and st.get(r) == v: continue
        C_rows.append(S.pack_int(d=v, reg=r, src=0, ph=S.PH_C)); st[r] = v
        if r == 15: pass
    # CMD is always written (executes the command) -- already in regs_of; force it below
# (regs_of puts 15 last in dict order, and the CMD write must always happen: handled by the r != 15 test)
# ---- fixed rows
def row(**kw): return S.pack_int(**kw)
def irow(reg, src, d, ccol, cpol): return row(d=d, reg=reg, src=src, D=1, cpol=cpol, ccol=ccol, ph=S.PH_P)
CMDB, HB, ORI = 21, 20, 15
def ihi(reg, c, d0_, ccol, cpol): return irow(reg, 7, c | d0_, ccol, cpol)
interp = [irow(S.AXL, S.SRC_SUM, 16, CMDB, 1), irow(S.AYL, S.SRC_SUM, 19, CMDB, 1), ihi(S.AXH, CX, 0, CMDB, 1), ihi(S.AYH, CY, 0, CMDB, 1),
          irow(S.BXL, S.SRC_SUM, 4, ORI, 0), irow(S.BYL, S.SRC_SUM, 7, ORI, 0), ihi(S.BXH, CX, 1, ORI, 0), ihi(S.BYH, CY, 0, ORI, 0),
          irow(S.BXL, S.SRC_SUM, 6, ORI, 1), irow(S.BYL, S.SRC_SUM, 5, ORI, 1), ihi(S.BXH, CX, 0, ORI, 1), ihi(S.BYH, CY, 1, ORI, 1),
          irow(S.CMD, S.SRC_WF, 0, CMDB, 1), irow(S.AYL, S.SRC_SUM, 17, HB, 1), irow(S.KIND, S.SRC_WF, 1, HB, 1), irow(S.VAL, S.SRC_WF, 2, HB, 1)]
A_rows = [row(d=0, reg=S.ANGLE, src=0, ph=S.PH_A)]
pat = [conv_pat(x) for x in PT.build_pattern(X0, RX, DX)]
data = list(words)
pad = W - (len(A_rows) + len(interp) + len(pat) + len(data) + len(C_rows))
print('A', len(A_rows), 'interp', len(interp), 'pat', len(pat), 'data', len(data), 'C', len(C_rows), '(C commands', len(cC), ') pad', pad)
assert pad >= 0, 'W too small'
rows = A_rows + interp + pat + data + [0] * pad + C_rows
assert len(rows) == W
json.dump(dict(rows=rows, W=W, M=M, X0=X0, RX=RX, DX=DX, BX=BX, AYP=AYP, Y0P=Y0P, CX=CX, CY=CY, nA=len(A_rows), nint=len(interp), npat=len(pat), ndata=len(data), npad=pad, nC=len(C_rows)), open('/tmp/e4_rows.json', 'w'))
# ---- parent world: plane (parent coords, uses the real bits of every row) + engine body + C commands
planec = PL.plane([S.bits(w) for w in rows], X0, Y0P, RX)
parent = planec + [blk(c) for c in body] + cC
child_expect = shift(parent, DX)
pickle.dump((parent, child_expect), open('/tmp/e4_parent.pkl', 'wb'))
OFS_X, OFS_Y = 300, 40000 - 0
ys = [c[3] if c[0] != 'via' else c[2] for c in parent] + [c[5] for c in parent if c[0] == 'track']
print('parent commands', len(parent), 'y range', min(ys), max(ys))
cnt = collections.Counter(c[0] for c in parent); print(cnt)
