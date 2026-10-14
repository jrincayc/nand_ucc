import random, sys, copy, time
import common, lockstep
from fastsim import Fast

def mutate(c, rng):
    c2 = copy.copy(c); g = list(c.gates)
    base = c.n_in + c.n_dff
    i = rng.randrange(len(g)); a, b = g[i]
    new = rng.randrange(base + i)
    if rng.random() < 0.5: g[i] = (new, b)
    else: g[i] = (a, new)
    c2.gates = g
    return c2, i

def survives(isa, c2, ref_state, net_state, fuzz_gen, kernels, seeds):
    try:
        for s in seeds:
            lockstep.run_image(isa, c2, ref_state, net_state, fuzz_gen(random.Random(s)), s, max_instr=4000)
        for k in kernels:
            r = lockstep.run_lockstep(isa, c2, ref_state, net_state, k, max_ticks=200000)
            if not r['ok']: return False
    except Exception:
        return False
    return True

def campaign(isa, c, ref_state, net_state, fuzz_gen, kernels, nmut, seeds=(0, 1, 2), seed=1):
    rng = random.Random(seed); surv = []
    t0 = time.time()
    for m in range(nmut):
        c2, i = mutate(c, rng)
        if c2.gates[i] == c.gates[i]: continue
        if survives(isa, c2, ref_state, net_state, fuzz_gen, kernels, seeds):
            surv.append((i, c.gate_tags[i], c.gates[i], c2.gates[i]))
    print(f'{nmut} mutations, {len(surv)} survived, {time.time()-t0:.0f}s')
    for s in surv: print('  survivor gate', s)
    return surv
