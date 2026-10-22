#!/usr/bin/env python3
"""place_ref.py -- NORMATIVE integer-only reference of the in-world placement order (multilevel size-capped label propagation + greedy chaining).
Everything an RV32EC program has to reproduce bit for bit: u8 pair weights, u32 xorshift PRNG, Fisher-Yates shuffle per sweep, first-maximum tie rule,
integer chain scores.  order(nl, caps, seed) -> list of gate indices (rank -> gate).  Used with rowchan.layout (serpentine fold) for the layout."""
import sys, os
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]

MAXFAN = 12; WSCALE = 60; SWEEPS = 15


class Rng:
    def __init__(self, seed): self.s = (seed * 2654435761 + 1) & 0xFFFFFFFF or 1
    def next(self):
        x = self.s; x ^= (x << 13) & 0xFFFFFFFF; x ^= x >> 17; x ^= (x << 5) & 0xFFFFFFFF; self.s = x; return x
    def below(self, n): return ((self.next() >> 8) * n) >> 24          # 24-bit fraction times n: no division


def nets_anchored(nl):
    N = len(nl.nodes); pins = {}
    for k, (kind, ins) in enumerate(nl.nodes):
        pins.setdefault(k, [k])
        for t in ins:
            b = t.split('@')[0]
            if b.startswith('n') and b[1:].isdigit():
                d = int(b[1:]); pins.setdefault(d, [d])
                if k not in pins[d]: pins[d].append(k)
            elif b.startswith('rom') or b.startswith('ramo'):
                pins.setdefault(b, [N])
                if k not in pins[b]: pins[b].append(k)
    for name, t in nl.ports:
        b = t.split('@')[0]
        if b.startswith('n') and b[1:].isdigit():
            d = int(b[1:]); pins.setdefault(d, [d])
            if N not in pins[d]: pins[d].append(N)
    return [v for v in pins.values() if len(v) > 1]


def build_graph(nl):
    N = len(nl.nodes) + 1; adj = [dict() for _ in range(N)]
    for n in nets_anchored(nl):
        if len(n) > MAXFAN: continue
        w = WSCALE // (len(n) - 1)
        for a in n:
            for b in n:
                if a != b: adj[a][b] = min(65535, adj[a].get(b, 0) + w)
    return adj


def lpa(nodes, adj, vsize, cap, rng):
    lab = {v: v for v in nodes}; size = {v: vsize[v] for v in nodes}; order = list(nodes)
    for _ in range(SWEEPS):
        for i in range(len(order) - 1, 0, -1):
            j = rng.below(i + 1); order[i], order[j] = order[j], order[i]
        moved = 0
        for v in order:
            votes = {}
            for u, w in adj[v].items():
                l = lab[u]; votes[l] = votes.get(l, 0) + w            # dict keeps first-touch order, like the touched list
            if not votes: continue
            best = max(votes.values()); cur = lab[v]
            if votes.get(cur, 0) >= best: continue
            new = None
            for l, x in votes.items():
                if x == best and size[l] + vsize[v] <= cap: new = l; break
            if new is None: continue
            size[cur] -= vsize[v]; size[new] += vsize[v]; lab[v] = new; moved += 1
        if not moved: break
    groups = {}
    for v in nodes: groups.setdefault(lab[v], []).append(v)
    return list(groups.values())


def chain(items, adj):
    """items: list of lists of node ids (all in one parent).  adj over those nodes' ids.  returns the items in chain order"""
    if len(items) <= 1: return items
    gid = {}
    for i, g in enumerate(items):
        for v in g: gid[v] = i
    cw = [dict() for _ in items]
    for v, i in gid.items():
        for u, w in adj[v].items():
            j = gid.get(u)
            if j is not None and j != i: cw[i][j] = cw[i].get(j, 0) + w
    left = set(range(len(items)))
    cur = max(sorted(left), key=lambda i: sum(cw[i].values())); out = [cur]; left.discard(cur)
    while left:
        sc = {}
        for k, g in enumerate(reversed(out[-3:])):
            mul = (6, 3, 2)[k]
            for j, w in cw[g].items():
                if j in left: sc[j] = sc.get(j, 0) + w * mul
        nxt = max(sorted(sc), key=lambda j: sc[j]) if sc else min(left)
        out.append(nxt); left.discard(nxt)
    return [items[i] for i in out]


def order(nl, caps=(8, 32, 128, 512), seed=1):
    rng = Rng(seed); adj = build_graph(nl); N = len(nl.nodes) + 1
    nodes = list(range(N)); vsize = {v: 1 for v in nodes}; tree = {v: v for v in nodes}
    cur_adj = adj
    for cap in caps:
        gs = lpa(nodes, cur_adj, vsize, cap, rng)
        if len(gs) == len(nodes): continue
        gid = {}
        for i, g in enumerate(gs):
            for v in g: gid[v] = i
        nadj = [dict() for _ in gs]
        for v in nodes:
            for u, w in cur_adj[v].items():
                if gid[u] != gid[v]: nadj[gid[v]][gid[u]] = min(65535, nadj[gid[v]].get(gid[u], 0) + w)
        tree = {i: [tree[v] for grp in chain([[x] for x in g], cur_adj) for v in grp] for i, g in enumerate(gs)}
        vsize = {i: sum(vsize[v] for v in g) for i, g in enumerate(gs)}; nodes = list(range(len(gs))); cur_adj = nadj
    top = [v for grp in chain([[x] for x in nodes], cur_adj) for v in grp]
    out = []
    def flat(t):
        if isinstance(t, int): out.append(t)
        else:
            for c in t: flat(c)
    for v in top: flat(tree[v])
    if out.index(N - 1) < len(out) // 2: out.reverse()
    out.remove(N - 1)
    return out
