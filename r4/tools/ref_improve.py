#!/usr/bin/env python3
"""ref_improve.py -- NORMATIVE reference for the hardware improver (copied unchanged from nandgen/y/tools/ref_improve.py, Y_SPEC.md section 6).
The ROM program must produce exactly the same gate lists.  Deterministic: no random numbers, no database, no knowledge of any particular function.

A module is (n_in, gates, outs): gates[g] = (a, b) NAND inputs as signal numbers (inputs 0..n_in-1, gate g = n_in+g,
every input of a gate is an earlier signal); outs = output signals.  Limits: n_in <= 3, n_out <= 2, n_gates <= 32.

improve(module):
  repeat
    compact()                                   merge identical gates, drop dead gates, keep order, renumber
    for root r in increasing order:
      for each cut of r, smaller cuts first (ties: lexicographic):
        saved = number of cone gates freed if r is re-implemented over the cut leaves
        f     = truth table of r over the leaves (leaf i = variable i, byte tables 0xAA 0xCC 0xF0)
        if f is the table of a leaf: rewire r's users to that leaf; restart
        for g = 1 .. min(saved-1, GMAX): exhaustive search for a g-NAND circuit over the leaves computing f
          if found: add its gates, rewire r's users to its last gate; restart
  until no change
Chain cuts of r: leaves = sorted {a, b} of r; yield; then repeatedly replace the highest-numbered leaf that is a gate by its
two inputs (set union, sorted); stop when more than 3 leaves would result or no gate leaf remains.
Cone(r, leaves) = r and all gates reachable from r without passing through a leaf.
Saved = number of cone gates g with: g == r, or (every use of g (gate pin or module output) is inside the cone and g is not
a module output).
Exhaustive search (iterative deepening): signals = leaf tables then new gates; each level adds NAND(sig[i], sig[j]) for
j in 0..L-1, i in 0..j (this order); a gate whose table already exists among the signals is skipped; prune if the target is
absent and no gates are left; success when the target table is among the signals after g gates.  First hit wins."""
import sys, os
GMAX = 6
LIMIT_IN, LIMIT_OUT, LIMIT_GATES = 3, 2, 26


def var_tables(k):
    N = 1 << k; full = (1 << N) - 1
    return [sum(1 << r for r in range(N) if (r >> v) & 1) for v in range(k)], full


def tables(n_in, gates):
    base, full = var_tables(n_in)
    sig = list(base)
    for a, b in gates: sig.append(full ^ (sig[a] & sig[b]))
    return sig


def compact(n_in, gates, outs):
    """merge identical gates (the later one is replaced by the first), drop dead gates, keep the relative order of the survivors
    (so the list stays topologically ordered) and renumber.  One pass, no search, no table: easy to do in place."""
    gates, outs = list(gates), list(outs)
    remap, seen = {}, {}
    for g in range(len(gates)):
        a, b = gates[g]; a, b = remap.get(a, a), remap.get(b, b); gates[g] = (a, b)
        k = (min(a, b), max(a, b))
        if k in seen: remap[n_in + g] = seen[k]
        else: seen[k] = n_in + g
    outs = [remap.get(o, o) for o in outs]
    live, stack = set(), list(outs)
    while stack:
        s = stack.pop()
        if s < n_in or s in live: continue
        live.add(s); stack += list(gates[s - n_in])
    ren, new = {i: i for i in range(n_in)}, []
    for g in range(len(gates)):
        if n_in + g in live:
            a, b = gates[g]; ren[n_in + g] = n_in + len(new); new.append((ren[a], ren[b]))
    return new, [ren[o] for o in outs]


def chain_cuts(n_in, gates, root):
    a, b = gates[root - n_in]; leaves = sorted({a, b}); out = []
    while True:
        out.append(list(leaves))
        gl = [s for s in leaves if s >= n_in]
        if not gl: return out
        s = max(gl); x, y = gates[s - n_in]
        nl = sorted((set(leaves) - {s}) | {x, y})
        if len(nl) > 3: return out
        leaves = nl


def cone_of(n_in, gates, root, leaves):
    cone, stack = set(), [root]
    while stack:
        s = stack.pop()
        if s in leaves or s < n_in or s in cone: continue
        cone.add(s); stack += list(gates[s - n_in])
    return cone


