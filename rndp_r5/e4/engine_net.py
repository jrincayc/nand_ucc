#!/usr/bin/env python3
"""engine_net.py -- gate-level netlist of the E4 engine (NAND + DFF), built with the Net builder.  build(W) -> (net, spec).
External inputs x0..x23 = plane word columns, x24 = plane ring output (token of the last row).  Outputs: arm ADDR = x8..x11 (straight through), arm EN, arm DATA[7:0], D0 (ring input).
`run` is a DFF whose D is a tie-high node wired last (late class 2), as in R4."""
import sys
import netlist as NLm
import spec as S

def inc(N, bits):
    """bits + 1 (LSB first): returns (sum bits, carries) with carries[i] = AND(bits[0..i-1]) (carries[0] = 1)"""
    c = [1]; s = []
    for i, b in enumerate(bits):
        s.append(N.xor(b, c[i])); c.append(N.and_(c[i], b))
    return s, c

def const_load(N, load, val, alt):
    """per bit: load ? val_i : alt_i"""
    out = []
    for i, a in enumerate(alt):
        if (val >> i) & 1: out.append(N.or_(load, a))
        else: out.append(N.and_(N.not_(load), a))
    return out

def build(W):
    N = NLm.Net(); E0 = 8192 - W; M = 8191
    x = [N.inp(f'x{i}') for i in range(25)]
    w = x[:24]; qlast = x[24]
    run_q = N.dff('run'); started = N.dff('started'); N.set_d(run_q, N.inp('tie'))
    t = [N.dff(f't{i}') for i in range(14)]; rr = [N.dff(f'rr{i}') for i in range(14)]
    wr = [N.dff(f'wr{i}') for i in range(24)]
    mA, mCAP, mE, mC = (N.dff(n) for n in ('mA', 'mCAP', 'mE', 'mC'))
    start = N.and_(run_q, N.not_(started))
    N.set_d(started, N.or_(started, run_q))
    # ---- counters
    t1, tc = inc(N, t); wrap = N.and_(tc[13], N.not_(t[13]))               # t == 0x1FFF
    L = N.or_(start, wrap)
    for q, d in zip(t, const_load(N, L, E0, t1)): N.set_d(q, d)
    rr1, rc = inc(N, rr); last = N.and_(rc[13], N.not_(rr[13]))
    adv = N.and_n([mE, wrap, N.not_(last)])
    rr_hold = [N.mux(adv, a, b) for a, b in zip(rr, rr1)]
    for q, d in zip(rr, const_load(N, start, E0, rr_hold)): N.set_d(q, d)
    # ---- capture
    neq = [N.xor(a, b) for a, b in zip(t, rr)]
    eq = N.not_(N.or_n(neq))
    capture = N.and_(mCAP, eq)
    for q, wi, ci in zip(wr, w, wr): N.set_d(q, N.mux(capture, q, wi))
    # ---- instruction fields
    d = w[0:8]; reg = w[8:12]; src = w[12:15]; cen, cpol = w[15], w[16]; ccol = w[17:22]; ph = w[22:24]
    ph1 = N.and_(ph[0], N.not_(ph[1])); ph2 = N.and_(N.not_(ph[0]), ph[1]); ph3 = N.and_(ph[0], ph[1])
    # condition: wr[ccol] == cpol
    lev = list(wr)
    for k in range(5):
        lev = [N.mux(ccol[k], lev[2 * i], lev[2 * i + 1]) if 2 * i + 1 < len(lev) else lev[2 * i] for i in range((len(lev) + 1) // 2)]
    cm = lev[0]
    cond_ok = N.or_(N.not_(cen), N.not_(N.xor(cm, cpol)))
    en = N.or_n([N.and_(mA, ph1), N.and_n([mE, ph2, cond_ok]), N.and_(mC, ph3)])
    # ---- data
    s0 = N.and_n([N.not_(src[0]), N.not_(src[1]), N.not_(src[2])])      # const
    s1 = N.and_n([src[0], N.not_(src[1]), N.not_(src[2])])              # ylo(rr)
    s2 = N.and_n([N.not_(src[0]), src[1], N.not_(src[2])])              # yhi(rr)
    s3 = N.and_n([src[0], src[1], N.not_(src[2])])                      # ylo(rr+1)
    s4 = N.and_n([N.not_(src[0]), N.not_(src[1]), src[2]])              # yhi(rr+1)
    rr1x = rr1 + [N.xor(rr[13], rc[13])]                                # not needed beyond bit 13 (rr+1 <= 8192): bit 13 of rr+1 is rr1[13]
    data = []
    for k in range(8):
        terms = [(s0, d[k])]
        if k < 2: terms += [(N.or_(s1, s3), d[k])]
        else: terms += [(s1, rr[k - 2]), (s3, rr1[k - 2])]
        hi = N.not_(rr[13]) if k == 7 else rr[6 + k]
        hi1 = N.not_(rr1[13]) if k == 7 else rr1[6 + k]
        terms += [(s2, hi), (s4, hi1)]
        data.append(N.and_or(terms))
    # ---- modes
    nA = N.or_(start, N.and_(mA, N.not_(wrap)))
    nCAP = N.or_n([N.and_(mA, wrap), adv, N.and_(mCAP, N.not_(wrap))])
    nE = N.or_(N.and_(mCAP, wrap), N.and_(mE, N.not_(wrap)))
    nC = N.or_(N.and_n([mE, wrap, last]), N.and_(mC, N.not_(wrap)))
    for q, dd in ((mA, nA), (mCAP, nCAP), (mE, nE), (mC, nC)): N.set_d(q, dd)
    D0 = N.or_(qlast, start)
    spec = dict(arm_addr=[w[8], w[9], w[10], w[11]], arm_en=en, wdata=data, ram_addr0=D0, run=run_q, E0=E0)
    return N, spec

def export_nl(N, spec, path):
    """write the R4 .nl format.  DFFs first (run's D = tie@2), then NANDs; external inputs are tokens x<k>."""
    kinds = N.kind; used = N.used_nodes([spec['arm_en'], spec['ram_addr0']] + spec['wdata'] + [q for q in range(2, len(kinds)) if kinds[q][0] == 'dff'])
    dffs = [n for n in range(2, len(kinds)) if kinds[n][0] == 'dff']
    nands = [n for n in range(2, len(kinds)) if kinds[n][0] == 'nand' and n in used]
    idx = {}; i = 0
    for n in dffs: idx[n] = i; i += 1
    tie = i; i += 1                                                         # tie-high node placed first among the NANDs
    for n in nands: idx[n] = i; i += 1
    def tok(n, late=''):
        k = kinds[n]
        if k[0] == 'in': return k[1] + late
        return f'n{idx[n]}' + late
    lines = ['rom 0', 'ram 1']
    for n in dffs:
        if n == spec['run']: lines.append(f'n {idx[n]} D n{tie}@2')
        else: lines.append(f'n {idx[n]} D {tok(kinds[n][1])}')
    lines.append(f'n {tie} N open open')
    for n in nands: lines.append(f'n {idx[n]} N {tok(kinds[n][1])} {tok(kinds[n][2])}')
    for k, n in enumerate(spec['arm_addr']): lines.append(f'p arm_addr{k} {tok(n)}')
    lines.append(f'p arm_en {tok(spec["arm_en"], "@1")}')
    for k, n in enumerate(spec['wdata']): lines.append(f'p wdata{k} {tok(n)}')
    lines.append(f'p ram_addr0 {tok(spec["ram_addr0"])}')
    open(path, 'w').write('\n'.join(lines) + '\n')
    return dict(nand=len(nands) + 1, dff=len(dffs), idx=idx, tie=tie)

if __name__ == '__main__':
    W = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
    N, sp = build(W); roots = [sp['arm_en'], sp['ram_addr0']] + sp['wdata'] + [q for q in range(2, len(N.kind)) if N.kind[q][0] == 'dff']
    used = N.used_nodes(roots); g = sum(1 for n in used if N.kind[n][0] == 'nand'); d = sum(1 for q in range(2, len(N.kind)) if N.kind[q][0] == 'dff')
    print(f'W={W}: NAND {g} (+1 tie) DFF {d}  metric NAND+6DFF = {g + 1 + 6 * d}')
