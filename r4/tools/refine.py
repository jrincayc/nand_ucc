#!/usr/bin/env python3
"""refine.py -- gate-level 2-D placement refinement for rowchan: start from a (row, col) placement (default the serpentine fold), anneal gate moves/swaps
within a window on the proxy  sum over nets of (trunk length per used row, extended to the net's mean column) + alpha * row span.  Offline reference."""
import math, random, sys, os
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]
from modplace import nets_of


def serp(N, R):
    cols = -(-N // R); rc = []
    for k in range(N):
        r = k // cols; j = k % cols; rc.append((r, cols - 1 - j if r % 2 else j))
    return rc, cols


def refine(nl, R, iters=400000, seed=1, alpha=8.0, win=(2, 40), T0=6.0, T1=0.15, slack=1.04, rc=None):
    N = len(nl.nodes); rc0, cols0 = serp(N, R)
    rc = list(rc0) if rc is None else list(rc); cols = int(cols0 * slack) + 1       # a little slack so that gates can move
    nets = nets_of(nl); PS = N          # pseudo node N = the parts (ROM, ARM, RAM) at the right end of the last row
    drvnet = {}
    for i, n in enumerate(nets):
        pass
    # nets keyed by driver: rebuild so that part pins can be added
    pins = {}
    for k, (kind, ins) in enumerate(nl.nodes):
        pins.setdefault(k, {k})
        for t in ins:
            b = t.split('@')[0]
            if b.startswith('n') and b[1:].isdigit(): pins.setdefault(int(b[1:]), {int(b[1:])}).add(k)
            elif b.startswith('rom') or b.startswith('ramo'): pins.setdefault(b, {PS}).add(k)
    for name, t in nl.ports:
        b = t.split('@')[0]
        if b.startswith('n') and b[1:].isdigit(): pins.setdefault(int(b[1:]), {int(b[1:])}).add(PS)
    nets = [sorted(v) for v in pins.values() if len(v) > 1]
    un = [[] for _ in range(N)]
    for i, n in enumerate(nets):
        for k in n:
            if k < N: un[k].append(i)
    rc.append((R - 1, cols + 4)); occ = {rc[k]: k for k in range(N)}
    def cost_net(i):
        n = nets[i]; rows = {}; sm = 0
        for k in n: r, c = rc[k]; rows.setdefault(r, []).append(c); sm += c
        mean = sm / len(n)
        if len(rows) == 1:
            cs = next(iter(rows.values())); return max(cs) - min(cs)
        return sum(max(max(cs), mean) - min(min(cs), mean) for cs in rows.values()) + alpha * (max(rows) - min(rows))
    cost = [cost_net(i) for i in range(len(nets))]; tot0 = tot = sum(cost); rnd = random.Random(seed)
    cool = (T1 / T0) ** (1.0 / iters); T = T0
    for it in range(iters):
        a = rnd.randrange(N); r, c = rc[a]
        nr = min(R - 1, max(0, r + rnd.randint(-win[0], win[0]))); nc = min(cols - 1, max(0, c + rnd.randint(-win[1], win[1])))
        if (nr, nc) == (r, c): continue
        b = occ.get((nr, nc))
        touched = set(un[a]) | (set(un[b]) if b is not None else set())
        rc[a] = (nr, nc)
        if b is not None: rc[b] = (r, c)
        new = {i: cost_net(i) for i in touched}; d = sum(new[i] - cost[i] for i in touched)
        if d <= 0 or rnd.random() < math.exp(-d / T):
            for i in touched: cost[i] = new[i]
            tot += d
            if b is None: del occ[(r, c)]
            occ[(nr, nc)] = a
            if b is not None: occ[(r, c)] = b
        else:
            rc[a] = (r, c)
            if b is not None: rc[b] = (nr, nc)
        T *= cool
    rc.pop(); return rc, tot0, tot


if __name__ == '__main__':
    import lay
    nl = lay.read_nl(sys.argv[1]); rc, a, b = refine(nl, int(sys.argv[2])); print(a, '->', b)
