"""verify_y_world.py -- check a saved RNDW state: generation g (arm origin (0, 140 g)) must equal the reference commands exactly.
usage: verify_y_world.py STATE HDFILE IMAGE_BIN GEN..."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
for d in ('tools', 'isa', '.'):
    sys.path.insert(0, os.path.join(HERE, '..', d))
import hd as HDM, ref_flatten as RF


def load(path):
    parts, wires, roms, faults, tick = {}, [], {}, None, None
    for l in open(path):
        t = l.split()
        if not t: continue
        if t[0] == 'part': parts[int(t[1])] = (int(t[2]), int(t[3]), int(t[4]))
        elif t[0] == 'wire': wires.append(tuple(int(x) for x in t[1:5]))
        elif t[0] == 'rom': roms.setdefault(int(t[1]), {})[int(t[2])] = int(t[3])
        elif t[0] == 'faults': faults = int(t[1])
        elif t[0] == 'tick': tick = int(t[1])
    return parts, wires, roms, faults, tick


def check(state, gens):
    """gens: list of (generation number g, hd file, image file): generation g (arm origin (0, 140 g)) must equal the reference commands."""
    parts, wires, roms, faults, tick = load(state)
    print(f'world: tick {tick}, faults {faults}, {len(parts)} parts, {len(wires)} wires, {len(roms)} ROMs')
    wset = set(wires); pset = set(parts.values()); bypos = {v: p for p, v in parts.items()}
    kc = {'nand': 0, 'dff': 1, 'rom': 2, 'arm': 3}
    ok = faults == 0
    for g, hdfile, imgfile in gens:
        f = RF.flatten(HDM.read(open(hdfile).read())); image = open(imgfile, 'rb').read()
        oy = RF.STRIDE * g
        ref = RF.commands(f, image, 0, oy)
        ep = set((kc[c[1]], c[2], c[3]) for c in ref if c[0] == 'place')
        ew = set(c[1:5] for c in ref if c[0] == 'wire')
        er = {c[3]: c[4] for c in ref if c[0] == 'rom'}
        rid = bypos.get((2, 0, oy + RF.ARM_H)); got = roms.get(rid, {})
        print(f'gen {g}: parts {len(ep)} expected, missing {len(ep - pset)}; wires {len(ew)} expected, missing {len(ew - wset)}; '
              f'ROM {len(got)} bytes, identical to the image: {got == er}', flush=True)
        ok &= not (ep - pset) and ew <= wset and got == er
    return ok


if __name__ == '__main__':
    # usage: verify_y_world.py STATE G:HDFILE:IMAGE [G:HDFILE:IMAGE ...]
    gens = [(int(a.split(':')[0]), a.split(':')[1], a.split(':')[2]) for a in sys.argv[2:]]
    print('ALL OK' if check(sys.argv[1], gens) else 'MISMATCH')
