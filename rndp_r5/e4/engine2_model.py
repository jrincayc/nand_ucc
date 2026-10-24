#!/usr/bin/env python3
"""engine2_model.py -- cycle-level model of engine2 (two passes, interpreter datapath).  rows: list of 24-bit ints (spec2).  Returns arm writes.
Same timing convention as engine_model: cycle k outputs from state S_k; arm executes them in tick k+1; then S_{k+1}."""
import spec2 as S

def run(words, M, max_cycles=None):
    W = len(words); E0 = M - W + 1; mask14 = (1 << 14) - 1
    tok = -1; started = 0; t = 0; rr = 0; wreg = 0
    mA = mCAP = mE = mC = p2 = 0; ax = ay = 0
    writes = []; cyc = 0
    while True:
        word = words[tok] if tok >= 0 else 0
        f = S.unpack(word)
        start = 1 if not started else 0                       # run is high from cycle 0
        wrap = (t == M); last = (rr == M)
        wb = lambda i: (wreg >> i) & 1
        lev = [wb(i) for i in range(24)] + [1] * 8
        cm = lev[f['ccol']]
        cond_eq = 1 if cm == f['cpol'] else 0
        isdata = 1 if (wb(22) == 0 and wb(23) == 0) else 0
        okD = 1 if (not f['D'] or isdata) else 0
        pg = f['D'] ^ p2
        cond_ok = cond_eq & okD & pg
        ph = f['ph']
        en = 1 if ((mA and ph == 1) or (mE and ph == 2 and cond_ok) or (mC and ph == 3)) else 0
        # data
        src = f['src']; d = f['d']; data = 0
        if src == S.SRC_CONST: data = d
        elif src in (S.SRC_YLO, S.SRC_YLO1):
            v = rr + (1 if src == S.SRC_YLO1 else 0); data = ((v & 63) << 2) | (d & 3)
        elif src in (S.SRC_YHI, S.SRC_YHI1):
            v = rr + (1 if src == S.SRC_YHI1 else 0); data = ((((v >> 13) & 1) ^ 1) << 7) | ((v >> 6) & 127)
        elif src in (S.SRC_SUM, 7):
            if src == 7:
                op1 = ay if (f['reg'] >> 1) & 1 else ax; add = ((wreg >> 9) & 63) if d & 1 else 0
                sm9 = (op1 + add) & 511; data = (d & 0xFE) | (sm9 >> 8)
            else:
                op1 = ay if d & 1 else ax; sel = (d >> 1) & 7
                add = (wreg & 511) if sel == 0 else ((wreg >> 16) & 3) if sel == 1 else ((wreg >> 9) & 63) if sel == 2 else 0
                sm9 = (op1 + add) & 511; data = sm9 & 255
        elif src == S.SRC_WF:
            sel = d & 3
            data = ((wb(18)) | (wb(19) << 2)) if sel == 0 else (wb(9) | wb(10) << 1) if sel == 1 else wb(11) if sel == 2 else 0
        if en: writes.append((f['reg'], data))
        nax, nay = ax, ay
        if en and src == S.SRC_SUM and (d >> 4) & 1:
            if d & 1: nay = sm9
            else: nax = sm9
        # next state
        capture = mCAP and t == rr
        nwreg = word if capture else wreg
        ntok = (tok + 1) if 0 <= tok < W - 1 else -1
        if tok == W - 1 or start: ntok = 0
        nt = E0 if (start or wrap) else t + 1
        p2start = mE and wrap and last and not p2
        adv = mE and wrap and not last
        ldrr = start or p2start
        nrr = E0 if ldrr else (rr + 1 if adv else rr)
        nA = 1 if start else (mA and not wrap)
        nCAP = (mA and wrap) or adv or p2start or (mCAP and not wrap)
        nE = (mCAP and wrap) or (mE and not wrap)
        nC = (mE and wrap and last and p2) or (mC and not wrap)
        done = started and not (mA or mCAP or mE or mC) and cyc > 0
        if done and not start: break
        started = 1; t = nt & mask14; rr = nrr & mask14; wreg = nwreg; tok = ntok
        mA, mCAP, mE, mC = int(bool(nA)), int(bool(nCAP)), int(bool(nE)), int(bool(nC))
        p2 = int(bool(p2 or p2start)); ax, ay = nax, nay
        cyc += 1
        if max_cycles and cyc > max_cycles: raise RuntimeError('too long')
    return writes, cyc
