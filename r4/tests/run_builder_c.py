#!/usr/bin/env python3
"""run_builder_c.py OUTDIR NL LAY -- run the compact builder on rvemu; compare the arm commands it issues (a) with an independent decoder of the ROM data
(layrom.py) and (b) as copper with the layout tool's output: same parts, same set of copper cells per layer, same vias, ROM programmed before any wire,
EN's path last among the port paths, RUN path after it."""
import os, sys, time, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, '..', 'tools'), HERE, '/home/claude/c3/tools']
import rvemu, lay, layrom
from run_builder import run, decode

def cover(cmds, dx=0, dy=0):
    cells = [set(), set()]; vias = set(); parts = collections.Counter(); rom = {}
    for c in cmds:
        if c[0] == 'track':
            l, x0, y0, x1, y1 = c[1], c[2], c[3], c[4], c[5]
            for x in range(min(x0, x1), max(x0, x1) + 1):
                for y in range(min(y0, y1), max(y0, y1) + 1): cells[l].add((x, y))
        elif c[0] == 'via': vias.add((c[1], c[2]))
        elif c[0] == 'place': parts[(c[1], c[2], c[3], c[4], c[5])] += 1
        elif c[0] == 'rom': rom[c[3]] = c[4]
    return cells, vias, parts, rom

if __name__ == '__main__':
    outdir, nlf, layf = sys.argv[1:4]
    m, rom, dt, hi, bad = run(outdir, int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 10**9)
    print(f'halted={m.halted}: {m.icount} instructions, {dt:.0f}s; RAM high-water {hi:#x}; bad writes {len(bad)} {bad[:3]}')
    got = decode(m.armlog)
    print('got', dict(collections.Counter(c[0] for c in got)))
    ok = m.halted and not bad
    # (a) independent decoder of the ROM image
    ref = layrom.decode(rom, os.path.join(outdir, 'symbols.txt'))
    g = collections.Counter(map(tuple, got)); r = collections.Counter(map(tuple, ref))
    print('vs ROM decoder: missing', sum((r - g).values()), 'extra', sum((g - r).values()), '| order identical:', [tuple(c) for c in got] == [tuple(c) for c in ref])
    ok = ok and g == r and [tuple(c) for c in got] == [tuple(c) for c in ref]
    # (b) copper equal to the layout tool's output
    nl = lay.read_nl(nlf); L = lay.read_lay(layf)
    ax, ay = L.parts['arm'][:2]; W = L.W
    lc = lay.commands(L, nl, [])
    shifted = []
    for c in lc:
        if c[0] == 'place':
            shifted.append(('place', c[1], c[2] - ax + W, c[3] - ay, c[4], c[5]))
        elif c[0] == 'track': shifted.append(('track', c[1], c[2] - ax + W, c[3] - ay, c[4] - ax + W, c[5] - ay))
        elif c[0] == 'via': shifted.append(('via', c[1] - ax + W, c[2] - ay))
    (ca, va, pa, ra), (cb, vb, pb, rb_) = cover(got), cover(shifted)
    print('copper layer 0 equal:', ca[0] == cb[0], len(ca[0]), '| layer 1 equal:', ca[1] == cb[1], len(ca[1]), '| vias equal:', va == vb, len(va), '| parts equal:', pa == pb, sum(pa.values()))
    ok = ok and ca == cb and va == vb and pa == pb
    kinds = [c[0] for c in got]
    last_rom = max((i for i, k in enumerate(kinds) if k == 'rom'), default=-1)
    first_wire = min((i for i, k in enumerate(kinds) if k in ('track', 'via')), default=10**9)
    print('ROM before wires:', last_rom < first_wire, '| ROM bytes programmed', len(ra), 'nonzero in image', sum(1 for v in rom if v))
    ok = ok and last_rom < first_wire and len(ra) == sum(1 for v in rom if v) and all(rom[a] == v for a, v in ra.items())
    print('RESULT', 'PASS' if ok else 'FAIL'); sys.exit(0 if ok else 1)
