#!/usr/bin/env python3
"""R6 step 1: ROM image -> grid-structured plane netlist (row bus hi[h], column bus lo[l], cell (h,l)=NAND, per-row per-bit OR chain,
column reduction).  Counts gates in the used cone, checks sampled addresses, prints strip statistics.  usage: grid_plane.py rom.bin [nbytes]"""
import sys, random
sys.path[:0] = ['/home/claude/r5/exp']
from common import Net, count, Sim
data = open(sys.argv[1], 'rb').read(); N = len(data); n = 14; H = L = 128
words = list(data) + [0] * ((1 << n) - N)
net = Net(); a = [net.inp(f'a{i}') for i in range(n)]; na = [net.not_(x) for x in a]
def onehot(bits):       # bits: list of (pos, neg); returns 2^len active-high lines, index = value; pairs of 2 bits first
    out = [None]
    for i, (p, q) in enumerate(bits):
        new = []
        for v in (0, 1):
            for o in out: new.append(net.and_(o, p if v else q) if o is not None else (p if v else q))
        out = [None] * 0 + new if False else new
    return out
def oh(bits):           # index value = sum bit_i << i ; build as hi-part x lo-part with 2-3 bit groups
    if len(bits) <= 3:
        r = []
        for v in range(1 << len(bits)): r.append(net.and_n([bits[i][0] if (v >> i) & 1 else bits[i][1] for i in range(len(bits))]))
        return r
    h = len(bits) // 2; lo, hi = oh(bits[:h]), oh(bits[h:])
    return [net.and_(hi[j], lo[i]) for j in range(len(hi)) for i in range(len(lo))]
bits = [(a[i], na[i]) for i in range(n)]
lo = oh(bits[:7]); hi = oh(bits[7:])           # address = h*128 + l
rowres = [[None] * 8 for _ in range(H)]; stat = []
for h in range(H):
    for j in range(8):
        acc = None; k = 0
        for l in range(L):
            if (words[h * L + l] >> j) & 1:
                w = net.nand(hi[h], lo[l]); k += 1                 # active low, selected = 0
                acc = net.not_(w) if acc is None else net.or_(acc, net.not_(w)) if False else (net.nand(net.not_(acc), w))
        rowres[h][j] = acc; stat.append(k)
outs = []
for j in range(8):
    xs = [rowres[h][j] for h in range(H) if rowres[h][j] is not None]
    while len(xs) > 1:
        nx = [net.or_(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2)]
        if len(xs) % 2: nx.append(xs[-1])
        xs = nx
    outs.append(xs[0])
nand, dff = count(net, outs); ones = sum(bin(w).count('1') for w in words)
print(f'N={N} ones={ones} gates={nand} ({nand/ones:.2f}/one)  max ones per row-bit={max(stat)} mean={sum(stat)/len(stat):.1f}')
s = Sim(net, outs); rnd = random.Random(1)
for ad in [rnd.randrange(1 << n) for _ in range(150)] + list(range(0, 40)):
    for i, x in enumerate(a): s.set(x, (ad >> i) & 1)
    s.comb(); assert s.bus(outs) == words[ad], ad
print('sampled check ok')
