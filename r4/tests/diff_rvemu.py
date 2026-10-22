#!/usr/bin/env python3
"""diff_rvemu.py -- random RV32EC programs run on tools/rvemu.py and on the Rust emulator; ROM_BITS=15 build; RAM, arm log, icount must agree.
usage: diff_rvemu.py [first_seed [count [n_instr]]]"""
import os, random, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault('ROM_BITS', '15'); AB = os.environ.get('AB', os.environ['ROM_BITS']); RAMB = int(os.environ.get('RAM_BITS', '8'))
sys.path[:0] = [os.path.join(HERE, '..', 'tools'), HERE]
import rvasm, rvemu, randprog
EXE = os.path.join(HERE, '..', 'rvemu_rs', 'target', 'release', 'rvemu')
s0 = int(sys.argv[1]) if len(sys.argv) > 1 else 0; cnt = int(sys.argv[2]) if len(sys.argv) > 2 else 50; n = int(sys.argv[3]) if len(sys.argv) > 3 else 200
bad = 0
with tempfile.TemporaryDirectory() as t:
    for seed in range(s0, s0 + cnt):
        src = randprog.gen(random.Random(seed), n); p = os.path.join(t, 'p.s'); open(p, 'w').write(src)
        a, img = rvasm.assemble([p], os.path.join(t, 'o')); rp = os.path.join(t, 'rom.bin'); open(rp, 'wb').write(bytes(img))
        m = rvemu.Machine(img)
        try: m.run(100000)
        except rvemu.Illegal as e: print(seed, 'py illegal', e); bad += 1; continue
        r = subprocess.run([EXE, rp, '--rom-bits', os.environ['ROM_BITS'], '--ab', AB, '--ram-bytes', str(1 << RAMB), '--max', '100000', '--armlog', t + '/arm', '--dump-ram', t + '/ram'], capture_output=True, text=True)
        arm = [tuple(map(int, l.split())) for l in open(t + '/arm')]; ram = open(t + '/ram', 'rb').read()
        ok = r.returncode == 0 and ram == bytes(m.ram) and arm == m.armlog and f'instructions {m.icount} ' in r.stderr
        if not ok: print(seed, 'MISMATCH', r.returncode, r.stderr.strip(), m.icount); bad += 1
print('diff_rvemu:', 'FAIL' if bad else 'PASS', f'({cnt} programs)'); sys.exit(1 if bad else 0)