def search(k, f, gmax):
    """returns list of (i, j) for the new gates, or None"""
    base, full = var_tables(k)
    for g in range(1, gmax + 1):
        sig = list(base); prog = []
        def rec(d):
            have = f in sig
            if not have and g - d < 1: return False
            if d == g: return have
            L = len(sig)
            for j in range(L):
                for i in range(j + 1):
                    t = full ^ (sig[i] & sig[j])
                    if t in sig: continue
                    sig.append(t); prog.append((i, j))
                    if rec(d + 1): return True
                    sig.pop(); prog.pop()
            return False
        if rec(0): return prog
    return None


def stats_new():
    return dict(searches=0, nodes=0)


def improve(n_in, gates, outs, stats=None):
    gates, outs = compact(n_in, gates, outs)
    while True:
        changed = False
        fo = [0] * (n_in + len(gates))
        for a, b in gates: fo[a] += 1; fo[b] += 1
        for o in outs: fo[o] += 1
        for g in range(len(gates)):
            root = n_in + g
            for leaves in sorted(chain_cuts(n_in, gates, root), key=lambda c: (len(c), c)):
                cone = cone_of(n_in, gates, root, set(leaves))
                inner = {s: 0 for s in cone}
                for s in cone:
                    for x in gates[s - n_in]:
                        if x in inner: inner[x] += 1
                saved = sum(1 for s in cone if s == root or (fo[s] == inner[s] and s not in outs))
                k = len(leaves); base, full = var_tables(k)
                val = {leaves[i]: base[i] for i in range(k)}
                for s in sorted(cone):
                    a, b = gates[s - n_in]; val[s] = full ^ (val[a] & val[b])
                f = val[root]
                if f in base:
                    new_sig = leaves[base.index(f)]; added = []
                else:
                    gmax = min(saved - 1, GMAX)
                    if gmax < 1: continue
                    if stats is not None: stats['searches'] += 1
                    prog = search(k, f, gmax)
                    if prog is None: continue
                    added = prog
                # the new gates are inserted just before root (so that the list stays topological); root's users use the
                # last new gate (or the leaf); root itself is then dead and compact() removes it
                n = len(added)
                sh = lambda x: x if x < root else x + n
                ng = [(sh(a), sh(b)) for a, b in gates]
                idx = list(leaves); add = []
                for t, (i, j) in enumerate(prog if not f in base else []):
                    add.append((idx[i], idx[j])); idx.append(root + t)
                ns = idx[-1] if add else new_sig
                ng = ng[:g] + add + ng[g:]; r2 = root + n
                ng = [(ns if a == r2 else a, ns if b == r2 else b) for a, b in ng]
                gates, outs = compact(n_in, ng, [ns if sh(o) == r2 else sh(o) for o in outs])
                changed = True; break
            if changed: break
        if not changed: return gates, outs


REC_MAX = 40                                  # an improved record must fit the improver's RAM buffer (bytes), else it is not used


def to_compact(n_in, slots, outs):
    """slot form (list of (a,b) or None for a hole; signals n_in+slot) -> gate list in slot order with holes, dead and duplicate
    gates removed; None if the slot order is not topological (then the module is left alone)"""
    for s, x in enumerate(slots):
        if x is not None and (x[0] >= n_in + s or x[1] >= n_in + s): return None
    return _drop_holes(n_in, slots, outs)


def _drop_holes(n_in, slots, outs):
    ren, g = {i: i for i in range(n_in)}, []
    for s, x in enumerate(slots):
        if x is not None: ren[n_in + s] = n_in + len(g); g.append((ren[x[0]], ren[x[1]]))
    return compact(n_in, g, [ren[o] for o in outs])


def partition(n_in, gates, outs):
    """move the output gates to the end, ordered by their pinned slot (position in `outs` order is kept in the result's outs);
    None if a non-output gate would depend on an output (then the slot order could not stay topological)"""
    if len(set(outs)) != len(outs) or any(o < n_in for o in outs): return None
    order = [n_in + g for g in range(len(gates)) if n_in + g not in outs] + sorted(outs)   # sorted by signal number = by pinned slot later
    pos = {s: k for k, s in enumerate(order)}
    ren = {i: i for i in range(n_in)}
    for s, k in pos.items(): ren[s] = n_in + k
    new = [None] * len(gates)
    for s in order:
        a, b = gates[s - n_in]
        if ren[a] >= ren[s] or ren[b] >= ren[s]: return None
        new[ren[s] - n_in] = (ren[a], ren[b])
    return new, [ren[o] for o in outs]


