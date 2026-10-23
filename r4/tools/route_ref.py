#!/usr/bin/env python3
"""route_ref.py -- array-style integer reference of the row-and-channel router (same results as rowchan.layout + lay.commands, but written the way the RV32EC
kernel is written: flat arrays, counting sorts, no dictionaries, no floats).  route(nl, order, R, Z) -> (commands, info); `info` holds the intermediate arrays
that the assembly stages are compared with.

Input: the netlist (lay.read_nl) and `order` (rank -> gate, from place_ref.order).  Fold: rank -> row = rank // cols, j = rank % cols, column j (odd rows reversed).
Stages: F fold | N nets (sink lists by counting sort) | Z zone and lane per net | X physical x | V channel intervals | T tracks (left edge) | E emission.
"""
import sys, os
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]
import place_ref

P = 3
KP = dict(gY=0, gA=1, gB=2, prom=3, pramo=4, pleft=5, pw=6)


def late_of(tok):
    return 2 if '@2' in tok else 1 if '@1' in tok else 0


def route(nl, order, R=22, Z=14):
    N = len(nl.nodes); NN = N + 16; Rm = nl.rom; Q = nl.ram
    info = {}
    # ---- F: fold
    cols = -(-N // R); ROW = [0] * N; COL = [0] * N
    for rank, k in enumerate(order):
        r = rank // cols; j = rank % cols; ROW[k] = r; COL[k] = cols - 1 - j if r % 2 else j
    cols = max(COL) + 1
    nz = max(0, (cols - 1) // Z)
    # ---- ports as (kind, index, src net id, late)
    ports = []
    for name, tok in nl.ports:
        d = place_ref.net_id(tok, N)
        if name.startswith('rom_addr'): kd, a = 'rom', int(name[8:]); k = 0
        elif name.startswith('arm_addr'): kd, a = 'arm', int(name[8:]); k = 0
        elif name == 'arm_en': kd, a = 'arm', 4; k = 0
        elif name.startswith('wdata'): kd, a = 'arm', int(name[5:]); k = 1
        elif name.startswith('ram_addr'): kd, a = 'ram', int(name[8:]); k = 0
        elif name == 'ram_we': kd, a = 'ram', Q; k = 0
        elif name.startswith('ram_din'): kd, a = 'ram', Q + 1 + int(name[7:]); k = 0
        else: raise KeyError(name)
        ports.append((kd, a, k, d, late_of(tok)))             # k = 1: right-hand pin (wdata) else left
    # logical part anchors (zone choice only)
    base = 3 * cols + 4; xs = base; pbl = {}
    for name, wl, wr in (('rom', Rm, 8), ('arm', 5, 8), ('ram', Q + 9, 8)):
        x = xs + wl + 1; pbl[name] = x; xs = x + 2 + wr + 1
    # ---- N: sink lists per net, in pin-list order (gates ascending, input 0 then 1, then ports in file order)
    cnt = [0] * (NN + 1)
    sinks = []                                                # (net, record, late)   record: gate input 2*k+p, port 0x8000+i
    for k, (kind, ins) in enumerate(nl.nodes):
        for p, tok in enumerate(ins):
            d = place_ref.net_id(tok, N)
            if d is None: continue
            sinks.append((d, 2 * k + p, late_of(tok)))
    for i, (kd, a, k, d, late) in enumerate(ports):
        if d is not None: sinks.append((d, 0x8000 + i, late))
    for d, rec, late in sinks: cnt[d] += 1
    NOFF = [0] * (NN + 1); s = 0
    for n in range(NN): NOFF[n] = s; s += cnt[n]
    NOFF[NN] = s; fill = NOFF[:]; NSNK = [0] * s
    for d, rec, late in sinks: NSNK[fill[d]] = rec; fill[d] += 1
    info['NOFF'] = NOFF; info['NSNK'] = NSNK
    def sink_row(rec): return ROW[rec >> 1] if rec < 0x8000 else R - 1
    def sink_anchor(rec):
        if rec < 0x8000: return 3 * COL[rec >> 1]
        kd = ports[rec - 0x8000][0]; return pbl[kd]
    def drv_row(n): return ROW[n] if n < N else R - 1
    def drv_anchor(n):
        if n < N: return 3 * COL[n]
        return pbl['rom'] if n < N + 8 else pbl['ram']
    # ---- Z: zone per net, lanes by (zone, cmin, cmax, net)
    ZONE = [0] * NN; CMIN = [0] * NN; CMAX = [0] * NN; LIDX = [255] * NN; lane_nets = []
    for n in range(NN):
        if NOFF[n + 1] == NOFF[n]: continue
        rmin = [None] * R; rmax = [None] * R
        pr = [(drv_row(n), drv_anchor(n))] + [(sink_row(rec), sink_anchor(rec)) for rec in NSNK[NOFF[n]:NOFF[n + 1]]]
        cmin = min(r for r, a in pr); cmax = max(r for r, a in pr)
        CMIN[n] = cmin; CMAX[n] = cmax
        if cmin == cmax: continue
        for r, a in pr:
            if rmin[r] is None or a < rmin[r]: rmin[r] = a
            if rmax[r] is None or a > rmax[r]: rmax[r] = a
        best = None
        for u in range(nz):
            xz2 = 2 * P * (u + 1) * Z - 3; c = 0
            for r in range(R):
                if rmin[r] is None: continue
                c += max(0, 2 * rmin[r] - xz2, xz2 - 2 * rmax[r])
            if best is None or c < best[0]: best = (c, u)
        ZONE[n] = best[1]; lane_nets.append(n)
    # counting sort of lane_nets by (zone, cmin, cmax), stable in net order
    NB = max(1, nz) * R * R; bc = [0] * (NB + 1)
    def bucket(n): return (ZONE[n] * R + CMIN[n]) * R + CMAX[n]
    for n in lane_nets: bc[bucket(n) + 1] += 1
    for b in range(NB): bc[b + 1] += bc[b]
    SORTED = [0] * len(lane_nets)
    for n in lane_nets: SORTED[bc[bucket(n)]] = n; bc[bucket(n)] += 1
    lend = [[] for _ in range(max(1, nz))]
    for n in SORTED:
        u = ZONE[n]; L = lend[u]
        for i in range(len(L)):
            if L[i] < CMIN[n]: L[i] = CMAX[n]; LIDX[n] = i; break
        else: L.append(CMAX[n]); LIDX[n] = len(L) - 1
    ZW = [max(1, len(lend[u])) for u in range(nz)]
    info['ZONE'] = ZONE; info['LIDX'] = LIDX; info['ZW'] = ZW; info['SORTED'] = SORTED
    # ---- X: physical columns
    GXT = [0] * cols
    for j in range(cols):
        GXT[j] = P * j + sum(ZW[u] for u in range(nz) if (u + 1) * Z <= j)
    def zx(u, i): return P * (u + 1) * Z + sum(ZW[:u]) + i
    Wg = GXT[cols - 1] + P; xs = Wg + 4; pb = {}
    for name, wl, wr in (('rom', Rm, 8), ('arm', 5, 8), ('ram', Q + 9, 8)):
        x = xs + wl + 1; pb[name] = x; xs = x + 2 + wr + 1
    W = xs; xr, xa, xm = pb['rom'], pb['arm'], pb['ram']
    info['GXT'] = GXT; info['pb'] = pb; info['W'] = W; info['ROW'] = ROW; info['COL'] = COL; info['cols'] = cols; info['nz'] = nz; info['pbl'] = pbl
    info['CMINA'] = CMIN; info['CMAXA'] = CMAX; info['LANE_ORDER'] = SORTED
    # pin description -> (row, col, stub) ; stub = list of (x, yrel, layer)
    def left(x, rw): return (x - 1 - rw, [(x, rw, 0), (x - 1 - rw, rw, 0), (x - 1 - rw, rw, 1)])
    def sink_pin(rec):
        if rec < 0x8000:
            k = rec >> 1; p = rec & 1; X = GXT[COL[k]]
            if p == 0: return ROW[k], X + 1, [(X + 1, 0, 1)]
            return ROW[k], X, [(X + 1, 1, 0), (X, 1, 0), (X, 1, 1)]
        kd, a, side, d, late = ports[rec - 0x8000]
        if side == 1:
            x = pb[kd]; c = x + 2 + a; return R - 1, c, [(x + 1, a, 0), (c, a, 0), (c, a, 1)]
        c, st = left(pb[kd], a); return R - 1, c, st
    def drv_pin(n):
        if n < N: X = GXT[COL[n]]; return ROW[n], X + 2, [(X + 2, 0, 1)]
        if n < N + 8: j = n - N; return R - 1, xr + 2 + j, [(xr + 1, j, 0), (xr + 2 + j, j, 0), (xr + 2 + j, j, 1)]
        c = n - N - 8; return R - 1, xm + 2 + c, [(xm + 1, c, 0), (xm + 2 + c, c, 0), (xm + 2 + c, c, 1)]
    def laneX(n):
        return zx(ZONE[n], LIDX[n]) if LIDX[n] != 255 else None
    # ---- V: channel intervals (net, row, lo, hi), contiguous per net
    IVS = [0] * (NN + 1); IV_ROW = []; IV_LO = []; IV_HI = []; iv_of = {}
    for n in range(NN):
        IVS[n] = len(IV_ROW)
        if NOFF[n + 1] == NOFF[n]: continue
        lo = [None] * R; hi = [None] * R
        pins = [drv_pin(n)] + [sink_pin(rec) for rec in NSNK[NOFF[n]:NOFF[n + 1]]]
        for r, c, st in pins:
            if lo[r] is None or c < lo[r]: lo[r] = c
            if hi[r] is None or c > hi[r]: hi[r] = c
        L = laneX(n)
        for r in range(R):
            if lo[r] is None: continue
            a, b = lo[r], hi[r]
            if L is not None: a = min(a, L); b = max(b, L)
            IV_ROW.append(r); IV_LO.append(a); IV_HI.append(b)
    IVS[NN] = len(IV_ROW); NI = len(IV_ROW)
    info['IVS'] = IVS; info['NI'] = NI
    # ---- T: left-edge tracks.  Order by (row, lo, hi, net): LSD counting sorts; the interval index order is net order already
    def csort(keys, order_in, K):
        c = [0] * (K + 1)
        for i in order_in: c[keys[i] + 1] += 1
        for b in range(K): c[b + 1] += c[b]
        out = [0] * len(order_in)
        for i in order_in: out[c[keys[i]]] = i; c[keys[i]] += 1
        return out
    o = list(range(NI)); o = csort(IV_HI, o, W + 1); o = csort(IV_LO, o, W + 1); o = csort(IV_ROW, o, R)
    TRK = [0] * NI; T = [0] * R; ends = []; cur = -1
    for i in o:
        if IV_ROW[i] != cur:
            if cur >= 0: T[cur] = len(ends)
            cur = IV_ROW[i]; ends = []
        for t in range(len(ends)):
            if ends[t] < IV_LO[i]: ends[t] = IV_HI[i]; TRK[i] = t; break
        else: ends.append(IV_HI[i]); TRK[i] = len(ends) - 1
    if cur >= 0: T[cur] = len(ends)
    Y = [0] * R; Y[0] = T[0] + 1
    for r in range(1, R): Y[r] = Y[r - 1] + 3 + T[r]
    info['TRK'] = TRK; info['T'] = T; info['Y'] = Y
    hmax = max(2, Rm, Q + 9, 9); H = Y[R - 1] + hmax; info['H'] = H
    # ---- E: commands
    cmds = []
    for k, (kind, ins) in enumerate(nl.nodes):
        cmds.append(('place', 1 if kind == 'D' else 0, GXT[COL[k]] + 1, Y[ROW[k]], 0, 0))
    cmds.append(('place', 2, xr, Y[R - 1], 0, Rm)); cmds.append(('place', 3, xa, Y[R - 1], 0, 0))
    if Q: cmds.append(('place', 4, xm, Y[R - 1], 0, Q))
    late_cmds = [[], [], []]
    for n in range(NN):
        s0, s1 = NOFF[n], NOFF[n + 1]
        if s0 == s1: continue
        drow, dcol, dst = drv_pin(n); dY = Y[drow]; L = laneX(n)
        ty = [None] * R
        for i in range(IVS[n], IVS[n + 1]): ty[IV_ROW[i]] = Y[IV_ROW[i]] - 1 - TRK[i]
        # sinks sorted by (late, row distance, column distance, index): stable insertion sort on a composite key
        keyed = []
        for rec in NSNK[s0:s1]:
            row, col, st = sink_pin(rec)
            late = late_of(nl.nodes[rec >> 1][1][rec & 1]) if rec < 0x8000 else ports[rec - 0x8000][4]
            keyed.append(((late << 19) | (abs(row - drow) << 12) | abs(col - dcol), rec, late, row, col, st))
        for a in range(1, len(keyed)):
            x = keyed[a]; b = a - 1
            while b >= 0 and keyed[b][0] > x[0]: keyed[b + 1] = keyed[b]; b -= 1
            keyed[b + 1] = x
        tlo = [None] * R; thi = [None] * R; span = None; first = True
        for _, rec, late, row, col, st in keyed:
            c = row; pts = [(cc, Y[row] + rr, l) for cc, rr, l in st] + [(col, ty[c], 1), (col, ty[c], 0)]
            dstub = [(cc, dY + rr, l) for cc, rr, l in reversed(dst)]
            if first:
                first = False
                if c == drow:
                    if dcol != col: pts += [(dcol, ty[c], 0), (dcol, ty[c], 1)]
                    pts += dstub; tlo[c] = min(col, dcol); thi[c] = max(col, dcol)
                else:
                    pts += [(L, ty[c], 0), (L, ty[c], 1), (L, ty[drow], 1), (L, ty[drow], 0), (dcol, ty[drow], 0), (dcol, ty[drow], 1)] + dstub
                    tlo[c] = min(col, L); thi[c] = max(col, L); tlo[drow] = min(dcol, L); thi[drow] = max(dcol, L)
                    span = (min(ty[c], ty[drow]), max(ty[c], ty[drow]))
            elif tlo[c] is not None:
                lo, hi = tlo[c], thi[c]
                if col < lo: pts.append((lo, ty[c], 0))
                elif col > hi: pts.append((hi, ty[c], 0))
                tlo[c] = min(lo, col); thi[c] = max(hi, col)
            else:
                pts += [(L, ty[c], 0), (L, ty[c], 1)]
                if span is None:
                    pts += [(L, ty[drow], 1), (L, ty[drow], 0)]
                    lo, hi = tlo[drow], thi[drow]
                    if L < lo: pts.append((lo, ty[drow], 0))
                    elif L > hi: pts.append((hi, ty[drow], 0))
                    tlo[drow] = min(lo, L); thi[drow] = max(hi, L); span = (min(ty[c], ty[drow]), max(ty[c], ty[drow]))
                else:
                    if ty[c] < span[0]: pts.append((L, span[0], 1)); span = (ty[c], span[1])
                    elif ty[c] > span[1]: pts.append((L, span[1], 1)); span = (span[0], ty[c])
                tlo[c] = min(col, L); thi[c] = max(col, L)
            for a, b in zip(pts, pts[1:]):
                if a[2] == b[2]: late_cmds[late].append(('track', a[2], a[0], a[1], b[0], b[1]))
                else: assert a[:2] == b[:2]; late_cmds[late].append(('via', a[0], a[1]))
    for lc in late_cmds: cmds += lc
    info['nlate'] = [len(lc) for lc in late_cmds]        # commands of late class 0 (normal), 1 (EN), 2 (RUN): the last ones in the stream
    info['W'] = W
    return cmds, info


def pack(nl, order, ram, V=None):
    """write the router inputs (SRC with late bits, KINDA, PTAB, FINAL = order, V_N, V_NP, RV_ROMB, RV_RAMB) into a RAM image (bytearray) - see kernels/memmap_route.s"""
    import struct
    N = len(nl.nodes); Q = nl.ram
    src = []
    for kind, ins in nl.nodes:
        for p in range(2):
            tok = ins[p] if p < len(ins) else 'open'; d = place_ref.net_id(tok, N)
            src.append(0xFFFF if d is None else d | (late_of(tok) << 14))
    struct.pack_into('<%dH' % len(src), ram, 0x26000, *src)
    for k, (kind, ins) in enumerate(nl.nodes): ram[0x2A800 + k] = 1 if kind == 'D' else 0
    ptab = []
    for name, tok in nl.ports:
        d = place_ref.net_id(tok, N)
        if name.startswith('rom_addr'): part, side, a = 0, 0, int(name[8:])
        elif name.startswith('arm_addr'): part, side, a = 1, 0, int(name[8:])
        elif name == 'arm_en': part, side, a = 1, 0, 4
        elif name.startswith('wdata'): part, side, a = 1, 1, int(name[5:])
        elif name.startswith('ram_addr'): part, side, a = 2, 0, int(name[8:])
        elif name == 'ram_we': part, side, a = 2, 0, Q
        elif name.startswith('ram_din'): part, side, a = 2, 0, Q + 1 + int(name[7:])
        ptab += [part | (side << 8), a, 0xFFFF if d is None else d | (late_of(tok) << 14)]
    struct.pack_into('<%dH' % len(ptab), ram, 0x2C000, *ptab)
    struct.pack_into('<%dH' % N, ram, 0x33000, *order)
    struct.pack_into('<I', ram, 0x68, N); struct.pack_into('<I', ram, 0x144, len(nl.ports))
    struct.pack_into('<I', ram, 0x130, nl.rom); struct.pack_into('<I', ram, 0x134, nl.ram)
