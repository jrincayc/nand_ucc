#!/usr/bin/env python3
"""gate_vs_rtl.py -- the NAND/DFF CPU (compiled to C) against the microcode model, tick for tick, on rvasm / clang / random programs."""
import os, random, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools'), HERE]
import cpu_rtl, netsim, rvasm, randprog


def compare(exe, rom, nticks, tmp, label=''):
    open(os.path.join(tmp, 'rom.bin'), 'wb').write(rom)
    out = subprocess.run([exe, os.path.join(tmp, 'rom.bin'), str(nticks), '1'], capture_output=True, text=True, check=True).stdout.split('\n')
    c = cpu_rtl.CPU(rom)
    for t in range(nticks):
        c.tick()
        if t == 0: c.upc = 0
        u, k, ir, ar, A, R, C, Z, SA, SB = c.state()
        want = '%02x %x %02x%02x%02x%02x %04x %02x %02x %x%x%x%x' % (u, k, ir[0], ir[1], ir[2], ir[3], ar, A, R, C, Z, SA, SB)
        if out[t] != want:
            return f'{label}: tick {t}: gate {out[t]!r} rtl {want!r}'
    # final RAM / arm
    ram = [l for l in out if l.startswith('RAM')][0][4:]
    if ram != bytes(c.ram).hex(): return f'{label}: RAM differs at end'
    arm = [l for l in out if l.startswith('ARM')][0].split()[2:]
    if arm != [f'{a:x}:{v:02x}' for a, v in c.arm]: return f'{label}: arm log differs'
    return None


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    nt = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
    tmp = tempfile.mkdtemp()
    exe, _ = netsim.compile_sim(os.path.join(tmp, 'sim'))
    exe = os.path.join(tmp, 'sim', 'sim')
    bad = 0
    for seed in range(n):
        rng = random.Random(seed); src = randprog.gen(rng, 150); p = os.path.join(tmp, 'p.s'); open(p, 'w').write(src)
        a, img = rvasm.assemble([p], os.path.join(tmp, 'o'))
        r = compare(exe, img, nt, tmp, f'rand seed {seed}')
        if r: print(r); bad += 1
    print('gate_vs_rtl:', 'FAIL' if bad else f'PASS ({n} programs x {nt} ticks)'); sys.exit(1 if bad else 0)
