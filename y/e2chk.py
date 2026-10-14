import random, sys
sys.path.insert(0,'/home/claude/pkg/rndw-stage/isa')
exec(open('e2.py').read().split("for v in (0,1,2):")[0])
def ev(c, ins, dff):
    v = list(ins)+list(dff)
    for a,b in c.gates: v.append(1-(v[a]&v[b]))
    return {k:[v[i] for i in ids] for k,ids in c.outs.items() if k in ('rom_addr','arm_en','wdata','ram_addr','ram_we','addr','we')}, [v[i] for i in c.dffd]
cs={}
for var in (0,1,2):
    o=patch(var); cs[var]=build_core(0,5)
    for k,f in o.items(): setattr(ng.Net,k,f)
c0=cs[0]; bad=0
for t in range(3000):
    ins=[random.getrandbits(1) for _ in range(c0.n_in)]; d=[random.getrandbits(1) for _ in range(c0.n_dff)]
    r0=ev(c0,ins,d)
    for var in (1,2):
        if ev(cs[var],ins,d)!=r0: bad+=1
print('mismatches',bad)
