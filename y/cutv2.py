"""Variant of cutrw.py with 'chain' cuts only: expand the highest-numbered gate leaf each time (simple to implement in ROM)."""
import cutrw
from cutrw import *
def cuts_chain(n_in,gates,root,maxleaf=3):
    a,b=gates[root-n_in]; leaves=sorted({a,b}); out=[]
    while True:
        out.append(frozenset(leaves))
        g=[s for s in leaves if s>=n_in]
        if not g: break
        s=max(g); x,y=gates[s-n_in]
        nl=sorted((set(leaves)-{s})|{x,y})
        if len(nl)>maxleaf: break
        leaves=nl
    return out
def run(mods,variant):
    if variant=='chain': cutrw.cuts=lambda n_in,gates,root,maxleaf=3: cuts_chain(n_in,gates,root,maxleaf)
    res={}
    for k,m in mods.items():
        r,t=cutrw.improve(m)
        same=[tts(m[0],m[1])[o] for o in m[2]]==[tts(r[0],r[1])[o] for o in r[2]]
        res[k]=(len(r[1]),same)
    return res
if __name__=='__main__':
    import random,sys,importlib
    mods=dict(MODS)
    # random 2- and 3-input single-output functions as textbook sum-of-products
    rnd=random.Random(5)
    for i in range(60):
        n=rnd.choice([2,3]); N=1<<n; tt_=rnd.getrandbits(N)
        if tt_ in (0,(1<<N)-1): continue
        b=B(n)
        terms=[]
        for r in range(N):
            if (tt_>>r)&1:
                lits=[ (v if (r>>v)&1 else b.not_(v)) for v in range(n)]
                t=lits[0]
                for l in lits[1:]: t=b.and_(t,l)
                terms.append(t)
        o=terms[0]
        for t in terms[1:]: o=b.or_(o,t)
        mods[f'rand{i}_{n}in_{tt_:0{N}b}']=(n,b.g,[o])
    r1=run(mods,'all'); 
    importlib.reload(cutrw)
    import cutv2 as me
    r2=me.run(mods,'chain')
    bad=0; worse=0
    for k in mods:
        if not r1[k][1] or not r2[k][1]: print('NOT EQUAL',k,r1[k],r2[k]); bad+=1
        if r2[k][0]>r1[k][0]: worse+=1; print('chain worse',k,r1[k][0],r2[k][0])
    print('modules',len(mods),'not-equal',bad,'chain worse than all-cuts',worse)
    for k in list(MODS): print(f'{k:16s} textbook {len(MODS[k][1]):3d} all-cuts {r1[k][0]:3d} chain {r2[k][0]:3d}')
