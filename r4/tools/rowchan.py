#!/usr/bin/env python3
"""rowchan.py NL OUT.lay [R [Z]] -- reference "row and channel" place and route for R4 (squarish board).  Reference for the in-world version.

Placement: the netlist order is folded serpentine into R rows (row r holds nodes r*cols .. (r+1)*cols-1, odd rows reversed).  A gate occupies three
columns (gap/B column X, A column X+1, Y column X+2) as in strip.py.  Every Z gate columns a FEEDTHROUGH ZONE of w columns (lanes) is inserted in
all rows (same x everywhere).  ROM, ARM and RAM stand to the right of the gate area, on the baseline of the lowest row (R-1).
Routing: every row r has one single-sided channel BELOW it (y smaller); each pin reaches the channel of its own row by a layer-1 vertical stub in its
own column; trunks are layer-0 tracks (left-edge, density-optimal because there are no vertical constraints).  A net with pins in several rows gets one
LANE: a layer-1 vertical in a zone column, from the trunk of its lowest channel to the trunk of its highest channel; the trunk of every channel it
uses is extended to the lane column and joined by a via.  Lanes are shared by nets with disjoint channel ranges (interval colouring per zone).
Normative rules: integer arithmetic only; nets are processed in the order of nk() (gate outputs by number, ROM bits, RAM-out bits); lane colouring sorted by (zone, cmin, cmax, nk); left-edge sorted by (lo, hi, nk); sinks of a net in order (late, row distance, column distance, pin list index).
Output: the same .lay format as strip.py (so tests/validate_layout.py builds and checks it in rndp)."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE]
import lay

P = 3
KR = {'n': 0, 'rom': 1, 'ramo': 2}


def nk(key):
    """canonical integer sort key of a net: gate outputs first (by number), then ROM data bits, then RAM data-out bits"""
    return (KR[key[0]], key[1])


def layout(nl, R=40, Z=0, rc=None):
    """rc: optional list of (row, col) per node (module-level placement); default is the serpentine fold of the netlist order"""
    N = len(nl.nodes); Rm = nl.rom; Q = nl.ram
    cols = (max(c for r, c in rc) + 1) if rc else -(-N // R)
    if not Z: Z = max(3, cols // 10)
    nz = max(0, (cols - 1) // Z)
    def node_rc(k):
        if rc: return rc[k]
        r = k // cols; j = k % cols
        return r, (cols - 1 - j if r % 2 else j)
    # ---- pins with LOGICAL columns first (to choose zones) -> then physical
    # pin = dict(net, role, row, lcol, off, stub(builder f(x0)->(col, pts_rel)), late, who)
    def netof(tok):
        b = tok.split('@')[0]
        return ('ramo', int(b[4:])) if b.startswith('ramo') else ('rom', int(b[3:])) if b.startswith('rom') else ('n', int(b[1:]))
    pinl = []      # (netkey, role, row, anchor, kind, args, late, who)   anchor = logical x for zone choice
    for k, (kind, ins) in enumerate(nl.nodes):
        r, j = node_rc(k)
        pinl.append((('n', k), 'drv', r, 3 * j, 'gY', (r, j), 0, f'n{k}'))
        for p, s in enumerate(ins):
            if s == 'open': continue
            late = 2 if '@2' in s else 1 if '@1' in s else 0
            pinl.append((netof(s), 'snk', r, 3 * j, 'gA' if p == 0 else 'gB', (r, j), late, f'n{k}.{p}'))
    # parts: logical anchors to the right of the gates
    base = 3 * cols + 4
    pb = {}; xs = base
    def block(name, wl, wr):
        nonlocal xs
        x = xs + wl + 1; pb[name] = x; xs = x + 2 + wr + 1
    block('rom', Rm, 8); block('arm', 5, 8); block('ram', Q + 9, 8)
    def partpins(emit):
        xr, xa, xm = pb['rom'], pb['arm'], pb['ram']
        for j in range(8): emit(('rom', j), 'drv', 'prom', (j,), 0, f'rom{j}', xr)
        for c in range(8): emit(('ramo', c), 'drv', 'pramo', (c,), 0, f'ramo{c}', xm)
        for name, s in nl.ports:
            late = 2 if '@2' in s else 1 if '@1' in s else 0
            if name.startswith('rom_addr'): emit(netof(s), 'snk', 'pleft', ('rom', int(name[8:])), late, name, xr)
            elif name.startswith('arm_addr'): emit(netof(s), 'snk', 'pleft', ('arm', int(name[8:])), late, name, xa)
            elif name == 'arm_en': emit(netof(s), 'snk', 'pleft', ('arm', 4), late, name, xa)
            elif name.startswith('wdata'): emit(netof(s), 'snk', 'pw', ('arm', int(name[5:])), late, name, xa)
            elif name.startswith('ram_addr'): emit(netof(s), 'snk', 'pleft', ('ram', int(name[8:])), late, name, xm)
            elif name == 'ram_we': emit(netof(s), 'snk', 'pleft', ('ram', Q), late, name, xm)
            elif name.startswith('ram_din'): emit(netof(s), 'snk', 'pleft', ('ram', Q + 1 + int(name[7:])), late, name, xm)
            else: raise KeyError(name)
    def e1(key, role, kind, args, late, who, x): pinl.append((key, role, R - 1, x, kind, args, late, who))
    partpins(e1)
    # ---- nets, rows, lanes
    nets = {}
    for pn in pinl: nets.setdefault(pn[0], []).append(pn)
    zone_of = {}; lanes = {}       # net -> (zone, lane idx);  zone -> list of lane end-channels
    need = []
    for key, ps in sorted(nets.items(), key=lambda kv: nk(kv[0])):
        if not any(p[1] == 'snk' for p in ps): continue
        rows = [p[2] for p in ps]; cmin, cmax = min(rows), max(rows)
        if cmin == cmax: continue
        if nz == 0: raise SystemExit('no zones: reduce Z')
        # zone with the least total trunk extension over the rows the net uses; all arithmetic in half-columns (integers), ties -> lowest zone
        byrow = {}
        for p in ps: byrow.setdefault(p[2], []).append(p[3])
        best = None
        for uu in range(nz):
            xz2 = 2 * P * (uu + 1) * Z - 3
            c = sum(max(0, 2 * min(v) - xz2, xz2 - 2 * max(v)) for v in byrow.values())
            if best is None or c < best[0]: best = (c, uu)
        u = best[1]
        need.append((u, cmin, cmax, nk(key), key))
    need.sort()
    zl = {u: [] for u in range(nz)}; lane_idx = {}
    for u, cmin, cmax, _, key in need:
        L = zl[u]
        for i, e in enumerate(L):
            if e < cmin: L[i] = cmax; lane_idx[key] = (u, i); break
        else: L.append(cmax); lane_idx[key] = (u, len(L) - 1)
    zw = [max(1, len(zl[u])) for u in range(nz)]
    # ---- physical x
    def gx(j):
        return P * j + sum(zw[u] for u in range(nz) if (u + 1) * Z <= j)
    def zx(u, i): return P * (u + 1) * Z + sum(zw[v] for v in range(u)) + i
    Wg = gx(cols - 1) + P
    xs = Wg + 4; pb = {}
    block('rom', Rm, 8); block('arm', 5, 8); block('ram', Q + 9, 8)
    W = xs
    xr, xa, xm = pb['rom'], pb['arm'], pb['ram']
    # ---- physical pins: (col, stub points relative to row base y)
    pins = {}
    def padd(key, role, row, col, st, late, who):
        d = pins.setdefault(key, dict(driver=None, sinks=[]))
        ent = (row, col, st, late, who)
        if role == 'drv': d['driver'] = ent
        else: d['sinks'].append(ent)
    def left(x, row): return (x - 1 - row, [(x, row, 0), (x - 1 - row, row, 0), (x - 1 - row, row, 1)])
    def pphys(key, role, row, kind, args, late, who):
        if kind == 'gY': r, j = args; X = gx(j); padd(key, role, r, X + 2, [(X + 2, 0, 1)], late, who)
        elif kind == 'gA': r, j = args; X = gx(j); padd(key, role, r, X + 1, [(X + 1, 0, 1)], late, who)
        elif kind == 'gB': r, j = args; X = gx(j); padd(key, role, r, X, [(X + 1, 1, 0), (X, 1, 0), (X, 1, 1)], late, who)
        elif kind == 'prom': j, = args; padd(key, role, R - 1, xr + 2 + j, [(xr + 1, j, 0), (xr + 2 + j, j, 0), (xr + 2 + j, j, 1)], late, who)
        elif kind == 'pramo': c, = args; padd(key, role, R - 1, xm + 2 + c, [(xm + 1, c, 0), (xm + 2 + c, c, 0), (xm + 2 + c, c, 1)], late, who)
        elif kind == 'pleft': x, rw = pb[args[0]], args[1]; c, st = left(x, rw); padd(key, role, R - 1, c, st, late, who)
        elif kind == 'pw': x, rw = pb[args[0]], args[1]; c = x + 2 + rw; padd(key, role, R - 1, c, [(x + 1, rw, 0), (c, rw, 0), (c, rw, 1)], late, who)
    for key, role, row, anchor, kind, args, late, who in pinl: pphys(key, role, row, kind, args, late, who)
    # ---- channel intervals
    laneL = {}
    for key, (u, i) in lane_idx.items(): laneL[key] = zx(u, i)
    chan = {}       # (net, c) -> [lo, hi]
    for key, d in pins.items():
        if not d['sinks']: continue
        ents = [d['driver']] + d['sinks']
        for row, col, st, late, who in ents:
            iv = chan.setdefault((key, row), [col, col]); iv[0] = min(iv[0], col); iv[1] = max(iv[1], col)
        if key in laneL:
            for (k2, c), iv in chan.items():
                if k2 == key: iv[0] = min(iv[0], laneL[key]); iv[1] = max(iv[1], laneL[key])
    # left-edge per channel
    bych = {}
    for (key, c), (lo, hi) in chan.items(): bych.setdefault(c, []).append((lo, hi, nk(key), key))
    track = {}; T = [0] * R
    for c in range(R):
        ends = []
        for lo, hi, _, key in sorted(bych.get(c, [])):
            for t, e in enumerate(ends):
                if e < lo: ends[t] = hi; track[(key, c)] = t; break
            else: ends.append(hi); track[(key, c)] = len(ends) - 1
        T[c] = len(ends)
    Y = [0] * R; Y[0] = T[0] + 1
    for r in range(1, R): Y[r] = Y[r - 1] + 3 + T[r]
    hmax = max(2, Rm, Q + 9, 9); H = Y[R - 1] + hmax
    out = [f'dims {W} {H} px {P} py 2 cols {cols} rows {R}']
    out.append(f'part rom {xr} {Y[R-1]} 0 {Rm}'); out.append(f'part arm {xa} {Y[R-1]} 0 0')
    if Q: out.append(f'part ram {xm} {Y[R-1]} 0 {Q}')
    for k, (kind, ins) in enumerate(nl.nodes):
        r, j = node_rc(k); out.append(f'site {k} {gx(j) + 1} {Y[r]} {kind} {k}')
    # ---- emit
    ntrk = 0
    for key, d in sorted(pins.items(), key=lambda kv: nk(kv[0])):
        if not d['sinks']: continue
        drow, dcol, dst, _, dwho = d['driver']; dY = Y[drow]
        L = laneL.get(key); ty = {c: Y[c] - 1 - track[(key, c)] for (k2, c) in chan if k2 == key}
        trunk = {}; span = None; first = True
        order = [e for _, e in sorted(enumerate(d['sinks']), key=lambda ie: (ie[1][3], abs(ie[1][0] - drow), abs(ie[1][1] - dcol), ie[0]))]
        for row, col, st, late, who in order:
            c = row; pts = [(cc, Y[row] + rr, l) for cc, rr, l in st] + [(col, ty[c], 1), (col, ty[c], 0)]
            dstub = [(cc, dY + rr, l) for cc, rr, l in reversed(dst)]
            if first:
                first = False
                if c == drow:
                    if dcol != col: pts += [(dcol, ty[c], 0), (dcol, ty[c], 1)]
                    pts += dstub; trunk[c] = [min(col, dcol), max(col, dcol)]
                else:
                    pts += [(L, ty[c], 0), (L, ty[c], 1), (L, ty[drow], 1), (L, ty[drow], 0), (dcol, ty[drow], 0), (dcol, ty[drow], 1)] + dstub
                    trunk[c] = [min(col, L), max(col, L)]; trunk[drow] = [min(dcol, L), max(dcol, L)]; span = (min(ty[c], ty[drow]), max(ty[c], ty[drow]))
            elif c in trunk:
                lo, hi = trunk[c]
                if col < lo: pts.append((lo, ty[c], 0))
                elif col > hi: pts.append((hi, ty[c], 0))
                trunk[c] = [min(lo, col), max(hi, col)]
            else:
                pts += [(L, ty[c], 0), (L, ty[c], 1)]
                if span is None:
                    pts += [(L, ty[drow], 1), (L, ty[drow], 0)]
                    lo, hi = trunk[drow]
                    if L < lo: pts.append((lo, ty[drow], 0))
                    elif L > hi: pts.append((hi, ty[drow], 0))
                    trunk[drow] = [min(lo, L), max(hi, L)]; span = (min(ty[c], ty[drow]), max(ty[c], ty[drow]))
                else:
                    if ty[c] < span[0]: pts.append((L, span[0], 1)); span = (ty[c], span[1])
                    elif ty[c] > span[1]: pts.append((L, span[1], 1)); span = (span[0], ty[c])
                trunk[c] = [min(col, L), max(col, L)]
            out.append(f'sink {who} - {late} {dwho} : ' + ' '.join(f'{x},{y},{l}' for x, y, l in pts))
    return '\n'.join(out) + '\n', dict(W=W, H=H, tracks=sum(T), maxtrack=max(T), lanes=sum(zw), nets=len(chan), area=W * H, R=R, Z=Z, cols=cols, _chan=chan, _track=track, _T=T)


if __name__ == '__main__':
    nl = lay.read_nl(sys.argv[1]); R = int(sys.argv[3]) if len(sys.argv) > 3 else 40; Z = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    text, st = layout(nl, R, Z); open(sys.argv[2], 'w').write(text); print(st)
