#!/usr/bin/env python3
"""ram_sim.py BUILD -- cycle simulation of the logical RAM block netlist: random writes/reads vs a Python model."""
import sys, json, random
bf = sys.argv[1]; d = json.load(open(bf + '.pins.json')); pins = {(x, y): n for x, y, n in d['pins']}
NW, NB = d['NW'], d['NBITS']
gates = {}; dffs = {}
for l in open(bf):
    t = l.split()
    if t[0] != 'place': continue
    k, x, y = int(t[1]), int(t[2]), int(t[3])
    if k == 0: gates[pins[(x + 1, y)]] = (pins[(x, y)], pins[(x, y + 1)])
    else: dffs[pins[(x + 1, y)]] = pins[(x, y)]
state = {q: 0 for q in dffs}
def comb(inputs, want):
    val = dict(inputs); val.update(state); memo = {}
    def get(n):
        if n in val: return val[n]
        if n in memo: return memo[n]
        if n not in gates: return 0            # unconnected input
        st = [n]
        while st:
            m = st[-1]
            if m in memo or m in val: st.pop(); continue
            a, b = gates[m]; need = [q for q in (a, b) if q not in val and q not in memo and q in gates]
            if need: st.extend(need); continue
            va = val.get(a, memo.get(a, 0)); vb = val.get(b, memo.get(b, 0)); memo[m] = 1 ^ (va & vb); st.pop()
        return memo[n]
    return [get(n) for n in want]
def setin(addr, din, we):
    v = {d['WE']: we}
    for b in range(8): v[d['DIN'][b]] = (din >> b) & 1
    for i in range(NB): v[d['abit'][i]] = (addr >> i) & 1
    return v
rnd = random.Random(3); model = [0] * NW; bad = 0
for step in range(int(sys.argv[2]) if len(sys.argv) > 2 else 200):
    a = rnd.randrange(NW); din = rnd.randrange(256); we = rnd.randrange(2)
    inp = setin(a, din, we)
    out = comb(inp, d['DOUT']); got = sum(x << i for i, x in enumerate(out))
    if got != model[a]: bad += 1; print('READ MISMATCH', step, a, got, model[a]) if bad < 5 else 0
    nxt = comb(inp, [dffs[q] for q in dffs])
    for q, v in zip(list(dffs), nxt): state[q] = v
    if we: model[a] = din
print(f'steps done, mismatches {bad}, gates {len(gates)}, dffs {len(dffs)}')
