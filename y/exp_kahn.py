import sys; sys.path.insert(0,'tools')
import ref_improve as R, exp_variants as E

def canon(n_in, gates, outs, keyf=None):
    gates=list(gates); outs=list(outs)
    # merge to fixpoint
    while True:
        done=True
        n=len(gates)
        for g in range(n):
            if gates[g] is None: continue
            for h in range(g):
                if gates[h] is None: continue
                if sorted(gates[h])==sorted(gates[g]):
                    sg,sh=n_in+g,n_in+h
                    gates=[None if i==g else None if x is None else tuple(sh if y==sg else y for y in x) for i,x in enumerate(gates)]
                    outs=[sh if o==sg else o for o in outs]; done=False; break
            if not done: break
        if done: break
    live=set(); ch=True
    for o in outs:
        if o>=n_in: live.add(o)
    while ch:
        ch=False
        for s in list(live):
            for x in gates[s-n_in]:
                if x>=n_in and x not in live: live.add(x); ch=True
    ren={i:i for i in range(n_in)}; k=0
    while k<len(live):
        best=None
        for s in sorted(live):
            if s in ren: continue
            a,b=gates[s-n_in]
            if a in ren and b in ren:
                key=tuple(sorted((ren[a],ren[b])))
                if keyf: key=keyf(ren[a],ren[b])
                if best is None or key<best[0]: best=(key,s)
        ren[best[1]]=n_in+k; k+=1
    new=[None]*k
    for s in live:
        a,b=gates[s-n_in]; new[ren[s]-n_in]=(ren[a],ren[b])
    return new,[ren[o] for o in outs]

def imp(n,g,o,keyf=None):
    comp=lambda n_,g_,o_: canon(n_,g_,o_,keyf)
    return E.improve_v(n,g,o,comp,lambda c:(len(c),c))
if __name__=='__main__':
    for nm,keyf in (('sorted',None),('ab',lambda a,b:(a,b)),('rev',lambda a,b:(-max(a,b),-min(a,b)))):
        print(nm,[(m,len(imp(n,g,o,keyf)[0])) for m,n,g,o in E.lib()],
          [(k,len(imp(*v,keyf)[0])) for k,v in E.unlisted().items()], sum(len(imp(*E.rnd(s),keyf)[0]) for s in range(200)))

def pipeline(n,g,o,keyf=None):
    g1,o1=canon(n,g,o,keyf)
    g2,o2=E.improve_v(n,g1,o1,E.compact_stable,lambda c:(len(c),c))
    return g2,o2
def second(n,g,o,keyf=None):
    g2,o2=pipeline(n,g,o,keyf)
    g3,o3=pipeline(n,g2,o2,keyf)
    return len(g2),len(g3)
if __name__=='__main__':
    print('--- canon first, then stable loop')
    for nm,keyf in (('sorted',None),('ab',lambda a,b:(a,b)),('rev',lambda a,b:(-max(a,b),-min(a,b)))):
        L=[(m,second(n,g,o,keyf)) for m,n,g,o in E.lib()]
        U=[(k,second(*v,keyf)) for k,v in E.unlisted().items()]
        R=[second(*E.rnd(s),keyf) for s in range(200)]
        print(nm,L,U,'rand',sum(a for a,b in R),'regress',sum(1 for a,b in R if b<a))
