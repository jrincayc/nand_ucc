#!/usr/bin/env python3
"""test_improve_asm.py -- kernels/improve.s (imp_record) on the Rust emulator against ref_improve.improve_record, byte for byte:
every library module of hd/m18/cpu_mod.hd, unlisted modules (xnor, and3, maj, ...), random modules with duplicates / dead gates / holes, and the improved records again (fixed point)."""
import os, random, struct, subprocess, sys, tempfile
os.environ.update(ROM_BITS='16', AB='18', RAM_BITS='18')
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools')]
import rvasm, ref_improve as R, hd as H
EXE = os.path.join(HERE, '..', 'rvemu_rs', 'target', 'release', 'rvemu'); K = os.environ.get('IMP_KDIR') or os.path.join(HERE, '..', 'kernels')
tmp = tempfile.mkdtemp(); stub = tmp + '/stub.s'
open(stub, 'w').write('start:\n    li sp, SWTOP\n    jal ra, imp_record\nhalt:\n    j halt\n')
_, img = rvasm.assemble([stub] + [os.path.join(K, f) for f in ('memmap_imp.s', 'improve.s')], tmp + '/o'); open(tmp + '/rom.bin', 'wb').write(bytes(img)); print('improver ROM bytes (with stub):', len(img))
def run(n_in, slots, outs):
    ram = bytearray(0x40000)
    struct.pack_into('<III', ram, 0x200, n_in, 0, len(outs)); struct.pack_into('<I', ram, 0x230, len(slots))
    for s, x in enumerate(slots):
        ram[0x1600 + s] = 0xFF if x is None else x[0]; ram[0x1640 + s] = 0xFF if x is None else x[1]
    for j, o in enumerate(outs): ram[0x1680 + j] = o
    open(tmp + '/ram.bin', 'wb').write(ram)
    rp = subprocess.run([EXE, tmp + '/rom.bin', '--rom-bits', '16', '--ab', '18', '--ram-bytes', str(0x40000), '--load-ram', tmp + '/ram.bin', '--dump-ram', tmp + '/out.bin', '--max', '2000000000'], capture_output=True, text=True)
    assert rp.returncode == 0, rp.stderr
    o = open(tmp + '/out.bin', 'rb').read(); ni = int(rp.stderr.split('instructions')[1].split()[0])
    if struct.unpack_from('<I', o, 0x238)[0] == 0: return None, ni
    S = len(slots); new = [None if o[0x1700 + s] == 0xFF else (o[0x1700 + s], o[0x1740 + s]) for s in range(S)]
    return (new, [o[0x1780 + j] for j in range(len(outs))]), ni
def check(name, n_in, slots, outs, stats):
    ref = R.improve_record(n_in, slots, outs); got, ni = run(n_in, slots, outs)
    ok = ref == got; stats[0] += ni; stats[1] += 1
    if not ok: stats[2] += 1; print('MISMATCH', name, n_in, slots, outs, '\n  ref', ref, '\n  got', got)
    return ref
def rand_module(rr):
    n_in = rr.randint(1, 3); no = rr.randint(1, 2); S = rr.randint(no, 14)
    slots = []
    for s in range(S):
        if rr.random() < 0.12: slots.append(None); continue
        cand = list(range(n_in)) + [n_in + t for t in range(s) if slots[t] is not None]
        slots.append((rr.choice(cand), rr.choice(cand)))
    live = [n_in + s for s, x in enumerate(slots) if x is not None]
    if len(live) < no: return None
    outs = rr.sample(live, no) if rr.random() < 0.9 else [live[-1]] * no
    return n_in, slots, outs

