#!/usr/bin/env python3
"""modnet.py -- a Net whose datapath operations are emitted as MODULE INSTANCES of the textbook library (not, and, or, xor, mux, ha, fa),
the way Y's hd_export wrote them, instead of folded NAND gates.  No structural hashing, no inverter sharing, no module-internal
optimisation: this is the *seed* the module improver starts from.  Constants (0/1) are still folded at generation time.
Code inside `with net.flat(label):` (the microcode PLA and the instruction expander) is built as ordinary hashed NAND gates: a fixed tile.
flatten() -> plain Net (nand/dff only);  to_hd() -> hd.HD (module library + body + ports)."""
import contextlib, os, sys
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]
from netlist import Net
import hd as hdlib

LIB_TEXT = '''
module not 1 1
  g0 = nand i0 i0   # not
  out g0
end
module and 2 1
  g0 = nand i0 i1   # nand of the and
  g1 = nand g0 g0   # and = not(nand)
  out g1
end
module or 2 1
  g0 = nand i0 i0   # not a
  g1 = nand i1 i1   # not b
  g2 = nand g0 g1   # or = nand(not a, not b)
  out g2
end
module xor 2 1
  g0 = nand i1 i1   # not b
  g1 = nand i0 g0   # nand of the and
  g2 = nand g1 g1   # a and not b
  g3 = nand i0 i0   # not a
  g4 = nand g3 i1   # nand of the and
  g5 = nand g4 g4   # not a and b
  g6 = nand g2 g2   # not a
  g7 = nand g5 g5   # not b
  g8 = nand g6 g7   # xor = (a and not b) or (not a and b)
  out g8
end
module mux 3 1
  g0 = nand i2 i2   # not sel
  g1 = nand i0 g0   # nand of the and
  g2 = nand g1 g1   # a and not sel
  g3 = nand i1 i2   # nand of the and
  g4 = nand g3 g3   # b and sel
  g5 = nand g2 g2   # not a
  g6 = nand g4 g4   # not b
  g7 = nand g5 g6   # mux = or(...)
  out g7
end
module ha 2 2
  g0 = nand i1 i1   # not b
  g1 = nand i0 g0   # nand of the and
  g2 = nand g1 g1   # a and not b
  g3 = nand i0 i0   # not a
  g4 = nand g3 i1   # nand of the and
  g5 = nand g4 g4   # not a and b
  g6 = nand g2 g2   # not a
  g7 = nand g5 g5   # not b
  g8 = nand g6 g7   # xor = (a and not b) or (not a and b)
  g9 = nand i0 i1   # nand of the and
  g10 = nand g9 g9   # carry = a and b
  out g8 g10
end
module fa 3 2
  g0 = nand i1 i1   # not b
  g1 = nand i0 g0   # nand of the and
  g2 = nand g1 g1   # a and not b
  g3 = nand i0 i0   # not a
  g4 = nand g3 i1   # nand of the and
  g5 = nand g4 g4   # not a and b
  g6 = nand g2 g2   # not a
  g7 = nand g5 g5   # not b
  g8 = nand g6 g7   # xor = (a and not b) or (not a and b)
  g9 = nand i0 i1   # nand of the and
  g10 = nand g9 g9   # c1 = a and b
  g11 = nand i2 i2   # not b
  g12 = nand g8 g11   # nand of the and
  g13 = nand g12 g12   # a and not b
  g14 = nand g8 g8   # not a
  g15 = nand g14 i2   # nand of the and
  g16 = nand g15 g15   # not a and b
  g17 = nand g13 g13   # not a
  g18 = nand g16 g16   # not b
  g19 = nand g17 g18   # xor = (a and not b) or (not a and b)
  g20 = nand g8 i2   # nand of the and
  g21 = nand g20 g20   # c2 = s1 and cin
  g22 = nand g10 g10   # not a
  g23 = nand g21 g21   # not b
  g24 = nand g22 g23   # carry = c1 or c2
  out g19 g24
end
'''
LIB = hdlib.read(LIB_TEXT)


