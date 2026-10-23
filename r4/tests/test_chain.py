#!/usr/bin/env python3
"""test_chain.py -- kernels/chain.s on the Rust emulator against place_ref.chain([[x] for x in S], adj): random weighted graphs, random vertex subsets
(isolated items, disconnected parts, ties) and the real level-0 graph restricted to 3 sizes of subsets."""
import os, random, struct, subprocess, sys, tempfile
os.environ.update(ROM_BITS='16', AB='18', RAM_BITS='18')
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools')]
import rvasm, lay, place_ref
EXE = os.path.join(HERE, '..', 'rvemu_rs', 'target', 'release', 'rvemu'); K = os.path.join(HERE, '..', 'kernels')
tmp = tempfile.mkdtemp(); stub = tmp + '/stub.s'
open(stub, 'w').write('start:\n    lw a0, 0xC0(x0)\n    lw a1, 0xC4(x0)\n    jal gp, chain\nhalt:\n    j halt\n')
_, img = rvasm.assemble([stub, os.path.join(K, 'memmap.s'), os.path.join(K, 'chain.s')], tmp + '/o'); open(tmp + '/rom.bin', 'wb').write(bytes(img)); print('kernel ROM bytes (with stub):', len(img))
SVA = 0x37000
def run(adj, S):
    NV = len(adj); ram = bytearray(0x40000); off = [0]; nbr = []; wt = []
    for v in range(NV):
        for u, w in adj[v].items(): nbr.append(u); wt.append(w)
        off.append(len(nbr))
    for base, arr in ((0x1000, off), (0x12000, nbr), (0x1C000, wt), (SVA, S)): struct.pack_into('<%dH' % len(arr), ram, base, *arr)
    struct.pack_into('<4096H', ram, 0x07000, *([65535] * 4096)); struct.pack_into('<II', ram, 0xC0, SVA, len(S))
    open(tmp + '/ram.bin', 'wb').write(ram)
    rp = subprocess.run([EXE, tmp + '/rom.bin', '--rom-bits', '16', '--ab', '18', '--ram-bytes', str(0x40000), '--load-ram', tmp + '/ram.bin', '--dump-ram', tmp + '/out.bin', '--max', '500000000'], capture_output=True, text=True)
    assert rp.returncode == 0, rp.stderr
    out = open(tmp + '/out.bin', 'rb').read(); m = len(S); got = [S[i] for i in struct.unpack_from('<%dH' % m, out, 0x31000)]
    idx_clean = set(struct.unpack_from('<4096H', out, 0x07000)) <= {65535}
    ref = [g[0] for g in place_ref.chain([[x] for x in S], adj)]
    return got == ref and idx_clean, int(rp.stderr.split('instructions')[1].split()[0])
rr = random.Random(3); bad = 0
for t in range(60):
    n = rr.choice([2, 3, 7, 30, 120, 400]); adj = [dict() for _ in range(n)]
    for _ in range(rr.randint(0, 4 * n)):
        a, b = rr.randrange(n), rr.randrange(n)
        if a != b: w = rr.choice([1, 2, 3, 5, 60, 65535]); adj[a][b] = adj[b][a] = w
    S = sorted(rr.sample(range(n), rr.randint(1, n)))
    ok, ni = run(adj, S)
    if not ok: bad += 1; print('MISMATCH', t, n, len(S))
print('random:', 60 - bad, '/ 60 identical')
nl = lay.read_nl(os.path.join(HERE, '..', 'hd', 'm18', 'cpu_g1.nl')); adj = place_ref.build_graph(nl)
for m in (8, 64, 512, 3000):
    S = sorted(random.Random(m).sample(range(len(adj)), m)) if m < 3000 else list(range(len(adj)))[:3000]
    ok, ni = run(adj, S); print(f'real graph, {len(S)} items: {"identical" if ok else "MISMATCH"}, {ni} instructions'); bad += 0 if ok else 1
print('RESULT', 'PASS' if not bad else 'FAIL'); sys.exit(1 if bad else 0)
