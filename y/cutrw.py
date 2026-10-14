"""E8: module improver = (a) 2/3-leaf cut rewriting, replacement found by exhaustive synthesis (no database),
(b) dedupe identical gates, (c) dead-gate removal.  Module = (n_in, gates[(a,b)], outs); signal i<n_in is an input, n_in+g is gate g."""
import itertools, time
from enumnand import search, tt
def tts(n_in, gates):
    N=1<<n_in; full=(1<<N)-1; sig=[]
    for v in range(n_in): sig.append(sum(1<<r for r in range(N) if (r>>v)&1))
    for a,b in gates: sig.append(full^(sig[a]&sig[b]))
    return sig
def fanout(n_in,gates,outs):
    fo=[0]*(n_in+len(gates))
    for a,b in gates: fo[a]+=1; fo[b]+=1
    for o in outs: fo[o]+=1
    return fo
def cuts(n_in,gates,root,maxleaf=3):
    """all leaf sets (frozenset) of size<=maxleaf for gate-signal root, by expanding gate leaves"""
    out=set(); start=frozenset([root]); seen={start}; stack=[start]
    while stack:
        c=stack.pop()
        for s in c:
            if s>=n_in:
                a,b=gates[s-n_in]; nc=frozenset((c-{s})|{a,b})
                if len(nc)<=maxleaf and nc not in seen:
                    seen.add(nc); stack.append(nc); out.add(nc)
    return out
def cone(n_in,gates,root,leaves):
    res=set(); st=[root]
    while st:
        s=st.pop()
        if s in leaves or s<n_in or s in res: continue
        res.add(s); a,b=gates[s-n_in]; st+= [a,b]
    return res
def local_tt(n_in,gates,root,leaves):
    L=sorted(leaves); k=len(L); N=1<<k; full=(1<<N)-1
    val={l:sum(1<<r for r in range(N) if (r>>i)&1) for i,l in enumerate(L)}
    def ev(s):
        if s in val: return val[s]
        a,b=gates[s-n_in]; val[s]=full^(ev(a)&ev(b)); return val[s]
    return L,ev(root)
GMAX=6
def rewrite_once(n_in,gates,outs):
    fo=fanout(n_in,gates,outs)
    for g in range(len(gates)):
        root=n_in+g
        for leaves in sorted(cuts(n_in,gates,root),key=lambda c:(len(c),sorted(c))):
            cn=cone(n_in,gates,root,leaves)
            # removable: cone gates whose every fanout is inside the cone (root always counts)
            inside=set(cn)
            ref={s:0 for s in cn}
            for s in cn:
                a,b=gates[s-n_in]
                for x in (a,b):
                    if x in ref and x!=s: ref[x]+=1
            rem=[s for s in cn if s==root or (fo[s]==ref[s] and s not in outs)]
            if len(rem)<2: continue
            L,f=local_tt(n_in,gates,root,leaves)
            k=len(L)
            gmax=min(len(rem)-1,GMAX)
            ltab=[sum(1<<r for r in range(1<<k) if (r>>i)&1) for i in range(k)]
            if f in ltab:      # root equals one of its leaves (double inverter etc.): rewire, zero gates
                leaf=L[ltab.index(f)]
                newg=[(leaf if a==root else a, leaf if b==root else b) for a,b in gates]
                return compact(n_in,newg,[leaf if o==root else o for o in outs])
            res=search(k,[f],gmax,30)
            if res[0] is None: continue
            gnew,prog=res[0],res[1]
            # build: new gates appended after existing ones, then redirect root's uses
            idx=list(L)+[None]*gnew            # local signal -> global signal
            newg=list(gates); base=n_in+len(newg)
            for t,(i,j) in enumerate(prog):
                newg.append((idx[i],idx[j])); idx[k+t]=n_in+len(newg)-1
            newroot=idx[k+gnew-1]
            def sub(s): return newroot if s==root else s
            newg=[(sub(a),sub(b)) if n_in+q!=newroot else (a,b) for q,(a,b) in enumerate(newg)]
            nouts=[sub(o) for o in outs]
            return compact(n_in,newg,nouts)
    return None
