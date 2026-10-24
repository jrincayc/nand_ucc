#!/usr/bin/env python3
"""test_model.py -- the model's arm writes, executed by the arm model, must reproduce plane.plane() for all rows (as an arm-relative command multiset) plus the A and C stream."""
import sys, collections
import spec as S, pattern as PT, plane as PL, engine_model as EM
from arm import Arm
X0, RX, xoff = 150, 144, 0
pat = PT.build_pattern(X0, RX, xoff)
def const_cmds(cmds):
    """stream words writing a list of commands with constant coordinates (no persistence tricks, full writes) -> instruction dicts"""
    out = []
    for c in cmds:
        regs = {}
        if c[0] == 'place': _, k, x, y, rot, val = c; regs = {0: x & 255, 1: (x >> 8) & 255, 2: y & 255, 3: (y >> 8) & 255, 8: k, 9: rot, 10: val}; code = 1
        elif c[0] == 'track': _, l, x0, y0, x1, y1 = c; regs = {0: x0 & 255, 1: (x0 >> 8) & 255, 2: y0 & 255, 3: (y0 >> 8) & 255, 4: x1 & 255, 5: (x1 >> 8) & 255, 6: y1 & 255, 7: (y1 >> 8) & 255, 10: l}; code = 4
        else: _, x, y = c; regs = {0: x & 255, 1: (x >> 8) & 255, 2: y & 255, 3: (y >> 8) & 255}; code = 5
        for r, v in regs.items(): out.append(dict(reg=r, src=0, d=v, ph=S.PH_NONE))
        out.append(dict(reg=15, src=0, d=code, ph=S.PH_NONE))
    return out
A_cmds = [('place', 0, 5, -60, 0, 0), ('track', 0, 5, -60, 5, -50), ('via', 6, -61)]
C_cmds = [('track', 1, 7, -70, 7, -66)]
rowsA = [dict(x, ph=S.PH_A) for x in const_cmds(A_cmds)]; rowsC = [dict(x, ph=S.PH_C) for x in const_cmds(C_cmds)]
rows = rowsA + [dict(x, ph=S.PH_P) for x in pat] + rowsC
W = len(rows); print('rows', W, ' (A', len(rowsA), 'P', len(pat), 'C', len(rowsC), ')')
# the plane content of exactly these rows
bits = [S.pack(**{k: v for k, v in r.items()}) for r in rows]
writes, cyc = EM.run(rows)
print('cycles', cyc, 'arm writes', len(writes))
arm = Arm()
for r, v in writes: arm.write(r, v)
print('arm faults', arm.faults, 'commands', len(arm.cmds))
# expected: A cmds first, then plane(bits) in arm-relative coords, then C
Y0 = 1000; AY = Y0 + 4 * W
exp = plane = None
def rel(c):
    if c[0] == 'place': return ('place', c[1], c[2] + xoff, c[3] - AY, c[4], c[5])
    if c[0] == 'track': return ('track', c[1], c[2] + xoff, c[3] - AY, c[4] + xoff, c[5] - AY)
    return ('via', c[1] + xoff, c[2] - AY)
expd = [rel(c) for c in PL.plane(bits, X0, Y0, RX)]
got = arm.cmds
ga, gc = got[:len(A_cmds)], got[len(got) - len(C_cmds):]; gm = got[len(A_cmds):len(got) - len(C_cmds)]
print('A ok', ga == A_cmds, ' C ok', gc == C_cmds)
a = collections.Counter(gm); b = collections.Counter(expd)
print('dump commands got', len(gm), 'expected', len(expd), ' missing', sum((b - a).values()), 'extra', sum((a - b).values()))
if b - a: print(list((b - a))[:5])
if a - b: print(list((a - b))[:5])
