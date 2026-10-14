#!/usr/bin/env python3
"""test_m3.py -- M3 tests: HD round trip, audits A/B, improver fixed point, flatten+lockstep, build-command geometry."""
import os, sys, random
HERE = os.path.dirname(os.path.abspath(__file__))
for d in ('tools', 'isa', '.'):
    sys.path.insert(0, os.path.join(HERE, '..', d))
sys.path.insert(0, HERE)
import hd as H, hd_export as X, ref_flatten as RF, ref_improve as R, machine_lockstep as ML
import cutrw, cutv2

import isahack as IH, common
def gen(rng, n):   # valid random Hack-vN-AB programs (same generator as isa/fuzz_hack.py)
    COMPS = list(IH.COMP.values()); words = []
    while len(words) < n:
        r = rng.random()
        if r < 0.25: words.append(rng.getrandbits(15))
        elif r < 0.33: words.append(6 << 13)
        elif r < 0.43:
            words.append(common.ROM_BASE + 2 * (len(words) + 3))
            words.append(7 << 13 | rng.getrandbits(1) << 12 | rng.choice(COMPS) << 6 | rng.getrandbits(3) << 3 | rng.randrange(1, 8))
            words.append(7 << 13 | rng.getrandbits(1) << 12 | rng.choice(COMPS) << 6 | rng.getrandbits(3) << 3)
        else: words.append(7 << 13 | rng.getrandbits(1) << 12 | rng.choice(COMPS) << 6 | rng.getrandbits(3) << 3)
    words += [common.ROM_BASE + 2 * len(words), 7 << 13 | 0b101010 << 6 | 7]
    return b''.join(bytes([w & 255, w >> 8]) for w in words)

fails = []
def check(name, ok, extra=''):
    print(('PASS ' if ok else 'FAIL ') + name + (' ' + extra if extra else ''))
    if not ok: fails.append(name)

def tt_outs(n_in, gates, outs):
    t = R.tables(n_in, gates); return [t[o] for o in outs]

hd0 = H.read(open(os.path.join(HERE, '..', 'hd', 'core.hd')).read())
check('hd round trip', H.write(H.read(H.write(hd0))) == H.write(hd0))
check('hd file equals fresh export', H.write(X.build_hd(5)) == H.write(hd0)) if not isinstance(X.build_hd(5), tuple) else check('hd file equals fresh export', H.write(X.build_hd(5)[0]) == H.write(hd0))

# audit A: textbook gate counts
want = {'not': 1, 'and': 2, 'or': 3, 'xor': 9, 'mux': 8, 'ha': 11, 'fa': 25}
got = {m.name: m.n_gates() for m in hd0.modules if m.name in want}
check('audit A textbook counts', got == want, str(got))

# improver on the library
hd1, rep = R.improve_hd(hd0)
r = {n: (a, b) for n, a, b, _ in rep}
check('improved library', {k: v[1] for k, v in r.items() if k in want} == {'not': 1, 'and': 2, 'or': 3, 'xor': 4, 'mux': 4, 'ha': 5, 'fa': 9}, str(r))

# audit B: unlisted modules
def build(n, f):
    b = cutrw.B(n); o = f(b, *range(n)); o = list(o) if isinstance(o, tuple) else [o]; return n, b.g, o
unl = {'xnor': build(2, lambda b, a, c: b.not_(b.xor(a, c))), 'and3': build(3, lambda b, a, c, d: b.and_(b.and_(a, c), d)),
       'maj': build(3, lambda b, a, c, d: b.or_(b.or_(b.and_(a, c), b.and_(a, d)), b.and_(c, d)))}
for k, (n, g, o) in unl.items():
    g2, o2 = R.improve(n, g, o)
    check(f'audit B {k}', tt_outs(n, g, o) == tt_outs(n, g2, o2), f'{len(g)} -> {len(g2)}')
    r2 = R.improve(n, g2, o2)
    check(f'fixed point {k}', r2 == (g2, o2))
check('audit B xnor 10->5', len(R.improve(*unl['xnor'])[0]) == 5)
check('audit B and3 stays 4', len(R.improve(*unl['and3'])[0]) == 4)

