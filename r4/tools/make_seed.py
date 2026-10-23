#!/usr/bin/env python3
"""make_seed.py OUTDIR [PX PY] -- the seed (parent) world for the in-rndp run (S8).
Builds the program for the improved HD (the fixed point: its child is a copy of itself), runs it on the Rust emulator, takes the arm commands, undoes the child-frame
offset (RV_OX, RV_OY, read from the emulator's RAM dump) and places the resulting machine at (PX, PY) as the PARENT.
OUTDIR/seed.build  everything except the RUN wires (machine is held in reset);  OUTDIR/run.build  the RUN wires;  OUTDIR/seed.json  parameters (DX = shift parent -> child).
Then:  rndp --rom on --ram on --layers 2 --max-ram-addr-bits 18 --build seed.build --steps 40 --save s1.state
       rndp --world s1.state --build run.build --steps N --checkpoint ck.state --checkpoint-every M --save done.state"""
import json, os, struct, subprocess, sys
for k, v in (('ROM_BITS', '16'), ('AB', '18'), ('RAM_BITS', '18')): os.environ.setdefault(k, v)
HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(HERE, '..'); sys.path[:0] = [HERE]
import hd as H, hd2nl, lay, place_ref, route_ref, ref_improve
out = sys.argv[1]; PX = int(sys.argv[2]) if len(sys.argv) > 2 else 40; PY = int(sys.argv[3]) if len(sys.argv) > 3 else 1200
os.makedirs(out, exist_ok=True)
hdf = os.path.join(R, 'hd', 'm18', 'cpu_mod_improved.hd')
subprocess.run([sys.executable, os.path.join(HERE, 'build_rom.py'), out + '/o', hdf], check=True, capture_output=True)
EXE = os.path.join(R, 'rvemu_rs', 'target', 'release', 'rvemu')
r = subprocess.run([EXE, out + '/o/rom.bin', '--rom-bits', '16', '--ab', '18', '--ram-bytes', str(1 << 18), '--max', '3000000000', '--armlog', out + '/arm.log', '--dump-ram', out + '/emu.ram'], capture_output=True, text=True)
assert r.returncode == 0, r.stderr
ram = open(out + '/emu.ram', 'rb').read(); OX, OY = struct.unpack_from('<ii', ram, 0x138)
h = H.read(open(hdf).read()); text, _ = hd2nl.convert(h, h.params['ram_abits']); open(out + '/imp.nl', 'w').write(text)
nl = lay.read_nl(out + '/imp.nl'); _, info = route_ref.route(nl, place_ref.order(nl, seed=1)); nrun = info['nlate'][2]
s16 = lambda v: v - 65536 if v >= 32768 else v
regs = [0] * 16; cmds = []
for l in open(out + '/arm.log'):
    reg, v = map(int, l.split()); regs[reg] = v
    if reg != 15: continue
    w = lambda i: regs[i] | regs[i + 1] << 8
    ax, ay, bx, by = s16(w(0)), s16(w(2)), s16(w(4)), s16(w(6))
    X = lambda x: x - OX + PX; Y = lambda y: y - OY + PY                   # child-frame coordinates, placed as the parent at (PX, PY)
    if v == 1: cmds.append(f'place {regs[8]} {X(ax)} {Y(ay)} {regs[9]} {regs[10]}')
    elif v == 3: cmds.append(f'rom {X(ax)} {Y(ay)} {w(4)} {regs[10]}')
    elif v == 4: cmds.append(f'track {regs[10]} {X(ax)} {Y(ay)} {X(bx)} {Y(by)}')
    elif v == 5: cmds.append(f'via {X(ax)} {Y(ay)}')
    else: raise SystemExit(f'unknown command {v}')
open(out + '/seed.build', 'w').write('\n'.join(cmds[:-nrun]) + '\n'); open(out + '/run.build', 'w').write('\n'.join(cmds[-nrun:]) + '\n')
par = dict(PX=PX, PY=PY, OX=OX, OY=OY, W=info['W'], H=info['H'], xa=info['pb']['arm'], ylast=info['Y'][21], DX=info['W'] + 8, ncmds=len(cmds), nrun=nrun, arm_writes=sum(1 for _ in open(out + '/arm.log')))
json.dump(par, open(out + '/seed.json', 'w'), indent=1); print(par)
