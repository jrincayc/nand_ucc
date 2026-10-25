#!/usr/bin/env python3
"""tile_enc.py TILE.json OUT.asm -- compact tile data: places, path trails (dpath segment format), lone vias.  Self-check by decoding."""
import json, sys, collections
T = json.load(open(sys.argv[1])); trails = json.load(open(sys.argv[1].replace('tile.json', 'tile_paths.json')))
inside = set(); recs = []; lone = set(tuple(v) for v in T['vias']) | set(tuple(p) for p in T['ports'].values())
def fix(start, segs):
    """return list of (start, segs) with segs starting/ending in 's'; vias that cannot be represented are returned as lone"""
    L, x, y = start; out = []; loneset = []
    # walk to give each segment its start; split on unrepresentable vias
    items = []
    cur = (L, x, y)
    for s in segs:
        if s[0] == 'v': items.append(('v', cur[1], cur[2])); cur = (1 - cur[0], cur[1], cur[2])
        else:
            n = s[2]; d = s[1]; items.append(('s', cur, d, n)); cur = (cur[0], cur[1] + d[0] * n, cur[2] + d[1] * n)
    # split into chains at leading/trailing/double vias
    chains = [[]]
    for it in items:
        chains[-1].append(it)
    while chains and chains[0] and chains[0][0][0] == 'v': loneset.append(chains[0].pop(0)[1:])
    while chains and chains[0] and chains[0][-1][0] == 'v': loneset.append(chains[0].pop()[1:])
    return chains[0], loneset
data = []
for start, segs in trails:
    items, ln = fix(tuple(start), segs)
    for v in ln: pass
    if not items: continue
    first = next(it for it in items if it[0] == 's')
    _, (L, sx, sy), _, _ = first
    data.append((sx, sy, items, L))
    for it in items:
        if it[0] == 'v': inside.add(it[1:])
lone_list = sorted(lone - inside)
lines = []
places = T['gates']
lines.append(f'    .byte {len(places)}')
for kind, ins, x, y, name in places: lines.append(f'    .byte {x | (128 if kind == "D" else 0)},{y}')
nb = 0
for sx, sy, items, L in data:
    # first via bit = start layer
    bs = []
    for i, it in enumerate(items):
        if it[0] == 'v': continue
        _, (l, x, y), d, n = it
        dirc = {(1, 0): 0, (-1, 0): 1, (0, 1): 2, (0, -1): 3}[tuple(d)]
        viab = (1 if l == 1 else 0) if not bs else (1 if items[i - 1][0] == 'v' else 0)
        rem = n
        while rem:
            ln = min(rem, 255)
            # chunks: a continued chunk never carries a via bit
            vb = viab if rem == n else 0
            if ln <= 15: bs.append(('b', vb << 6 | dirc << 4 | ln))
            else: bs.append(('b', vb << 6 | dirc << 4)); bs.append(('b', ln))
            rem -= ln
    # mark last: set bit 7 on the last segment byte (which is its header byte): find index of last header
    hdr = []
    i = 0
    while i < len(bs):
        hdr.append(i); i += 2 if (bs[i][1] & 15) == 0 else 1
    bs[hdr[-1]] = ('b', bs[hdr[-1]][1] | 128)
    lines.append(f'    .byte {sx},{sy},' + ','.join(str(b[1]) for b in bs))
lines.append('    .byte 255')
lines.append(f'    .byte {len(lone_list)}')
for x, y in lone_list: lines.append(f'    .byte {x},{y}')
open(sys.argv[2], 'w').write('t_tile:\n' + '\n'.join(lines) + '\n')
sz = sum(l.count(',') + 1 for l in lines if '.byte' in l)
print('trails', len(data), 'lone vias', len(lone_list), 'bytes', sz)
