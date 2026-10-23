#!/usr/bin/env python3
"""E2: cost of memory built from NAND/DFF.  Variants (all verified by cycle simulation):
  addr     addressable RAM, N words x W bits: DFF + 2:1 hold mux per bit, decoded word lines, AND-OR read
  ringw    word-parallel recirculating ring (N words x W bits shifting one word per tick) + position counter + match comparator
  ringb    bit-serial recirculating ring (N*W bits, one DFF per bit) + position counter + match comparator
Each reports NAND, DFF and units = NAND + 6 DFF (also per stored bit).  Ring variants include their own position counter and 'hit' comparator (the address register that holds the target is part of the CPU in all variants and not counted).
usage: e2_mem.py"""
import random
from common import Net, count, Sim

def inc_bus(net, q):                        # q + 1 (ripple), returns next-state signals
    c = 1; out = []
    for x in q: out.append(net.xor(x, c)); c = net.and_(x, c)
    return out

def eq_bus(net, a, b): return net.and_n([net.xnor(x, y) for x, y in zip(a, b)])

def build_addr(N, W):
    net = Net(); m = (N - 1).bit_length(); a = [net.inp(f'a{i}') for i in range(m)]; we = net.inp('we'); din = [net.inp(f'd{j}') for j in range(W)]
    na = [net.not_(x) for x in a]
    def line(i): return net.and_n([a[k] if (i >> k) & 1 else na[k] for k in range(m)])
    lines = [line(i) for i in range(N)]
    cells = []
    for i in range(N):
        wl = net.and_(lines[i], we); row = []
        for j in range(W):
            q = net.dff(); net.set_d(q, net.mux(wl, q, din[j])); row.append(q)
        cells.append(row)
    dout = [net.or_n([net.and_(lines[i], cells[i][j]) for i in range(N)]) for j in range(W)]
    return net, dict(a=a, we=we, din=din, dout=dout), dout

def build_ringw(N, W):
    net = Net(); m = (N - 1).bit_length(); t = [net.inp(f't{i}') for i in range(m)]; we = net.inp('we'); din = [net.inp(f'd{j}') for j in range(W)]
    pos = [net.dff() for _ in range(m)]
    nxt = inc_bus(net, pos)
    # wrap at N: pos' = (pos == N-1) ? 0 : pos+1  (only needed if N not a power of two)
    if N & (N - 1): wrap = eq_bus(net, pos, [(N - 1 >> i) & 1 for i in range(m)]); nxt = [net.and_(x, net.not_(wrap)) for x in nxt]
    for p, x in zip(pos, nxt): net.set_d(p, x)
    ring = [[net.dff() for _ in range(W)] for _ in range(N)]
    tap = ring[N - 1]
    for j in range(W): net.set_d(ring[0][j], net.mux(we, tap[j], din[j]))
    for i in range(1, N):
        for j in range(W): net.set_d(ring[i][j], ring[i - 1][j])
    hit = eq_bus(net, pos, t)
    return net, dict(t=t, we=we, din=din, hit=hit, tap=tap, pos=pos), tap + [hit]

def build_ringb(N, W):
    M = N * W; net = Net(); m = (M - 1).bit_length(); t = [net.inp(f't{i}') for i in range(m)]; we = net.inp('we'); din = net.inp('d')
    pos = [net.dff() for _ in range(m)]
    nxt = inc_bus(net, pos)
    if M & (M - 1): wrap = eq_bus(net, pos, [(M - 1 >> i) & 1 for i in range(m)]); nxt = [net.and_(x, net.not_(wrap)) for x in nxt]
    for p, x in zip(pos, nxt): net.set_d(p, x)
    ring = [net.dff() for _ in range(M)]
    net.set_d(ring[0], net.mux(we, ring[M - 1], din))
    for i in range(1, M): net.set_d(ring[i], ring[i - 1])
    hit = eq_bus(net, pos, t)
    return net, dict(t=t, we=we, din=din, hit=hit, tap=ring[M - 1], pos=pos), [ring[M - 1], hit]

