#!/usr/bin/env python3
"""test2_model.py -- engine2_model on a small ring: A rows, interpreter rows, pattern rows, data words, C rows.  Checks pass 1 (decoded layout commands) and pass 2 (plane dump)."""
import sys, collections
import spec2 as S, pattern as PT, plane as PL, fmt2, engine2_model as EM
from arm import Arm
X0, RX = 150, 144
NDATA = int(sys.argv[1]) if len(sys.argv) > 1 else 300

def row(**kw): return S.pack_int(**kw)
def conv_pat(x):
    if x.get('cen', 0): return S.pack_int(d=x['d'], reg=x['reg'], src=x['src'], D=0, cpol=x['cpol'], ccol=x['ccol'], ph=S.PH_P)
    return S.pack_int(d=x['d'], reg=x['reg'], src=x['src'], D=0, cpol=1, ccol=S.CC_ALWAYS, ph=S.PH_P)
pat = [conv_pat(x) for x in PT.build_pattern(X0, RX, 0)]
# interpreter rows (D=1, ph=P)
def irow(reg, src, d, ccol, cpol): return row(d=d, reg=reg, src=src, D=1, cpol=cpol, ccol=ccol, ph=S.PH_P)
CMDB, HYB, HKB, ORI = 21, 20, 19, 14
interp = [
    irow(S.AXL, S.SRC_SUM, 16, CMDB, 1),           # Ax += dx
    irow(S.AYL, S.SRC_SUM, 19, CMDB, 1),           # Ay += dy
    irow(S.BXL, S.SRC_SUM, 4, ORI, 0),             # H: Bx = Ax + len
    irow(S.BYL, S.SRC_SUM, 7, ORI, 0),             #    By = Ay
    irow(S.BXL, S.SRC_SUM, 6, ORI, 1),             # V: Bx = Ax
    irow(S.BYL, S.SRC_SUM, 5, ORI, 1),             #    By = Ay + len
    irow(S.CMD, S.SRC_WF, 0, CMDB, 1),             # CMD <- c
    irow(S.AYL, S.SRC_SUM, 17, HYB, 1),            # Hy: Ay += delta8
    irow(S.KIND, S.SRC_WF, 1, HKB, 1),             # Hk: kind
    irow(S.VAL, S.SRC_WF, 2, HKB, 1),              #     val
]
A_rows = [row(d=0, reg=r, src=0, ph=S.PH_A) for r in (S.AXH, S.BXH, S.AYH, S.BYH, S.ANGLE)]
C_cmds = [(7, 255), (10, 1), (15, 4)]
C_rows = [row(d=v, reg=r, src=0, ph=S.PH_C) for r, v in C_cmds]
# data words from the real layout
import elay, eplace, eroute
nl = elay.read_nl('/tmp/eng.nl'); cmds, info = eroute.route(nl, eplace.order(nl, seed=1), R=22, Z=14)
t = info['nlate'][1] + info['nlate'][2]; body = cmds[:len(cmds) - t]
words, st = fmt2.encode(body)
data = words[:NDATA]
rows = A_rows + interp + pat + data + C_rows
W = len(rows); M = 16319
print('rows', W, '(A', len(A_rows), 'interp', len(interp), 'pat', len(pat), 'data', len(data), 'C', len(C_rows), ')')
writes, cyc = EM.run(rows, M)
print('cycles', cyc, 'arm writes', len(writes))
arm = Arm()
for r, v in writes: arm.write(r, v)
print('arm faults', arm.faults, 'commands', len(arm.cmds))
AY = 4 * (M + 1) - 32768; Y0 = AY - 4 * W
# expected: pass 1 = decode of data words (hi bytes 0), pass 2 = plane dump (absolute coords), C
a2 = Arm()
for r, v in fmt2.decode(data): a2.write(r, v)
exp1 = a2.cmds
bitsrows = [S.bits(w) for w in rows]
exp2 = [c for c in PL.plane(bitsrows, X0, Y0, RX)]
def s16(v): return v - 65536 if v >= 32768 else v
def absc(c):
    if c[0] == 'place': return ('place', c[1], c[2], c[3], c[4], c[5])
    if c[0] == 'track': return ('track', c[1], c[2], c[3], c[4], c[5])
    return ('via', c[1], c[2])
got = arm.cmds
n1 = len(exp1); n2 = len(exp2)
g1 = got[:n1]; g2 = got[n1:n1 + n2]; g3 = got[n1 + n2:]
print('pass1 cmds', n1, 'match', g1 == exp1)
c2 = collections.Counter(map(absc, g2)); e2 = collections.Counter(map(absc, exp2))
print('pass2 cmds', len(g2), 'expected', n2, 'multiset equal', c2 == e2)
print('tail', g3)
if g1 != exp1:
    for i, (a, b) in enumerate(zip(g1, exp1)):
        if a != b: print('first diff', i, a, b); break
if c2 != e2:
    print('missing', list((e2 - c2).items())[:3], 'extra', list((c2 - e2).items())[:3])
