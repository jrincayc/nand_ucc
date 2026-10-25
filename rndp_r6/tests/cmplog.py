import re,sys
m=[l.split() for l in open(sys.argv[1]) if not l.startswith('STEP')]
bad=0;n=0
for l in open(sys.argv[2]):
    g=re.match(r't(\d+) arm0 (\w+) A=\((-?\d+),(-?\d+)\) B=\((-?\d+),(-?\d+)\) kind=(\d+) angle=(\d+) val=(\d+) -> (\w+)',l)
    if not g: print('?',l); continue
    t,cmd,ax,ay,bx,by,k,an,v,ok=g.groups(); ax=int(ax)-292;ay=int(ay)-54;bx=int(bx)-292;by=int(by)-54
    e=m[n]
    if cmd=='place': got=['place',k,str(ax),str(ay),an,v]
    elif cmd=='track': got=['track',v,str(ax),str(ay),str(bx),str(by)]
    else: got=['via',str(ax),str(ay)]
    if got[:len(e)]!=e[:len(got)] and got!=e:
        # model tuple may omit trailing fields
        if not (got[0]==e[0] and got[1:4]==e[1:4]): bad+=1; print('MISMATCH',n,got,e)
    n+=1
print('compared',n,'bad',bad,'ok-flags',)
