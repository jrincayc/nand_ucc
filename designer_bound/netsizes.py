import sys, json, math
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
build, pinsjson = sys.argv[1], sys.argv[2]
W, H = 1400, 8200
def cid(l, x, y): return (l*H + y)*W + x
E0=[]; E1=[]   # edges
ntrack=0; nvia=0; npl=0
pinlist=[]     # (cellid layer0, kind)
for line in open(build):
    t=line.split()
    if t[0]=='track':
        l,x0,y0,x1,y1=map(int,t[1:]); ntrack+=1
        if x0==x1:
            ys=np.arange(min(y0,y1),max(y0,y1)+1); a=(l*H+ys)*W+x0
        else:
            xs=np.arange(min(x0,x1),max(x0,x1)+1); a=(l*H+y0)*W+xs
        E0.append(a[:-1]); E1.append(a[1:])
    elif t[0]=='via':
        x,y=int(t[1]),int(t[2]); nvia+=1
        E0.append(np.array([cid(0,x,y)])); E1.append(np.array([cid(1,x,y)]))
    elif t[0]=='place':
        x,y=int(t[2]),int(t[3]); npl+=1
        for (px,py) in ((x,y),(x,y+1),(x+1,y)):
            E0.append(np.array([cid(0,px,py)])); E1.append(np.array([cid(1,px,py)]))
e0=np.concatenate(E0); e1=np.concatenate(E1)
cells,inv=np.unique(np.concatenate([e0,e1]),return_inverse=True)
n=len(cells); m=len(e0)
a=inv[:m]; b=inv[m:]
g=coo_matrix((np.ones(m,dtype=np.int8),(a,b)),shape=(n,n))
nc,lab=connected_components(g,directed=False)
# component sizes: cells and edges (edges may be duplicated if tracks overlap in same cells -> dedupe)
key=np.minimum(a,b).astype(np.int64)*n+np.maximum(a,b)
ukey=np.unique(key); ua=ukey//n; 
cn=np.bincount(lab,minlength=nc); cm=np.bincount(lab[ua],minlength=nc)
print(f'tracks {ntrack} vias {nvia} gates {npl}; copper cells {n}; distinct edges {len(ukey)}; components {nc}')
# validate against logical netlist
pj=json.load(open(pinsjson))
cell2idx={int(c):i for i,c in enumerate(cells)}
comp_of_net={}; net_of_comp={}; bad=0
for x,y,net in pj['pins']:
    i=cell2idx.get(cid(0,x,y))
    if i is None: bad+=1; continue
    c=lab[i]
    comp_of_net.setdefault(net,set()).add(c); net_of_comp.setdefault(c,set()).add(net)
opens=sum(1 for s in comp_of_net.values() if len(s)>1); shorts=sum(1 for s in net_of_comp.values() if len(s)>1)
print(f'pins {len(pj["pins"])} logical nets {len(comp_of_net)} missing {bad} opens {opens} shorts {shorts}')
# only components that hold pins matter as nets
pc=np.array(sorted(net_of_comp))
sz=cn[pc]; ed=cm[pc]
print(f'pin-carrying nets {len(pc)}; cells: median {np.median(sz):.0f} p90 {np.percentile(sz,90):.0f} p99 {np.percentile(sz,99):.0f} max {sz.max()}; total {sz.sum()}')
order=np.argsort(-sz)[:8]
print('largest nets (cells, edges):',[(int(sz[i]),int(ed[i])) for i in order])
cover=2.0*ed*(sz-1)
tot=cover.sum(); mx=cover.max()
print(f'cover-time bound 2m(n-1): sum {tot:.3e} (2^{math.log2(tot):.1f}), max net {mx:.3e} (2^{math.log2(mx):.1f})')
cmds=sum(1 for _ in open(build))
for rep in (1,30):
    s=tot*rep
    print(f' walks x{rep}: steps {s:.2e} 2^{math.log2(s):.1f}; with per-step scan of {cmds} commands: 2^{math.log2(s*cmds):.1f}')
# share of total from top-k nets
cs=np.sort(cover)[::-1]; print('top 10 nets share of cover-bound sum: %.1f%%'%(100*cs[:10].sum()/tot))
