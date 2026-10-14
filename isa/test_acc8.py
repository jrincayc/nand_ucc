import sys, time
import isaacc, common, lockstep
from nl_acc8 import build_acc8
from fastsim import Fast

c = build_acc8(2)
Fast.boundary = lambda self: self.st('st') & 1
ref_state = lambda r: (r.pc, r.acc, r.p, r.z, r.c)
net_state = lambda f: (f.st('pc'), f.st('acc'), f.st('p'), f.st('z'), f.st('c'))
if __name__ == '__main__':
    for k in sys.argv[1:] or common.KERNELS:
        t = time.time()
        r = lockstep.run_lockstep(isaacc, c, ref_state, net_state, k)
        print(r, f'{time.time()-t:.0f}s', flush=True)
