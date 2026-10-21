#!/usr/bin/env python3
"""pla.py -- Quine-McCluskey minimiser (small, exact primes + greedy cover) and NAND-NAND synthesis of sum-of-products."""
import itertools


def primes(nvars, on, dc):
    """prime implicants as (mask, value): mask has 1 for specified literals."""
    full = (1 << nvars) - 1
    cur = {(full, m) for m in set(on) | set(dc)}
    allp = set()
    while cur:
        nxt = set(); used = set()
        byc = {}
        for c in cur: byc.setdefault(c[0], []).append(c)
        for mask, cs in byc.items():
            vals = {v for _, v in cs}
            for _, v in cs:
                for bit in range(nvars):
                    if mask >> bit & 1 and (v ^ (1 << bit)) in vals:
                        nxt.add((mask & ~(1 << bit), v & ~(1 << bit))); used.add((mask, v)); used.add((mask, v ^ (1 << bit)))
        allp |= cur - used
        cur = nxt
    return allp


def cover(nvars, on, dc, ps=None):
    on = set(on)
    if not on: return []
    ps = ps if ps is not None else primes(nvars, on, dc)
    ps = list(ps)
    covers = {p: {m for m in on if (m & p[0]) == p[1]} for p in ps}
    ps = [p for p in ps if covers[p]]
    chosen = []; left = set(on)
    # essential primes
    for m in sorted(on):
        cs = [p for p in ps if m in covers[p]]
        if len(cs) == 1 and cs[0] not in chosen: chosen.append(cs[0]); left -= covers[cs[0]]
    while left:
        best = max(ps, key=lambda p: (len(covers[p] & left), -bin(p[0]).count('1')))
        chosen.append(best); left -= covers[best]
    return chosen


def synth(net, vars_, cubes):
    """vars_[i] = signal of variable i.  cubes (mask, value) -> signal (OR of ANDs)."""
    terms = []
    for mask, val in cubes:
        lits = []
        for i in range(len(vars_) - 1, -1, -1):
            if mask >> i & 1: lits.append(vars_[i] if val >> i & 1 else net.not_(vars_[i]))
        terms.append(net.and_n(lits))
    return net.or_n(terms)
