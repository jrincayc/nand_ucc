#!/usr/bin/env python3
"""E6 (description bits/gate, no decompressor beyond a tiny decoder) and E7 (regularity) on gate netlists.
Test beds: Hack-vN and ACC8 level-2 netlists (nandgen/isa/*.netlist.txt, MEASURED CPUs) and r4 cpu_g1.nl (the RV32EC CPU, 3770 NAND + 81 DFF).
Usage: e6_e7.py hackvn.txt acc8.txt cpu_g1.nl
Everything printed as MEASURED is an exact count of an encoding that a small decoder could invert (I check round-trip for the fixed codes);
rows marked BOUND are zero-order entropies = lower bounds for a statically-modelled coder, not an implemented encoding."""
import sys, re, math, collections

def read_txt(path):
    nin = ndff = 0; dff = []; gates = []; ids = {}
    for line in open(path):
        w = line.split()
        if not w: continue
        if w[0] == 'in': nin = int(w[1])
        elif w[0] == 'dff': ndff = int(w[1])
        elif w[1] == '<=': dff.append(w[2])
        elif w[1] == '=': gates.append((w[0], w[3], w[4]))
    src = nin + ndff
    pos = {f'w{i}': i for i in range(src)}
    for k, (n, a, b) in enumerate(gates): pos[n] = src + k
    G = [(pos[a], pos[b]) for n, a, b in gates]
    return dict(nsrc=src, nin=nin, ndff=ndff, G=G, D=[pos[d] for d in dff])

def read_nl(path):
    nodes = {}; order = []
    for line in open(path):
        w = line.split()
        if w and w[0] == 'n': nodes[int(w[1])] = (w[2], [t.split('@')[0] for t in w[3:]]); order.append(int(w[1]))
    dff = [i for i in order if nodes[i][0] == 'D']; gt = [i for i in order if nodes[i][0] == 'N']
    ext = sorted({t for i in order for t in nodes[i][1] if not re.fullmatch(r'n\d+', t)})   # external inputs (ram/rom read data ...)
    pos = {i: k for k, i in enumerate(dff)}
    for k, i in enumerate(gt): pos[i] = len(dff) + len(ext) + k
    ep = {t: len(dff) + k for k, t in enumerate(ext)}
    ref = lambda t: ep[t] if t in ep else pos[int(t[1:])]
    G = [(ref(nodes[i][1][0]), ref(nodes[i][1][1])) for i in gt]
    D = [ref(nodes[i][1][0]) for i in dff]
    return dict(nsrc=len(dff) + len(ext), nin=len(ext), ndff=len(dff), G=G, D=D)

def forward_refs(T):
    n = T['nsrc']; return sum(1 for k, (a, b) in enumerate(T['G']) if a >= n + k or b >= n + k)

def reorder(T, how):
    """Return gate order (list of old gate positions) -> new netlist. 'orig' keeps; 'dfs' = post-order from DFF D inputs (cones become contiguous)."""
    n = T['nsrc']; G = T['G']
    if how == 'orig': return T
    seen = set(); out = []
    sys.setrecursionlimit(100000)
    def visit(x):
        st = [(x, 0)]
        while st:
            v, ph = st.pop()
            if v < n or (ph == 0 and v in seen): continue
            if ph == 0:
                seen.add(v); st.append((v, 1)); a, b = G[v - n]; st.append((b, 0)); st.append((a, 0))
            else: out.append(v)
    for d in T['D']: visit(d)
    for v in range(n, n + len(G)):
        if v not in seen: visit(v)
    new = {v: n + k for k, v in enumerate(out)}
    for s in range(n): new[s] = s
    G2 = [None] * len(G)
    for v in out: a, b = G[v - n]; G2[new[v] - n] = (new[a], new[b])
    return dict(T, G=G2, D=[new[d] for d in T['D']])

def gamma(x):  # x>=1 -> bits
    return 2 * x.bit_length() - 1

# ---- encodings.  A gate = (a,b).  NOT gate (a==b) flagged.  Ref to a source (input/DFF) vs to an earlier gate: distance d = cur - ref >= 1 for gates; sources absolute.
def enc_cost(T):
    n = T['nsrc']; G = T['G']; N = len(G); res = {}
    srcbits = max(1, (n - 1).bit_length())
    # (1) flat absolute: 2 x ceil(log2(total nodes)) bits, no order assumption
    tot = n + N; res['absolute 2*log2(N)'] = 2 * (tot - 1).bit_length()
    # (2) relative distance, Elias-gamma, source refs as flag + absolute; NOT flag 1 bit. Round trip checked below.
    def tokens(k, a):
        cur = n + k
        if a >= n: return ('g', cur - a)
        return ('s', a)
    bits = 0; stream = []
    for k, (a, b) in enumerate(G):
        bits += 1                                   # NOT flag
        refs = [a] if a == b else [a, b]
        for r in refs:
            t, v = tokens(k, r); bits += 1          # src/gate flag
            bits += gamma(v) if t == 'g' else srcbits
            stream.append((t, v))
    res['relative+gamma, NOT flag'] = bits / N
    # (3) same with 'repeat previous gate's distance pair' / 'previous-1': context token
    # entropy bound: zero-order entropy over classes = (flag, bucket) then raw low bits
    cnt = collections.Counter(); raw = 0; tot_syms = 0
    for k, (a, b) in enumerate(G):
        refs = [a] if a == b else [a, b]
        cnt[('not', a == b)] += 1
        for r in refs:
            t, v = tokens(k, r)
            if t == 'g': cnt[('g', v.bit_length())] += 1; raw += v.bit_length() - 1
            else: cnt[('s', 0)] += 1; raw += srcbits
            tot_syms += 1
    H = 0; Ntok = sum(cnt.values())
    for key, c in cnt.items(): H += -c * math.log2(c / Ntok)
    res['BOUND: bucket entropy + raw low bits'] = (H + raw) / N
    # (4) context 'same distance pair as gate j back' (j=1..8) or literal; counts of each hit
    hist = collections.Counter(); pairs = []
    for k, (a, b) in enumerate(G):
        pairs.append(((n + k - a) if a >= n else -a - 1, (n + k - b) if b >= n else -b - 1))
    lit = 0
    for k, p in enumerate(pairs):
        for j in range(1, 9):
            if k - j >= 0 and pairs[k - j] == p: hist[j] += 1; break
        else: hist[0] += 1
    res['_repeat-pair hit rate (distance pair equals that of gate j<=8 back)'] = 1 - hist[0] / N
    res['_hist'] = dict(sorted(hist.items()))
    return res, stream