def improve_record(n_in, slots, outs, pinned=None):
    """slot-form module -> improved slot-form (new_slots, outs) or None when there is no strict gain / it cannot be laid out.
    Output gates stay in their original slots (outs unchanged): other modules' references into this instance stay valid."""
    r = to_compact(n_in, slots, outs)
    if r is None: return None
    real = sum(1 for x in slots if x is not None)
    g, o = improve(n_in, *r)
    while True:
        p = partition(n_in, g, o)
        if p is None: return None
        if p[0] == g and p[1] == o: break
        g, o = improve(n_in, *p)
    if len(g) >= real: return None
    S = len(slots); pins = list(outs)
    slot_of = {o[j]: pins[j] - n_in for j in range(len(o))}          # output j -> its pinned slot
    free = [s for s in range(S) if n_in + s not in pins]
    nonout = [n_in + k for k in range(len(g)) if n_in + k not in o]
    if len(nonout) > len(free): return None
    for sig, slot in zip(nonout, free): slot_of[sig] = slot            # the others: lowest free slots, in order
    new = [None] * S; sg = lambda x: x if x < n_in else n_in + slot_of[x]
    for k, (a, b) in enumerate(g):
        sl = slot_of[n_in + k]; new[sl] = (sg(a), sg(b))
        if sg(a) >= n_in + sl or sg(b) >= n_in + sl: return None       # layout must stay topological
    new_outs = [sg(x) for x in o]
    nent = sum(1 for _ in _entries(new))
    if 4 + 3 * nent + len(outs) > REC_MAX: return None
    return new, new_outs


def _entries(slots):
    k = 0
    for x in slots:
        if x is None: k += 1; continue
        if k: yield ('skip', k); k = 0
        yield ('gate', x)
    if k: yield ('skip', k)


def improvable(m):
    return m.kind == 'comb' and m.n_in <= LIMIT_IN and m.n_out <= LIMIT_OUT and m.n_gates() <= LIMIT_GATES


def improve_hd(hd):
    """new HD whose library modules are improved (slot form: holes are None); returns (hd2, report)"""
    import copy, hd as H
    hd2 = copy.copy(hd); hd2.modules = []; rep = []
    for m in hd.modules:
        if not improvable(m): hd2.modules.append(m); continue
        r = improve_record(m.n_in, m.gates, m.outs)
        if r is None: hd2.modules.append(m); rep.append((m.name, m.n_gates(), m.n_gates(), 0)); continue
        m2 = H.Module(m.name, m.n_in, m.n_out); m2.gates, m2.outs = r[0], r[1]
        m2.comments = ['improved' if x is not None else 'hole' for x in r[0]]
        g0 = [x for x in m.gates]; t0 = tables(m.n_in, g0)
        t1 = tables_slots(m2.n_in, m2.gates)
        assert [t0[x] for x in m.outs] == [t1[x] for x in m2.outs], f'{m.name}: function changed!'
        hd2.modules.append(m2); rep.append((m.name, m.n_gates(), sum(1 for x in r[0] if x is not None), 0))
    return hd2, rep


def tables_slots(n_in, slots):
    base, full = var_tables(n_in); sig = list(base)
    memo = {}
    def val(s):
        if s < n_in: return base[s]
        if s not in memo:
            a, b = slots[s - n_in]; memo[s] = full ^ (val(a) & val(b))
        return memo[s]
    return [val(s) if s < n_in or slots[s - n_in] is not None else None for s in range(n_in + len(slots))]


if __name__ == '__main__':
    HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
    import hd as H
    hd = H.read(open(sys.argv[1]).read()); hd2, rep = improve_hd(hd)
    for r in rep: print('%-6s %3d -> %3d NAND' % r[:3])
    if len(sys.argv) > 2: open(sys.argv[2], 'w').write(H.write(hd2))
