"""Single-row machine: core netlist (data) + generated RAM, nodes in one row, node s at x = X0 + 3 s.
Produces the reference PLACE / PROGRAM_ROM / WIRE sequence (spec section 7 order) for the quine builder."""
from nl_core import build_core

PITCH = 2
ROM_H, ARM_H = 12, 9
STRIDE = ROM_H + ARM_H + 1          # row stripe per generation (22)


class Row:
    def __init__(self):
        self.kind, self.a, self.b = [], [], []       # refs: ('n', idx) | ('rom', j) | ('tie',)
    def add(self, kind, a=None, b=None):
        self.kind.append(kind); self.a.append(a); self.b.append(b); return len(self.kind) - 1
    def nand(self, a, b): return self.add('nand', a, b)
    def inv(self, a): return self.nand(a, a)
    def dff(self): return self.add('dff')


def N(i): return ('n', i)


def build(ram_abits, level=2):
    c = build_core(level, ram_abits)
    R = Row()
    nin, nd = c.n_in, c.n_dff
    rom_ids, ramrd_ids, run_id = c.buses['romdata'], c.buses['ramrd'], c.buses['run'][0]
    ramrd = [None] * 8                                 # placeholders patched after the RAM exists
    def ref(w):
        if w in rom_ids: return ('rom', rom_ids.index(w))
        if w in ramrd_ids: return ('ramrd', ramrd_ids.index(w))
        if w == run_id: return ('tie',)
        return N(w - nin)
    for i in range(nd): R.dff()
    for g, (a, b) in enumerate(c.gates): R.nand(ref(a), ref(b))
    for i, d in enumerate(c.dffd): R.a[i] = ref(d)
    core_end = len(R.kind)
    A = [N(w - nin) for w in c.outs['ram_addr']]
    WD = [N(w - nin) for w in c.outs['wdata']]
    WE = N(c.outs['ram_we'][0] - nin)
    # ---- RAM generator (chain read, v2) ---------------------------------------------------------------
    W, h = 1 << ram_abits, ram_abits // 2
    assert h >= 2 and ram_abits - h >= 2, 'ram_abits >= 4'
    nA = [N(R.inv(A[k])) for k in range(ram_abits)]
    def AND(x, y): return N(R.inv(N(R.nand(x, y))))
    def tree(ks):                       # one-hot decode of address bits ks; last level = consecutive AND pairs
        sel = [None]
        for k in ks:
            sel = [AND(s, nA[k]) if s is not None else nA[k] for s in sel] + \
                  [AND(s, A[k]) if s is not None else A[k] for s in sel]
        return sel
    lo = tree(range(h))
    hiR = tree(range(h, ram_abits))
    hiW = [AND(s, WE) for s in hiR]
    R.pre_end = len(R.kind)
    # phantom tile (60 unwired NANDs: their outputs read 1 = "previous chain value" of word 0)
    TILE = 4 + 7 * 8
    R.phantom = len(R.kind)
    ph = [R.add('nand') for _ in range(TILE)]
    prev_nacc = [ph[4 + 7 * j + 6] for j in range(8)]
    R.tile0 = len(R.kind)
    q = []
    for w in range(W):
        qrow = []
        n_, m_ = w >> h, w & ((1 << h) - 1)
        nwen = R.nand(hiW[n_], lo[m_]); wen = R.inv(N(nwen))
        ndec = R.nand(hiR[n_], lo[m_]); dec = R.inv(N(ndec))
        for j in range(8):
            d = R.dff(); qrow.append(d)
            t1 = R.nand(N(d), N(nwen)); t2 = R.nand(WD[j], N(wen)); o = R.nand(N(t1), N(t2)); R.a[d] = N(o)
            np_ = R.nand(N(dec), N(d)); acc = R.nand(N(prev_nacc[j]), N(np_)); nacc = R.inv(N(acc))
            prev_nacc[j] = nacc
            if w == W - 1: ramrd[j] = N(acc)
        q.append(qrow)
    R.W, R.h, R.TILE = W, h, TILE
    R.lo, R.hiR, R.hiW, R.WD = lo, hiR, hiW, WD
    # patch core inputs that read the RAM output
    for i in range(core_end):
        for arr in (R.a, R.b):
            r = arr[i]
            if r is not None and r[0] == 'ramrd': arr[i] = ramrd[r[1]]
    outs = dict(rom_addr=[N(w - nin) for w in c.outs['rom_addr']], arm_addr=[N(w - nin) for w in c.outs['arm_addr']],
                arm_en=N(c.outs['arm_en'][0] - nin), wdata=WD)
    R.q = q
    return R, outs, core_end, c


def commands(R, outs, rom_bytes, ox=0, oy=STRIDE):
    """Reference build sequence for a child whose ARM origin is (ox, oy) relative to the issuing arm (spec v0.5).
    Layout (all offsets >= 0): ARM at (ox,oy); ROM at (ox,oy+9); row node i at (ox+6+2i, oy+9)."""
    n = len(R.kind)
    y0 = oy + ARM_H
    xs = lambda i: ox + 6 + PITCH * i
    rx, ry = ox, y0
    ax, ay = ox, oy
    tie = n
    cmds = [('place', R.kind[i], xs(i), y0) for i in range(n)]
    cmds.append(('place', 'nand', xs(tie), y0))
    cmds.append(('place', 'rom', rx, ry)); cmds.append(('place', 'arm', ax, ay))
    for a, v in enumerate(rom_bytes):
        if v: cmds.append(('rom', rx, ry, a, v))
    def out_site(r):
        if r[0] == 'n': return (xs(r[1]) + 1, y0)
        if r[0] == 'rom': return (rx + 1, ry + r[1])
        return (xs(tie) + 1, y0)
    run_wires = []
    for i in range(n):
        if R.kind[i] == 'dff':
            cmds.append(('wire',) + out_site(R.a[i]) + (xs(i), y0))
        else:
            for pin, r in ((0, R.a[i]), (1, R.b[i])):
                if r is None: continue          # phantom tie-high NANDs stay unwired
                (run_wires if r[0] == 'tie' else cmds).append(('wire',) + out_site(r) + (xs(i), y0 + pin))
    for i, r in enumerate(outs['rom_addr']): cmds.append(('wire',) + out_site(r) + (rx, ry + i))
    for i, r in enumerate(outs['arm_addr']): cmds.append(('wire',) + out_site(r) + (ax, ay + i))
    for j, r in enumerate(outs['wdata']): cmds.append(('wire',) + out_site(r) + (ax + 1, ay + j))
    cmds.append(('wire',) + out_site(outs['arm_en']) + (ax, ay + 4))
    cmds += run_wires
    return cmds


if __name__ == '__main__':
    import sys
    for ab in (5, 6, 7, 8):
        R, outs, core_end, c = build(ab)
        from collections import Counter
        k = Counter(R.kind)
        print(f'RAM {1<<ab:4} B: core nodes {core_end}, total nodes {len(R.kind)} (nand {k["nand"]}, dff {k["dff"]}), row width {3*len(R.kind)}')
