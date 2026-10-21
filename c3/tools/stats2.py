import sys, collections, math, heapq
sys.path[:0] = ['tools']; import lay
L = lay.read_lay(sys.argv[1])
def segs(pts):
    out = []; layer = pts[0][2]; via = 1 if layer == 1 else 0; i = 0
    cur = pts[0]
    for b in pts[1:]:
        if b[2] != cur[2]: via = 1; cur = b; continue
        dx, dy = b[0] - cur[0], b[1] - cur[1]
        d = 0 if dx > 0 else 1 if dx < 0 else 2 if dy > 0 else 3
        out.append([via, d, abs(dx) + abs(dy)]); via = 0; cur = b
    return out
sym = collections.Counter(); raw = 0; longs = 0; nseg = 0
for who, late, drv, pts in L.sinks:
    ss = segs(pts); nseg += len(ss)
    for k, (v, d, n) in enumerate(ss):
        last = 1 if k == len(ss) - 1 else 0
        if n > 15: longs += 1; n = 0
        sym[(last, v, d, n)] += 1
N = sum(sym.values()); H = -sum(c / N * math.log2(c / N) for c in sym.values())
# huffman code lengths
h = [(c, i, [s]) for i, (s, c) in enumerate(sym.items())]; heapq.heapify(h); depth = collections.Counter(); cnt = len(h)
while len(h) > 1:
    a = heapq.heappop(h); b = heapq.heappop(h)
    for s in a[2] + b[2]: depth[s] += 1
    cnt += 1; heapq.heappush(h, (a[0] + b[0], cnt, a[2] + b[2]))
bits = sum(sym[s] * depth[s] for s in sym)
print('segments', nseg, 'longs(>15)', longs, 'distinct symbols', len(sym), 'entropy %.2f bits/seg' % H, 'huffman %.2f bits/seg' % (bits / N), 'max code len', max(depth.values()))
print('v1 bytes (1/seg + long ext):', nseg + longs, ' huffman bytes: %.0f + long raw %d + table %d' % (bits / 8, longs, len(sym)))
