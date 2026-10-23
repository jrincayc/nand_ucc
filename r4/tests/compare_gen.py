#!/usr/bin/env python3
"""compare_gen.py STATE [DX=880] -- S8 quine check: the child (parts with x >= parent min x + DX - 4) must equal the parent shifted by DX: same parts (kind, x, y, rot, val), track segments (collinear pieces merged), vias, ROM bytes. R4: DX = W + 8 = 880 (tools/make_seed.py writes it to seed.json)."""
import sys, collections
st = sys.argv[1]; DX = int(sys.argv[2]) if len(sys.argv) > 2 else 880
parts, segs, vias, mems = [], [], [], collections.defaultdict(dict)
for line in open(st):
    w = line.split()
    if not w: continue
    if w[0] == 'part': parts.append(tuple(map(int, w[1:])))
    elif w[0] == 'seg':
        l, x0, y0, x1, y1 = map(int, w[1:]); a, b = sorted([(x0, y0), (x1, y1)]); segs.append((l,) + a + b)
    elif w[0] == 'via': vias.append(tuple(map(int, w[1:])))
    elif w[0] == 'mem': mems[int(w[1])][int(w[2])] = int(w[3])
import os; CUTM = int(os.environ.get("CUTM", "4"))
xmin = min(p[2] for p in parts)
cut = xmin + DX - CUTM
cut2 = xmin + 2 * DX - CUTM     # beyond this: the grandchild, ignored
def split(items, fx):
    a = [i for i in items if fx(i) < cut]; b = [i for i in items if cut <= fx(i) < cut2]; return a, b
pa, pb = split(parts, lambda p: p[2])
sa, sb = split(segs, lambda s: s[1])
va, vb = split(vias, lambda v: v[0])
print(f'parent: {len(pa)} parts {len(sa)} segs {len(va)} vias   child: {len(pb)} parts {len(sb)} segs {len(vb)} vias')
ok = True
def merge(S):
    # collinear touching/overlapping segments on a layer are one wire (the builder splits runs longer than 255)
    out = []; g = collections.defaultdict(list)
    for l, x0, y0, x1, y1 in S:
        if x0 == x1: g[(l, 'v', x0)].append((y0, y1))
        else: g[(l, 'h', y0)].append((x0, x1))
    for (l, o, c), iv in g.items():
        iv.sort(); a, b = iv[0]
        for p, q in iv[1:]:
            if p <= b: b = max(b, q)
            else: out.append((l, a, b, c, o)); a, b = p, q
        out.append((l, a, b, c, o))
    return [(l, c, a, c, b) if o == 'v' else (l, a, c, b, c) for l, a, b, c, o in out]
def cmp(name, A, B):
    global ok
    c = collections.Counter(A) - collections.Counter(B); d = collections.Counter(B) - collections.Counter(A)
    print(f'{name}: parent-only {sum(c.values())}  child-only {sum(d.values())}', list(c)[:3], list(d)[:3])
    ok &= not c and not d
cmp('parts', [p[1:] for p in pa], [(p[1], p[2] - DX) + p[3:] for p in pb])
cmp('segs', merge(sa), merge([(s[0], s[1] - DX, s[2], s[3] - DX, s[4]) for s in sb]))
cmp('vias', va, [(v[0] - DX, v[1]) for v in vb])
rom_p = [p[0] for p in pa if p[1] == 2]; rom_c = [p[0] for p in pb if p[1] == 2]
if rom_p and rom_c:
    mp, mc = mems[rom_p[0]], mems[rom_c[0]]
    diff = [a for a in set(mp) | set(mc) if mp.get(a, 0) != mc.get(a, 0)]
    print(f'ROM: parent {len(mp)} bytes, child {len(mc)} bytes, differing addresses {len(diff)}'); ok &= not diff
else:
    print('ROM: child ROM missing'); ok = False
print('QUINE', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
