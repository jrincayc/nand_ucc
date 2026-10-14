"""Builder v2: tile engine.  One ref decoder serves the core, the predecode and the RAM word tiles.

Stream segments (each starts on a byte boundary so a tile can be re-read by reloading BP):
  seg_a : core DFFs (1 ref each), then NANDs up to pre_end (2 refs each)
  seg_h : word head, 4 NANDs x 2 refs  (nwen, wen, ndec, dec)
  seg_s : slice, DFF (1 ref) + 6 NANDs (2 refs):  d, t1, t2, o, np, acc, nacc   [d first]
  seg_o : ROM addr (12), ARM addr (4), wdata (8), EN (1)
Ref = Exp-Golomb(k=2) of the backward node distance d >= 1, or escape (value 0) + 3-bit kind:
  0 ROM data bit j (3 bits)   1 forward (EG of 1-d)   2 tie (deferred run wire)   3 head line k (2 bits)
  4 WD[j] pointer   5 hiR pointer   6 hiW pointer (= hiR + KHW)   7 lo pointer
"""
from builder import (uid, lo, hi, ARM, OX, OY, ROW_Y, X_START, ROM_BASE, Vars, inc16_by2, dec16_loop,
                     place_one, place_run, build_rom_arm, build_rom_copy)
import builder as B
import machine_row as MR
from blib import Lib
from wirepass import eg, inc2_odd
from isahack import Asm

TILE = 60
VARS = [('C', 1), ('PINS', 1), ('MODE', 1), ('RET', 1), ('RET2', 1), ('RET3', 1), ('RET4', 1), ('R0', 2), ('R1', 2),
        ('U', 1), ('BP', 2), ('BB', 1), ('BN', 1), ('Z', 1), ('FV', 1), ('DX', 2), ('XS', 2),
        ('XH', 2), ('HP', 2), ('LP', 2), ('WDP', 2)]
ALIAS = {'CN': 'Z', 'TB': 'U', 'P': 'HP', 'I': 'LP', 'GP': 'XH', 'GN': 'LP', 'GY': 'WDP'}   # lifetimes are disjoint


def xn(i): return X_START + 2 * i


class Plan:
    def __init__(self, R, outs, ce):
        self.R, self.outs, self.ce = R, outs, ce
        k = R.kind
        self.nd = 0
        while k[self.nd] == 'dff': self.nd += 1
        self.pre_end, self.phantom, self.tile0 = R.pre_end, R.phantom, R.tile0
        self.W, self.h = R.W, R.h
        self.n_total = len(k)
        rs = lambda r: xn(r[1]) + 1                         # output site x of node ref r
        self.LO0, self.HR0, self.HW0, self.WD0 = rs(R.lo[0]), rs(R.hiR[0]), rs(R.hiW[0]), rs(R.WD[0])
        for m in range(len(R.lo)): assert rs(R.lo[m]) == self.LO0 + 4 * m
        for m in range(len(R.hiR)): assert rs(R.hiR[m]) == self.HR0 + 4 * m
        for m in range(len(R.hiW)): assert rs(R.hiW[m]) == self.HW0 + 4 * m
        for j in range(8): assert rs(R.WD[j]) == self.WD0 + 6 * j
        self.KHW = self.HW0 - self.HR0
        self.tie_x = xn(self.n_total) + 1
        assert 0 < self.KHW < 256


# ---------------------------------------------------------------------------------------------- encoder
def esc(kind, payload=''): return eg(0) + format(kind, '03b') + payload


def enc_ref(plan, i, r, hs=None, w=None, k=None):
    """Bits for source ref r of destination node i.  hs/w/k given for RAM tile nodes (k=0 head, 1 slice)."""
    R = plan.R
    if r[0] == 'rom': return esc(0, format(r[1], '03b'))
    if r[0] == 'tie': return esc(2)
    s = r[1]
    if k is not None:
        n_, m_ = w >> R.h, w & ((1 << R.h) - 1)
        if k == 0:
            if r == R.hiR[n_]: return esc(5)
            if r == R.hiW[n_]: return esc(6)
            if r == R.lo[m_]: return esc(7)
        else:
            if r in R.WD: return esc(4)
            if hs <= s < hs + 4: return esc(3, format(s - hs, '02b'))
    d = i - s
    if d >= 1: return eg(d)
    return esc(1, eg(1 - d))


def node_bits(plan, i, **kw):
    R = plan.R
    refs = [R.a[i]] if R.kind[i] == 'dff' else [R.a[i], R.b[i]]
    return ''.join(enc_ref(plan, i, r, **kw) for r in refs)


