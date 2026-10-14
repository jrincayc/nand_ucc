"""Classify mutation survivors: compare original and mutated netlists on random *valid-ish* states
(one-hot control state, valid opcode in IR, random data), all lanes at once."""
import random, copy, sys, re
import nandgen as ng

def lanes_state(c, rng, L, st_names, valid_ir=None):
    sim = ng.Sim(c, L)
    M = (1 << L) - 1
    for w in range(c.n_in + c.n_dff):
        sim.v[w] = rng.getrandbits(L)
    # one-hot control state
    st = c.outs['st']
    choice = [rng.randrange(len(st)) for _ in range(L)]
    for k, w in enumerate(st):
        sim.v[w] = sum(1 << l for l in range(L) if choice[l] == k)
    sim.v[c.buses['reset'][0]] = 0
    if valid_ir:
        irw = valid_ir['wires']
        ops = [rng.choice(valid_ir['codes']) for _ in range(L)]
        for b, w in enumerate(irw):
            sim.v[w] = sum(1 << l for l in range(L) if (ops[l] >> b) & 1)
    return sim

def differs(c, c2, rng, L, valid_ir=None, rounds=6):
    for _ in range(rounds):
        seed = rng.getrandbits(32)
        outs = []
        for cc in (c, c2):
            s = lanes_state(cc, random.Random(seed), L, None, valid_ir)
            s.eval()
            outs.append([s.v[d] for d in cc.dffd] + [s.v[w] for k in ('addr', 'wdata', 'we') for w in cc.outs[k]])
        if outs[0] != outs[1]: return True
    return False
