"""E3 (binary-level feasibility, X): relabel RAM variable addresses in the ROM image and verify by emulation."""
import audit, itertools, random, json
from collections import Counter
audit.init('X'); G = audit.G; img = bytes(G['img']); n = G['n']; fe = G['fetched']
RAMN = G['ramn']
def word(b, o): return b[o] | b[o+1] << 8
def isA(w): return w < 0x8000
def uses_mem(w):
    if (w >> 13) == 0b110: return True            # AP
    if (w >> 13) == 0b111: return bool(w >> 12 & 1) or bool(w >> 3 & 1)   # a bit or dest M
    return False
refs = []   # byte offsets of executed A-instructions that name a RAM variable
for o in range(0, n - 3, 2):
    if fe[o] & 1 and fe[o+1] & 2 and fe[o+2] & 1:
        w = word(img, o)
        if isA(w) and w < RAMN and uses_mem(word(img, o+2)): refs.append(o)
vals = Counter(word(img, o) for o in refs)
print('var-ref A-instructions', len(refs), 'distinct RAM addresses used', len(vals), sorted(vals.items()))
def relabel(perm):
    m = bytearray(img)
    for o in refs:
        w = word(img, o); v = perm.get(w, w)
        m[o] = v & 255; m[o+1] = (m[o+1] & 0x80) | (v >> 8)
    return m
def ok(perm): return audit.classify(relabel(perm))
print('identity', ok({}))
used = sorted(vals)
res = {}
for i, j in itertools.combinations(range(RAMN), 2):
    if i in vals or j in vals:
        res[(i, j)] = ok({i: j, j: i})
c = Counter(res.values()); print('transpositions', c)
good = [p for p, r in res.items() if r == 'FIX']
print('verified FIX transpositions', len(good), good[:40])
for s in (1, 2, -1, -2):
    perm = {v: v + s for v in used}
    if all(0 <= v + s < RAMN for v in used): print('shift', s, ok(perm))
json.dump({'good': good, 'counts': {str(k): v for k, v in c.items()}}, open('e3x.json', 'w'))
