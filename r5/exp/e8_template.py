#!/usr/bin/env python3
"""E8: 'template layout' = netlist stored IN placement order + deterministic fold/router (R4 route_ref).  Wiring is implied; layout description = netlist bits only.
Compares node orders for board size and wire length on a netlist.  Run from r4/: python3 ../r5/exp/e8_template.py <nl> [R Z]"""
import sys, os, random, collections
os.environ.update(ROM_BITS='16', AB='18', RAM_BITS='18')
sys.path[:0] = ['tools', '../r5/exp']
import lay, place_ref, route_ref
import e6_e7 as E
path = sys.argv[1]; R = int(sys.argv[2]) if len(sys.argv) > 2 else 22; Z = int(sys.argv[3]) if len(sys.argv) > 3 else 14
nl = lay.read_nl(path); N = len(nl.nodes)
def dfs_order(nl):
    pos = {}; 
    idx = {}
    T = None
    # node index -> fanins by 'nK' tokens
    fan = []
    for k, (kind, ins) in enumerate(nl.nodes):
        fan.append([int(t.split('@')[0][1:]) for t in ins if t.split('@')[0][1:].isdigit() and t[0] == 'n'])
    seen = set(); out = []
    def visit(x):
        st = [(x, 0)]
        while st:
            v, ph = st.pop()
            if ph == 0:
                if v in seen: continue
                seen.add(v); st.append((v, 1))
                if nl.nodes[v][0] != 'D':
                    for f in reversed(fan[v]): st.append((f, 0))
            else: out.append(v)
    dins = [[int(t.split('@')[0][1:]) for t in ins if t[0] == 'n' and t.split('@')[0][1:].isdigit()] for kind, ins in nl.nodes]
    for k, (kind, _) in enumerate(nl.nodes):
        if kind == 'D':
            for f in dins[k]: visit(f)
    for k in range(N): visit(k)
    return out
orders = {'identity': list(range(N)), 'dfs': dfs_order(nl), 'lpa (R4 placer)': place_ref.order(nl, seed=1)}
r = random.Random(1); rr = list(range(N)); r.shuffle(rr); orders['random'] = rr
for name, o in orders.items():
    assert sorted(o) == list(range(N)), name
    try: cmds, info = route_ref.route(nl, o, R, Z)
    except Exception as e: print(f"{name:16s} router failed: {type(e).__name__} {e}"); continue
    tr = [c for c in cmds if c[0] == 'track']
    length = sum(abs(c[2] - c[4]) + abs(c[3] - c[5]) for c in tr)
    xs = [c[2] for c in cmds if c[0] == 'place'] + [c[4] for c in tr]; ys = [c[3] for c in cmds if c[0] == 'place'] + [c[5] for c in tr]
    print(f'{name:16s} W={info["W"]:4d} board~{max(xs)-min(xs)+1}x{max(ys)-min(ys)+1}  cmds={len(cmds):6d} tracks={len(tr):6d} vias={sum(1 for c in cmds if c[0]=="via"):6d} wire length={length}')

# ---- bits to store the netlist IN each placement order (signed backward/forward distance, zigzag-gamma; external inputs absolute).  MEASURED encoding size, decoder not counted.
def gamma(x): return 2 * x.bit_length() - 1
def zz(v): return 1 + gamma(abs(v))     # sign bit + gamma(|distance|)
ng = sum(1 for k, _ in nl.nodes if k == 'N')
print(f'\nnetlist storage cost in placement order ({ng} NAND, {N - ng} DFF):')
for name, o in orders.items():
    pos = {k: i for i, k in enumerate(o)}; bits = 0
    for k in o:
        kind, ins = nl.nodes[k]; refs = [t.split('@')[0] for t in ins]
        if kind == 'N':
            bits += 1; uniq = [refs[0]] if refs[0] == refs[1] else refs
        else: uniq = refs[:1]
        for t in uniq:
            bits += 1
            if t[0] == 'n' and t[1:].isdigit() and nl.nodes[int(t[1:])][0] == 'N': bits += zz(pos[int(t[1:])] - pos[k])
            elif t[0] == 'n' and t[1:].isdigit(): bits += max(1, (N - ng - 1).bit_length())     # DFF output: index among DFFs
            else: bits += max(1, (len(nl.nodes)).bit_length())
    print(f'  {name:16s} {bits / ng:6.2f} bits/NAND')
