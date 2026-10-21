#!/usr/bin/env python3
"""netlist.py -- NAND/DFF netlist builder with constant folding and structural hashing, plus exporters (C simulator source, HD text).
Signals are small ints: 0 = constant 0, 1 = constant 1, >= 2 = node ids.  Node kinds: input, nand, dff."""
import itertools


class Net:
    def __init__(self):
        self.kind = [None, None]          # per node: ('in', name) | ('nand', a, b) | ('dff', d)
        self.hash = {}
        self.inv_of = {}                  # node -> x when node == nand(x, x)
        self.inputs = {}
        self.names = {}                   # node -> debug name

    # ------------------------------------------------------------------ primitives
    def inp(self, name):
        n = len(self.kind); self.kind.append(('in', name)); self.inputs[name] = n; self.names[n] = name; return n

    def dff(self, name=None):
        n = len(self.kind); self.kind.append(['dff', None]); 
        if name: self.names[n] = name
        return n

    def set_d(self, q, d):
        assert self.kind[q][0] == 'dff' and self.kind[q][1] is None, 'dff already driven'
        if d in (0, 1): raise ValueError('constant D input: ' + self.names.get(q, str(q)))
        self.kind[q][1] = d

    def nand(self, a, b):
        if a == 0 or b == 0: return 1
        if a == 1: return self.not_(b)
        if b == 1: return self.not_(a)
        if a > b: a, b = b, a
        if a == b: return self.not_(a)
        if self.inv_of.get(a) == b or self.inv_of.get(b) == a: return 1
        key = (a, b)
        n = self.hash.get(key)
        if n is None:
            n = len(self.kind); self.kind.append(('nand', a, b)); self.hash[key] = n
        return n

    def not_(self, a):
        if a == 0: return 1
        if a == 1: return 0
        if a in self.inv_of: return self.inv_of[a]
        key = (a, a)
        n = self.hash.get(key)
        if n is None:
            n = len(self.kind); self.kind.append(('nand', a, a)); self.hash[key] = n; self.inv_of[n] = a
        return n

    # ------------------------------------------------------------------ derived
    def and_(self, a, b): return self.not_(self.nand(a, b))
    def or_(self, a, b): return self.nand(self.not_(a), self.not_(b))
    def nor(self, a, b): return self.not_(self.or_(a, b))

    def and_n(self, xs):
        xs = [x for x in xs if x != 1]
        if any(x == 0 for x in xs): return 0
        if not xs: return 1
        r = xs[0]
        for x in xs[1:]: r = self.and_(r, x)
        return r

    def nand_n(self, xs): return self.not_(self.and_n(xs))

    def or_n(self, xs):
        xs = [x for x in xs if x != 0]
        if any(x == 1 for x in xs): return 1
        if not xs: return 0
        # NAND of inverted inputs, tree of nand/and alternation: or(a,b,c) = nand(~a, ~b, ~c) built as nand(and(~a,~b), ~c)
        nots = [self.not_(x) for x in xs]
        return self.nand_n(nots)

    def xor(self, a, b):
        if a == 0: return b
        if b == 0: return a
        if a == 1: return self.not_(b)
        if b == 1: return self.not_(a)
        if a == b: return 0
        n = self.nand(a, b)
        return self.nand(self.nand(a, n), self.nand(b, n))

    def xnor(self, a, b): return self.not_(self.xor(a, b))

    def mux(self, s, a, b):
        """s ? b : a"""
        if s == 0: return a
        if s == 1: return b
        if a == b: return a
        return self.nand(self.nand(a, self.not_(s)), self.nand(b, s))

    def and_or(self, pairs):
        """OR of (sel AND val) terms, as NAND-NAND."""
        ts = []
        for s, v in pairs:
            if s == 0 or v == 0: continue
            ts.append(self.nand(s, v))
        if not ts: return 0
        if any(t == 1 for t in ts) and False: pass
        return self.nand_n_of_nands(ts)

    def nand_n_of_nands(self, ts):
        """out = NAND(t1, t2, ...)  where each ti = nand(...)  -> OR of the underlying products"""
        ts = [t for t in ts if t != 1]
        if not ts: return 0
        return self.nand_n(ts)

    # ------------------------------------------------------------------ buses
    def mux_bus(self, s, a, b): return [self.mux(s, x, y) for x, y in zip(a, b)]

    def full_adder(self, a, b, c):
        x = self.xor(a, b)
        s = self.xor(x, c)
        n1 = self.nand(a, b); n2 = self.nand(x, c)
        return s, self.nand(n1, n2)

    # ------------------------------------------------------------------ analysis
    def n_gates(self):
        return sum(1 for k in self.kind[2:] if k[0] == 'nand'), sum(1 for k in self.kind[2:] if k[0] == 'dff')

    def used_nodes(self, roots):
        seen = set(); stack = [r for r in roots if r > 1]
        while stack:
            n = stack.pop()
            if n in seen: continue
            seen.add(n)
            k = self.kind[n]
            for s in (k[1:] if k[0] != 'in' else []):
                if s > 1 and s not in seen: stack.append(s)
        return seen
