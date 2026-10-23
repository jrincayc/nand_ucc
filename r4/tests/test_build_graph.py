#!/usr/bin/env python3
"""test_build_graph.py -- kernels/build_graph.s on the Rust emulator against place_ref.build_graph (CSR arrays identical): random netlists with duplicate inputs,
self references, open inputs, ROM / RAM-out sources, ports, big nets (> 12 pins, skipped), and the real cpu_g1 netlists (old and new map)."""
import os, random, struct, subprocess, sys, tempfile
os.environ.update(ROM_BITS='16', AB='18', RAM_BITS='18')
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools')]
import rvasm, lay, place_ref
EXE = os.path.join(HERE, '..', 'rvemu_rs', 'target', 'release', 'rvemu'); KERN = os.path.join(HERE, '..', 'kernels', 'build_graph.s')
tmp = tempfile.mkdtemp(); stub = tmp + '/stub.s'; open(stub, 'w').write('start:\n    jal ra, build_graph\nhalt:\n    j halt\n')
_, img = rvasm.assemble([stub, os.path.join(HERE, '..', 'kernels', 'memmap.s'), KERN], tmp + '/o'); open(tmp + '/rom.bin', 'wb').write(bytes(img)); print('kernel ROM bytes (with stub):', len(img))
class NL: pass
def run(nl):
    N = len(nl.nodes); ram = bytearray(0x40000); src = []
    for kind, ins in nl.nodes:
        for p in range(2):
            t = ins[p] if p < len(ins) else 'open'; d = place_ref.net_id(t, N); src.append(0xFFFF if d is None else d)
    psrc = [d for d in (place_ref.net_id(t, N) for _, t in nl.ports) if d is not None and d < N]
    struct.pack_into('<%dH' % len(src), ram, 0x26000, *src); struct.pack_into('<%dH' % len(psrc), ram, 0x2A000, *psrc); struct.pack_into('<II', ram, 0x68, N, len(psrc))
    open(tmp + '/ram.bin', 'wb').write(ram)
    rp = subprocess.run([EXE, tmp + '/rom.bin', '--rom-bits', '16', '--ab', '18', '--ram-bytes', str(0x40000), '--load-ram', tmp + '/ram.bin', '--dump-ram', tmp + '/out.bin', '--max', '500000000'], capture_output=True, text=True)
    assert rp.returncode == 0, rp.stderr
    out = open(tmp + '/out.bin', 'rb').read(); nv = struct.unpack_from('<I', out, 0x54)[0]; err = struct.unpack_from('<I', out, 0x70)[0]
    off = struct.unpack_from('<%dH' % (nv + 1), out, 0x1000); E = off[-1]
    nbr = struct.unpack_from('<%dH' % E, out, 0x12000); wt = struct.unpack_from('<%dH' % E, out, 0x1C000)
    adj = place_ref.build_graph(nl); eoff = [0]; en = []; ew = []
    for v in range(len(adj)):
        for u, w in adj[v].items(): en.append(u); ew.append(w)
        eoff.append(len(en))
    n = int(rp.stderr.split('instructions')[1].split()[0])
    return err == 0 and nv == len(adj) and list(off) == eoff and list(nbr) == en and list(wt) == ew, n, E
def rand_nl(rng, N):
    nl = NL(); nodes = []
    for k in range(N):
        ins = []
        for p in range(2):
            r = rng.random()
            if r < .08: ins.append('open')
            elif r < .16: ins.append(f'rom{rng.randrange(8)}')
            elif r < .22: ins.append(f'ramo{rng.randrange(8)}')
            elif r < .27: ins.append(f'n{k}')
            else: ins.append(f'n{rng.randrange(N)}' + rng.choice(['', '', '@1', '@2']))
        if rng.random() < .15: ins[1] = ins[0]
        nodes.append((rng.choice('ND'), ins))
    nl.nodes = nodes; nl.ports = [(f'p{i}', f'n{rng.randrange(N)}' + rng.choice(['', '@1'])) for i in range(rng.randint(0, min(N, 400)))] + [('ramport', 'ramo1')]
    if rng.random() < .5:
        hub = rng.randrange(N)
        for k in range(N):
            if rng.random() < .5: nodes[k][1][0] = f'n{hub}'              # big net (> 12 pins)
    return nl
bad = 0; rr = random.Random(9)
for t in range(25):
    nl = rand_nl(rr, rr.choice([1, 2, 5, 20, 80, 300]))
    ok, n, E = run(nl)
    if not ok: bad += 1; print('MISMATCH random', t, len(nl.nodes))
print('random netlists:', 25 - bad, '/ 25 identical')
for name in ('cpu_g1.nl', 'm18/cpu_g1.nl'):
    nl = lay.read_nl(os.path.join(HERE, '..', 'hd', name)); ok, n, E = run(nl)
    print(f'{name}: N={len(nl.nodes)} directed edges={E}: {"identical" if ok else "MISMATCH"}, {n} instructions'); bad += 0 if ok else 1
print('RESULT', 'PASS' if not bad else 'FAIL'); sys.exit(1 if bad else 0)
