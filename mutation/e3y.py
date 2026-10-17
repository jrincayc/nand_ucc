import json, random, math, itertools
exec(open('e3x.py').read().split("print('identity'")[0])   # re-use setup (refs, relabel, ok)
good = set(map(tuple, json.load(open('e3x.json'))['good']))
adj = {a: set() for a in range(RAMN)}
for i, j in good: adj[i].add(j); adj[j].add(i)
# greedy clique of mutually-swappable addresses
best = []
rng = random.Random(1)
for t in range(300):
    order = list(range(RAMN)); rng.shuffle(order); S = []
    for a in order:
        if all(a in adj[b] for b in S): S.append(a)
    if len(S) > len(best): best = S
S = sorted(best); print('clique size', len(S), S)
# all-permutation tests
def trial(S, k):
    r = Counter()
    for _ in range(k):
        T = S[:]; rng.shuffle(T); r[ok(dict(zip(S, T)))] += 1
    return r
print('random perms of clique', trial(S, 150))
# injective random relabel of all used addresses into 32 slots
r = Counter()
for _ in range(150):
    T = list(range(RAMN)); rng.shuffle(T); r[ok({a: T[a] for a in range(RAMN)})] += 1
print('uniform random full permutation of 32 addresses', r)
print('log2(|S|!) =', math.log2(math.factorial(len(S))), ' log2(32!) =', math.log2(math.factorial(32)))
