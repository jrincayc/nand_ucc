"""Check a saved RNDW world: generation g (arm origin (0, 22*g)) must equal the reference machine structure."""
import sys
import engine, machine_row as MR, builder as B

def load(path):
    parts, wires, roms, arms, faults, tick = {}, [], {}, [], None, None
    for l in open(path):
        t = l.split()
        if not t: continue
        if t[0] == 'part': parts[int(t[1])] = (int(t[2]), int(t[3]), int(t[4]))
        elif t[0] == 'wire': wires.append(tuple(int(x) for x in t[1:5]))
        elif t[0] == 'rom': roms.setdefault(int(t[1]), {})[int(t[2])] = int(t[3])
        elif t[0] == 'faults': faults = int(t[1])
        elif t[0] == 'tick': tick = int(t[1])
    return parts, wires, roms, faults, tick

def expected(plan, ox, oy):
    R, outs = plan.R, plan.outs
    n = len(R.kind); y0 = oy + 9
    xs = lambda i: ox + 6 + 2 * i
    code = {'nand': 0, 'dff': 1}
    parts = {i: (code[R.kind[i]], xs(i), y0) for i in range(n)}
    parts['tie'] = (0, xs(n), y0); parts['rom'] = (2, ox, y0); parts['arm'] = (3, ox, oy)
    def src(r):
        if r[0] == 'n': return (r[1], 0)
        if r[0] == 'rom': return ('rom', r[1])
        return ('tie', 0)
    w = set()
    for i in range(n):
        if R.kind[i] == 'dff': w.add((src(R.a[i]), (i, 0)))
        else:
            for pin, r in ((0, R.a[i]), (1, R.b[i])):
                if r is not None: w.add((src(r), (i, pin)))
    for i, r in enumerate(outs['rom_addr']): w.add((src(r), ('rom', i)))
    for i, r in enumerate(outs['arm_addr']): w.add((src(r), ('arm', i)))
    for j, r in enumerate(outs['wdata']): w.add((src(r), ('arm', 5 + j)))
    w.add((src(outs['arm_en']), ('arm', 4)))
    return parts, w

def check(path, plan, gens, rom_image=None):
    parts, wires, roms, faults, tick = load(path)
    print(f'world: tick {tick}, faults {faults}, {len(parts)} parts, {len(wires)} wires')
    ok = faults == 0
    wset = set(wires)
    bypos = {v: p for p, v in parts.items()}
    for g in gens:
        ox, oy = 0, MR.STRIDE * g
        ref = MR.commands(plan.R, plan.outs, rom_image or b'', ox, oy)
        exp = set(t[1:5] for t in ref if t[0] == 'wire')
        ep = set((0 if t[1] == 'nand' else 1 if t[1] == 'dff' else 2 if t[1] == 'rom' else 3, t[2], t[3]) for t in ref if t[0] == 'place')
        pset = set(parts.values())
        got = exp & wset
        # wires belonging to this generation present in the world (by region of the destination)
        extra = set()
        print(f'gen {g}: parts missing {len(ep - pset)}, wires expected {len(exp)} present {len(got)} missing {len(exp - wset)}')
        ok &= not (ep - pset) and exp <= wset and not extra
        rid = bypos.get((2, ox, oy + 9))
        r = roms.get(rid, {})
        if rom_image is not None:
            want = {a: v for a, v in enumerate(rom_image) if v}
            print(f'   ROM ({len(r)} bytes) identical to the reference image: {r == want}')
            ok &= r == want
    return ok

if __name__ == '__main__':
    path, ab = sys.argv[1], int(sys.argv[2])
    gens = [int(x) for x in sys.argv[3:]] or [1, 2]
    a, plan, V, sl = engine.make_program(ab)
    image = a.assemble()
    print('ALL OK' if check(path, plan, gens, image) else 'MISMATCH')
