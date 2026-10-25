#!/usr/bin/env python3
"""tile_paths.py TILE.json OUT.json -- decompose the tile copper (tracks + vias + port vias) into trails for dpath-style replay; verify by re-expanding."""
import json, sys, collections
T = json.load(open(sys.argv[1]))
edges = set(); vias = set()
def cells(L, x0, y0, x1, y1):
    if x0 == x1: return [(L, x0, y) for y in range(min(y0, y1), max(y0, y1) + 1)]
    return [(L, x, y0) for x in range(min(x0, x1), max(x0, x1) + 1)]
for L, x0, y0, x1, y1 in T['tracks']:
    c = cells(L, x0, y0, x1, y1)
    for a, b in zip(c, c[1:]): edges.add((a, b))
V = set(map(tuple, T['vias'])) | set(tuple(p) for p in T['ports'].values())
for x, y in V: edges.add(((0, x, y), (1, x, y)))      # via edge between layers
adj = collections.defaultdict(set)
for a, b in edges: adj[a].add(b); adj[b].add(a)
# trail decomposition: greedy walks that consume edges, preferring to go straight
used = set(); trails = []
def ek(a, b): return (a, b) if (a, b) in edges else (b, a)
def straight(a, b, c):
    return (b[0] == c[0] == a[0]) and (b[1] - a[1], b[2] - a[2]) == (c[1] - b[1], c[2] - b[2])
for start in sorted(adj, key=lambda c: (len(adj[c]) == 2, c)):
    while any(ek(start, n) not in used for n in adj[start]):
        cur = start; path = [cur]; prev = None
        while True:
            opts = [n for n in adj[cur] if ek(cur, n) not in used]
            if not opts: break
            if prev is not None:
                st = [n for n in opts if straight(prev, cur, n)]
                nxt = st[0] if st else sorted(opts)[0]
            else: nxt = sorted(opts)[0]
            used.add(ek(cur, nxt)); path.append(nxt); prev, cur = cur, nxt
        trails.append(path)
# encode: start (L,x,y), segments (dir,len) with via markers
def enc(path):
    segs = []; i = 0
    start = path[0]; L0 = start[0]
    cur = start
    for a, b in zip(path, path[1:]):
        if a[0] != b[0]: segs.append(('v',)); continue
        d = (b[1] - a[1], b[2] - a[2])
        if segs and segs[-1][0] == 's' and segs[-1][1] == d: segs[-1] = ('s', d, segs[-1][2] + 1)
        else: segs.append(('s', d, 1))
    return (start, segs)
out = [enc(p) for p in trails]
nseg = sum(sum(1 for s in e[1] if s[0] == 's') for e in out); nv = sum(sum(1 for s in e[1] if s[0] == 'v') for e in out)
print('trails', len(trails), 'segments', nseg, 'via marks', nv)
# verify re-expansion covers the same edge set
got = set()
for start, segs in out:
    L, x, y = start
    for s in segs:
        if s[0] == 'v': got.add(((0, x, y), (1, x, y))); L = 1 - L
        else:
            for _ in range(s[2]):
                n = (L, x + s[1][0], y + s[1][1]); got.add(ek((L, x, y), n)); x, y = n[1], n[2]
print('edges', len(edges), 'covered', len(got & {ek(*e) for e in edges}), 'extra', len(got - {ek(*e) for e in edges}))
json.dump(out, open(sys.argv[2], 'w'))