def sop_module(rr):
    """random truth-table function(s) as a naive sum of products built from NANDs (shared literals are NOT shared: duplicates and cones for the improver)"""
    n_in = rr.randint(2, 3); no = rr.randint(1, 2); g = []
    def nand(a, b): g.append((a, b)); return n_in + len(g) - 1
    def inv(a): return nand(a, a)
    def and_(a, b): return inv(nand(a, b))
    def or_(a, b): return nand(inv(a), inv(b))
    outs = []
    for _ in range(no):
        tt = [rr.random() < 0.5 for _ in range(1 << n_in)]
        if not any(tt): tt[rr.randrange(len(tt))] = True
        acc = None
        for m, bit in enumerate(tt):
            if not bit: continue
            lits = [v if (m >> v) & 1 else inv(v) for v in range(n_in)]
            p = lits[0]
            for l in lits[1:]: p = and_(p, l)
            acc = p if acc is None else or_(acc, p)
        outs.append(acc)
    if len(set(outs)) != len(outs) or any(o < n_in for o in outs) or n_in + len(g) > 60: return None
    return n_in, list(g), outs
stats = [0, 0, 0]
hd = H.read(open(os.path.join(HERE, '..', 'hd', 'm18', 'cpu_mod.hd')).read())
for m in hd.modules:
    if not R.improvable(m): continue
    r = check(m.name, m.n_in, m.gates, m.outs, stats)
    print(f'{m.name:5s} {m.n_gates():3d} slots ->', 'unchanged' if r is None else f'{sum(1 for x in r[0] if x is not None)} NAND', f'({stats[0]} instr so far)')
    if r is not None: check(m.name + ' (again)', m.n_in, r[0], r[1], stats)
def lib(name, n_in, gates, outs): return (name, n_in, gates, outs)
extra = [('xnor', 2, [(0, 1), (0, 2), (1, 2), (3, 4), (5, 5)], [6]),
         ('and3', 3, [(0, 1), (3, 3), (2, 4), (5, 5)], [6]),
         ('maj', 3, [(0, 1), (0, 2), (1, 2), (3, 4), (5, 5), (6, 7), (8, 8), (2, 2), (9, 9)], [8]),
         ('dup', 2, [(0, 1), (1, 0), (2, 3), (4, 4)], [5]),
         ('two', 2, [(0, 1), (0, 0), (1, 1), (3, 4), (2, 2), (6, 6)], [5, 7])]
for name, n_in, gates, outs in extra:
    r = check(name, n_in, gates, outs, stats)
    print(f'{name:5s} {len(gates):3d} slots ->', 'unchanged' if r is None else f'{sum(1 for x in r[0] if x is not None)} NAND')
# modules found by running a mutated reference (fan-out test ignored) against the real one: they separate the two
DISC = [[2, [[0, 0], [1, 1], [2, 3], [4, 4], [1, 1], [0, 6], [7, 7], [5, 5], [8, 8], [9, 10], [0, 0], [12, 1], [13, 13], [11, 11], [14, 14], [15, 16], [0, 1], [18, 18], [17, 17], [19, 19], [20, 21], [0, 1], [23, 23]], [22, 24]], [2, [[0, 0], None, [2, 1], [2, 4], [5, 5], [6, 0], None, [0, 5], [4, 2], [2, 1], [6, 5], [10, 12], [1, 5]], [13, 6]], [2, [[1, 1], [0, 2], [0, 1], [2, 1], [5, 0], [2, 2], [5, 2], [2, 8], [2, 1], [7, 1], [3, 10], [7, 1], [3, 9]], [12, 13]]]
for i, (n_in, sl, outs) in enumerate(DISC):
    sl = [tuple(x) if x is not None else None for x in sl]; check(f'disc{i}', n_in, sl, outs, stats)
rr = random.Random(5); nrand = 0
for t in range(int(os.environ.get('IMP_NRAND', '300'))):
    m = rand_module(rr)
    if m is None: continue
    nrand += 1; check(f'rand{t}', *m, stats)
nsop = 0
for t in range(int(os.environ.get('IMP_NSOP', '40'))):
    m = sop_module(rr)
    if m is None: continue
    nsop += 1; r = check(f'sop{t}', *m, stats)
print(f'{nsop} sum-of-products modules done')
print(f'{stats[1]} cases ({nrand} random), {stats[2]} mismatches, {stats[0]} instructions in total, {stats[0] // stats[1]} per case')
print('RESULT', 'PASS' if stats[2] == 0 else 'FAIL'); sys.exit(1 if stats[2] else 0)
