import sys,collections
sys.path[:0]=['/home/claude/r2c/tools','/home/claude/r2c/isa','/home/claude/r2c/tests']
from run_builder import run, decode, norm
m,cpu,n,rom,dt=run('out3',10**9)
got=[norm(c) for c in decode(m.armlog)]
def cv(t):
    if t[0]=='place': return ('place',int(t[1]),int(t[2]),int(t[3]))
    if t[0]=='via': return ('via',int(t[1]),int(t[2]))
    return norm(('track',int(t[1]),int(t[2]),int(t[3]),int(t[4]),int(t[5])))
ref=[cv(l.split()) for l in open('../out/ram2.build') if l.strip()]
a=collections.Counter(ref);b=collections.Counter(got)
for k,name in((a-b,'missing'),(b-a,'extra')):
    print(name,sum(k.values()),collections.Counter(x[0] for x in k.elements()))
    print(sorted(k)[:12])
def cells(L):
    s=set()
    for t in L:
        if t[0]=='track':
            _,l,x0,y0,x1,y1=t
            for x in range(min(x0,x1),max(x0,x1)+1):
                for y in range(min(y0,y1),max(y0,y1)+1): s.add((l,x,y))
    return s
ca,cb=cells(ref),cells(got)
print('cover diff',len(ca-cb),len(cb-ca),'places/vias equal',sorted(x for x in ref if x[0]!='track')==sorted(x for x in got if x[0]!='track'))
