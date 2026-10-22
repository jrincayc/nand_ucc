#!/usr/bin/env python3
"""rowchan_model.py NL -- ESTIMATE of a row-and-channel layout: the strip order folded into R rows (serpentine), one trunk per net in the channel
next to its median row, vertical feedthrough columns for pins in other rows.  Prints width/height/area per R.  Model only (no layout is built)."""
import sys, collections
nl = [l.split() for l in open(sys.argv[1]) if l.startswith('n ')]
N = len(nl); P = 3          # gate pitch in columns (as strip.py)
pins = collections.defaultdict(list)    # net -> list of node idx (pins incl. driver)
for t in nl:
    k = int(t[1]); pins[k].append(k)
    for s in t[3:5]:
        if s.startswith('n') and s[1:].split('@')[0].isdigit(): pins[int(s[1:].split('@')[0])].append(k)
nets = [v for v in pins.values() if len(v) > 1]
print('nodes', N, 'multi-pin nets', len(nets), 'pins', sum(len(v) for v in nets))
for R in (8, 12, 16, 20, 24, 32, 40, 48):
    cols = -(-N // R)
    def pos(k):
        r = k // cols; c = k % cols
        if r % 2: c = cols - 1 - c
        return r, c
    dens = [collections.Counter() for _ in range(R + 1)]   # channel -> column -> trunks
    feed = [0] * (R + 1); trunks = [[] for _ in range(R + 1)]
    for v in nets:
        ps = [pos(k) for k in v]; rows = sorted(r for r, c in ps); med = rows[len(rows) // 2]
        ch = med                                   # channel above row med
        cs = [c for r, c in ps]; lo, hi = min(cs), max(cs)
        trunks[ch].append((lo, hi))
        for r, c in ps:
            for g in range(min(r + 1, ch), max(r + 1, ch)): feed[g] += 1   # pin must cross the gaps between its row and the channel (rows' own gaps)
    track = []
    for ch in range(R + 1):
        ev = collections.Counter()
        for lo, hi in trunks[ch]: ev[lo] += 1; ev[hi + 1] -= 1
        d = m = 0
        for x in sorted(ev): d += ev[x]; m = max(m, d)
        track.append(m)
    W = cols * P + max(feed) // R + 1 if False else cols * P + (max(feed) * 1)
    # feedthroughs: spread over each row's gaps; one column per crossing, worst row
    fw = max(feed); W = cols * P + fw
    H = R * 3 + sum(track)
    print(f'R={R:3d} cols={cols:4d} maxdensity={max(track):4d} sumdensity={sum(track):5d} feedthrough cols(worst row)={fw:5d}  W={W:6d} H={H:5d} area={W*H:9d} aspect={max(W,H)/min(W,H):.1f}')