def compact(n_in,gates,outs):
    # dedupe identical gates, drop dead gates, renumber topologically (gates only refer to earlier after sort)
    changed=True
    gates=list(gates); outs=list(outs)
    while changed:
        changed=False
        seen={}; m={}
        for q,(a,b) in enumerate(gates):
            a=m.get(a,a); b=m.get(b,b); key=(min(a,b),max(a,b)); 
            gates[q]=(a,b)
            if key in seen: m[n_in+q]=seen[key]; changed=True
            else: seen[key]=n_in+q
        outs=[m.get(o,o) for o in outs]
        live=set(); st=list(outs)
        while st:
            s=st.pop()
            if s in live or s<n_in: continue
            live.add(s); st+=list(gates[s-n_in])
        # topological order: process by dependency
        order=[]; done=set()
        def visit(s):
            if s<n_in or s in done: return
            done.add(s); a,b=gates[s-n_in]; visit(a); visit(b); order.append(s)
        for o in outs: visit(o)
        ren={i:i for i in range(n_in)}
        for t,s in enumerate(order): ren[s]=n_in+t
        ng=[(ren[gates[s-n_in][0]],ren[gates[s-n_in][1]]) for s in order]
        no=[ren[o] for o in outs]
        if len(ng)!=len(gates): changed=True
        gates,outs=ng,no
    return n_in,gates,outs
def improve(mod):
    n_in,gates,outs=mod; n_in,gates,outs=compact(n_in,gates,outs); t0=time.time()
    while True:
        r=rewrite_once(n_in,gates,outs)
        if r is None or len(r[1])>=len(gates) and r[1]==gates: break
        if len(r[1])>len(gates): break
        n_in,gates,outs=r
    return (n_in,gates,outs),time.time()-t0
# textbook modules (level 0 generator conventions)
class B:
    def __init__(s,n): s.n=n; s.g=[]
    def nand(s,a,b): s.g.append((a,b)); return s.n+len(s.g)-1
    def not_(s,a): return s.nand(a,a)
    def and_(s,a,b): return s.not_(s.nand(a,b))
    def or_(s,a,b): return s.nand(s.not_(a),s.not_(b))
    def xor(s,a,b): return s.or_(s.and_(a,s.not_(b)),s.and_(s.not_(a),b))
    def mux(s,a,b,sel): return s.or_(s.and_(a,s.not_(sel)),s.and_(b,sel))
    def ha(s,a,b): return s.xor(a,b),s.and_(a,b)
    def fa(s,a,b,c):
        x,c1=s.ha(a,b); y,c2=s.ha(x,c); return y,s.or_(c1,c2)
def mk(n,f):
    b=B(n); o=f(b,*range(n)); o=list(o) if isinstance(o,tuple) else [o]; return (n,b.g,o)
MODS={
 'not':mk(1,lambda b,a:b.not_(a)),'and':mk(2,lambda b,a,c:b.and_(a,c)),'or':mk(2,lambda b,a,c:b.or_(a,c)),
 'xor':mk(2,lambda b,a,c:b.xor(a,c)),'mux':mk(3,lambda b,a,c,s:b.mux(a,c,s)),
 'ha':mk(2,lambda b,a,c:b.ha(a,c)),'fa':mk(3,lambda b,a,c,d:b.fa(a,c,d)),
 'xnor(unlisted)':mk(2,lambda b,a,c:b.not_(b.xor(a,c))),
 'and3(unlisted)':mk(3,lambda b,a,c,d:b.and_(b.and_(a,c),d)),
 'maj(unlisted)':mk(3,lambda b,a,c,d:b.or_(b.or_(b.and_(a,c),b.and_(a,d)),b.and_(c,d))),
}
if __name__=='__main__':
    for k,m in MODS.items():
        r,t=improve(m)
        ok=tts(m[0],m[1])[-0:] 
        same=[tts(m[0],m[1])[o] for o in m[2]]==[tts(r[0],r[1])[o] for o in r[2]]
        print(f'{k:16s} textbook {len(m[1]):3d} -> {len(r[1]):3d}  same function {same}  {t:.1f}s')
