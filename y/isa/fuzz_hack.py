import random, sys
import isahack as H, lockstep, common
from nl_hackvn import build_hackvn
from fastsim import Fast
from test_hackvn import ref_state, net_state
Fast.boundary = lambda self: self.st('st') & 1
COMPS = list(H.COMP.values())

def gen(rng, n):
    words = []
    while len(words) < n:
        r = rng.random()
        if r < 0.25:
            words.append(rng.getrandbits(15))                               # A-instruction
        elif r < 0.33:
            words.append(6 << 13)                                           # AP
        elif r < 0.43:
            # conditional jump over exactly one following instruction: @target ; comp;Jxxx ; <skipped>
            tgt = common.ROM_BASE + 2 * (len(words) + 3)
            words.append(tgt)
            words.append(7 << 13 | rng.getrandbits(1) << 12 | rng.choice(COMPS) << 6 | rng.getrandbits(3) << 3 | rng.randrange(1, 8))
            words.append(7 << 13 | rng.getrandbits(1) << 12 | rng.choice(COMPS) << 6 | rng.getrandbits(3) << 3)
        else:
            words.append(7 << 13 | rng.getrandbits(1) << 12 | rng.choice(COMPS) << 6 | rng.getrandbits(3) << 3)
    h = common.ROM_BASE + 2 * len(words)
    words += [h, 7 << 13 | 0b101010 << 6 | 7]                                # @halt ; 0;JMP
    return b''.join(bytes([w & 255, w >> 8]) for w in words)

c = build_hackvn(2)
if __name__ == '__main__':
    tot = 0
    for seed in range(int(sys.argv[1]) if len(sys.argv) > 1 else 20):
        img = gen(random.Random(seed), 800)
        i, t = lockstep.run_image(H, c, ref_state, net_state, img, seed)
        tot += i
    print('fuzz ok, instructions compared:', tot)
