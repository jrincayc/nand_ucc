import sys, random
import isaacc as I, mutate
from fuzz_acc8 import gen, c
from test_acc8 import ref_state, net_state
mutate.campaign(I, c, ref_state, net_state, lambda rng: gen(rng, 600), ['K1','K2','K3','K4'], int(sys.argv[1]), seeds=range(12))
