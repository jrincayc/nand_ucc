#!/usr/bin/env python3
"""test_lpa_level.py -- kernels/lpa_level.s on the Rust emulator (ROM 16 bits, AB 18, 256 KiB RAM) against place_ref.lpa_labels:
labels of all vertices and the final xorshift state must be identical.  Random graphs (various sizes, vertex sizes, caps, weights up to 65535) and the real level-0 graph of cpu_g1.
usage: test_lpa_level.py [count]"""
import os, random, struct, subprocess, sys, tempfile
os.environ.update(ROM_BITS='16', AB='18', RAM_BITS='18')
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools')]
import rvasm, lay, place_ref
EXE = os.path.join(HERE, '..', 'rvemu_rs', 'target', 'release', 'rvemu'); KERN = os.path.join(HERE, '..', 'kernels', 'lpa_level.s')
A = dict(OFF=0x1000, LAB=0x3000, VSZ=0x5000, NBR=0x12000, WT=0x1C000); V_RNG, V_NV, V_CAP = 0x50, 0x54, 0x58
tmp = tempfile.mkdtemp(); stub = os.path.join(tmp, 'stub.s')
open(stub, 'w').write('start:\n    jal ra, lpa_level\nhalt:\n    j halt\n')
_, img = rvasm.assemble([stub, os.path.join(HERE, '..', 'kernels', 'memmap.s'), KERN], os.path.join(tmp, 'o')); open(tmp + '/rom.bin', 'wb').write(bytes(img))
print('kernel ROM bytes (with stub):', len(img))

def run(adj, vsize, cap, seed):
    NV = len(adj); assert NV < 4096
    ram = bytearray(0x40000); off = [0]; nbr = []; wt = []
    for v in range(NV):
        for u, w in adj[v].items(): nbr.append(u); wt.append(w)
        off.append(len(nbr))
    assert len(nbr) <= 20480
    for base, arr in ((A['OFF'], off), (A['NBR'], nbr), (A['WT'], wt), (A['VSZ'], [vsize[v] for v in range(NV)])): struct.pack_into('<%dH' % len(arr), ram, base, *arr)
    r0 = place_ref.Rng(seed); struct.pack_into('<III', ram, V_RNG, r0.s, NV, cap)
    open(tmp + '/ram.bin', 'wb').write(ram)
    rp = subprocess.run([EXE, tmp + '/rom.bin', '--rom-bits', '16', '--ab', '18', '--ram-bytes', str(0x40000), '--load-ram', tmp + '/ram.bin', '--dump-ram', tmp + '/out.bin', '--max', '2000000000'], capture_output=True, text=True)
    assert rp.returncode == 0, rp.stderr
    out = open(tmp + '/out.bin', 'rb').read(); got = list(struct.unpack_from('<%dH' % NV, out, A['LAB'])); grng = struct.unpack_from('<I', out, V_RNG)[0]
    n = int(rp.stderr.split('instructions')[1].split()[0])
    r = place_ref.Rng(seed); lab = place_ref.lpa_labels(list(range(NV)), adj, vsize, cap, r)
    return got == [lab[v] for v in range(NV)] and grng == r.s, n, len(nbr)

def rand_graph(rng, n):
    adj = [dict() for _ in range(n)]
    for _ in range(rng.randint(n, 4 * n)):
        a, b = rng.randrange(n), rng.randrange(n)
        if a != b:
            w = rng.choice([1, 5, 12, 60, 300, 65535]) if rng.random() < .3 else rng.randint(1, 60)
            adj[a][b] = adj[b][a] = min(65535, w)
    return adj
cnt = int(sys.argv[1]) if len(sys.argv) > 1 else 30; bad = 0; rr = random.Random(5)
for t in range(cnt):
    n = rr.choice([2, 3, 10, 40, 200, 600]); adj = rand_graph(rr, n); vs = {v: rr.choice([1, 1, 1, 2, 5, 9]) for v in range(n)}; cap = rr.choice([4, 8, 32, 128, 512])
    ok, ni, ne = run(adj, vs, cap, rr.randint(1, 1000))
    if not ok: bad += 1; print('MISMATCH random', t, n, cap)
print('random graphs:', cnt - bad, '/', cnt, 'identical')
nl = lay.read_nl(os.path.join(HERE, '..', 'hd', 'm18', 'cpu_g1.nl')); adj = place_ref.build_graph(nl); N = len(adj)
for cap in (8, 32, 128, 512):
    ok, ni, ne = run(adj, {v: 1 for v in range(N)}, cap, 1)
    print(f'real level-0 graph: N={N} directed edges={ne} cap={cap}: {"identical" if ok else "MISMATCH"}, {ni} instructions'); bad += 0 if ok else 1
print('RESULT', 'PASS' if not bad else 'FAIL'); sys.exit(1 if bad else 0)
