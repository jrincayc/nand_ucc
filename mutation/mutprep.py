import json, random, os, sys, collections
import audit, emu
audit.init('X'); G = audit.G
OX, OY = 0, 22
def prep(name, img, outdir):
    os.makedirs(outdir, exist_ok=True)
    r = emu.run(G['ab'], G['ramn'], bytes(img).rstrip(b'\0') or b'\0', max_instr=4 * G['refinstr'], record=True, outcap=3_000_000, rom_origin=G['origin'])
    info = dict(name=name, status=r.name, instr=r.instr, ncmd=r.nnon, nrom=r.nrom)
    if r.name not in ('halt', 'timeout'):
        return info, None
    with open(f'{outdir}/{name}.cmds', 'w') as f:
        for c in r.cmds:
            cmd, kind, angle, ax, ay, bx, by = c
            if cmd == 1: f.write(f'P {kind} {OX+ax} {OY+ay} {angle}\n')
            elif cmd == 2: f.write(f'W {OX+ax} {OY+ay} {OX+bx} {OY+by}\n')
        for c in r.cmds:
            f.write('X ' + ' '.join(map(str, list(c) + [0])) + '\n')
    child = (r.child or b'')
    open(f'{outdir}/{name}.rom', 'wb').write(child.ljust(4096, b'\0')[:4096])
    return info, r
if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'ref':
        info, r = prep('ref', G['img'], 'mut'); print(info)
    else:
        n = int(sys.argv[2]); out = json.load(open('e2_X_all.json'))
        cls = lambda p: 'F' if G['fetched'][p] else 'D'
        hw = [(p, b) for p, b, seq in out if seq[0] == 'HWDIFF']
        rng = random.Random(7); sample = rng.sample(hw, n)
        res = []
        for p, b in sample:
            m = bytearray(G['img']); m[p] ^= 1 << b
            info, r = prep(f'm_{p}_{b}', m, 'mut'); info.update(p=p, b=b, cls=cls(p)); res.append(info)
        json.dump(res, open('mut_sample.json', 'w'))
        print(collections.Counter((i['status'], i['cls']) for i in res))
