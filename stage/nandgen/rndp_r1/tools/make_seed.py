#!/usr/bin/env python3
"""make_seed.py HD ROM.BIN OUTDIR [OX OY] -- write the seed world build files for Replicator 1:
   seed.build  every part and wire of the machine EXCEPT the RUN wires (so the machine starts held in reset),
   run.build   the RUN wires (apply after a few ticks of reset: 'rndp --world seed.state --build run.build --steps N')."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', 'tests')]
import hd as H, ref_flatten as RF, validate_geometry as V
hdf, romf, out = sys.argv[1:4]
ofs = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (32, 32)
f = RF.flatten(H.read(open(hdf).read()))
cmds = RF.commands(f, list(open(romf, 'rb').read()))
n = f.n_run_cmds
os.makedirs(out, exist_ok=True)
V.write_build(cmds[:-n], f'{out}/seed.build', ofs)
V.write_build(cmds[-n:], f'{out}/run.build', ofs)
print(f'{len(cmds) - n} seed commands, {n} RUN commands, offset {ofs}, extent {RF.extent(f)}')
