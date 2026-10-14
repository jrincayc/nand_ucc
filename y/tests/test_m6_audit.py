#!/usr/bin/env python3
"""test_m6_audit.py -- audit rules for the data point Y.
 A  the seed library is textbook: no hole, no sharing, the expected gate counts, nothing improved;
 B  the seed ROM image does not contain any improved record (the improver really computes them: no answer is stored);
 C  the improver is general: three modules it was never shown (xnor, and3, maj, in bloated form) are added to the library and used in
    the body; the assembly builder (+ improver) on the behavioural model builds exactly the reference improved child."""
import os, sys, random, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
for d in ('tools', 'isa', 'tests', '.'):
    sys.path.insert(0, os.path.join(HERE, '..', d))
import hd as HDM, hd2asm, ref_flatten as RF, ref_improve as RI, run_builder as RB, isahack as H
import exp_variants as E
from machine_lockstep import MR

ROOT = os.path.join(HERE, '..'); fails = []
SRC = [os.path.join(ROOT, 'src', f) for f in ('macros.asm', 'ram.asm', 'builder.asm', 'improver.asm')]
def check(name, ok, extra=''):
    print(('PASS ' if ok else 'FAIL ') + name + (' ' + extra if extra else ''), flush=True)
    if not ok: fails.append(name)

def image_of(hd, tag):
    out = tempfile.mkdtemp(); data = os.path.join(out, tag + '.asm'); open(data, 'w').write(hd2asm.Enc(hd).encode().text())
    return RB.assemble(SRC + [data], out)

def seed(ra):
    hd = __import__('hd_export').build_hd(ra); return hd[0] if isinstance(hd, tuple) else hd

# ---- A
hd = seed(5); want = {'not': 1, 'and': 2, 'or': 3, 'xor': 9, 'mux': 8, 'ha': 11, 'fa': 25}
got = {m.name: m.n_gates() for m in hd.modules if m.kind == 'comb'}
check('A: seed library has the textbook gate counts', got == want, str(got))
check('A: no hole in the seed', all(g is not None for m in hd.modules for g in m.gates))

# ---- B
img = image_of(hd, 'seed'); child = RI.improve_hd(hd)[0]; n_checked = 0; leaked = []
for m_seed, m_new in zip(hd.modules, child.modules):
    if m_seed.kind != 'comb' or m_seed.key() == m_new.key(): continue
    ent = []; g = 0; n = m_new.n_gates()
    while g < n:
        if m_new.gates[g] is None:
            k = 0
            while g + k < n and m_new.gates[g + k] is None: k += 1
            ent += [2, k, 0]; g += k
        else: ent += [0, *m_new.gates[g]]; g += 1
    pat = bytes(ent)
    n_checked += 1
    if pat in img: leaked.append(m_new.name)
check('B: no improved gate list of a changed module appears in the seed image', not leaked and n_checked >= 4, f'{n_checked} modules checked, leaked {leaked}')

# ---- C
hd2asm.BODY_OFF += 0x50; hd2asm.MOD_AREA += 0x50          # three more records: widen the record area (the r5 image has room)
hd = seed(5); un = E.unlisted(); base_names = [i.name for i in hd.body[-6:]]
for k, (n, g, o) in un.items():
    m = HDM.Module(k, n, len(o)); m.gates = list(g); m.outs = list(o); m.comments = [''] * len(g); hd.modules.append(m)
    hd.body.append(HDM.Inst('u_' + k, k, base_names[:n]))
child = RI.improve_hd(hd)[0]
for k in un: print(f'   {k}: {hd.module(k).n_gates()} -> {sum(1 for x in child.module(k).gates if x is not None)} gates')
g0 = image_of(hd, 'c0'); g1 = image_of(child, 'c1'); ref = RF.commands(RF.flatten(child), g1, 0, RF.STRIDE)
m = MR(256); m.load_rom(0, g0); rng = random.Random(3); m.ram[:] = bytes(rng.getrandbits(8) for _ in range(256)); cpu = H.CPU(m); n = 0
while cpu.step(): n += 1
c = RB.decode_arm(m.armlog)
same = len(c) == len(set(c)) and set(c) == set(ref) and c[-3:] == ref[-3:]
check('C: unlisted modules are improved by the ROM improver and the child equals the reference', same, f'{n:,} instructions, {len(c)} commands, missing {len(set(ref) - set(c))}, extra {len(set(c) - set(ref))}')
check('C: at least one unlisted module got smaller', any(sum(1 for x in child.module(k).gates if x is not None) < hd.module(k).n_gates() for k in un))
print('FAILED: ' + ', '.join(fails) if fails else 'ALL AUDIT TESTS PASSED'); sys.exit(1 if fails else 0)
