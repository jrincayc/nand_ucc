import pickle, collections, sys
from arm import Arm
def merge(S):
    g = collections.defaultdict(list)
    for l, x0, y0, x1, y1 in S:
        if x0 == x1: g[(l, 'v', x0)].append((min(y0, y1), max(y0, y1)))
        else: g[(l, 'h', y0)].append((min(x0, x1), max(x0, x1)))
    out = set()
    for k, iv in g.items():
        iv.sort(); a, b = iv[0]
        for p, q in iv[1:]:
            if p <= b: b = max(b, q)
            else: out.add(k + (a, b)); a, b = p, q
        out.add(k + (a, b))
    return out
def split(cs):
    pl = collections.Counter(c for c in cs if c[0] == 'place'); vi = collections.Counter(c for c in cs if c[0] == 'via')
    tr = merge([c[1:] for c in cs if c[0] == 'track']); return pl, vi, tr
if __name__ == '__main__':
    parent, child = pickle.load(open('/tmp/e4_parent.pkl', 'rb'))
    b = open(sys.argv[1], 'rb').read(); arm = Arm()
    for i in range(0, len(b), 2): arm.write(b[i], b[i + 1])
    g, e = split(arm.cmds), split(child)
    print('faults', arm.faults, 'parts equal', g[0] == e[0], 'vias equal', g[1] == e[1], 'wires equal', g[2] == e[2], '| parts', sum(e[0].values()), 'vias', sum(e[1].values()), 'wire runs', len(e[2]))
    for nm, i in (('parts', 0), ('vias', 1)):
        print(nm, 'missing', list((e[i] - g[i]).items())[:3], 'extra', list((g[i] - e[i]).items())[:3])
    print('wires missing', list(e[2] - g[2])[:3], 'extra', list(g[2] - e[2])[:3])