def pad(bits): return bits + '0' * (-len(bits) % 8)
def tob(bits): return bytes(int(bits[k:k + 8], 2) for k in range(0, len(bits), 8))


def make_stream(plan):
    R = plan.R
    seg_a = ''.join(node_bits(plan, i) for i in range(plan.pre_end))
    w = 1
    hs = plan.tile0 + TILE * w
    seg_h = ''.join(node_bits(plan, i, hs=hs, w=w, k=0) for i in range(hs, hs + 4))
    seg_s = ''.join(node_bits(plan, i, hs=hs, w=w, k=1) for i in range(hs + 4, hs + 11))
    o = plan.outs
    out_refs = list(o['rom_addr']) + list(o['arm_addr']) + list(o['wdata']) + [o['arm_en']]
    seg_o = ''
    for r in out_refs:
        d = plan.pre_end - r[1]; assert d >= 1
        seg_o += eg(d)
    return [tob(pad(x)) for x in (seg_a, seg_h, seg_s, seg_o)]


# ---------------------------------------------------------------------------------------------- decoder (asm)
def ref_sub(L, V, plan):
    a = L.a
    R0, R1, XS, DX, FV, CN, XH = (V[k] for k in ('R0', 'R1', 'XS', 'DX', 'FV', 'CN', 'XH'))
    HP, LP, WDP = V['HP'], V['LP'], V['WDP']
    def body():
        L.save_ret('RET3')
        escl, emitA, emitB, done = uid('esc'), uid('eA'), uid('eB'), uid('dn')
        L.call('readEG')
        a.ldD(R1 + 1); a.jump(escl + 'n', 'JNE', 'D')
        a.ldD(R1); a.A(4); a.C('D', 'D-A'); a.jump(escl, 'JEQ', 'D')
        a.label(escl + 'n')
        L.call('shl1')
        a.ldD(XS); a.stD(R0); a.ldD(XS + 1); a.stD(R0 + 1)
        L.call('sub16')
        a.label(emitA)
        a.ldD(R0); a.stD(ARM + 0); a.ldD(R0 + 1); a.stD(ARM + 1)
        a.label(emitB)
        a.ldD(DX); a.stD(ARM + 4); a.ldD(DX + 1); a.stD(ARM + 5)
        a.setc(ARM + 15, 2)
        a.jump(done)
        # ---- escapes: 3-bit kind
        a.label(escl)
        a.setc(CN, 3); L.call('getbits')
        kinds = [uid('k') for _ in range(7)]
        a.ldD(FV); a.jump(kinds[0], 'JEQ', 'D')
        for k in range(1, 7):
            a.C('D', 'D-1'); a.jump(kinds[k], 'JEQ', 'D')
        # 7: lo pointer
        a.ldD(LP); a.stD(ARM + 0); a.ldD(LP + 1); a.stD(ARM + 1); a.jump(emitB)
        a.label(kinds[0])                                          # ROM data bit j
        a.setc(CN, 3); L.call('getbits')
        a.setc(ARM + 0, lo(OX + 1)); a.setc(ARM + 1, hi(OX + 1))
        a.ldDc(ROW_Y); a.A(FV); a.C('D', 'D+M'); a.stD(ARM + 2)
        a.ldD(DX); a.stD(ARM + 4); a.ldD(DX + 1); a.stD(ARM + 5)
        a.setc(ARM + 15, 2)
        a.setc(ARM + 2, lo(ROW_Y))
        a.jump(done)
        a.label(kinds[1])                                          # forward: Sx = XS + 2n - 18
        L.call('readEG'); L.call('shl1')
        a.ldD(XS); a.stD(R0); a.ldD(XS + 1); a.stD(R0 + 1)
        L.call('add16')
        a.setc(R1, 18); a.setc(R1 + 1, 0); L.call('sub16')
        a.jump(emitA)
        a.label(kinds[2])                                          # tie: no wire now (the run wire is issued last)
        a.jump(done)
        a.label(kinds[3])                                          # head line k: Sx = XH + 2k + 1
        a.setc(CN, 2); L.call('getbits')
        a.ldD(FV); a.A(FV); a.C('D', 'D+M'); a.C('D', 'D+1'); a.stD(R1); a.setc(R1 + 1, 0)
        a.ldD(XH); a.stD(R0); a.ldD(XH + 1); a.stD(R0 + 1)
        L.call('add16'); a.jump(emitA)
        a.label(kinds[4])                                          # WD[j] pointer
        a.ldD(WDP); a.stD(ARM + 0); a.ldD(WDP + 1); a.stD(ARM + 1); a.jump(emitB)
        a.label(kinds[5])                                          # hiR pointer
        a.ldD(HP); a.stD(ARM + 0); a.ldD(HP + 1); a.stD(ARM + 1); a.jump(emitB)
        a.label(kinds[6])                                          # hiW pointer = hiR + KHW
        a.ldD(HP); a.stD(R0); a.ldD(HP + 1); a.stD(R0 + 1)
        a.setc(R1, plan.KHW); a.setc(R1 + 1, 0); L.call('add16'); a.jump(emitA)
        a.label(done)
        L.ret(saved=True, slot='RET3')
    return body


