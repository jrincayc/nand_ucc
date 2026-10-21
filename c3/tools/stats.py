import sys, collections, math
sys.path[:0] = ['tools']; import lay
L = lay.read_lay(sys.argv[1])
def moves(pts):
    ops = []
    for a, b in zip(pts, pts[1:]):
        if a[2] != b[2]: ops.append(('v',))
        else:
            dx, dy = b[0] - a[0], b[1] - a[1]
            d = 'R' if dx > 0 else 'L' if dx < 0 else 'D' if dy > 0 else 'U'
            ops.append((d, abs(dx) + abs(dy)))
    return ops
nseg = collections.Counter(); lens = collections.Counter(); first = collections.Counter(); vi = collections.Counter(); ops_tot = 0
tot = 0
for who, late, drv, pts in L.sinks:
    ops = moves(pts); ops_tot += len(ops)
    nseg[len([o for o in ops if o[0] != 'v'])] += 1; vi[len([o for o in ops if o[0] == 'v'])] += 1
    for o in ops:
        if o[0] != 'v': lens[o[1]] += 1
    first[pts[0][2]] += 1
print('sinks', len(L.sinks), 'ops', ops_tot, 'avg ops/sink %.2f' % (ops_tot / len(L.sinks)))
print('segments/path', sorted(nseg.items())); print('vias/path', sorted(vi.items())); print('first layer', first)
print('seg len hist', sorted(lens.items())[:40], 'max', max(lens), 'n>31', sum(v for k, v in lens.items() if k > 31), 'n>63', sum(v for k, v in lens.items() if k > 63))
# entropy of a plausible symbol: (dir,len<=15) / via / end
sym = collections.Counter()
for who, late, drv, pts in L.sinks:
    for o in moves(pts): sym[o if o[0] == 'v' else (o[0], min(o[1], 16))] += 1
    sym['end'] += 1
N = sum(sym.values()); H = -sum(c / N * math.log2(c / N) for c in sym.values())
print('symbols', len(sym), 'total', N, 'entropy %.2f bits -> %.0f bytes' % (H, N * H / 8))
