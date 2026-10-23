#!/usr/bin/env python3
"""build_rom.py OUTDIR [HDFILE] -- assemble the whole R4 program (kernels + HD data) into OUTDIR/{rom.bin,rom.lst,symbols.txt}.
Env: ROM_BITS=16 AB=18 RAM_BITS=18 (set here if missing).  PLACE_SEED (default 1) is the placement RNG seed."""
import os, sys
for k, v in (('ROM_BITS', '16'), ('AB', '18'), ('RAM_BITS', '18')): os.environ.setdefault(k, v)
HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(HERE, '..'); sys.path[:0] = [HERE]
import rvasm, hd2bin, place_ref, hd as H
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
hdf = sys.argv[2] if len(sys.argv) > 2 else os.path.join(R, 'hd', 'm18', 'cpu_mod.hd')
open(out + '/hd_data.s', 'w').write(hd2bin.text(H.read(open(hdf).read())))
open(out + '/const.s', 'w').write(f'.equ RNG_SEED, {place_ref.Rng(int(os.environ.get("PLACE_SEED", "1"))).s}\n')
K = os.path.join(R, 'kernels')
files = [out + '/const.s'] + [os.path.join(K, f) for f in ('start.s', 'memmap.s', 'memmap_route.s', 'memmap_imp.s', 'memmap_hd.s', 'improve.s', 'route1.s', 'route2.s', 'route3.s', 'hdflat.s', 'main.s', 'build_graph.s', 'lpa_level.s', 'chain.s', 'place_order.s')] + [out + '/hd_data.s']
_, img = rvasm.assemble(files, out); open(out + '/rom.bin', 'wb').write(bytes(img)); print(len(img), 'bytes ->', out + '/rom.bin')
