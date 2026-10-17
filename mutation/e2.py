"""E2 (single-bit mutation) and E6 (dead cells).   usage: e2.py X|Y bits N|all   |   e2.py X|Y dead"""
import sys, json, random, time, multiprocessing as mp
from collections import Counter
import audit, emu
G = audit.G

def run_full(img):
    r = emu.run(G['ab'], G['ramn'], bytes(img).rstrip(b'\0') or b'\0', max_instr=G['maxi'], ref=G['ref'], rom_origin=G['origin'])
    img = bytes(img)
    if r.name == 'halt':
        if r.child == img: return 'FIX', None, r.instr
        if r.child == G['refimg']: return 'TOREF', None, r.instr
        return 'SAMEHW', r.child, r.instr
    if r.name in ('diverged', 'short', 'badrom'): return 'HWDIFF', None, (r.div, r.name)
    return 'CRASH', None, r.name

def chain(img, depth=8):
    """follow children while the build stays hardware-identical; returns list of classes"""
    seq = []; seen = {bytes(img)}
    for _ in range(depth):
        c, child, info = run_full(img); seq.append(c)
        if c != 'SAMEHW': return seq
        if child in seen: seq.append('LOOP'); return seq
        seen.add(child); img = child
    seq.append('DEPTH'); return seq

def mut(arg):
    p, b = arg
    m = bytearray(G['img']); m[p] ^= 1 << b
    seq = chain(m)
    return p, b, seq

def pool_run(items, w, procs=2):
    out = []; t = time.time()
    with mp.Pool(procs, initializer=audit.init, initargs=(w,)) as pool:
        for k, x in enumerate(pool.imap_unordered(mut, items, chunksize=16)):
            out.append(x)
            if (k + 1) % 2000 == 0: print(f'  {k+1}/{len(items)} {time.time()-t:.0f}s', flush=True)
    return out

if __name__ == '__main__':
    w, mode = sys.argv[1], sys.argv[2]
    audit.init(w); n = G['n']; img = G['img']
    cls = {}
    for p in range(n): cls[p] = 'F' if G['fetched'][p] else ('D' if G['dread'][p] else 'U')
    if mode == 'bits':
        nb = sys.argv[3]; rng = random.Random(2026)
        allbits = [(p, b) for p in range(n) for b in range(8)]
        items = allbits if nb == 'all' else rng.sample(allbits, int(nb))
        out = pool_run(items, w)
        json.dump(out, open(f'e2_{w}_{nb}.json', 'w'))
        tab = Counter(); fin = Counter()
        for p, b, seq in out:
            tab[(cls[p], seq[0])] += 1
            fin[tuple(seq)] += 1
        print(f'{w}: {len(out)} single-bit mutants')
        for k, v in sorted(tab.items()): print('  first-step', k, v)
        print('  full chains (class sequences):')
        for k, v in sorted(fin.items(), key=lambda kv: -kv[1])[:25]: print('   ', k, v)
    if mode == 'dead':
        zero = bytearray(n)
        print('all-zero ROM:', run_full(zero))
        print('halt-only image:', run_full(bytes([0x00, 0x00, 0x00, 0x00]) if False else bytes(2*0)))
        # image whose first instruction is the halt idiom: '@L ; 0;JMP' at L-2 style (jump to self-minus-2)
        base = G['ab']; rb = 1 << (G['ab'] - 1)
        halt = bytearray(); 
        # word0: A-instruction @ROM_BASE+0 ; word1: 0;JMP  -> jump target = A = address of instruction before the jump = halts
        a = rb; halt += bytes([a & 255, a >> 8]); jmp = 7 << 13 | 0b101010 << 6 | 7; halt += bytes([jmp & 255, jmp >> 8])
        print('halt-only image (emits nothing):', run_full(halt))
        print('reference image:', run_full(img))
