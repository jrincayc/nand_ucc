#!/usr/bin/env python3
"""r4_designer_measure.py R4DIR WORKDIR -- step 0 of DESIGNER_LADDER_SPEC.md: measure R4 as a designer.

R4DIR is the r4/ directory of a clone of https://github.com/jrincayc/nand_ucc (rndp_r4 in the Project).
Needs python3 and cargo (builds r4/rvemu_rs, no crates).  For the seed and the improved hardware description it
assembles the ROM (tools/build_rom.py), runs it on the RV32EC emulator with --profile, and reports
  ROM bytes, split by source file (hd_data.s is the design input, everything else is designer code),
  RAM bytes written and touched (the arm window 0x3FFF0.. is excluded),
  instructions executed and arm register writes.
S = ROM bytes + RAM bytes written, in bits.
"""
import collections, os, subprocess, sys

r4, work = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
os.makedirs(work, exist_ok=True)
env = dict(os.environ, ROM_BITS='16', AB='18', RAM_BITS='18')
subprocess.run(['cargo', 'build', '--release', '-q'], cwd=os.path.join(r4, 'rvemu_rs'), check=True)
emu = os.path.join(r4, 'rvemu_rs', 'target', 'release', 'rvemu')
ARM = 0x3FFF0

for name, hd in (('seed', 'cpu_mod.hd'), ('improved', 'cpu_mod_improved.hd')):
    out = os.path.join(work, name)
    subprocess.run([sys.executable, os.path.join(r4, 'tools', 'build_rom.py'), out, os.path.join(r4, 'hd', 'm18', hd)],
                   env=env, check=True, stdout=subprocess.DEVNULL)
    prof, arm = out + '.prof', out + '.arm'
    res = subprocess.run([emu, out + '/rom.bin', '--rom-bits', '16', '--ab', '18', '--ram-bytes', '262144', '--max', '200000000',
                          '--armlog', arm, '--profile', prof], capture_output=True, text=True)
    last = (res.stdout + res.stderr).strip().splitlines()[-1]
    rom = open(out + '/rom.bin', 'rb').read()
    per = collections.Counter()
    for l in open(out + '/rom.lst'):
        p = l.split('|')
        if len(p) >= 2:
            per[p[1].strip().split(':')[0]] += len(p[0].split()[1:])
    written = touched = 0
    for l in open(prof):
        p = l.split()
        if p[0] == 'ram':
            lo, hi, f = int(p[1], 16), min(int(p[2], 16), ARM - 1), int(p[3])
            if hi >= lo:
                touched += hi - lo + 1
                if f & 2:
                    written += hi - lo + 1
    code = sum(n for f, n in per.items() if f != 'hd_data.s')
    print(f'== {name} ({hd})')
    print('  emulator:', last)
    print(f'  ROM bytes {len(rom)} (nonzero {sum(1 for b in rom if b)}): designer code {code}, design input (hd_data.s) {per["hd_data.s"]}')
    for f, n in per.most_common():
        if n:
            print(f'    {f:16s} {n}')
    print(f'  RAM bytes written {written}, touched (read or written) {touched}')
    s = (len(rom) + written) * 8
    print(f'  S = ROM + RAM written = {len(rom) + written} bytes = {s} bits ({s:.3g}); RAM share {written / (len(rom) + written):.1%}')
    print(f'  designer only (code + RAM written) = {code + written} bytes = {(code + written) * 8} bits')
