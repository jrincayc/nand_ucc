#!/usr/bin/env python3
"""modplace.py -- module-level placement for rowchan: the netlist order is cut into clusters ("modules") of S consecutive gates, each cluster is a
rectangle of h rows x w columns (serpentine inside), and the clusters are placed on a grid of GR cluster rows x GC cluster columns by simulated annealing
on a trunk-length proxy.  returns rc = [(row, col)] per node.  Offline reference."""
import math, random, sys, os
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]


def nets_of(nl):
    pins = {}
    for k, (kind, ins) in enumerate(nl.nodes):
        pins.setdefault(k, [k])
        for s in ins:
            if s.startswith('n') and s[1:].split('@')[0].isdigit(): pins.setdefault(int(s[1:].split('@')[0]), []).append(k)
    return [sorted(set(v)) for v in pins.values() if len(set(v)) > 1]


def place(nl, h=4, w=15, GR=5, seed=1, iters=40000, alpha=6.0):
    N = len(nl.nodes); S = h * w; nc = -(-N // S); GC = -(-nc // GR)
    assert GR * GC >= nc
    nets = nets_of(nl)
    cl = lambda k: k // S
    def inner(k):                       # (row, col) inside the cluster, serpentine along rows of width w
        i = k % S; r = i // w; c = i % w
        return r, (w - 1 - c if r % 2 else c)
    slot = list(range(GR * GC)); random.Random(seed).shuffle(slot); slot = slot[:nc] if False else slot
    pos = {c: slot[c] for c in range(nc)}        # cluster -> slot index
    used = set(pos.values())
    def xy(k, pos):
        s = pos[cl(k)]; gr, gc = s // GC, s % GC; r, c = inner(k); return gr * h + r, gc * w + c
    cnets = {}
    for i, n in enumerate(nets):
        for c in {cl(k) for k in n}: cnets.setdefault(c, []).append(i)
    def cost_net(n, pos):
        ps = [xy(k, pos) for k in n]; rows = {}
        for r, c in ps: rows.setdefault(r, []).append(c)
        mean = sum(c for r, c in ps) / len(ps)
        tl = sum(max(max(cs), mean) - min(min(cs), mean) for cs in rows.values()) if len(rows) > 1 else max(c for r, c in ps) - min(c for r, c in ps)
        return tl + alpha * (max(rows) - min(rows))
    cost = [cost_net(n, pos) for n in nets]; tot = sum(cost); rnd = random.Random(seed + 1)
    T = 30.0; T1 = 0.3; cool = (T1 / T) ** (1.0 / iters)
    free = [s for s in range(GR * GC) if s not in used]
    for it in range(iters):
        a = rnd.randrange(nc)
        if free and rnd.random() < 0.2:
            fi = rnd.randrange(len(free)); sa = pos[a]; sb = free[fi]; b = None
        else:
            b = rnd.randrange(nc)
            if a == b: continue
            sa, sb = pos[a], pos[b]
        old = pos.copy() if False else None
        touched = set(cnets.get(a, [])) | (set(cnets.get(b, [])) if b is not None else set())
        pos[a] = sb
        if b is not None: pos[b] = sa
        new = {i: cost_net(nets[i], pos) for i in touched}
        d = sum(new[i] - cost[i] for i in touched)
        if d <= 0 or rnd.random() < math.exp(-d / T):
            for i in touched: cost[i] = new[i]
            tot += d
            if b is None: free[fi] = sa
        else:
            pos[a] = sa
            if b is not None: pos[b] = sb
        T *= cool
    return [xy(k, pos) for k in range(N)], tot, sum(cost_net(n, {c: (c // GC if False else c) for c in range(nc)}) for n in nets) if False else tot


if __name__ == '__main__':
    import lay
    nl = lay.read_nl(sys.argv[1]); rc, tot, _ = place(nl); print('cost', tot)