def lz_cost(T, W=4096, minlen=3):
    """Greedy LZ77 over the symbol sequence (pair of relative distances; sources as negative-absolute symbols).  Cost model: literal = flag + the same gamma/src bits as (2);
    copy = flag + log2(window offset in symbols, gamma) + gamma(len).  Decoder: ~30-40 RISC-style instructions, not counted.  MEASURED for this model."""
    n = T['nsrc']; G = T['G']; N = len(G); srcbits = max(1, (n - 1).bit_length())
    sym = []
    for k, (a, b) in enumerate(G):
        sym.append(((n + k - a) if a >= n else -a - 1, (n + k - b) if b >= n else -b - 1))
    def litbits(p):
        c = 1
        for x in ([p[0]] if p[0] == p[1] else p):
            c += 1 + (gamma(x) if x > 0 else srcbits)
        return c
    i = 0; bits = 0; copies = 0; lits = 0; copied = 0
    idx = collections.defaultdict(list)
    while i < N:
        best = (0, 0)
        for j in reversed(idx.get(sym[i], [])[-64:]):
            if i - j > W: break
            l = 0
            while i + l < N and sym[j + l] == sym[i + l] and j + l < i + l: l += 1
            if l > best[0]: best = (l, i - j)
        if best[0] >= minlen:
            bits += 1 + gamma(best[1]) + gamma(best[0]); copies += 1; copied += best[0]
            for t in range(best[0]): idx[sym[i + t]].append(i + t)
            i += best[0]
        else:
            bits += 1 + litbits(sym[i]); lits += 1; idx[sym[i]].append(i); i += 1
    return bits / N, copies, lits, copied

def wl_classes(T, depth):
    """Weisfeiler-Lehman-style: class(gate) = hash(sorted fanin classes) from depth 0.  Sources are one class each by kind; gates start as one class."""
    n = T['nsrc']; G = T['G']
    cl = [('s',)] * n + [('g',)] * len(G)
    out = []
    for d in range(depth + 1):
        out.append(len(set(cl[n:])))
        cl = cl[:n] + [hash((cl[a], cl[b]) if cl[a] <= cl[b] else (cl[b], cl[a])) if True else 0 for a, b in G] if False else \
             cl[:n] + [hash(tuple(sorted((hash(cl[a]), hash(cl[b]))))) for a, b in G]
    return out

def wl_down(T, depth):
    """Classes by structure *below* a gate (cone to depth d) -- classes computed topologically so cl[a], cl[b] are current-round values of the fanins at the previous round."""
    n = T['nsrc']; G = T['G']; res = []
    cl = [0] * n + [1] * len(G)
    for d in range(depth + 1):
        res.append(len(set(cl[n:])))
        prev = cl
        cl = prev[:n] + [hash(tuple(sorted((prev[a], prev[b])))) for a, b in G]
    return res

def main():
    paths = sys.argv[1:]
    for p in paths:
        T = read_nl(p) if p.endswith('.nl') else read_txt(p)
        N = len(T['G']); print(f'\n=== {p.split("/")[-1]}: {N} NAND, {T["ndff"]} DFF, sources {T["nsrc"]}, forward refs {forward_refs(T)} ===')
        nots = sum(1 for a, b in T['G'] if a == b); print(f'  NOT-form gates (a==b): {nots} ({nots / N:.0%})')
        for how in ('orig', 'dfs'):
            T2 = reorder(T, how)
            if how != 'orig': assert forward_refs(T2) == 0 or how == 'dfs'
            res, _ = enc_cost(T2)
            lz, cp, li, cd = lz_cost(T2)
            print(f'  order={how}:')
            for k, v in res.items():
                if k == '_hist': print(f'     repeat histogram {v}')
                elif k.startswith('_'): print(f'     {k[1:]}: {v:.2f}')
                else: print(f'     {k}: {v:.2f} bits/gate')
            print(f'     MEASURED LZ over distance-pair symbols: {lz:.2f} bits/gate  ({cp} copies covering {cd} gates, {li} literal gates; "gates described" = {cp + li}/{N} = {(cp + li) / N:.0%})')
        print('  E7 WL classes (down-cone depth 0..6) among gates:', wl_down(T, 6))
if __name__ == '__main__': main()
