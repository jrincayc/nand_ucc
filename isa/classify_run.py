import sys, random, copy
import nandgen as ng, mutate, classify
which = sys.argv[1]; n = int(sys.argv[2])
if which == 'acc8':
    import isaacc as I
    from nl_acc8 import build_acc8
    from fuzz_acc8 import gen
    from test_acc8 import ref_state, net_state
    c = build_acc8(2); isa = I
    codes = [code for _, _, code in I.SPEC]
    def pick(rng):
        return rng.choice(codes)
    irbits = 8
else:
    import isahack as H
    from nl_hackvn import build_hackvn
    from fuzz_hack import gen, COMPS
    from test_hackvn import ref_state, net_state
    c = build_hackvn(2); isa = H
    def pick(rng):
        v = rng.getrandbits(13) & ~(63 << 6) | rng.choice(COMPS) << 6   # 13 bits: lo 8 + hi 5; comp = bits 6..11
        return v
    irbits = 13

def differs(c, c2, rng, L=512, rounds=8):
    for _ in range(rounds):
        seed = rng.getrandbits(32); res = []
        for cc in (c, c2):
            r = __import__('random').Random(seed)
            sim = ng.Sim(cc, L)
            for w in range(cc.n_in + cc.n_dff): sim.v[w] = r.getrandbits(L)
            st = cc.outs['st']; ch = [r.randrange(len(st)) for _ in range(L)]
            for k, w in enumerate(st): sim.v[w] = sum(1 << l for l in range(L) if ch[l] == k)
            sim.v[cc.buses['reset'][0]] = 0
            ops = [pick(r) for _ in range(L)]
            for b, w in enumerate(cc.outs['ir']): sim.v[w] = sum(1 << l for l in range(L) if (ops[l] >> b) & 1)
            sim.eval()
            res.append([sim.v[d] for d in cc.dffd] + [sim.v[w] for k in ('addr', 'wdata', 'we') for w in cc.outs[k]])
        if res[0] != res[1]: return True
    return False

rng = random.Random(1)
surv = []
import mutate as M
rngm = random.Random(1)
for m in range(n):
    c2, i = M.mutate(c, rngm)
    if c2.gates[i] == c.gates[i]: continue
    if M.survives(isa, c2, ref_state, net_state, lambda r: gen(r, 600), ['K1','K2','K3','K4'], range(12)):
        d = differs(c, c2, rng)
        surv.append((i, c.gate_tags[i], c.gates[i], c2.gates[i], 'DIFFERS-on-valid-state' if d else 'equivalent'))
for s in surv: print(s)
print(len(surv), 'survivors;', sum(1 for s in surv if s[4] == 'equivalent'), 'equivalent')