def test_addr(N, W, rnd):
    net, p, outs = build_addr(N, W); s = Sim(net, outs); ref = [0] * N
    for _ in range(200):
        a = rnd.randrange(N); w = rnd.getrandbits(W); we = rnd.getrandbits(1)
        for i, x in enumerate(p['a']): s.set(x, (a >> i) & 1)
        s.set(p['we'], we)
        for j, x in enumerate(p['din']): s.set(x, (w >> j) & 1)
        s.comb(); assert s.bus(p['dout']) == ref[a]
        s.tick()
        if we: ref[a] = w
    return net, outs

def test_ringw(N, W, rnd):
    net, p, outs = build_ringw(N, W); s = Sim(net, outs); ref = [0] * N
    def at(k, we, w):                          # wait until position == k, then access in that tick
        for i, x in enumerate(p['t']): s.set(x, (k >> i) & 1)
        for _ in range(4 * N):
            s.comb()
            if s.v[p['hit']]: break
            s.set(p['we'], 0); s.tick()
        else: raise AssertionError('no hit')
        # at hit the word at tap is the one stored for index 'k' relative to a fixed rotation; use the convention: the word seen at tap when pos==k is slot k
        s.set(p['we'], we)
        for j, x in enumerate(p['din']): s.set(x, (w >> j) & 1)
        s.comb(); got = s.bus(p['tap']); s.tick(); s.set(p['we'], 0); return got
    # the ring rotates so a word written at hit(k) re-appears at the tap N ticks later = next hit(k): consistent slot semantics
    for _ in range(60):
        k = rnd.randrange(N); w = rnd.getrandbits(W); we = rnd.getrandbits(1)
        got = at(k, we, w); assert got == ref[k], (k, got, ref[k])
        if we: ref[k] = w
    return net, outs

def test_ringb(N, W, rnd):
    net, p, outs = build_ringb(N, W); s = Sim(net, outs); M = N * W; ref = [0] * M
    for _ in range(40):
        k = rnd.randrange(M); w = rnd.getrandbits(1); we = rnd.getrandbits(1)
        for i, x in enumerate(p['t']): s.set(x, (k >> i) & 1)
        for _ in range(3 * M):
            s.comb()
            if s.v[p['hit']]: break
            s.set(p['we'], 0); s.tick()
        else: raise AssertionError('no hit')
        s.set(p['we'], we); s.set(p['din'], w); s.comb(); got = s.v[p['tap']]; s.tick(); s.set(p['we'], 0)
        assert got == ref[k], (k, got, ref[k])
        if we: ref[k] = w
    return net, outs

if __name__ == '__main__':
    rnd = random.Random(3)
    print(f'{"kind":6s} {"N":>5s} {"W":>3s} {"bits":>6s} | {"NAND":>6s} {"DFF":>5s} {"units":>7s} | {"NAND/bit":>8s} {"units/bit":>9s} {"avg access ticks":>17s}')
    for N, W in ((8, 8), (16, 8), (32, 8), (64, 8), (16, 16), (32, 16), (64, 16), (256, 8)):
        for kind, f, tf, lat in (('addr', build_addr, test_addr, lambda N, W: 1), ('ringw', build_ringw, test_ringw, lambda N, W: N / 2), ('ringb', build_ringb, test_ringb, lambda N, W: N * W / 2)):
            if kind != 'addr' and N * W > 4096: continue
            if N * W > 2048 and kind == 'ringb': continue
            net, outs = tf(N, W, rnd) if N * W <= 1024 else (lambda r: (r[0], r[2]))(f(N, W))
            nd, df = count(net, outs); bits = N * W
            print(f'{kind:6s} {N:5d} {W:3d} {bits:6d} | {nd:6d} {df:5d} {nd + 6 * df:7d} | {nd / bits:8.2f} {(nd + 6 * df) / bits:9.2f} {lat(N, W):17.0f}')
