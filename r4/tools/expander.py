#!/usr/bin/env python3
"""expander.py -- gate-level RV32C -> RV32 expander, derived from rvemu.expand by probing.
Each compressed instruction kind (a pattern on h) drives every output bit of the 32-bit encoding from a constant or from one bit of h
(possibly inverted); the probe checks this on random legal members of the kind, the hardware ORs the kinds together per source.
verify(): exhaustive check of all 65536 halfwords with h[1:0] != 3 against rvemu.expand (bits 2..31 of legal encodings)."""
import os, random, sys
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]
import rvemu

# (name, {bit: value} pattern, predicate-for-sampling, hardware extra: ('z62', want) / ('rd2', want) / None)
def b(h, i): return (h >> i) & 1
KINDS = [
    ('addi4spn', {1: 0, 0: 0, 15: 0, 14: 0, 13: 0}, lambda h: (h >> 5) & 255 != 0, None),
    ('lw',   {1: 0, 0: 0, 15: 0, 14: 1, 13: 0}, None, None),
    ('sw',   {1: 0, 0: 0, 15: 1, 14: 1, 13: 0}, None, None),
    ('addi', {1: 0, 0: 1, 15: 0, 14: 0, 13: 0}, None, None),
    ('jal',  {1: 0, 0: 1, 15: 0, 14: 0, 13: 1}, None, None),
    ('li',   {1: 0, 0: 1, 15: 0, 14: 1, 13: 0}, None, None),
    ('lui',  {1: 0, 0: 1, 15: 0, 14: 1, 13: 1}, lambda h: ((h >> 7) & 31) != 2 and (((b(h, 12) << 5) | ((h >> 2) & 31)) != 0), ('rd2', 0)),
    ('addi16sp', {1: 0, 0: 1, 15: 0, 14: 1, 13: 1}, lambda h: ((h >> 7) & 31) == 2 and (((b(h, 12) << 5) | ((h >> 2) & 31)) != 0), ('rd2', 1)),
    ('srli', {1: 0, 0: 1, 15: 1, 14: 0, 13: 0, 11: 0, 10: 0}, lambda h: not b(h, 12), None),
    ('srai', {1: 0, 0: 1, 15: 1, 14: 0, 13: 0, 11: 0, 10: 1}, lambda h: not b(h, 12), None),
    ('andi', {1: 0, 0: 1, 15: 1, 14: 0, 13: 0, 11: 1, 10: 0}, None, None),
    ('sub',  {1: 0, 0: 1, 15: 1, 14: 0, 13: 0, 12: 0, 11: 1, 10: 1, 6: 0, 5: 0}, None, None),
    ('xor',  {1: 0, 0: 1, 15: 1, 14: 0, 13: 0, 12: 0, 11: 1, 10: 1, 6: 0, 5: 1}, None, None),
    ('or',   {1: 0, 0: 1, 15: 1, 14: 0, 13: 0, 12: 0, 11: 1, 10: 1, 6: 1, 5: 0}, None, None),
    ('and',  {1: 0, 0: 1, 15: 1, 14: 0, 13: 0, 12: 0, 11: 1, 10: 1, 6: 1, 5: 1}, None, None),
    ('j',    {1: 0, 0: 1, 15: 1, 14: 0, 13: 1}, None, None),
    ('beqz', {1: 0, 0: 1, 15: 1, 14: 1, 13: 0}, None, None),
    ('bnez', {1: 0, 0: 1, 15: 1, 14: 1, 13: 1}, None, None),
    ('slli', {1: 1, 0: 0, 15: 0, 14: 0, 13: 0}, lambda h: not b(h, 12), None),
    ('lwsp', {1: 1, 0: 0, 15: 0, 14: 1, 13: 0}, lambda h: ((h >> 7) & 31) != 0, None),
    ('jr',   {1: 1, 0: 0, 15: 1, 14: 0, 13: 0, 12: 0}, lambda h: (h >> 2) & 31 == 0 and (h >> 7) & 31 != 0, ('z62', 1)),
    ('mv',   {1: 1, 0: 0, 15: 1, 14: 0, 13: 0, 12: 0}, lambda h: (h >> 2) & 31 != 0, ('z62', 0)),
    ('jalr', {1: 1, 0: 0, 15: 1, 14: 0, 13: 0, 12: 1}, lambda h: (h >> 2) & 31 == 0 and (h >> 7) & 31 != 0, ('z62', 1)),
    ('add',  {1: 1, 0: 0, 15: 1, 14: 0, 13: 0, 12: 1}, lambda h: (h >> 2) & 31 != 0, ('z62', 0)),
    ('swsp', {1: 1, 0: 0, 15: 1, 14: 1, 13: 0}, None, None),
]


