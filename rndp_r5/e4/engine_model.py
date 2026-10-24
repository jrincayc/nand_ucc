#!/usr/bin/env python3
"""engine_model.py -- cycle-level behavioural model of the E4 engine + token-ring plane.
Cycle k: outputs O_k = f(state S_k); the arm executes O_k during tick k+1 (RNDP tick procedure); then S_{k+1} = next(S_k).
rows: list of instruction dicts (spec.pack fields).  E0 = 8192 - W.  Returns the list of arm writes (reg, data)."""
import spec as S

def run(rows, max_cycles=None, trace=None):
    W = len(rows); E0 = 8192 - W; words = [S.pack(**r) for r in rows]
    M = 8191
    tok = -1                       # row under the token (-1 none)
    started = 0; t = 0; rr = 0; wreg = [0] * S.B
    mA = mCAP = mEXE = mC = 0
    writes = []; cyc = 0
    while True:
        # ----- outputs from state
        word = words[tok] if tok >= 0 else [0] * S.B
        f = S.unpack(word)
        run_ = 1
        start = run_ and not started
        wrap = (t == M)
        if mA and f['ph'] == S.PH_A: en = 1
        elif mEXE and f['ph'] == S.PH_P: en = 1 if (not f['cen'] or wreg[f['ccol']] == f['cpol']) else 0
        elif mC and f['ph'] == S.PH_C: en = 1
        else: en = 0
        src = f['src']
        if src == S.SRC_CONST: data = f['d']
        else:
            n = 1 if src in (S.SRC_YLO1, S.SRC_YHI1) else 0
            v = rr + n
            if src in (S.SRC_YLO, S.SRC_YLO1): data = ((v & 63) << 2) | (f['d'] & 3)
            else: data = (((v >> 13) & 1 ^ 1) << 7) | ((v >> 6) & 127)
        if en: writes.append((f['reg'], data))
        if trace is not None and cyc < trace: print(cyc, 'tok', tok, 't', t, 'rr', rr, 'mode', mA, mCAP, mEXE, mC, 'en', en)
        # ----- next state
        capture = mCAP and t == rr
        nwreg = word if capture else wreg
        ntok = (tok + 1) if 0 <= tok < W - 1 else -1
        if tok == W - 1 or start: ntok = 0 if (tok == W - 1 or start) else ntok     # ring closure / injection: D0 = Qlast | start
        nt = E0 if (start or wrap) else t + 1
        last = (rr == M)
        nrr = E0 if start else (rr + 1 if (mEXE and wrap and not last) else rr)
        nA = 1 if start else (mA and not wrap)
        nCAP = (mA and wrap) or (mEXE and wrap and not last) or (mCAP and not wrap)
        nEXE = (mCAP and wrap) or (mEXE and not wrap)
        nC = (mEXE and wrap and last) or (mC and not wrap)
        done = started and not (mA or mCAP or mEXE or mC) and cyc > 0 and started
        if done and not (start): break
        started = 1; t = nt; rr = nrr; wreg = nwreg; tok = ntok
        mA, mCAP, mEXE, mC = int(bool(nA)), int(bool(nCAP)), int(bool(nEXE)), int(bool(nC))
        cyc += 1
        if max_cycles and cyc > max_cycles: raise RuntimeError('too long')
    return writes, cyc
