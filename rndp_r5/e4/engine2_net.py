#!/usr/bin/env python3
"""engine2_net.py -- E4 engine with the data-word interpreter datapath (gate-count build, not yet verified against a model).
Row word fields (columns): d[7:0] reg[11:8] src[14:12] D[15] cpol[16] ccol[21:17] ph[23:22].
 src: 0 const, 1 ylo(rr), 2 yhi(rr), 3 ylo(rr+1), 4 yhi(rr+1), 5 SUM (d ctl: d0 mirror sel Y, d[3:1] addend sel, d4 update mirror), 6 WF (d[1:0]: 0 c-field, 1 byte0, 2 byte1)
 cond: wr[ccol]==cpol; ccol 24..31 read constant 1 (unconditional = ccol 24, cpol 1); D rows: executed only in pass 1 and only for data words; D=0 rows only in pass 2.
 Data words (ph=00), see fmt3.py: cmd dx[8:0] len[14:9] orient[15] dy[17:16] c[19:18] Cmd[21]; H delta9[8:0] kind[10:9] val[11] flag[20].  src 7 = HI9: {d[7:1], sum[8]}."""
import sys
import netlist as NLm

def inc(N, bits, cin=1):
    c = [cin]; s = []
    for i, b in enumerate(bits):
        s.append(N.xor(b, c[i])); c.append(N.and_(c[i], b))
    return s, c

def eq_const(N, bits, val):
    return N.and_n([b if (val >> i) & 1 else N.not_(b) for i, b in enumerate(bits)])

