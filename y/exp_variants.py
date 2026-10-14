import sys, random; sys.path.insert(0,'tools')
import ref_improve as R
from ref_improve import *

def compact_stable(n_in, gates, outs):
    """in-place friendly: merge identical (keep first), drop dead, keep relative order (stays topological)"""
    gates=list(gates); outs=list(outs)
    remap={}
    seen={}
    for g in range(len(gates)):
        a,b=gates[g]; a,b=remap.get(a,a),remap.get(b,b); gates[g]=(a,b)
        k=(min(a,b),max(a,b))
        if k in seen: remap[n_in+g]=seen[k]
        else: seen[k]=n_in+g
    outs=[remap.get(o,o) for o in outs]
    live=set(); st=list(outs)
    while st:
        s=st.pop()
        if s<n_in or s in live: continue
        live.add(s); st+=list(gates[s-n_in])
    ren={i:i for i in range(n_in)}; new=[]
    for g in range(len(gates)):
        s=n_in+g
        if s in live:
            a,b=gates[g]; ren[s]=n_in+len(new); new.append((ren[a],ren[b]))
    return new,[ren[o] for o in outs]

def improve_v(n_in,gates,outs,comp,cutkey,accept_strict=True):
    gates,outs=comp(n_in,gates,outs)
    while True:
        changed=False
        fo=[0]*(n_in+len(gates))
        for a,b in gates: fo[a]+=1; fo[b]+=1
        for o in outs: fo[o]+=1
        for g in range(len(gates)):
            root=n_in+g
            for leaves in sorted(chain_cuts(n_in,gates,root),key=cutkey):
                cone=cone_of(n_in,gates,root,set(leaves))
                inner={s:0 for s in cone}
                for s in cone:
                    for x in gates[s-n_in]:
                        if x in inner: inner[x]+=1
                saved=sum(1 for s in cone if s==root or (fo[s]==inner[s] and s not in outs))
                k=len(leaves); base,full=var_tables(k)
                val={leaves[i]:base[i] for i in range(k)}
                for s in sorted(cone):
                    a,b=gates[s-n_in]; val[s]=full^(val[a]&val[b])
                f=val[root]
                if f in base: new_sig=leaves[base.index(f)]; prog=[]
                else:
                    gmax=min(saved-1,GMAX)
                    if gmax<1: continue
                    prog=search(k,f,gmax)
                    if prog is None: continue
                # insert new gates before root (stable layout): signals >=root shift by len(prog)
                n=len(prog)
                sh=lambda x: x if x<root else x+n
                ng=[(sh(a),sh(b)) for a,b in gates]
                idx=list(leaves); add=[]
                for t,(i,j) in enumerate(prog):
                    add.append((idx[i],idx[j])); idx.append(root+t)
                if prog: new_sig=idx[-1]
                ng=ng[:g]+add+ng[g:]
                r2=root+n
                ns=new_sig
                ng=[(ns if a==r2 else a, ns if b==r2 else b) for a,b in ng]
                no=[ns if sh(o)==r2 else sh(o) for o in outs]
                # the old root gate stays (dead now) -> compact removes
                gates,outs=comp(n_in,ng,no); changed=True; break
            if changed: break
        if not changed: return gates,outs

def lib():
    import hd as H
    hd=H.read(open('hd/core_r7.hd').read())
    return [(m.name,m.n_in,m.gates,m.outs) for m in hd.modules if R.improvable(m)]

def rnd(seed):
    r=random.Random(seed); n_in=r.choice([2,3]); ng=r.randint(3,14)
    gates=[(r.randrange(n_in+g),r.randrange(n_in+g)) for g in range(ng)]
    outs=[n_in+ng-1]+([r.randrange(n_in,n_in+ng)] if r.random()<.5 else [])
    return n_in,gates,outs

def run(name,fn):
    tot=0
    out=[]
    for nm,n_in,g,o in lib():
        out.append((nm,len(fn(n_in,g,o)[0])))
    rs=[len(fn(*rnd(s))[0]) for s in range(200)]
    print(name,out,'rand sum',sum(rs))
    return rs
if __name__=='__main__':
    run('v1',lambda n,g,o:R.improve(n,g,o))
    ck=lambda c:(len(c),c)
    run('dfs-comp',lambda n,g,o:improve_v(n,g,o,R.compact,ck))
    run('stable',lambda n,g,o:improve_v(n,g,o,compact_stable,ck))

def unlisted():
    # built from textbook and/or/not NAND expansions, flattened by hand
    def mk(n_in,expr):
        g=[]
        def N(a,b): g.append((a,b)); return n_in+len(g)-1
        NOT=lambda a:N(a,a); AND=lambda a,b:NOT(N(a,b)); OR=lambda a,b:N(NOT(a),NOT(b))
        o=expr(NOT,AND,OR); return n_in,g,[o]
    return {
     'xnor':mk(2,lambda NOT,AND,OR:NOT(OR(AND(0,NOT(1)),AND(NOT(0),1)))),
     'and3':mk(3,lambda NOT,AND,OR:AND(AND(0,1),2)),
     'maj':mk(3,lambda NOT,AND,OR:OR(OR(AND(0,1),AND(0,2)),AND(1,2))),
    }
if __name__=='__main__':
    for nm,(n,g,o) in unlisted().items():
        print(nm,len(g),len(R.improve(n,g,o)[0]),len(improve_v(n,g,o,compact_stable,(lambda c:(len(c),c)))[0]))
