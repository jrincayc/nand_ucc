import random, sys
import isaacc as I, lockstep, common
from nl_acc8 import build_acc8
from fastsim import Fast
from test_acc8 import ref_state, net_state
Fast.boundary = lambda self: self.st('st') & 1

def gen(rng, n):
    names = [s for s in I.SPEC]
    prog = []                       # (name, kind, arg-or-None)
    for _ in range(n):
        nm, k, code = rng.choice(names)
        prog.append([nm, k, code])
    # addresses
    addr, a = [], common.ROM_BASE
    for nm, k, code in prog:
        addr.append(a); a += I.SZ[k]
    out = bytearray()
    for idx, (nm, k, code) in enumerate(prog):
        out.append(code)
        if k in ('z', 'i'): out.append(rng.getrandbits(8))
        elif k == 'r':
            nxt = addr[idx] + 2
            t = addr[min(len(prog) - 1, idx + 1 + rng.randrange(4))]
            if t >> 8 != nxt >> 8: t = addr[idx + 1]
            out.append(t & 255)
        elif k == 'a':
            if nm == 'JMP':
                t = addr[min(len(prog) - 1, idx + 1 + rng.randrange(4))]
                out += bytes([t & 255, t >> 8])
            else:
                v = rng.getrandbits(13); out += bytes([v & 255, v >> 8])
    # halt at the end
    h = common.ROM_BASE + len(out)
    out += bytes([0x83, h & 255, h >> 8])
    return bytes(out)

c = build_acc8(2)
if __name__ == '__main__':
    tot = 0
    for seed in range(int(sys.argv[1]) if len(sys.argv) > 1 else 20):
        rng = random.Random(seed)
        img = gen(rng, 600)
        try:
            i, t = lockstep.run_image(I, c, ref_state, net_state, img, seed)
        except AssertionError as e:
            print('seed', seed, 'FAIL', e); raise
        tot += i
    print('fuzz ok, instructions compared:', tot)
