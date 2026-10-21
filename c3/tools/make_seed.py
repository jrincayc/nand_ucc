#!/usr/bin/env python3
"""make_seed.py NL LAY ROM.BIN OUTDIR [OX OY] -- write the seed world build files for a compact replicator:
   seed.build  every part and wire of the machine EXCEPT the RUN-sink path (so the machine starts held in reset),
   run.build   the RUN wires (apply after a few ticks of reset: 'rndp --world seed.state --build run.build --steps N')."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, '..', 'tests')]
import lay, validate_layout as V
nlf, layf, romf, out = sys.argv[1:5]
V.OFS = (int(sys.argv[5]), int(sys.argv[6])) if len(sys.argv) > 6 else (32, 32)
nl = lay.read_nl(nlf); L = lay.read_lay(layf)
cmds = lay.commands(L, nl, list(open(romf, 'rb').read()))
n = 0
for who, late, drv, pts in L.sinks:
    if late == 2: n += sum(1 for a, b in zip(pts, pts[1:]))
os.makedirs(out, exist_ok=True)
V.write_build(cmds[:-n], f'{out}/seed.build'); V.write_build(cmds[-n:], f'{out}/run.build')
print(f'{len(cmds) - n} seed commands, {n} RUN commands, board {L.W}x{L.H} (child offset {L.W})')