def wnodes_sub(L, V):
    """Visit C (<= 255) consecutive nodes starting at (DX, XS).  MODE 0: PLACE each (PINS==1: DFF, else NAND).
    MODE 1: wire PINS (0..2) refs per node.  Advances DX (+2) and XS (+2) per node."""
    a = L.a
    def body():
        L.save_ret('RET4')
        lp, wm, adv, dffk, pl = (uid(k) for k in ('wn', 'wm', 'adv', 'dk', 'pl'))
        a.label(lp)
        a.ldD(V['MODE']); a.jump(wm, 'JNE', 'D')
        a.ldD(V['DX']); a.stD(ARM + 0); a.ldD(V['DX'] + 1); a.stD(ARM + 1)
        a.ldD(V['PINS']); a.C('D', 'D-1'); a.jump(dffk, 'JEQ', 'D')
        a.setc(ARM + 8, 0); a.jump(pl)
        a.label(dffk); a.setc(ARM + 8, 1)
        a.label(pl); a.setc(ARM + 15, 1); a.jump(adv)
        a.label(wm)
        a.ldD(V['PINS']); a.jump(adv, 'JEQ', 'D')
        a.setc(ARM + 6, lo(ROW_Y)); L.call('ref')
        a.ldD(V['PINS']); a.C('D', 'D-1'); a.jump(adv, 'JEQ', 'D')
        a.setc(ARM + 6, lo(ROW_Y + 1)); L.call('ref')
        a.label(adv)
        inc16_by2(a, V['DX'], uid('dx')); inc2_odd(a, V['XS'])
        a.dec_loop(V['C'], lp)
        L.ret(saved=True, slot='RET4')
    return body


def setw(a, var, val):
    a.setc(var, lo(val)); a.setc(var + 1, hi(val))


def call_wnodes(L, V, count, pins):
    a = L.a
    a.setc(V['PINS'], pins)
    while count > 0:
        c = min(count, 255)
        a.setc(V['C'], c); L.call('wnodes'); count -= c


def set_bp(a, V, label):
    a.A(('lo', label)); a.C('D', 'A'); a.stD(V['BP']); a.A(('hi', label)); a.C('D', 'A'); a.stD(V['BP'] + 1)
    a.setc(V['BN'], 0)


def tile_loops(a, L, V, plan):
    """Nodes of the row in index order: core, predecode, phantom tile, W word tiles, tie NAND."""
    nd, W, h = plan.nd, plan.W, plan.h
    set_bp(a, V, 'seg_a')
    a.setc(ARM + 2, lo(ROW_Y)); a.setc(ARM + 3, hi(ROW_Y)); a.setc(ARM + 7, 0)
    setw(a, V['DX'], X_START); setw(a, V['XS'], X_START + 9)
    call_wnodes(L, V, nd, 1)
    call_wnodes(L, V, plan.pre_end - nd, 2)
    call_wnodes(L, V, TILE, 0)                                      # phantom tile: placed, never wired
    setw(a, V['HP'], plan.HR0)
    ln, lm, lj = uid('wn'), uid('wm'), uid('wj')
    a.label(ln)
    setw(a, V['LP'], plan.LO0)
    a.label(lm)
    set_bp(a, V, 'seg_h')
    a.ldD(V['DX']); a.stD(V['XH']); a.ldD(V['DX'] + 1); a.stD(V['XH'] + 1)
    call_wnodes(L, V, 4, 2)
    setw(a, V['WDP'], plan.WD0)
    a.label(lj)
    set_bp(a, V, 'seg_s')
    call_wnodes(L, V, 1, 1)
    call_wnodes(L, V, 6, 2)
    for _ in range(3): inc16_by2(a, V['WDP'], uid('wd'))
    a.ldD(V['WDP']); a.A(lo(plan.WD0 + 48)); a.C('D', 'D-A'); a.jump(lj, 'JNE', 'D')
    for _ in range(2): inc16_by2(a, V['LP'], uid('lp'))
    a.ldD(V['LP']); a.A(lo(plan.LO0 + 4 * (1 << h))); a.C('D', 'D-A'); a.jump(lm, 'JNE', 'D')
    for _ in range(2): inc16_by2(a, V['HP'], uid('hp'))
    a.ldD(V['HP']); a.A(lo(plan.HR0 + 4 * (W >> h))); a.C('D', 'D-A'); a.jump(ln, 'JNE', 'D')
    call_wnodes(L, V, 1, 0)                                         # the tie-high NAND


