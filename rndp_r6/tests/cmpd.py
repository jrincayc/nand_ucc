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
got=[g[:4] if g[0]=='place' else g for g in got]
a=collections.Counter(ref);b=collections.Counter(got)
print('instr',n,'got',len(got),'ref',len(ref))
for nm,k in (('missing',a-b),('extra',b-a)):
    print(nm,sum(k.values()),collections.Counter(x[0] for x in k.elements()))
    print(sorted(k)[:5])
