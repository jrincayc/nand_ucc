#!/usr/bin/env python3
"""mlpa_order.py -- MULTILEVEL label propagation ordering: size-capped LPA, contract the clusters, repeat on the cluster graph with a larger cap; the
resulting tree (gates < clusters < clusters of clusters ...) is flattened by chaining the children of every node greedily (strongest tie to the
last placed siblings).  No placement information is used.  Offline experiment."""
import random, sys, os, collections
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]
import lpa_order
from lpa_order import graph, chain, COUNT


def lpa_w(nodes, adj, vsize, cap, rnd, sweeps=15):
    lab = {v: v for v in nodes}; size = {v: vsize[v] for v in nodes}; order = list(nodes)
    for _ in range(sweeps):
        rnd.shuffle(order); moved = 0; COUNT['m_sweeps'] += 1
        for v in order:
            votes = collections.defaultdict(float); COUNT['m_vertex'] += 1
            for u, w in adj[v].items(): votes[lab[u]] += w; COUNT['m_edge'] += 1
            if not votes: continue
            cur = lab[v]; best = max(votes.values())
            if votes.get(cur, 0) >= best - 1e-12: continue
            cands = [l for l, x in votes.items() if x >= best - 1e-12 and size[l] + vsize[v] <= cap]
            if not cands: continue
            new = rnd.choice(cands); size[cur] -= vsize[v]; size[new] += vsize[v]; lab[v] = new; moved += 1
        if moved == 0: break
    groups = collections.defaultdict(list)
    for v in nodes: groups[lab[v]].append(v)
    return list(groups.values())


def order(nl, caps=(8, 32, 128, 512), seed=1, anchor=True):
    rnd = random.Random(seed); adj0 = graph(nl, anchor=anchor); N = len(nl.nodes) + (1 if anchor else 0)
    lpa_order.adj_g = adj0
    levels = []                                     # per level: (adj, groups(list of member node ids of previous level), vsize)
    nodes = list(range(N)); adj = adj0; vsize = {v: 1 for v in nodes}; trees = {v: v for v in nodes}
    tree = {v: ('leaf', v) for v in nodes}          # node id at this level -> tree
    for cap in caps:
        gs = lpa_w(nodes, adj, vsize, cap, rnd)
        if len(gs) == len(nodes): continue
        gid = {}
        for i, g in enumerate(gs):
            for v in g: gid[v] = i
        nadj = collections.defaultdict(lambda: collections.defaultdict(float))
        for v in nodes:
            for u, w in adj[v].items():
                if gid[u] != gid[v]: nadj[gid[v]][gid[u]] += w
        ntree = {}
        for i, g in enumerate(gs): ntree[i] = ('node', chain([[x] for x in g], adj), g, i)    # chain the children inside the group
        levels.append((adj, gs))
        tree = {i: ('grp', [tree[v] for grp in chain([[x] for x in g], adj) for v in grp]) for i, g in enumerate(gs)}
        nodes = list(range(len(gs))); vsize = {i: sum(vsize[v] for v in g) for i, g in enumerate(gs)}; adj = nadj
    # top: chain the remaining nodes with the top adjacency
    top = [v for grp in chain([[x] for x in nodes], adj) for v in grp]
    out = []
    def flat(t):
        if t[0] == 'leaf': out.append(t[1])
        else:
            for c in t[1]: flat(c)
    for v in top: flat(tree[v])
    # bottom clusters are chained by gate adjacency already (gates chained inside their group); return
    if anchor:
        if out.index(N - 1) < len(out) // 2: out.reverse()
        out.remove(N - 1)
    return out


if __name__ == '__main__':
    import lay
    nl = lay.read_nl(sys.argv[1]); o = order(nl); print(len(o), len(set(o)))
