"""E3: record the level-0 core as a cell-instance list and estimate a plain (no tricks) description size."""
import sys, math, collections
sys.path.insert(0,'/home/claude/pkg/rndw-stage/isa')
import nandgen as ng
from nl_core import build_core
rec=[]; depth=[0]
CELLS=['nand','not_','and_','or_','xor','mux','half_adder','full_adder']
for name in CELLS:
    f=getattr(ng.Net,name)
    def mk(f,name):
        def g(self,*a,**k):
            top = depth[0]==0
            depth[0]+=1
            try: r=f(self,*a,**k)
            finally: depth[0]-=1
            if top: rec.append((name,a,r))
            return r
        return g
    setattr(ng.Net,name,mk(f,name))
sd=ng.Net.set_d
dffs=[]
def set_d(self,q,d):
    dffs.append((q,d)); return sd(self,q,d)
ng.Net.set_d=set_d
c=build_core(0,5)
print('instances',len(rec),collections.Counter(r[0] for r in rec),'dff D links',len(dffs))
# signal numbering: inputs/dffs first (kind I,D by wire id), then cell outputs in record order
sig={}
def sid(w):
    return ('c',w) if w<0 else ('w',w)
outs=0
order={}
for k,(nm,a,r) in enumerate(rec):
    rs = r if isinstance(r,tuple) else (r,)
    for x in rs: order.setdefault(x,k)
def ref_cost(k,w):
    """bits to name signal w from instance k: backward distance in instance index (Exp-Golomb k=1),
    +1 flag for primary (input/DFF Q/const) which are named by absolute index (~log2 count)."""
    if w<0: return 2+1            # const0/const1 flag
    if w in order and order[w]<k:
        d=k-order[w]; return 1+2*int(math.log2(d+1))+1   # EG(0)-ish
    if w in order:  # forward ref (should only occur via DFF)
        return 12
    return 1+7                   # primary signal: ~log2(#inputs+#dffs) bits
tot=0
for k,(nm,a,r) in enumerate(rec):
    tot+=3+sum(ref_cost(k,w) for w in a if isinstance(w,int))
dtot=sum(ref_cost(len(rec),d)+7 for q,d in dffs)
print('bits for instances',tot,'bits for DFF D links',dtot,'bytes total',(tot+dtot)/8)
nprim=sum(1 for k in range(len(c.gates)) if False)
