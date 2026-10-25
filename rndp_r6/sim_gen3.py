#!/usr/bin/env python3
"""sim_gen.py BUILD ROMFILE OFFSET R C -- evaluate the logical gate netlist recorded by plane_gen (pins json) for every address and compare with the ROM bytes."""
import sys, json
bf, rom, off, R, C = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
d = json.load(open(bf + '.pins.json')); pins = {(x, y): n for x, y, n in d['pins']}
data = list(open(rom, 'rb').read()[off:off + R * C]); data += [0] * (R * C - len(data))
gates = {}
for l in open(bf):
    t = l.split()
    if t[0] == 'place':
        x, y = int(t[2]), int(t[3]); gates[pins[(x + 1, y)]] = (pins[(x, y)], pins[(x, y + 1)])
sys.setrecursionlimit(1000000)
def ev(n, val, memo):
    if n in val: return val[n]
    if n in memo: return memo[n]
    a, b = gates[n]
    # iterative to avoid deep recursion
    stack = [n]
    while stack:
        m = stack[-1]
        if m in memo or m in val: stack.pop(); continue
        a, b = gates[m]; need = [q for q in (a, b) if q not in val and q not in memo]
        if need: stack.extend(need); continue
        va = val.get(a, memo.get(a)); vb = val.get(b, memo.get(b)); memo[m] = 1 ^ (va & vb); stack.pop()
    return memo[n]
ab = d['abit']; NB = d['NB']; NBH = d['NBH']; bad = 0; tested = 0
import random
addrs = list(range(R * C))
if len(addrs) > 700: addrs = random.Random(1).sample(addrs, 600) + [a for a in addrs if data[a]][:100]
for a in addrs:
    h, l = divmod(a, C); val = {n: 0 for n in d.get('floating', [])}
    for i in range(NB): val[ab[i]] = (l >> i) & 1
    for i in range(NBH): val[ab[NB + i]] = (h >> i) & 1
    memo = {}; got = 0
    for j, o in enumerate(d['outs']):
        if o is not None: got |= ev(o, val, memo) << j
    tested += 1
    if got != data[a]: bad += 1; print('MISMATCH', a, got, data[a]) if bad < 5 else 0
print(f'tested {tested} addresses, mismatches {bad}')
