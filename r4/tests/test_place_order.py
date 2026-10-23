#!/usr/bin/env python3
"""test_place_order.py -- build_graph + place_order (+ lpa_level, contract, chain) on the Rust emulator against place_ref.order(nl, seed): the placement order
of every gate must be identical.  Random netlists and the real cpu_g1 (old and new map); prints the measured instruction count."""
import os, random, struct, subprocess, sys, tempfile
os.environ.update(ROM_BITS='16', AB='18', RAM_BITS='18')
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools'), HERE]
import rvasm, lay, place_ref
import test_build_graph_lib as T
EXE = os.path.join(HERE, '..', 'rvemu_rs', 'target', 'release', 'rvemu'); K = os.path.join(HERE, '..', 'kernels')
tmp = tempfile.mkdtemp(); stub = tmp + '/stub.s'
open(stub, 'w').write('start:\n    jal ra, build_graph\n    jal ra, place_order\nhalt:\n    j halt\n')
_, img = rvasm.assemble([stub] + [os.path.join(K, f) for f in ('memmap.s', 'build_graph.s', 'lpa_level.s', 'chain.s', 'place_order.s')], tmp + '/o')
open(tmp + '/rom.bin', 'wb').write(bytes(img)); print('ROM bytes (all kernels + stub):', len(img))
def run(nl, seed, levels=0):
    N = len(nl.nodes); ram = bytearray(0x40000)
    src = T.pack(nl, ram); struct.pack_into('<I', ram, 0x50, place_ref.Rng(seed).s); struct.pack_into('<I', ram, 0xBC, levels)
    open(tmp + '/ram.bin', 'wb').write(ram)
    rp = subprocess.run([EXE, tmp + '/rom.bin', '--rom-bits', '16', '--ab', '18', '--ram-bytes', str(0x40000), '--load-ram', tmp + '/ram.bin', '--dump-ram', tmp + '/out.bin', '--max', '3000000000'], capture_output=True, text=True)
    assert rp.returncode == 0, rp.stderr
    out = open(tmp + '/out.bin', 'rb').read(); got = list(struct.unpack_from('<%dH' % N, out, 0x33000)); err = struct.unpack_from('<I', out, 0x70)[0]
    ref = place_ref.order(nl, caps=(8, 32, 128, 512)[:levels or 4], seed=seed)
    return err == 0 and got == ref, int(rp.stderr.split('instructions')[1].split()[0])
rr = random.Random(11); bad = 0
for t in range(20):
    nl = T.rand_nl(rr, rr.choice([3, 10, 40, 200, 600, 1500])); ok, n = run(nl, rr.randint(1, 99))
    if not ok: bad += 1; print('MISMATCH random', t, len(nl.nodes))
print('random netlists:', 20 - bad, '/ 20 identical')
for name in ('cpu_g1.nl', 'm18/cpu_g1.nl'):
    nl = lay.read_nl(os.path.join(HERE, '..', 'hd', name))
    for seed in (1, 2):
        ok, n = run(nl, seed); print(f'{name} seed {seed}: {"identical" if ok else "MISMATCH"}, {n:,} instructions'); bad += 0 if ok else 1
print('RESULT', 'PASS' if not bad else 'FAIL'); sys.exit(1 if bad else 0)
