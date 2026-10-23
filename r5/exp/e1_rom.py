#!/usr/bin/env python3
"""E1: cost of a ROM built as constant NAND logic.  Three constructions of the same function (address -> W-bit word), all verified exhaustively:
  plane    two-level predecode (group size g), one active-low word line per word (1 NAND), OR-plane over the word lines of each output bit
  plane_or same decoder, OR-plane built with Net.or_n (generic)
  shannon  recursive Shannon expansion with structural hashing (the function as a shared mux DAG)
Prints NAND counts, per word and per stored 1-bit.  usage: e1_rom.py [seed]"""
import random, sys
from common import Net, count, Sim

def addr_inputs(net, n): return [net.inp(f'a{i}') for i in range(n)]

def decode_lines(net, a, g):
    """active-low word lines for every address 0..2^n-1: nand(hi_onehot, lo_onehot) with the address split in 2 halves, each half predecoded in groups of g bits"""
    n = len(a); na = [net.not_(x) for x in a]
    def onehot(bits):                       # all 2^len one-hot lines (active high) for a group of address bits, built by groups of g
        if len(bits) <= g:
            out = []
            for v in range(1 << len(bits)):
                lits = [(bits[i][0] if (v >> i) & 1 else bits[i][1]) for i in range(len(bits))]
                out.append(net.and_n(lits))
            return out
        h = len(bits) // 2; lo, hi = onehot(bits[:h]), onehot(bits[h:])
        return [net.and_(hi[j], lo[i]) for j in range(len(hi)) for i in range(len(lo))]
    bits = [(a[i], na[i]) for i in range(n)]
    h = n // 2; lo = onehot(bits[:h]) if h else [1]; hi = onehot(bits[h:])
    return [net.nand(hi[j], lo[i]) for j in range(len(hi)) for i in range(len(lo))]      # index = j * len(lo) + i = address

def or_low(net, xs):
    """OR of terms given as active-low signals xs (term true when x == 0): pair with NAND (-> active high), then merge active-high by OR"""
    if not xs: return 0
    hi = []
    for i in range(0, len(xs) - 1, 2): hi.append(net.nand(xs[i], xs[i + 1]))
    if len(xs) % 2: hi.append(net.not_(xs[-1]))
    while len(hi) > 1:
        nxt = [net.or_(hi[i], hi[i + 1]) for i in range(0, len(hi) - 1, 2)]
        if len(hi) % 2: nxt.append(hi[-1])
        hi = nxt
    return hi[0]

def rom_plane(words, n, W, g=2, tree='low'):
    net = Net(); a = addr_inputs(net, n); lines = decode_lines(net, a, g); outs = []
    for j in range(W):
        xs = [lines[i] for i in range(len(words)) if (words[i] >> j) & 1]
        outs.append(or_low(net, xs) if tree == 'low' else net.or_n([net.not_(x) for x in xs]))
    return net, a, outs

def rom_shannon(words, n, W):
    net = Net(); a = addr_inputs(net, n); memo = {}
    def build(tbl, k):                      # tbl: tuple of 2^k words, k address bits remain (bits a[k-1]..a[0]); returns list of W signals
        key = tbl
        if key in memo: return memo[key]
        if k == 0: r = [(tbl[0] >> j) & 1 for j in range(W)]
        elif all(t == tbl[0] for t in tbl): r = [(tbl[0] >> j) & 1 for j in range(W)]
        else:
            h = len(tbl) // 2; lo, hi = build(tbl[:h], k - 1), build(tbl[h:], k - 1)
            r = [net.mux(a[k - 1], lo[j], hi[j]) for j in range(W)]
        memo[key] = r; return r
    full = tuple(words) + (0,) * ((1 << n) - len(words))
    return net, a, build(full, n)

def verify(net, a, outs, words, W):
    s = Sim(net, outs)
    for addr in range(1 << len(a)):
        for i, x in enumerate(a): s.set(x, (addr >> i) & 1)
        s.comb(); want = words[addr] if addr < len(words) else 0
        got = s.bus(outs)
        assert got == want, (addr, got, want)

if __name__ == '__main__':
    rnd = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    print(f'{"N":>5} {"W":>2} {"p1":>5} {"ones":>6} | {"plane g2":>9} {"g3":>6} {"or_n":>6} {"shannon":>8} | best/word best/one   (NAND incl. inverters; verified)')
    for n in (4, 5, 6, 7, 8, 9, 10):
        for W in (8, 16):
            for p in (0.1, 0.25, 0.5):
                N = 1 << n; words = [sum((rnd.random() < p) << j for j in range(W)) for _ in range(N)]
                ones = sum(bin(w).count('1') for w in words); res = {}
                for name, f in (('g2', lambda: rom_plane(words, n, W, 2)), ('g3', lambda: rom_plane(words, n, W, 3)), ('or_n', lambda: rom_plane(words, n, W, 2, 'orn')), ('sh', lambda: rom_shannon(words, n, W))):
                    net, a, outs = f(); verify(net, a, outs, words, W) if N <= 1024 else None
                    res[name] = count(net, outs)[0]
                b = min(res.values())
                print(f'{N:5d} {W:2d} {p:5.2f} {ones:6d} | {res["g2"]:9d} {res["g3"]:6d} {res["or_n"]:6d} {res["sh"]:8d} | {b / N:8.2f} {b / max(ones, 1):7.2f}')
