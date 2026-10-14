import sys; sys.path.insert(0,'/home/claude/pkg/rndw-stage/isa')
import nandgen as ng
from nl_core import build_core
# module library: gate lists over inputs 0..n-1, gates appended as signals n, n+1, ...; outs = signal indices
LIB = {
 'xor': {'T': (2, [], None), },
}
def inst(self, n_in, gates, outs, ins):
    sig = [self.real(w) for w in ins]
    for (i, j) in gates: sig.append(self._raw(sig[i], sig[j]))
    return [sig[o] for o in outs]
OPT = {   # exhaustive-search results (enum.py)
 'xor': (2, [(0,1),(0,2),(1,2),(3,4)], [5]),
 'ha':  (2, [(0,1),(0,2),(1,2),(2,2),(3,4)], [5, 5+0]),   # patched below
 'mux': (3, [(0,2),(1,2),(0,3),(4,5)], [6]),               # (a,b,s)
 'or':  (2, [(0,0),(1,1),(2,3)], [4]),
}
# ha outputs: sum = gate idx 4 (signal 2+4=6?) carry = gate3 (not t) -> recompute indices
OPT['ha'] = (2, [(0,1),(0,2),(1,2),(2,2),(3,4)], [6, 5])
def patch(variant):
    N = ng.Net
    orig = {k: getattr(N, k) for k in ('xor','mux','half_adder','full_adder','or_')}
    if variant >= 1:
        N.xor = lambda s,a,b: inst(s,*OPT['xor'],[a,b])[0]
        N.mux = lambda s,a,b,sel: inst(s,*OPT['mux'],[a,b,sel])[0]
        N.or_ = lambda s,a,b: inst(s,*OPT['or'],[a,b])[0]
        N.half_adder = lambda s,a,b: tuple(inst(s,*OPT['ha'],[a,b]))
        def fa(s,a,b,c):
            x1,c1 = N.half_adder(s,a,b); x2,c2 = N.half_adder(s,x1,c)
            return x2, N.or_(s,c1,c2)
        N.full_adder = fa
    if variant >= 2:   # FA after intra-module peephole: sum chain of 2 HA, carry = nand(t1,t4): 9 NAND
        def fa9(s,a,b,c):
            a,b,c = s.real(a),s.real(b),s.real(c)
            t1=s._raw(a,b); x=s._raw(s._raw(a,t1),s._raw(b,t1))
            t4=s._raw(x,c); sm=s._raw(s._raw(x,t4),s._raw(c,t4))
            return sm, s._raw(t4,t1)
        N.full_adder = fa9
    return orig
for v in (0,1,2):
    orig = patch(v)
    c = build_core(0, 5)
    print('variant',v,'NAND',len(c.gates),'DFF',c.n_dff)
    for k,f in orig.items(): setattr(ng.Net,k,f)
print('level1',len(build_core(1,5).gates),'level2',len(build_core(2,5).gates))
