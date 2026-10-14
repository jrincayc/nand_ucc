import sys, random, time
import isahack as H, mutate as M
from fuzz_hack import gen, c
from test_hackvn import ref_state, net_state
rng = random.Random(1); n = int(sys.argv[1])
for m in range(n):
    c2, i = M.mutate(c, rng)
    t = time.time()
    r = M.survives(H, c2, ref_state, net_state, lambda r: gen(r, 600), ['K1','K2','K3','K4'], range(12))
    print(m, i, c.gate_tags[i], 'SURVIVED' if r else 'killed', f'{time.time()-t:.1f}s', flush=True)
