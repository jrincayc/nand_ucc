#!/usr/bin/env python3
"""huff_pack.py LAY_DATA_IN OUT -- replace the raw path byte stream (lay_paths .. lay_port_starts) by a canonical-Huffman bitstream + tables (hcnt, hsym)."""
import re, sys, collections, heapq
t = open(sys.argv[1]).read()
i = t.index('lay_paths:'); j = t.index('lay_port_starts:')
bs = []
for l in t[i:j].split('\n'):
    l = l.split('//')[0]
    m = re.match(r'\s*\.byte\s+(.*)', l)
    if m: bs += [int(x, 0) for x in m.group(1).split(',')]
c = collections.Counter(bs)
h = [(v, k, [k]) for k, v in c.items()]; heapq.heapify(h); L = collections.Counter(); n = 1000
while len(h) > 1:
    a = heapq.heappop(h); b = heapq.heappop(h)
    for k in a[2] + b[2]: L[k] += 1
    heapq.heappush(h, (a[0] + b[0], n, a[2] + b[2])); n += 1
ml = max(L.values()); assert ml <= 15
cnt = [0] * (ml + 1)
for s, l in L.items(): cnt[l] += 1
syms = sorted(L, key=lambda s: (L[s], s))
codes = {}; code = 0
for ln in range(1, ml + 1):
    for s in syms:
        if L[s] == ln: codes[s] = (code, ln); code += 1
    code <<= 1
bits = []
for b in bs:
    cd, ln = codes[b]; bits += [(cd >> (ln - 1 - k)) & 1 for k in range(ln)]
while len(bits) % 8: bits.append(0)
out = bytes(int(''.join(map(str, bits[k:k + 8])), 2) for k in range(0, len(bits), 8))
# self-check: decode as the Hack routine does (8-bit d)
def dec(stream, nsym):
    bp = 0; res = []; dm = 0
    for _ in range(nsym):
        d = 0; idx = 0
        for ln in range(1, ml + 1):
            bit = (stream[bp >> 3] >> (7 - (bp & 7))) & 1; bp += 1
            d = 2 * d + bit; dm = max(dm, d)
            if d < cnt[ln]: res.append(syms[idx + d]); break
            idx += cnt[ln]; d -= cnt[ln]
    return res, dm
res, dm = dec(out, len(bs)); assert res == bs and dm < 128
lines = ['lay_paths:                                    // Huffman bitstream of the path bytes (see huff_pack.py)']
for k in range(0, len(out), 16): lines.append('    .byte ' + ', '.join(str(x) for x in out[k:k + 16]))
lines.append('hcnt:                                         // codes per length 1..%d' % ml)
lines.append('    .byte ' + ', '.join(str(x) for x in cnt[1:]))
lines.append('hsym:                                         // symbols in canonical order')
for k in range(0, len(syms), 16): lines.append('    .byte ' + ', '.join(str(x) for x in syms[k:k + 16]))
head = t[:i]; tail = t[j:]
tail = tail.replace('lay_port_starts:', 'lay_port_starts:', 1)
open(sys.argv[2], 'w').write(head + '\n'.join(lines) + '\n' + tail)
print('symbols', len(bs), 'bitstream bytes', len(out), 'tables', ml + len(syms), 'maxlen', ml, 'max d', dm)
