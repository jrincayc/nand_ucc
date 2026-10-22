#!/usr/bin/env python3
"""lpa_order.py -- netlist ordering by size-capped label propagation, applied hierarchically (clusters of clusters), then a greedy chain of the clusters.
Linear work per sweep, no placement information needed.  Offline experiment."""
import random, sys, os, collections
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]
from modplace import nets_of


def nets_anchored(nl):
    """nets with a pseudo node N standing for the parts (ROM, ARM, RAM)"""
    N = len(nl.nodes); pins = {}
    for k, (kind, ins) in enumerate(nl.nodes):
        pins.setdefault(k, {k})
        for t in ins:
            b = t.split('@')[0]
            if b.startswith('n') and b[1:].isdigit(): pins.setdefault(int(b[1:]), {int(b[1:])}).add(k)
            elif b.startswith('rom') or b.startswith('ramo'): pins.setdefault(b, {N}).add(k)
    for name, t in nl.ports:
        b = t.split('@')[0]
        if b.startswith('n') and b[1:].isdigit(): pins.setdefault(int(b[1:]), {int(b[1:])}).add(N)
    return [sorted(v) for v in pins.values() if len(v) > 1]


COUNT = collections.Counter()


def graph(nl, maxfan=12, anchor=False):
    adj = collections.defaultdict(lambda: collections.defaultdict(float))
    for n in (nets_anchored(nl) if anchor else nets_of(nl)):
        if len(n) > maxfan: continue
        w = 1.0 / (len(n) - 1)
        for i in n:
            for j in n:
                if i != j: adj[i][j] += w
    return adj


def lpa(nodes, adj, cap, rnd, sweeps=15):
    lab = {v: v for v in nodes}; size = collections.Counter(lab.values()); ins = set(nodes)
    order = list(nodes)
    for _ in range(sweeps):
        rnd.shuffle(order); moved = 0; COUNT['sweeps'] += 1
        for v in order:
            votes = collections.defaultdict(float); COUNT['vertex_visits'] += 1
            for u, w in adj[v].items():
                COUNT['edge_visits'] += 1
                if u in ins: votes[lab[u]] += w; COUNT['edge_in_set'] += 1
            COUNT['vote_entries'] += len(votes)
            if not votes: continue
            cur = lab[v]; best = max(votes.values())
            cands = [l for l, x in votes.items() if x >= best - 1e-12 and (l == cur or size[l] < cap)]
            if not cands or cur in cands and votes.get(cur, 0) >= best - 1e-12: continue
            new = rnd.choice(cands)
            size[cur] -= 1; size[new] += 1; lab[v] = new; moved += 1
        if moved == 0: break
    groups = collections.defaultdict(list)
    for v in nodes: groups[lab[v]].append(v)
    return list(groups.values())


def chain(groups, adj):
    """greedy chain of groups: next = the unplaced group most connected to the last placed ones"""
    if len(groups) <= 1: return groups
    gid = {}
    for i, g in enumerate(groups):
        for v in g: gid[v] = i
    cw = collections.defaultdict(lambda: collections.defaultdict(float))
    for v in gid:
        for u, w in adj[v].items():
            COUNT['chain_edge_visits'] += 1
            if u in gid and gid[u] != gid[v]: cw[gid[v]][gid[u]] += w
    left = set(range(len(groups))); cur = max(left, key=lambda i: sum(cw[i].values())); out = [cur]; left.remove(cur)
    while left:
        sc = collections.defaultdict(float)
        for k, g in enumerate(reversed(out[-3:])):
            for j, w in cw[g].items():
                if j in left: sc[j] += w / (k + 1)
        nxt = max(sc, key=sc.get) if sc else min(left)
        out.append(nxt); left.remove(nxt); COUNT['chain_steps'] += 1; COUNT['chain_scan'] += len(left)
    return [groups[i] for i in out]


def bfs(nodes):
    ins = set(nodes); seen = set(); out = []
    deg = lambda v: sum(w for u, w in adj_g[v].items() if u in ins)
    for st in sorted(nodes, key=lambda v: -deg(v)):
        if st in seen: continue
        q = [st]; seen.add(st)
        while q:
            v = q.pop(0); out.append(v)
            COUNT['bfs_edge_visits'] += len(adj_g[v])
            for u in sorted(adj_g[v], key=lambda u: -adj_g[v][u]):
                if u in ins and u not in seen: seen.add(u); q.append(u)
    return out


def order(nl, caps=(480, 120, 30), seed=1, anchor=False):
    global adj_g
    rnd = random.Random(seed); adj = adj_g = graph(nl, anchor=anchor); N = len(nl.nodes)
    def rec(nodes, lvl):
        if lvl >= len(caps) or len(nodes) <= caps[-1]:
            return bfs(nodes)          # leaf: breadth-first order from the best connected gate (no use of the generator order)
        gs = lpa(nodes, adj, caps[lvl], rnd)
        if len(gs) == 1: return rec(nodes, lvl + 1)
        out = []
        for g in chain(gs, adj): out += rec(g, lvl + 1)
        return out
    o = rec(list(range(N + (1 if anchor else 0))), 0)
    if anchor:
        if o.index(N) < len(o) // 2: o.reverse()        # the parts end up at the end (last rows, right side)
        o.remove(N)
    return o


if __name__ == '__main__':
    import lay
    nl = lay.read_nl(sys.argv[1]); o = order(nl); print(len(o), len(set(o)))
