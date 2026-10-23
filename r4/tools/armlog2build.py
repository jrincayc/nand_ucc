#!/usr/bin/env python3
"""armlog2build.py ARM.LOG OUT.build [OFS] [--norom] -- decode the emulator's arm-register write log (lines 'reg value') into the rndp build-file
command list (place/track/via/rom), adding the board offset OFS (default 32).  --norom drops the PROGRAM_ROM commands (for comparison with golden/*.cmds)."""
import sys
a = [x for x in sys.argv[1:] if not x.startswith('--')]; norom = '--norom' in sys.argv
ofs = int(a[2]) if len(a) > 2 else 32
s16 = lambda v: v - 65536 if v >= 32768 else v
regs = [0] * 16; out = []
for l in open(a[0]):
    r, v = map(int, l.split()); regs[r] = v
    if r != 15: continue
    w = lambda i: regs[i] | regs[i + 1] << 8
    ax, ay, bx, by = s16(w(0)), s16(w(2)), s16(w(4)), s16(w(6))
    if v == 1: out.append(f'place {regs[8]} {ax + ofs} {ay + ofs} {regs[9]} {regs[10]}')
    elif v == 3:
        if not norom: out.append(f'rom {ax + ofs} {ay + ofs} {w(4)} {regs[10]}')
    elif v == 4: out.append(f'track {regs[10]} {ax + ofs} {ay + ofs} {bx + ofs} {by + ofs}')
    elif v == 5: out.append(f'via {ax + ofs} {ay + ofs}')
    else: raise SystemExit(f'unknown command {v}')
open(a[1], 'w').write('\n'.join(out) + '\n'); print(len(out), 'commands')