# random modules: function preserved, fixed point, equal to the cutv2 prototype count
rnd = random.Random(11); nbad = ndiff = ngt = 0; tot = 0
for i in range(60):
    n = rnd.choice([2, 3]); N = 1 << n; t = rnd.getrandbits(N)
    if t in (0, (1 << N) - 1): continue
    b = cutrw.B(n); terms = []
    for rr in range(N):
        if (t >> rr) & 1:
            lits = [(v if (rr >> v) & 1 else b.not_(v)) for v in range(n)]; x = lits[0]
            for l in lits[1:]: x = b.and_(x, l)
            terms.append(x)
    o = terms[0]
    for x in terms[1:]: o = b.or_(o, x)
    g2, o2 = R.improve(n, b.g, [o]); tot += 1
    if tt_outs(n, b.g, [o]) != tt_outs(n, g2, o2): nbad += 1
    if R.improve(n, g2, o2) != (g2, o2): nbad += 1
    cutrw.cuts = lambda n_, g_, r_, maxleaf=3: cutv2.cuts_chain(n_, g_, r_, maxleaf)
    pr = cutrw.improve((n, b.g, [o]))[0]
    ndiff += len(g2) - len(pr[1]); ngt += 1
check('random modules function+fixed point', nbad == 0, f'{tot} modules')
check('random modules: stable-order improver at most 0.2 gate/module worse than the DFS prototype', ndiff <= 0.2 * tot, f'{ndiff:+d} gates over {tot} modules')

# fixed point of the improved HD library
hd2, rep2 = R.improve_hd(hd1)
check('library fixed point', [(m.gates, m.outs) for m in hd2.modules if m.kind == 'comb'] == [(m.gates, m.outs) for m in hd1.modules if m.kind == 'comb'])

# flatten + lockstep
f0, f1 = RF.flatten(hd0), RF.flatten(hd1)
print('seed', RF.counts(f0), 'improved', RF.counts(f1))
c1 = RF.to_compiled(f1)
demo = os.path.join(HERE, '..', 'examples', 'demo.asm')
os.system(f'python3 {HERE}/../tools/asm.py -o {HERE}/_asm {demo} > /dev/null')
img = open(f'{HERE}/_asm/rom.bin', 'rb').read()
check('lockstep demo (improved)', ML.run_flat(c1, img, f1.W) == (131, 336))
rr = random.Random(3); ok = True
for k in range(25):
    im = gen(rr, 40); ri = bytes(rr.getrandbits(8) for _ in range(f1.W))
    try: ML.run_flat(c1, im, f1.W, ram_init=ri, max_instr=400)
    except AssertionError as e: ok = False; print('  ', k, e)
check('lockstep random images (improved)', ok)


# hd2asm: encode -> assemble -> decode must equal the reference flattener (seed and improved)
import hd2asm
def roundtrip(hd, tag):
    f = RF.flatten(hd); e = hd2asm.Enc(hd).encode(); p = f'{HERE}/_asm/{tag}.asm'
    open(p, 'w').write(e.text()); os.system(f'python3 {HERE}/../tools/asm.py -o {HERE}/_asm/{tag} {p} > /dev/null')
    im = open(f'{HERE}/_asm/{tag}/rom.bin', 'rb').read()
    d = hd2asm.decode(im, hd.params['ab'])
    same = (d.kind == f.kind and d.ins == f.ins and d.tkind == f.tkind and d.tins == f.tins and d.ports == [s for _, s in f.ports] and d.W == f.W and d.n_core == f.n_core)
    tc = os.system(f'python3 {HERE}/../tools/trace_check.py {HERE}/_asm/{tag} {p} > /dev/null') == 0
    check(f'trace_check on data asm ({tag})', tc)
    return same, len(im), e
for tag, h in (('seed', hd0), ('improved', hd1)):
    same, n, e = roundtrip(h, tag); check(f'hd2asm round trip ({tag})', same, f'{n} ROM bytes')
# every emitted line has a comment
check('data asm: every line commented', all('//' in l for l in e.text().split(chr(10)) if l.strip()))

# build-command geometry
cm = RF.commands(f1, img); cells = {}; placed = {}
for c in cm:
    if c[0] != 'place': continue
    _, kind, x, y = c; w, h = {'nand': (2, 2), 'dff': (2, 2), 'rom': (2, max(f1.rom_abits, 8)), 'arm': (2, 9)}[kind]
    for dx in range(w):
        for dy in range(h):
            if (x + dx, y + dy) in cells: fails.append('overlap'); print('overlap at', x + dx, y + dy)
            cells[(x + dx, y + dy)] = kind
    placed[(x, y)] = kind
check('no overlaps', 'overlap' not in fails)
driven = set(); bad = 0
for c in cm:
    if c[0] != 'wire': continue
    _, x1, y1, x2, y2 = c
    src = [(x1 - 1, y1)]; dst = (x2, y2)
    if dst in driven: bad += 1
    driven.add(dst)
    if cells.get((x1, y1)) is None or cells.get((x2, y2)) is None: bad += 1
check('wires: sinks driven once, endpoints on parts', bad == 0, f'{len(driven)} wires')
print('FAILED: ' + ', '.join(fails) if fails else 'ALL M3 TESTS PASSED'); sys.exit(1 if fails else 0)
