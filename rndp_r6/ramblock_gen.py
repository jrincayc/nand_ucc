#!/usr/bin/env python3
"""R6 RAM block, 128 x 8: 128 select lines (7-literal AND chains) + 128 routed-once tiles replicated by translation, bus verticals, chain links, 8 output inverters.
usage: ramblock_gen.py TILE.json OUT.build [WORDS=128]"""
import sys, json
from blk import G, and_line, inverters
T = json.load(open(sys.argv[1])); out = sys.argv[2]; NW = int(sys.argv[3]) if len(sys.argv) > 3 else 128
NBITS = max(1, (NW - 1).bit_length())
g = G(); W, H = T['W'], T['H']; TH = H + 1
XB = 4; XG = XB + 4 * NBITS + 4; XBUS = XG + 8 * 6 + 8; TX0 = XBUS + 2 * 9 + 6; INVY = 2; TY0 = INVY + 6 + 4
ab, nab = inverters(g, XB, INVY, NBITS)
bus_ext = {}
busx = lambda i, neg: XB + 4 * i + (1 if neg else -1)
def lit(i, bit, row):
    key = (i, bit == 0); bus_ext[key] = max(bus_ext.get(key, 0), row); return busx(i, bit == 0), (nab[i] if bit == 0 else ab[i])
WE = g.newnet(); DIN = [g.newnet() for _ in range(8)]
selnet = {}
ty = lambda k: TY0 + k * TH
# tie-high for tile 0's chain inputs
tie = g.nand(TX0 + 2, ty(0) - 6, [None, None]) if False else None
g.B.append(f'place 0 {TX0 + 2} {ty(0) - 6} 0 0'); tien = g.newnet(); g.pin(TX0 + 2 + 1, ty(0) - 6, tien); g.pin(TX0 + 2, ty(0) - 6, g.newnet()); g.pin(TX0 + 2, ty(0) - 5, g.newnet())
for k in range(NW):
    y0 = ty(k)
    # select line k aligned so that its output row is the tile's SEL port row
    ly = y0 + T['ports']['SEL'][1]
    s, xo = and_line(g, ly, k, 0, NBITS, XG, lit); selnet[k] = s
    g.trk(0, xo, ly, TX0 + T['ports']['SEL'][0], ly)
    # tile: gates and routed copper, translated
    local = {}
    for kind, ins, x, y, name in T['gates']:
        pass
    # logical nets of the tile: external names -> global nets
    ext = {'WE': WE, 'SEL': s}
    for b in range(8): ext['DIN%d' % b] = DIN[b]
    for b in range(8): ext['CI%d' % b] = (tien if k == 0 else g.carry[b])
    nets = dict(ext)
    pend = []
    for kind, ins, x, y, name in T['gates']:
        gx, gy = TX0 + x, y0 + y
        if kind == 'N':
            g.B.append(f'place 0 {gx} {gy} 0 0'); n = g.newnet(); nets[name] = n
            pend.append((gx, gy, ins, 'N'))
        else:
            g.B.append(f'place 1 {gx} {gy} 0 0'); n = g.newnet(); nets[name] = n
            pend.append((gx, gy, ins, 'D'))
        g.pin(gx + 1, gy, n)
    for gx, gy, ins, kind in pend:
        g.pin(gx, gy, nets[ins[0]])
        if kind == 'N': g.pin(gx, gy + 1, nets[ins[1]])
    for L, x0, yy0, x1, yy1 in T['tracks']: g.trk(L, TX0 + x0, y0 + yy0, TX0 + x1, y0 + yy1)
    for x, yy in T['vias']: g.via(TX0 + x, y0 + yy)
    for nm_, (px_, py_) in T['ports'].items(): g.via(TX0 + px_, y0 + py_)           # the tile's copper may leave a port pad on either layer
    # bus taps
    pr = T['ports']
    for idx, nm in enumerate(['WE'] + ['DIN%d' % b for b in range(8)]):
        px, pyy = pr[nm]; xb = XBUS + 2 * idx
        g.via(xb, y0 + pyy); g.trk(0, xb, y0 + pyy, TX0 + px, y0 + pyy)
    # chain links to the next tile
    if k < NW - 1:
        g.carry = [nets['CO%d' % b] for b in range(8)] if False else None
    g.carry = [nets['CO%d' % b] for b in range(8)]
    if k < NW - 1:
        for b in range(8):
            px, _ = pr['CO%d' % b]; g.trk(0, TX0 + px, y0 + H - 1, TX0 + px, ty(k + 1))
    else:
        last = {b: (TX0 + pr['CO%d' % b][0], y0 + H - 1, nets['CO%d' % b]) for b in range(8)}
    # first tile: tie wires
    if k == 0:
        for b in range(8):
            px, _ = pr['CI%d' % b]; g.trk(0, TX0 + px, ty(0) - 4, TX0 + px, ty(0))
        g.trk(0, TX0 + 3, ty(0) - 6, TX0 + 3, ty(0) - 4); g.trk(0, TX0 + 3, ty(0) - 4, TX0 + pr['CI7'][0], ty(0) - 4)
# output inverters under the last tile
DOUT = []; DPOS = []
yo = ty(NW - 1) + H + 3
for b in range(8):
    x, y, n = last[b]
    nx = x; o = g.nand(nx, yo, [n, n]); DOUT.append(o); DPOS.append([nx + 1, yo])
    g.trk(0, x, y, x, yo + 1)
# buses (layer 1)
top, bot = ty(0) - 1, ty(NW - 1) + 40
for idx in range(9):
    xb = XBUS + 2 * idx; g.trk(1, xb, top, xb, bot)
TOPR = ty(NW - 1) + 11
for i in range(NBITS):
    for neg in (False, True):
        x = busx(i, neg); y0b = INVY + 1 if not neg else INVY
        g.trk(1, x, y0b, x, TOPR)
g.save(out, dict(DPOS=DPOS, ABPOS=[[XB + 4 * i - 1, INVY + 1] for i in range(NBITS)], BUSPOS=[[XBUS + 2 * i, TY0 - 1] for i in range(9)], SIZE=[TX0 + W + 8, ty(NW - 1) + H + 8], WE=WE, DIN=DIN, abit=ab, DOUT=DOUT, NBITS=NBITS, NW=NW, H=H, W=W, TH=TH, TX0=TX0))
ng = sum(1 for l in g.B if l.startswith('place'))
print(f'words {NW} gates {ng} (dff {sum(1 for l in g.B if l.startswith("place 1"))}), board ~{TX0 + W} x {ty(NW - 1) + H + 8}')
