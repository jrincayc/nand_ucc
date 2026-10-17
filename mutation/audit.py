"""E1: per-byte perturbation audit.  usage: audit.py X|Y stage1|stage2 [nvalues]"""
import sys, os, json, time, random, multiprocessing as mp, emu, load

CFG = {'X': dict(ab=13, ramn=32), 'Y': dict(ab=15, ramn=256)}
def image(w): return load.X_image() if w == 'X' else load.Y_image(2)

G = {}
def init(w):
    c = CFG[w]; img = image(w); n = 1 << (c['ab'] - 1)
    r = emu.run(c['ab'], c['ramn'], img, max_instr=200_000_000, trace=True, record=True, outcap=3_000_000)
    G.update(w=w, ab=c['ab'], ramn=c['ramn'], img=bytearray(img) + bytearray(n - len(img)), n=n, ref=emu.RefObj(r.cmds),
             origin=r.origin, refimg=bytes(bytearray(img) + bytearray(n - len(img))), maxi=2 * r.instr + 1000, fetched=r.fetched, dread=r.dread, refinstr=r.instr)

def classify(img):
    r = emu.run(G['ab'], G['ramn'], bytes(img).rstrip(b'\0') or b'\0', max_instr=G['maxi'], ref=G['ref'], rom_origin=G['origin'])
    if r.name == 'halt':
        if r.child == bytes(img): return 'FIX'
        return 'TOREF' if r.child == G['refimg'] else 'SAMEHW'
    if r.name in ('diverged', 'short', 'badrom'): return 'HWDIFF'
    return 'CRASH'

def test(arg):
    p, vals = arg
    res = []
    for v in vals:
        m = bytearray(G['img']); m[p] = v
        res.append(classify(m))
    return p, res

def pooled(items, w, procs=2):
    with mp.Pool(procs, initializer=init, initargs=(w,)) as pool:
        t = time.time(); out = []
        for k, x in enumerate(pool.imap_unordered(test, items, chunksize=8)):
            out.append(x)
            if (k + 1) % 500 == 0: print(f'  {k+1}/{len(items)} {time.time()-t:.0f}s', flush=True)
    return out

if __name__ == '__main__':
    w, stage = sys.argv[1], sys.argv[2]
    init(w); n = G['n']; img = G['img']
    print(w, 'reference instr', G['refinstr'], 'commands', G['ref'].n, 'origin', G['origin'])
    ref_ok = classify(img); print('reference image classifies as', ref_ok)
    cls = {}
    for p in range(n):
        f = G['fetched'][p]
        cls[p] = 'F' if f else ('D' if G['dread'][p] else 'U')
    from collections import Counter
    print('byte classes (whole ROM):', Counter(cls.values()))
    if stage == 'stage2':
        st1 = json.load(open(f'audit_{w}_stage1.json'))['res']
        cand = sorted(int(p) for p, r in st1.items() if all(x in ('FIX', 'TOREF') for x in r))
        print('candidate free bytes from stage 1:', len(cand))
        nv = int(sys.argv[3]); rng = random.Random(7)
        items = []
        for p in cand:
            vals = [v for v in range(256) if v != img[p]] if nv >= 255 else rng.sample([v for v in range(256) if v != img[p]], nv)
            items.append((p, vals))
        out = pooled(items, w)
        good = []
        for p, r in out:
            c = Counter(r)
            if set(c) <= {'FIX', 'TOREF'}: good.append(p)
            else: print('  byte', p, 'orig', img[p], 'not free:', dict(c))
        good.sort(); print('bytes free for all tested values:', len(good), 'of', len(cand))
        json.dump(good, open(f'audit_{w}_free.json', 'w'))
    if stage == 'joint':
        good = json.load(open(f'audit_{w}_free.json')); rng = random.Random(11); trials = int(sys.argv[3]); bad = 0; cc = Counter()
        for t in range(trials):
            m = bytearray(img)
            for p in good: m[p] = rng.randrange(256)
            r = classify(m); cc[r] += 1
        print('joint random assignments of all', len(good), 'free bytes:', dict(cc))
    if stage == 'stage1':
        items = [(p, [img[p] ^ 0xFF, img[p] ^ 0x24]) for p in range(n) if cls[p] != 'F']
        out = pooled(items, w)
        res = {p: r for p, r in out}
        json.dump({'cls': cls, 'res': res}, open(f'audit_{w}_stage1.json', 'w'))
        c = Counter()
        for p, r in res.items(): c[(cls[p], tuple(sorted(set(r))))] += 1
        for k, v in sorted(c.items(), key=lambda kv: -kv[1]): print(k, v)