def sample(kind, rng):
    name, pat, pred, extra = kind
    while True:
        h = rng.getrandbits(16)
        for bit, v in pat.items(): h = (h & ~(1 << bit)) | (v << bit)
        if pred is None or pred(h): return h


def probe(nsamples=300, seed=1):
    """-> {kind_name: {outbit: ('c', 0|1) | ('h', j, inv)}}"""
    rng = random.Random(seed); table = {}
    for kind in KINDS:
        hs = [sample(kind, rng) for _ in range(nsamples)]
        es = [rvemu.expand(h) for h in hs]; row = {}
        for i in range(2, 32):
            vals = [(e >> i) & 1 for e in es]
            if len(set(vals)) == 1: row[i] = ('c', vals[0]); continue
            for j in range(16):
                hv = [(h >> j) & 1 for h in hs]
                if hv == vals: row[i] = ('h', j, 0); break
                if all(x != y for x, y in zip(hv, vals)): row[i] = ('h', j, 1); break
            else: raise RuntimeError(f'kind {kind[0]} output bit {i} is not a copy of one h bit')
        table[kind[0]] = row
    return table


def build(net, h):
    """h: 16 signals (LSB first) -> list E[0..31] of signals (bits 0,1 are constant 1 for completeness)"""
    table = probe()
    hn = [net.not_(x) for x in h]
    z62 = net.nor(net.or_n(h[2:6]), h[6]) if False else net.not_(net.or_n(h[2:7]))
    rd2 = net.and_n([h[8], net.not_(h[7]), net.not_(h[9]), net.not_(h[10]), net.not_(h[11])])
    sel = {}
    for name, pat, pred, extra in KINDS:
        lits = [h[b_] if v else hn[b_] for b_, v in sorted(pat.items(), reverse=True)]
        if extra:
            e, want = extra
            sig = z62 if e == 'z62' else rd2
            lits.append(sig if want else net.not_(sig))
        sel[name] = net.and_n(lits)
    E = [1, 1] + [0] * 30
    for i in range(2, 32):
        groups = {}                       # source -> list of kind selects
        for name, row in table.items():
            src = row[i]
            if src == ('c', 0): continue
            groups.setdefault(src, []).append(sel[name])
        terms = []
        for src, ks in groups.items():
            k = net.or_n(ks)
            if src == ('c', 1): terms.append(k)
            else:
                _, j, inv = src; terms.append(net.and_(k, hn[j] if inv else h[j]))
        E[i] = net.or_n(terms)
    return E


def verify():
    import netlist
    net = netlist.Net(); h = [net.inp(f'h{i}') for i in range(16)]
    E = build(net, h)
    # evaluate by direct interpretation
    order = list(range(len(net.kind)))
    bad = 0; n = 0
    for hv in range(65536):
        if hv & 3 == 3: continue
        try: want = rvemu.expand(hv)
        except rvemu.Illegal: continue
        val = [0, 1] + [0] * (len(net.kind) - 2)
        for i in range(16): val[h[i]] = (hv >> i) & 1
        for nid in range(2, len(net.kind)):
            k = net.kind[nid]
            if k[0] == 'nand': val[nid] = 1 - (val[k[1]] & val[k[2]])
        got = sum(val[E[i]] << i for i in range(2, 32))
        n += 1
        if got != (want & ~3):
            bad += 1
            if bad < 5: print(f'h={hv:#06x}: want {want:#010x} got {got | 3:#010x}')
    print(f'expander: {n} halfwords checked, {bad} mismatches, {net.n_gates()[0]} gates')
    return bad == 0


if __name__ == '__main__':
    sys.exit(0 if verify() else 1)
