#!/usr/bin/env python3
"""profile_report.py PROFILE ROM_LST -- instructions per source file (from rvemu --profile and the assembler listing) and the RAM working set (bytes read / written)."""
import re, sys, collections
base = 1 << 18
src = {}                                   # address -> source file for every instruction/data line
for ln in open(sys.argv[2]):
    f = [x.strip() for x in ln.rstrip('\n').split('|')]
    if len(f) < 4: continue
    m = re.match(r'([0-9A-F]+)\s+((?:[0-9A-F]{2} ?)+)$', f[0])
    if m: src[int(m.group(1), 16)] = f[1].split(':')[0]
cnt = collections.Counter(); ram = []; tot = 0
for l in open(sys.argv[1]):
    w = l.split()
    if w[0] == 'pc':
        a = int(w[1], 16); n = int(w[2]); tot += n
        while a not in src and a > base: a -= 2
        cnt[src.get(a, '?')] += n
    else: ram.append((int(w[1], 16), int(w[2], 16), int(w[3])))
print(f'instructions {tot}')
for f, n in cnt.most_common(): print(f'  {f:16s} {n:10d}  {100 * n / tot:5.1f} %')
r = sum(h - l + 1 for l, h, fl in ram if fl & 1); w_ = sum(h - l + 1 for l, h, fl in ram if fl & 2); both = sum(h - l + 1 for l, h, fl in ram)
print(f'RAM bytes touched {both}  (read {r}, written {w_}); highest touched address {max(h for l, h, _ in ram):#x}')
for lo, hi, name in ((0, 0x400, 'registers/vars 0-0x3FF'), (0x400, 0x8000, '0x400-0x7FFF'), (0x8000, 0x10000, '0x8000-0xFFFF'), (0x10000, 0x20000, '0x10000-0x1FFFF'), (0x20000, 0x40000, '0x20000-0x3FFFF')):
    t = sum(max(0, min(h, hi - 1) - max(l, lo) + 1) for l, h, _ in ram); print(f'  {name:26s} {t:8d} bytes touched')