def build(W, M=16319, NB=14, decoder=True):
    N = NLm.Net(); E0 = M - W + 1
    x = [N.inp(f'x{i}') for i in range(25)]
    w = x[:24]; qlast = x[24]
    run_q = N.dff('run'); started = N.dff('started'); N.set_d(run_q, N.inp('tie'))
    t = [N.dff(f't{i}') for i in range(NB)]; rr = [N.dff(f'rr{i}') for i in range(NB)]
    wr = [N.dff(f'wr{i}') for i in range(24)]
    mA, mCAP, mE, mC, p2 = (N.dff(n) for n in ('mA', 'mCAP', 'mE', 'mC', 'p2'))
    start = N.and_(run_q, N.not_(started)); N.set_d(started, N.or_(started, run_q))
    # counters
    t1, tc = inc(N, t); wrap = eq_const(N, t, M)
    L = N.or_(start, wrap)
    for i, (q, a) in enumerate(zip(t, t1)):
        N.set_d(q, N.or_(L, a) if (E0 >> i) & 1 else N.and_(N.not_(L), a))
    rr1, rc = inc(N, rr); last = eq_const(N, rr, M)
    adv = N.and_n([mE, wrap, N.not_(last)])
    p2start = N.and_n([mE, wrap, last, N.not_(p2)])                         # end of pass 1 -> restart rr, pass 2
    ldrr = N.or_(start, p2start)
    rr_hold = [N.mux(adv, a, b) for a, b in zip(rr, rr1)]
    for i, (q, a) in enumerate(zip(rr, rr_hold)):
        N.set_d(q, N.or_(ldrr, a) if (E0 >> i) & 1 else N.and_(N.not_(ldrr), a))
    # capture
    eq = N.not_(N.or_n([N.xor(a, b) for a, b in zip(t, rr)]))
    capture = N.and_(mCAP, eq)
    for q, wi in zip(wr, w): N.set_d(q, N.mux(capture, q, wi))
    # fields
    d = w[0:8]; reg = w[8:12]; src = w[12:15]; Dfl = w[15]; cpol = w[16]; ccol = w[17:22]; ph = w[22:24]
    ph1 = N.and_(ph[0], N.not_(ph[1])); ph2 = N.and_(N.not_(ph[0]), ph[1]); ph3 = N.and_(ph[0], ph[1])
    lev = list(wr) + [1] * 8
    for k in range(5):
        lev = [N.mux(ccol[k], lev[2 * i], lev[2 * i + 1]) for i in range(len(lev) // 2)]
    cm = lev[0]
    cond_eq = N.xnor(cm, cpol)
    if decoder:
        isdata = N.nor(wr[22], wr[23]); okD = N.or_(N.not_(Dfl), isdata); pg = N.xor(Dfl, p2)
        cond_ok = N.and_n([cond_eq, okD, pg])
    else:
        cond_ok = cond_eq
    en = N.or_n([N.and_(mA, ph1), N.and_n([mE, ph2, cond_ok]), N.and_(mC, ph3)])
    # data sources
    ns = [N.not_(s) for s in src]
    dec = lambda v: N.and_n([src[i] if (v >> i) & 1 else ns[i] for i in range(3)])
    s0, s1, s2, s3, s4 = (dec(v) for v in range(5))
    terms = [[] for _ in range(8)]
    for k in range(8):
        terms[k].append((s0, d[k]))
        if k < 2: terms[k].append((N.or_(s1, s3), d[k]))
        else: terms[k] += [(s1, rr[k - 2]), (s3, rr1[k - 2])]
        hi = N.not_(rr[13]) if k == 7 else rr[6 + k]
        hi1 = N.not_(rr1[13]) if k == 7 else rr1[6 + k]
        terms[k] += [(s2, hi), (s4, hi1)]
    if decoder:
        s5, s6, s7 = dec(5), dec(6), dec(7)
        ax = [N.dff(f'ax{i}') for i in range(9)]; ay = [N.dff(f'ay{i}') for i in range(9)]
        selY = N.or_(N.and_(s5, d[0]), N.and_(s7, reg[1]))
        op1 = [N.mux(selY, a, b) for a, b in zip(ax, ay)]
        a_dx = N.and_n([s5, N.not_(d[3]), N.not_(d[2]), N.not_(d[1])])           # addend sel 0: dx / delta9 = wr[8:0]
        a_dy = N.and_n([s5, N.not_(d[3]), N.not_(d[2]), d[1]])                    # 1: dy = wr[17:16]
        a_ln = N.or_(N.and_n([s5, N.not_(d[3]), d[2], N.not_(d[1])]), N.and_(s7, d[0]))   # 2: len = wr[14:9]  (or hi rows with d0)
        add = []
        for k in range(9):
            ts = [(a_dx, wr[k])]
            if k < 2: ts.append((a_dy, wr[16 + k]))
            if k < 6: ts.append((a_ln, wr[9 + k]))
            add.append(N.and_or(ts))
        sm = []; c = 0
        for k in range(9):
            if c == 0:
                sm.append(N.xor(op1[k], add[k])); c = N.and_(op1[k], add[k])
            else:
                s_, c = N.full_adder(op1[k], add[k], c); sm.append(s_)
        upd = N.and_(en, N.and_(s5, d[4]))
        for q, new in zip(ax, sm): N.set_d(q, N.mux(N.and_(upd, N.not_(d[0])), q, new))
        for q, new in zip(ay, sm): N.set_d(q, N.mux(N.and_(upd, d[0]), q, new))
        wf0, wf1, wf2 = (N.and_n([s6] + [(d[1] if (v >> 1) & 1 else N.not_(d[1])), (d[0] if v & 1 else N.not_(d[0]))]) for v in range(3))
        for k in range(8):
            terms[k].append((s5, sm[k]))
            if k >= 1: terms[k].append((s7, d[k]))
        terms[0].append((s7, sm[8]))
        terms[0].append((wf0, wr[18])); terms[2].append((wf0, wr[19]))             # CMD code {0,1,4,5} = c0 | c1<<2
        terms[0].append((wf1, wr[9])); terms[1].append((wf1, wr[10]))             # kind
        terms[0].append((wf2, wr[11]))                                            # val
    data = [N.and_or(t_) for t_ in terms]
    # modes
    nA = N.or_(start, N.and_(mA, N.not_(wrap)))
    nCAP = N.or_n([N.and_(mA, wrap), adv, p2start, N.and_(mCAP, N.not_(wrap))])
    nE = N.or_(N.and_(mCAP, wrap), N.and_(mE, N.not_(wrap)))
    nC = N.or_(N.and_n([mE, wrap, last, p2]), N.and_(mC, N.not_(wrap)))
    for q, dd in ((mA, nA), (mCAP, nCAP), (mE, nE), (mC, nC)): N.set_d(q, dd)
    N.set_d(p2, N.or_(p2, p2start))
    D0 = N.or_(qlast, start)
    return N, dict(arm_addr=[w[8], w[9], w[10], w[11]], arm_en=en, wdata=data, ram_addr0=D0, run=run_q, E0=E0)

def count(N, sp):
    roots = [sp['arm_en'], sp['ram_addr0']] + sp['wdata'] + [q for q in range(2, len(N.kind)) if N.kind[q][0] == 'dff']
    used = N.used_nodes(roots); g = sum(1 for n in used if N.kind[n][0] == 'nand'); dd = sum(1 for q in range(2, len(N.kind)) if N.kind[q][0] == 'dff')
    return g + 1, dd
if __name__ == '__main__':
    for dec in (False, True):
        N, sp = build(12000, decoder=dec); g, dd = count(N, sp); print('decoder' if dec else 'base   ', 'NAND', g, 'DFF', dd, 'metric', g + 6 * dd)
