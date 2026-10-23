#!/usr/bin/env python3
"""test_route3.py -- route1+route2+route3 on the Rust emulator: the arm-register log, decoded into commands, must equal route_ref.route(...)[0] (and so the golden command list);
a second run with board offsets (RV_OX, RV_OY) must equal the first plus the offset.  Prints instruction counts per run."""
import os, struct, subprocess, sys, tempfile
os.environ.update(ROM_BITS='16', AB='18', RAM_BITS='18')
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools')]
import rvasm, lay, place_ref, route_ref
EXE = os.path.join(HERE, '..', 'rvemu_rs', 'target', 'release', 'rvemu'); K = os.path.join(HERE, '..', 'kernels')
tmp = tempfile.mkdtemp(); stub = tmp + '/stub.s'
open(stub, 'w').write('start:\n    jal ra, route1\n    jal ra, route2\n    jal ra, route3_place\n    jal ra, route3_wire\nhalt:\n    j halt\n')
_, img = rvasm.assemble([stub] + [os.path.join(K, f) for f in ('memmap.s', 'memmap_route.s', 'route1.s', 'route2.s', 'route3.s')], tmp + '/o'); open(tmp + '/rom.bin', 'wb').write(bytes(img)); print('router ROM bytes (with stub):', len(img))
def s16(v): return v - 65536 if v >= 32768 else v
def decode(log):
    regs = [0] * 16; cmds = []
    for r, v in log:
        regs[r] = v
        if r != 15: continue
        w = lambda i: regs[i] | regs[i + 1] << 8
        ax, ay, bx, by = s16(w(0)), s16(w(2)), s16(w(4)), s16(w(6))
        if v == 1: cmds.append(('place', regs[8], ax, ay, regs[9], regs[10]))
        elif v == 4: cmds.append(('track', regs[10], ax, ay, bx, by))
        elif v == 5: cmds.append(('via', ax, ay))
        else: cmds.append(('?', v))
    return cmds
import random, re
nl = lay.read_nl(os.path.join(HERE, '..', 'hd', 'm18', 'cpu_g1.nl')); N = len(nl.nodes)
perm = list(range(N)); random.Random(12).shuffle(perm)       # same numbering as tests/golden_route.py
def rn(t):
    m = re.match(r'^n(\d+)(.*)$', t); return f'n{perm[int(m.group(1))]}{m.group(2)}' if m else t
new = [None] * N
for k, (kind, ins) in enumerate(nl.nodes): new[perm[k]] = (kind, [rn(t) for t in ins])
nl.nodes = new; nl.ports = [(n, rn(t)) for n, t in nl.ports]
order = place_ref.order(nl, seed=1)
gold = [tuple([c[0]] + [int(x) for x in c[1:]]) for c in (l.split() for l in open(os.path.join(HERE, '..', 'golden', 'cpu_g1_m18.cmds')))]
cmds, info = route_ref.route(nl, order); cmds = [tuple(c) for c in cmds]
assert cmds == gold, 'route_ref differs from golden'
bad = 0
for ox, oy in ((0, 0), (1000, 77)):
    ram = bytearray(0x40000); route_ref.pack(nl, order, ram); struct.pack_into('<II', ram, 0x138, ox, oy); open(tmp + '/ram.bin', 'wb').write(ram)
    rp = subprocess.run([EXE, tmp + '/rom.bin', '--rom-bits', '16', '--ab', '18', '--ram-bytes', str(0x40000), '--load-ram', tmp + '/ram.bin', '--armlog', tmp + '/arm.log', '--dump-ram', tmp + '/out.bin', '--max', '2000000000'], capture_output=True, text=True)
    assert rp.returncode == 0, rp.stderr
    log = [tuple(map(int, l.split())) for l in open(tmp + '/arm.log')]
    got = decode(log)
    exp = [(c[0], c[1], c[2] + ox, c[3] + oy, c[4], c[5]) if c[0] == 'place' else (c[0], c[1], c[2] + ox, c[3] + oy, c[4] + ox, c[5] + oy) if c[0] == 'track' else (c[0], c[1] + ox, c[2] + oy) for c in cmds]
    ok = got == exp
    ni = int(rp.stderr.split('instructions')[1].split()[0]); aw = int(rp.stderr.split('arm_writes')[1].split()[0])
    print(f'offset ({ox},{oy}): {len(got)} commands (reference {len(exp)}), {aw} arm byte writes, {ni} instructions:', 'IDENTICAL' if ok else 'MISMATCH')
    if not ok:
        bad += 1
        for i, (g, e) in enumerate(zip(got, exp)):
            if g != e: print(' first difference at', i, g, e); break
print('RESULT', 'PASS' if not bad else 'FAIL'); sys.exit(1 if bad else 0)
