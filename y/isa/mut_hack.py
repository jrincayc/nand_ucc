import sys, random
import isahack as H, mutate
from fuzz_hack import gen, c
from test_hackvn import ref_state, net_state
mutate.campaign(H, c, ref_state, net_state, lambda rng: gen(rng, 600), ['K1','K2','K3','K4'], int(sys.argv[1]), seeds=range(12))