class ModNet(Net):
    def __init__(self):
        super().__init__()
        self.flat_mode = False; self.insts = []; self.regions = []

    @contextlib.contextmanager
    def flat(self, label):
        lo = len(self.kind); old = self.flat_mode; self.flat_mode = True
        try: yield
        finally:
            self.flat_mode = old; self.regions.append((lo, len(self.kind), label))

    def const_node(self, v):
        """constants that reach a module input are real gates: n = nand(rom0,rom0); one = nand(rom0, n); zero = nand(one, one)  (as in Y)"""
        if not hasattr(self, '_one'):
            r0 = self.inputs['rom0']
            self.kind.append(('nand', r0, r0)); n = len(self.kind) - 1
            self.kind.append(('nand', r0, n)); self._one = len(self.kind) - 1
            self.kind.append(('nand', self._one, self._one)); self._zero = len(self.kind) - 1
            self.regions.append((n, self._zero + 1, 'constants'))
        return self._one if v == 1 else self._zero

    def _mod(self, t, ins, nout=1):
        ins = [self.const_node(x) if x in (0, 1) else x for x in ins]
        i = len(self.insts); outs = []
        for j in range(nout):
            n = len(self.kind); self.kind.append(('mod', t, tuple(ins), j, i)); outs.append(n)
        self.insts.append((t, tuple(ins), tuple(outs)))
        return outs

    # ---- module-mode operations (constants folded, nothing shared)
    def not_(self, a):
        if self.flat_mode or a in (0, 1): return super().not_(a)
        return self._mod('not', [a])[0]

    def and_(self, a, b):
        if self.flat_mode: return super().and_(a, b)
        if a == 0 or b == 0: return 0
        if a == 1: return b
        if b == 1: return a
        if a == b: return a
        return self._mod('and', [a, b])[0]

    def or_(self, a, b):
        if self.flat_mode: return super().or_(a, b)
        if a == 1 or b == 1: return 1
        if a == 0: return b
        if b == 0: return a
        if a == b: return a
        return self._mod('or', [a, b])[0]

    def xor(self, a, b):
        if self.flat_mode: return super().xor(a, b)
        if a == 0: return b
        if b == 0: return a
        if a == 1: return self.not_(b)
        if b == 1: return self.not_(a)
        if a == b: return 0
        return self._mod('xor', [a, b])[0]

    def mux(self, s, a, b):
        if self.flat_mode: return super().mux(s, a, b)
        if s == 0: return a
        if s == 1: return b
        if a == b: return a
        return self._mod('mux', [a, b, s])[0]

    def or_n(self, xs):
        if self.flat_mode: return super().or_n(xs)
        xs = [x for x in xs if x != 0]
        if any(x == 1 for x in xs): return 1
        if not xs: return 0
        r = xs[0]
        for x in xs[1:]: r = self.or_(r, x)
        return r

    def and_or(self, pairs):
        if self.flat_mode: return super().and_or(pairs)
        return self.or_n([self.and_(s, v) for s, v in pairs])

    def full_adder(self, a, b, c):
        if self.flat_mode: return super().full_adder(a, b, c)
        if c == 0:
            s, co = self._mod('ha', [a, b], 2); return s, co
        s, co = self._mod('fa', [a, b, c], 2); return s, co

    # ---- analysis
    def used_nodes(self, roots):
        seen = set(); stack = [r for r in roots if r > 1]
        while stack:
            n = stack.pop()
            if n in seen: continue
            seen.add(n); k = self.kind[n]
            if k[0] == 'mod':
                ins = list(k[2]) + list(self.insts[k[4]][2])
            else: ins = k[1:] if k[0] != 'in' else []
            for s in ins:
                if s > 1 and s not in seen: stack.append(s)
        return seen

    def counts(self, roots):
        """(module instance counts by type, flat NAND count, DFF count, total NAND count) among nodes reachable from roots"""
        used = self.used_nodes(roots); inst = set(); flat_n = 0; dff = 0; byt = {}
        for n in used:
            k = self.kind[n]
            if k[0] == 'mod':
                if k[4] not in inst: inst.add(k[4]); byt[k[1]] = byt.get(k[1], 0) + 1
            elif k[0] == 'nand': flat_n += 1
            elif k[0] == 'dff': dff += 1
        gates = flat_n + sum(LIB.module(t).n_gates() * c for t, c in byt.items())
        return byt, flat_n, dff, gates

    def flatten(self, roots, ports, state):
        """expand every reachable module instance with the library -> (plain Net, ports', state') ; nand/dff only, no sharing"""
        used = sorted(self.used_nodes(roots)); F = Net(); mp = {0: 0, 1: 1}; done = set()
        for n in used:
            k = self.kind[n]
            if k[0] == 'in': mp[n] = F.inp(k[1])
            elif k[0] == 'dff': mp[n] = F.dff(self.names.get(n))
        for n in used:
            k = self.kind[n]
            if k[0] == 'nand':
                F.kind.append(('nand', mp[k[1]], mp[k[2]])); mp[n] = len(F.kind) - 1
            elif k[0] == 'mod' and k[4] not in done:
                done.add(k[4]); t, ins, outs = self.insts[k[4]]; m = LIB.module(t)
                sig = [mp[x] for x in ins]
                for a, b in m.gates:
                    F.kind.append(('nand', sig[a], sig[b])); sig.append(len(F.kind) - 1)
                for o, j in zip(outs, m.outs): mp[o] = sig[j]
        for n in used:
            k = self.kind[n]
            if k[0] == 'dff': F.kind[mp[n]][1] = mp[k[1]]
        def mapv(v): return [mapv(x) for x in v] if isinstance(v, list) else mp[v]
        return F, {p: mp[s] for p, s in ports.items()}, {p: mapv(v) for p, v in state.items()}
