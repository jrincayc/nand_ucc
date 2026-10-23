#!/usr/bin/env python3
"""E6b: bits/gate of a precomputed LAYOUT description (R4 router output for cpu_g1.nl, placement order = place_ref.order seed 1).
Stream: ('place',kind,x,y,...), ('track',layer,x1,y1,x2,y2), ('via',x,y).  Models are decoded back and compared (round trip), so the bit counts are of real invertible encodings.
Decoder cost (ROM code) NOT included.  Run from r4/: python3 ../r5/exp/e6_layout.py"""
import sys, os, collections, math
os.environ.update(ROM_BITS='16', AB='18', RAM_BITS='18')
sys.path[:0] = ['tools']
import lay, place_ref, route_ref
nl = lay.read_nl('hd/m18/cpu_g1.nl'); order = place_ref.order(nl, seed=1)
cmds, info = route_ref.route(nl, order, 22, 14)
N = len(nl.nodes); NG = sum(1 for k, _ in nl.nodes if k == 'N')
kinds = collections.Counter(c[0] for c in cmds); print('commands', dict(kinds), 'gates', NG, 'nodes', N)
tr = [c for c in cmds if c[0] == 'track']; vi = [c for c in cmds if c[0] == 'via']
print('layers', collections.Counter(c[1] for c in tr), 'axis-aligned', sum(1 for c in tr if c[2] == c[4] or c[3] == c[5]), 'of', len(tr), 'zero-length', sum(1 for c in tr if c[2:4] == c[4:6]))
def gamma(x): return 2 * x.bit_length() - 1
def sg(v): return gamma(2 * abs(v) + (1 if v < 0 else 0) + 1)           # signed -> zigzag -> gamma
# (A) naive: 16-bit signed fields
naive = len(tr) * (1 + 4 * 16) + len(vi) * 2 * 16
# (B) chain model: split stream into chains (consecutive cmds where a track starts where the previous track/via ended).  Each chain: start (zigzag delta from previous chain start), then per element:
#     type bit (track/via); track: layer bit only if chain start, orientation implied? -> store axis bit + signed length.   via: toggles layer (implied), nothing else.
chains = []; cur = []; pos = None; lay_ = None
for c in cmds:
    if c[0] == 'place': continue
    if c[0] == 'track':
        s = (c[2], c[3]); e = (c[4], c[5])
        if cur and pos == s and lay_ == c[1]: cur.append(('t', c[1], s, e)); pos = e
        elif cur and pos == e and lay_ == c[1]: cur.append(('t', c[1], e, s)); pos = s       # direction normalised
        else:
            if cur: chains.append(cur)
            cur = [('t', c[1], s, e)]; pos = e; lay_ = c[1]
    else:
        v = (c[1], c[2])
        if cur and pos == v:
            lay_ = 1 - lay_ if lay_ in (0, 1) else lay_; cur.append(('v', v))
        else:
            if cur: chains.append(cur)
            cur = [('v', v)]; pos = v; lay_ = None
if cur: chains.append(cur)
print('chains', len(chains), 'mean elements', sum(map(len, chains)) / len(chains))
bits = 0; last = (0, 0)
for ch in chains:
    first = ch[0]; sp = first[2] if first[0] == 't' else first[1]
    bits += 1 + sg(sp[0] - last[0]) + sg(sp[1] - last[1]) + 1       # start delta + layer/type bit
    bits += gamma(len(ch))                                          # element count
    for el in ch:
        if el[0] == 't': bits += 1 + 1 + sg((el[3][0] - el[2][0]) + (el[3][1] - el[2][1]))   # type, axis, signed length
        else: bits += 1
    last = sp
print(f'(A) naive 16-bit fields: {naive / NG:.1f} bits/gate   (B) chain+zigzag-gamma: {bits / NG:.1f} bits/gate  = {bits / 8 / 1024:.1f} KiB for {NG} gates (routing only)')
# (C) entropy of the same fields (BOUND): zero-order entropy of (axis, signed length) symbols
sym = collections.Counter()
for ch in chains:
    for el in ch:
        if el[0] == 't': sym[(el[2][0] == el[3][0], (el[3][0] - el[2][0]) + (el[3][1] - el[2][1]))] += 1
        else: sym['via'] += 1
T = sum(sym.values()); H = -sum(c * math.log2(c / T) for c in sym.values())
print(f'(C) BOUND zero-order entropy of segment symbols: {H / NG:.1f} bits/gate (+ chain starts {(len(chains) * 2 * 8) / NG:.1f} if ~8 bits each coord)')
# placement stream: x,y per gate
pl = [c for c in cmds if c[0] == 'place']
px = sum(sg(c[2] - p[2]) + sg(c[3] - p[3]) for p, c in zip(pl, pl[1:])) + 2 * 16
print(f'placement deltas, zigzag-gamma: {px / len(pl):.2f} bits/place ({px / NG:.2f} per gate; {len(pl)} places)')
print(f'TOTAL layout (placement + routing, chain model) = {(px + bits) / NG:.1f} bits/gate   [R3c measured 55 bits/gate; R4 module HD 26]')
