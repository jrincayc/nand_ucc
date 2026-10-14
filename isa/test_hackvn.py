import sys, time
import isahack, common, lockstep
from nl_hackvn import build_hackvn
from fastsim import Fast

c = build_hackvn(2)
Fast.boundary = lambda self: self.st('st') & 1          # state F0 is bit0 of 'st'
ref_state = lambda r: (r.pc, r.A, r.D)
net_state = lambda f: (f.st('pc'), f.st('a'), f.st('d'))
if __name__ == '__main__':
    for k in sys.argv[1:] or common.KERNELS:
        t = time.time()
        r = lockstep.run_lockstep(isahack, c, ref_state, net_state, k)
        print(r, f'{time.time()-t:.0f}s', flush=True)