def make_program(ab):
    R, outs, ce, c = MR.build(ab)
    plan = Plan(R, outs, ce)
    vs = Vars(); V = {}
    for n, sz in VARS: V[n] = vs.v(n, sz)
    for k, v in ALIAS.items(): V[k] = V[v]
    V['K'] = V['WDP'] + 1
    a = Asm(); L = Lib(a, V)
    # reset gate: the node whose pins read the tie-high NAND (the "run" input)
    rg = [i for i in range(len(R.kind)) if R.kind[i] == 'nand' and R.a[i] == ('tie',)]
    assert len(rg) == 1 and R.b[rg[0]] == ('tie',)
    reset_x = xn(rg[0])
    # ---- phase 1 (MODE 0) places every node, then the ROM/ARM and the ROM copy; phase 2 (MODE 1) wires
    a.setc(ARM + 9, 0); a.setc(V['MODE'], 0)
    a.label('top')
    tile_loops(a, L, V, plan)
    a.ldD(V['MODE']); a.jump('phase2', 'JNE', 'D')
    build_rom_arm(a, V); build_rom_copy(a, V)
    a.setc(V['MODE'], 1); a.jump('top')
    a.label('phase2')
    # outputs: table of (dest x, dest y0, count); EN is the last entry
    set_bp(a, V, 'seg_o')
    a.A(('lo', 'gtab')); a.C('D', 'A'); a.stD(V['GP']); a.A(('hi', 'gtab')); a.C('D', 'A'); a.stD(V['GP'] + 1)
    setw(a, V['XS'], xn(plan.pre_end) + 9)
    a.setc(V['DX'] + 1, 0); a.setc(V['GN'], 4)
    lg, lr = uid('grp'), uid('rf')
    a.label(lg)
    a.A(V['GP']); a.AP(); a.C('D', 'M'); a.stD(V['DX']); a.inc16(V['GP'], uid('gi'))
    a.A(V['GP']); a.AP(); a.C('D', 'M'); a.stD(V['GY']); a.inc16(V['GP'], uid('gi'))
    a.A(V['GP']); a.AP(); a.C('D', 'M'); a.stD(V['K']); a.inc16(V['GP'], uid('gi'))
    a.label(lr)
    a.ldD(V['GY']); a.stD(ARM + 6)
    L.call('ref'); a.A(V['GY']); a.C('M', 'M+1')
    a.dec_loop(V['K'], lr)
    a.dec_loop(V['GN'], lg)
    # deferred run wires: tie -> the reset gate's two pins (the last two wires)
    a.setc(ARM + 0, lo(plan.tie_x)); a.setc(ARM + 1, hi(plan.tie_x))
    a.setc(ARM + 4, lo(reset_x)); a.setc(ARM + 5, hi(reset_x))
    a.setc(ARM + 6, lo(ROW_Y)); a.setc(ARM + 15, 2)
    a.setc(ARM + 6, lo(ROW_Y + 1)); a.setc(ARM + 15, 2)
    a.label('halt'); a.jump('halt')
    # ---- subroutines
    L.build()
    L.fns['ref'] = ref_sub(L, V, plan)
    L.fns['wnodes'] = wnodes_sub(L, V)
    L.used |= {'ref', 'wnodes'}
    done = set()
    while True:
        todo = sorted(L.used - done)
        if not todo: break
        for n in todo: a.label(n); L.fns[n](); done.add(n)
    segs = make_stream(plan)
    for name, data in zip(('seg_a', 'seg_h', 'seg_s', 'seg_o'), segs):
        a.label(name); a.data(data)
    a.label('gtab')
    for gx, gy, cnt in ((OX, ROW_Y, 12), (OX, OY, 4), (OX + 1, OY, 8), (OX, OY + 4, 1)):
        a.data(bytes([gx, gy, cnt]))
    a.label('end')
    L.finalize()
    return a, plan, V, [len(s) for s in segs]
