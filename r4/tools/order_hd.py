#!/usr/bin/env python3
"""order_hd.py IN.hd OUT.hd [iters] -- reorder the BODY of a module HD to shorten the nets of the 1-D strip placement (the placement order is the
body order).  Offline step: simulated annealing on total net span over body units (instances), deterministic (fixed seed).  The module
library and the function are untouched; ref_improve keeps the body order, so the improved HD inherits it."""
import os, sys, random, math
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]
import hd as hdlib


def units_graph(h):
    drv = {}                                            # ref name -> unit
    for u, it in enumerate(h.body):
        n = h.out_count(it.type)
        if n == 1: drv[it.name] = u
        else:
            for j in range(n): drv[f'{it.name}.{j}'] = u
    nets = {}
    for u, it in enumerate(h.body):
        for r in it.refs:
            if r in drv: nets.setdefault(drv[r], set()).add(u)
    for u in nets: nets[u].add(u)
    return [sorted(v) for v in nets.values() if len(v) > 1]


def anneal(nets, N, iters, seed=1, maxfan=14):
    rnd = random.Random(seed); pos = list(range(N)); at = list(range(N))
    un = [[] for _ in range(N)]
    for i, ns in enumerate(nets):
        for u in ns: un[u].append(i)
    def span(i): ps = [pos[x] for x in nets[i]]; return max(ps) - min(ps)
    cur = sum(span(i) for i in range(len(nets))); start = cur; T0, T1 = 6.0, 0.05
    cool = (T1 / T0) ** (1.0 / iters); T = T0
    small = [i for i in range(len(nets)) if len(nets[i]) <= maxfan]
    for it in range(iters):
        a = rnd.randrange(N)
        if not un[a]: continue
        ni = rnd.choice(un[a])
        if len(nets[ni]) > maxfan: continue
        b = rnd.choice(nets[ni])
        if a == b: continue
        tgt = pos[b] + rnd.choice((-1, 1))
        if tgt < 0 or tgt >= N: continue
        c = at[tgt]
        if c == a: continue
        pa = pos[a]; aff = set(un[a]) | set(un[c])
        before = sum(span(i) for i in aff)
        pos[a], pos[c] = tgt, pa; at[tgt] = a; at[pa] = c
        dl = sum(span(i) for i in aff) - before
        if dl <= 0 or rnd.random() < math.exp(-dl / T): cur += dl
        else: pos[a], pos[c] = pa, tgt; at[pa] = a; at[tgt] = c
        T *= cool
    return at, start, cur


if __name__ == '__main__':
    h = hdlib.read(open(sys.argv[1]).read()); iters = int(sys.argv[3]) if len(sys.argv) > 3 else 3000000
    nets = units_graph(h); N = len(h.body)
    at, s0, s1 = anneal(nets, N, iters)
    print(f'{N} units, {len(nets)} nets, total span {s0} -> {s1}')
    h.body = [h.body[u] for u in at]
    open(sys.argv[2], 'w').write(hdlib.write(h))
