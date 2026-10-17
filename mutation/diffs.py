import os, load, collections, random, sys
sys.setrecursionlimit(100000)
SD = load.SD
L = [l.split() for l in open(os.path.join(SD, 'quine_gen1_start.txt')) if l.strip()]
parts = {int(t[1]): tuple(map(int, t[2:6])) for t in L if t[0] == 'part'}
wires = [tuple(map(int, t[1:5])) for t in L if t[0] == 'wire']
site = {}   # (x,y) -> (partid, role)
row = {}
for pid, (k, x, y, r) in parts.items():
    if y == 31 and k in (0, 1): row[(x - 6) // 2] = (pid, k)
N = max(row) + 1
print('row nodes', N)
kinds = [row[i][1] for i in range(N)]
nd = 0
while kinds[nd] == 1: nd += 1
print('core DFFs', nd)
# wire map: input site -> output site
drv = {(w[2], w[3]): (w[0], w[1]) for w in wires}
def src_of(i, pin):                       # node i input pin 0/1 -> (kind,desc)
    x = 6 + 2 * i
    o = drv.get((x, 31 + pin))
    if o is None: return ('none',)
    if o[1] == 31 and o[0] % 2 == 1 and (o[0] - 7) // 2 < N and (o[0] - 7) % 2 == 0: return ('node', (o[0] - 7) // 2)
    return ('other', o)
def dsrc(i):
    x = 6 + 2 * i; o = drv.get((x, 31))
    return src_of(i, 0)
# regions: find RAM tiles: DFF pattern after core
tile_dff = [i for i in range(nd, N) if kinds[i] == 1]
first_tile_dff = tile_dff[0] if tile_dff else None
print('first DFF after core', first_tile_dff, 'DFFs total', sum(kinds))
def region(i):
    if i < nd: return 'core DFF'
    if first_tile_dff is not None and i >= first_tile_dff - 4 - 60: return f'RAM area (node {i})'
    return 'core/predecode NAND'
# function of node via cone
memo = {}
def leaves_and_eval(i, asg):
    if i in memo: return memo[i]
    s = ('node', i)
    if kinds[i] == 1: v = asg.setdefault(('dff', i), random.getrandbits(1))
    else:
        vs = []
        for pin in (0, 1):
            sr = src_of(i, pin)
            if sr[0] == 'node': vs.append(leaves_and_eval(sr[1], asg))
            elif sr[0] == 'none': vs.append(0)
            else: vs.append(asg.setdefault(('ext', sr[1]), random.getrandbits(1)))
        v = 1 - (vs[0] & vs[1])
    memo[i] = v; return v
def cone(i, seen=None):
    seen = set() if seen is None else seen
    st = [i]; leaves = set(); nodes = 0
    while st:
        k = st.pop()
        if k in seen: continue
        seen.add(k)
        if kinds[k] == 1: leaves.add(('dff', k)); continue
        nodes += 1
        for pin in (0, 1):
            sr = src_of(k, pin)
            if sr[0] == 'node': st.append(sr[1])
            elif sr[0] == 'other': leaves.add(('ext', sr[1]))
    return leaves, nodes
def equivalent(a, b, trials=3000):
    la, na = cone(a); lb, nb = cone(b)
    diff = 0
    for _ in range(trials):
        asg = {}; memo.clear(); va = leaves_and_eval(a, asg); memo.clear()
        # b with the same leaves
        asg2 = dict(asg); memo.clear(); vb = leaves_and_eval(b, asg2)
        # asg2 may have added leaves for b not in a: they're random, fine
        if va != vb: diff += 1
    return len(la), na, len(lb), nb, diff
cases = {'m_3584_1': [(4275, (1269, 1333, 1474, 32))], 'm_3078_4': [(3797, (959, 967, 996, 32))],
         'm_2554_7': [(3171, (161, 261, 370, 32)), (3172, (371, 355, 372, 31))], 'm_2506_4': [(3100, (191, 195, 300, 31))]}
for name, lst in cases.items():
    print('==', name)
    for idx, (ox, nx, dx, dy) in lst:
        so, sn, d = (ox - 7) // 2, (nx - 7) // 2, (dx - 6) // 2
        pin = dy - 31
        print(f'  cmd #{idx}: wire into node {d} pin {"AB"[pin]} ({region(d)}, kind {"NAND" if kinds[d]==0 else "DFF"}): was node {so} ({region(so)}, {"NAND" if kinds[so]==0 else "DFF"}), now node {sn} ({region(sn)}, {"NAND" if kinds[sn]==0 else "DFF"}); EG distance {d-so} -> {d-sn}')
        print('   neighbours of old src inputs', src_of(so, 0), src_of(so, 1), ' new src inputs', src_of(sn, 0), src_of(sn, 1))
        print('   cone leaves/nodes old', cone(so)[0].__len__(), cone(so)[1], 'new', cone(sn)[0].__len__(), cone(sn)[1], ' random-state equivalence (leaves_old, nodes_old, leaves_new, nodes_new, mismatches/3000):', equivalent(so, sn))
