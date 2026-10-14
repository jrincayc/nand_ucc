"""collect.py -- measurements for the M7 write-up (ROM map, RAM usage by phase, instruction counts per routine). Writes writeup/data/*.json"""
import os, sys, json, random, bisect, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
for d in ('tools', 'isa', 'tests', '.'): sys.path.insert(0, os.path.join(ROOT, d))
import hd as HDM, hd2asm, ref_improve as RI, run_builder as RB, isahack as H, common
from machine_lockstep import MR
SRC = [os.path.join(ROOT, 'src', f) for f in ('macros.asm', 'ram.asm', 'builder.asm', 'improver.asm')]
OUT = os.path.join(HERE, 'data')

def build(hd, tag):
    o = tempfile.mkdtemp(); d = os.path.join(o, 'd.asm'); open(d, 'w').write(hd2asm.Enc(hd).encode().text())
    img = RB.assemble(SRC + [d], o)
    syms = {}
    for l in open(os.path.join(o, 'symbols.txt')):
        if ' = ' in l: k, v = l.split(' = ', 1); syms[k.strip()] = int(v.split()[0], 0)
    return img, syms

hd0 = HDM.read(open(os.path.join(ROOT, 'hd', 'core_r8.hd')).read()); hd1 = RI.improve_hd(hd0)[0]
res = {}
for tag, hd in (('seed', hd0), ('child', hd1)):
    img, syms = build(hd, tag)
    # ---- ROM map
    rb = common.ROM_BASE
    code = sorted((v, k) for k, v in syms.items() if rb <= v < rb + 0x4000 and not k.startswith(('ret', 'inc')))
    rom = dict(image=len(img), builder_start=0, improver_start=syms['improve_type'] - rb if False else None)
    # routine boundaries: all labels in code, with their size = distance to the next label
    labs = [(v, k) for v, k in code]
    # instruction counting by routine over a full run
    m = MR(256); m.load_rom(0, img); rng = random.Random(7); m.ram[:] = bytes(rng.getrandbits(8) for _ in range(256))
    cpu = H.CPU(m); addrs = [v for v, _ in labs]; names = [k for _, k in labs]; cnt = {}; n = 0
    wr_by = {'builder': set(), 'improver': set()}; ow = m.wr; cur = ['builder']
    imp_lo, imp_hi = syms['irdb'] if 'irdb' in syms else None, None
    first_imp = min(v for k, v in syms.items() if k in ('irdb', 'bt', 'bs', 'keycmp', 'ins', 'load', 'compact', 'nextcut', 'cone', 'search', 'rewrite', 'partition', 'layout', 'improve_type'))
    imp_end = syms['vtab']
    def wr(a, v):
        if a < 256: wr_by['improver' if first_imp <= cpu.pc < imp_end else 'builder'].add(a)
        ow(a, v)
    m.wr = wr
    while True:
        i = bisect.bisect_right(addrs, cpu.pc) - 1; nm = names[i] if i >= 0 else '?'; cnt[nm] = cnt.get(nm, 0) + 1
        if not cpu.step(): break
        n += 1
    imp_instr = sum(c for k, c in cnt.items() if first_imp <= syms[k] < imp_end)
    res[tag] = dict(image=len(img), instr=n, improver_instr=imp_instr, builder_instr=n - imp_instr,
                    first_imp=first_imp - rb, imp_end=imp_end - rb, syms={k: v - rb for k, v in syms.items() if rb <= v < rb + 0x4000 and not k.startswith(('ret', 'inc', 'RA_'))},
                    by_routine=cnt,
                    ram_builder=sorted(wr_by['builder']), ram_improver=sorted(wr_by['improver']))
    print(tag, n, imp_instr, flush=True)
json.dump(res, open(os.path.join(OUT, 'measure.json'), 'w'))
