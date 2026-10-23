#!/usr/bin/env python3
"""E1b: ROM-as-logic cost on real byte streams (not random), with per-column polarity choice (implement the sparser of f and ~f, +1 inverter)."""
import sys
from e1_rom import *
def plane_pol(words, n, W, g=2):
    net = Net(); a = addr_inputs(net, n); lines = decode_lines(net, a, g); outs = []
    N = len(words)
    for j in range(W):
        ones = [i for i in range(N) if (words[i] >> j) & 1]
        if len(ones) * 2 > (1 << n):                      # store the complement (over the full address space 2^n)
            zs = [i for i in range(1 << n) if i >= N or not (words[i] >> j) & 1]
            outs.append(net.not_(or_low(net, [lines[i] for i in zs])))
        else: outs.append(or_low(net, [lines[i] for i in ones]))
    return net, a, outs
for path, nbytes in ((sys.argv[1], int(sys.argv[2])),):
    data = open(path, 'rb').read()[:nbytes]; n = (len(data) - 1).bit_length(); W = 8; words = list(data) + [0] * ((1 << n) - len(data))
    ones = sum(bin(w).count('1') for w in words)
    r = {}
    for name, f in (('plane', lambda: rom_plane(words, n, W, 2)), ('plane+pol', lambda: plane_pol(words, n, W, 2)), ('shannon', lambda: rom_shannon(words, n, W))):
        net, a, outs = f(); verify(net, a, outs, words, W); r[name] = count(net, outs)[0]
    print(f'{path.split("/")[-2]}/{path.split("/")[-1]} first {len(data)} B (n={n}): ones {ones} ({ones / (8 * len(words)):.2f}) | ' + ' '.join(f'{k} {v} ({v / len(words):.1f}/word {v / ones:.2f}/one)' for k, v in r.items()))
