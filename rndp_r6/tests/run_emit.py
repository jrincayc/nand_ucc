import sys, collections
sys.path[:0]=['/home/claude/r2c/tools','/home/claude/r2c/isa','/home/claude/r2c/tests']
from run_builder import run, decode, norm
outdir=sys.argv[1]
m,cpu,n,rom,dt=run(outdir,int(sys.argv[3]) if len(sys.argv)>3 else 10**9)
got=[norm(c) for c in decode(m.armlog)]
print('instr',n,'cmds',len(got),'ram hi',m.hi,'bad',len(m.bad),f'{dt:.0f}s')
ref=[tuple(l.split()) for l in open(sys.argv[2]) if l.strip()]
def cv(t):
    if t[0]=='place': return ('place',int(t[1]),int(t[2]),int(t[3]))
    if t[0]=='via': return ('via',int(t[1]),int(t[2]))
    return norm(('track',int(t[1]),int(t[2]),int(t[3]),int(t[4]),int(t[5])))
ref=[cv(t) for t in ref]
ca=collections.Counter(ref[:len(got)] if len(got)<len(ref) else ref); cb=collections.Counter(got); print('same order:',got==ref,'| missing',sum((ca-cb).values()),'extra',sum((cb-ca).values()))
if got!=ref[:len(got)]:
    for i,(a,b) in enumerate(zip(got,ref)):
        if a!=b: print(i,a,b); break
