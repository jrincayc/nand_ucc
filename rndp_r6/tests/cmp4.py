import sys,collections
sys.path[:0]=['/home/claude/r2c/tools','/home/claude/r2c/isa','/home/claude/r2c/tests']
from run_builder import run, decode, norm
m,cpu,n,rom,dt=run(sys.argv[1],10**9)
got=[norm(c) for c in decode(m.armlog)]
def cv(t):
    if t[0]=='place': return ('place',int(t[1]),int(t[2]),int(t[3]))
    if t[0]=='via': return ('via',int(t[1]),int(t[2]))
    return norm(('track',int(t[1]),int(t[2]),int(t[3]),int(t[4]),int(t[5])))
ref=[cv(l.split()) for l in open(sys.argv[2]) if l.strip()][int(sys.argv[3]):int(sys.argv[3])+int(sys.argv[4])]
def cells(L):
    s=set()
    for t in L:
        if t[0]=='track':
            _,l,x0,y0,x1,y1=t
            for x in range(min(x0,x1),max(x0,x1)+1):
                for y in range(min(y0,y1),max(y0,y1)+1): s.add((l,x,y))
    return s
print('cmds',len(got),len(ref),'cover diff',len(cells(ref)-cells(got)),len(cells(got)-cells(ref)),'vias',sorted(x for x in ref if x[0]=='via')==sorted(x for x in got if x[0]=='via'))
for i,(a,b) in enumerate(zip(got,ref)):
    if a!=b: print(i,a,b); break
print(got[:8]); print(ref[:8])
import collections
a=collections.Counter(ref);b=collections.Counter(got)
print('missing',[k for k in (a-b)][:6]);print('extra',[k for k in (b-a)][:6])
