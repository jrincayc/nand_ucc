"""nandgen.py -- NAND + DFF netlist generator for a Hack-class CPU and RAM.
(Copy of nandgen/nandgen.py from the Project, used here only for the differential test.)
"""
import lzma
import zlib
from contextlib import contextmanager

ZERO, ONE = -1, -2


class Net:
    def __init__(self, level=1):
        self.level = level
        self.kind, self.a, self.b, self.tag = [], [], [], []
        self.buses = {}
        self._hash, self._inv = {}, {}
        self._scope = ['top']
        self._c1 = self._c0 = None
        self.pos, self.cur = {}, None

    def _new(self, kind, a=-9, b=-9):
        self.kind.append(kind)
        self.a.append(a)
        self.b.append(b)
        self.tag.append(self._scope[-1])
        if self.cur is not None:
            self.pos[len(self.kind) - 1] = self.cur
        return len(self.kind) - 1

    @contextmanager
    def at(self, key):
        old, self.cur = self.cur, key
        try:
            yield
        finally:
            self.cur = old

    @contextmanager
    def scope(self, name):
        self._scope.append(name)
        try:
            yield
        finally:
            self._scope.pop()

    def input(self, name):
        w = self._new('I')
        self.buses[name] = [w]
        return w

    def bus_in(self, name, n):
        ws = [self._new('I') for _ in range(n)]
        self.buses[name] = ws
        return ws

    def dff_bus(self, n):
        return [self._new('D') for _ in range(n)]

    def set_d(self, q, d):
        self.a[q] = self.real(d)

    def _raw(self, a, b):
        return self._new('N', a, b)

    def _hraw(self, a, b):
        key = (a, b) if a <= b else (b, a)
        w = self._hash.get(key)
        if w is None:
            w = self._hash[key] = self._raw(a, b)
            if a == b:
                self._inv[w] = a
        return w

    def real(self, w):
        if w >= 0:
            return w
        if self._c1 is None:
            x = 0
            assert self.kind[0] == 'I'
            if self.level >= 1:
                self._c1 = self._hraw(x, self._hraw(x, x))
            else:
                self._c1 = self._raw(x, self._raw(x, x))
        if w == ONE:
            return self._c1
        if self._c0 is None:
            self._c0 = (self._hraw(self._c1, self._c1) if self.level >= 1
                        else self._raw(self._c1, self._c1))
        return self._c0

    def nand(self, a, b):
        if self.level == 0:
            return self._raw(self.real(a), self.real(b))
        if a == ZERO or b == ZERO:
            return ONE
        if a == ONE:
            return self.not_(b)
        if b == ONE:
            return self.not_(a)
        if a == b:
            return self.not_(a)
        if self._inv.get(a) == b or self._inv.get(b) == a:
            return ONE
        return self._hraw(a, b)

    def not_(self, a):
        if self.level == 0:
            return self._raw(self.real(a), self.real(a))
        if a == ZERO:
            return ONE
        if a == ONE:
            return ZERO
        if a in self._inv:
            return self._inv[a]
        return self._hraw(a, a)

    def and_(self, a, b):
        return self.not_(self.nand(a, b))

    def or_(self, a, b):
        return self.nand(self.not_(a), self.not_(b))

    def xor(self, a, b):
        if self.level >= 1:
            if a == ZERO: return b
            if b == ZERO: return a
            if a == ONE: return self.not_(b)
            if b == ONE: return self.not_(a)
        if self.level >= 2:
            t = self.nand(a, b)
            return self.nand(self.nand(a, t), self.nand(b, t))
        return self.or_(self.and_(a, self.not_(b)), self.and_(self.not_(a), b))

    def mux(self, a, b, sel):
        return self.or_(self.and_(a, self.not_(sel)), self.and_(b, sel))

    def half_adder(self, a, b):
        if self.level >= 2 and a >= 0 and b >= 0:
            t = self.nand(a, b)
            return self.nand(self.nand(a, t), self.nand(b, t)), self.not_(t)
        return self.xor(a, b), self.and_(a, b)

    def full_adder(self, a, b, c):
        if self.level >= 2 and a >= 0 and b >= 0 and c >= 0:
            t1 = self.nand(a, b)
            x = self.nand(self.nand(a, t1), self.nand(b, t1))
            t4 = self.nand(x, c)
            s = self.nand(self.nand(x, t4), self.nand(c, t4))
            return s, self.nand(t4, t1)
        s1, c1 = self.half_adder(a, b)
        s2, c2 = self.half_adder(s1, c)
        return s2, self.or_(c1, c2)

    def finalize(self, outputs):
        outs = {k: [self.real(w) for w in v] for k, v in outputs.items()}
        live, stack = set(), [w for v in outs.values() for w in v]
        while stack:
            w = stack.pop()
            if w in live:
                continue
            live.add(w)
            if self.kind[w] == 'N':
                stack += [self.a[w], self.b[w]]
            elif self.kind[w] == 'D':
                assert self.a[w] >= 0, 'DFF without D input'
                stack.append(self.a[w])
        ins = [w for w in range(len(self.kind)) if self.kind[w] == 'I']
        dffs = [w for w in range(len(self.kind)) if self.kind[w] == 'D' and w in live]
        gts = [w for w in range(len(self.kind)) if self.kind[w] == 'N' and w in live]
        nid = {w: i for i, w in enumerate(ins + dffs + gts)}
        c = Compiled()
        c.n_in, c.n_dff = len(ins), len(dffs)
        c.gates = [(nid[self.a[w]], nid[self.b[w]]) for w in gts]
        c.dffd = [nid[self.a[w]] for w in dffs]
        c.gate_tags = [self.tag[w] for w in gts]
        c.dff_tags = [self.tag[w] for w in dffs]
        c.buses = {k: [nid[w] for w in v] for k, v in self.buses.items()}
        c.outs = {k: [nid[w] for w in v] for k, v in outs.items()}
        c.nid = nid
        c.hint = {nid[w]: k for w, k in self.pos.items() if w in nid}
        return c


class Compiled:
    @property
    def nwires(self):
        return self.n_in + self.n_dff + len(self.gates)

    def by_scope(self):
        g, d = {}, {}
        for t in self.gate_tags:
            g[t] = g.get(t, 0) + 1
        for t in self.dff_tags:
            d[t] = d.get(t, 0) + 1
        return g, d

    def to_text(self):
        base = self.n_in + self.n_dff
        lines = [f'in {self.n_in}', f'dff {self.n_dff}']
        lines += [f'q{i} <= w{d}' for i, d in enumerate(self.dffd)]
        lines += [f'w{base + i} = NAND w{a} w{b}' for i, (a, b) in enumerate(self.gates)]
        return '\n'.join(lines) + '\n'


class Sim:
    def __init__(self, c, lanes=1):
        self.c, self.lanes, self.M = c, lanes, (1 << lanes) - 1
        self.v = [0] * c.nwires
        base = c.n_in + c.n_dff
        self.g = [(base + i, a, b) for i, (a, b) in enumerate(c.gates)]

    def set(self, name, bits):
        for w, x in zip(self.c.buses[name], bits):
            self.v[w] = x & self.M

    def eval(self):
        v, M = self.v, self.M
        for o, a, b in self.g:
            v[o] = ~(v[a] & v[b]) & M

    def tick(self):
        v = self.v
        new = [v[d] for d in self.c.dffd]
        for i, x in enumerate(new):
            v[self.c.n_in + i] = x

    def get(self, name):
        return [self.v[w] for w in self.c.outs[name]]


def bus_not(n, x):
    return [n.not_(b) for b in x]


def bus_and(n, x, y):
    return [n.and_(a, b) for a, b in zip(x, y)]


def bus_mux(n, a, b, sel):
    return [n.mux(p, q, sel) for p, q in zip(a, b)]


def adder_c(n, x, y, cin=ZERO):
    c, s = cin, []
    for a, b in zip(x, y):
        sm, c = n.full_adder(a, b, c)
        s.append(sm)
    return s, c


def adder(n, x, y, cin=ZERO):
    return adder_c(n, x, y, cin)[0]


def incrementer(n, x, cin=ONE):
    c, s = cin, []
    for p in x:
        sm, c = n.half_adder(p, c)
        s.append(sm)
    return s


def or_tree(n, bits):
    bits = list(bits)
    while len(bits) > 1:
        nxt = [n.or_(bits[i], bits[i + 1]) for i in range(0, len(bits) - 1, 2)]
        if len(bits) % 2:
            nxt.append(bits[-1])
        bits = nxt
    return bits[0]


def alu_c(n, x, y, zx, nx, zy, ny, f, no, cin=ZERO):
    zero = [ZERO] * len(x)
    x1 = bus_mux(n, x, zero, zx)
    x2 = bus_mux(n, x1, bus_not(n, x1), nx)
    y1 = bus_mux(n, y, zero, zy)
    y2 = bus_mux(n, y1, bus_not(n, y1), ny)
    sm, cout = adder_c(n, x2, y2, cin)
    fxy = bus_mux(n, bus_and(n, x2, y2), sm, f)
    out = bus_mux(n, fxy, bus_not(n, fxy), no)
    zr = n.not_(or_tree(n, out))
    return out, zr, out[-1], cout


def alu(n, x, y, zx, nx, zy, ny, f, no):
    out, zr, ng, _ = alu_c(n, x, y, zx, nx, zy, ny, f, no)
    return out, zr, ng


def register(n, q, load, d):
    for qi, di in zip(q, d):
        n.set_d(qi, n.mux(qi, di, load))


def mux_tree(n, items, sel):
    layer = list(items)
    for b in sel:
        nxt = [bus_mux(n, layer[i], layer[i + 1], b) for i in range(0, len(layer) - 1, 2)]
        if len(layer) % 2:
            nxt.append(layer[-1])
        layer = nxt
    assert len(layer) == 1
    return layer[0]


def eq_const(n, bits, c):
    t = ONE
    for i, b in enumerate(bits):
        t = n.and_(t, b if (c >> i) & 1 else n.not_(b))
    return t


def onehot(n, bits, base=ONE):
    sel = [base]
    for b in bits:
        nb = n.not_(b)
        sel = [n.and_(s, nb) for s in sel] + [n.and_(s, b) for s in sel]
    return sel


def build_alu(level=1, w=16):
    n = Net(level)
    x, y = n.bus_in('x', w), n.bus_in('y', w)
    ctl = [n.input(k) for k in ('zx', 'nx', 'zy', 'ny', 'f', 'no')]
    with n.scope('alu'):
        out, zr, ng = alu(n, x, y, *ctl)
    return n.finalize({'out': out, 'zr': [zr], 'ng': [ng]})


def build_cpu(level=1, w=16, aw=None):
    aw = min(w, 15) if aw is None else aw
    aA = max(w, aw)
    assert 1 <= w and 1 <= aw and aA <= 16
    n = Net(level)
    inM, ins, reset = n.bus_in('inM', w), n.bus_in('inst', 16), n.input('reset')
    A, D, PC = n.dff_bus(aA), n.dff_bus(w), n.dff_bus(aw)
    with n.scope('decode'):
        isC = ins[15]
        isA = n.not_(isC)
    with n.scope('mux_y'):
        y = bus_mux(n, A[:w], inM, ins[12])
    with n.scope('alu'):
        out, zr, ng = alu(n, D, y, ins[11], ins[10], ins[9], ins[8], ins[7], ins[6])
    with n.scope('areg'):
        loadA = n.or_(isA, n.and_(isC, ins[5]))
        register(n, A, loadA, bus_mux(n, ins[:aA], out + [ZERO] * (aA - w), isC))
    with n.scope('dreg'):
        register(n, D, n.and_(isC, ins[4]), out)
    with n.scope('pc'):
        pos = n.and_(n.not_(ng), n.not_(zr))
        jump = n.and_(isC, n.or_(n.or_(n.and_(ins[2], ng), n.and_(ins[1], zr)),
                                 n.and_(ins[0], pos)))
        nxt = bus_mux(n, incrementer(n, PC), A[:aw], jump)
        nr = n.not_(reset)
        for q, d in zip(PC, nxt):
            n.set_d(q, n.and_(d, nr))
    with n.scope('decode'):
        writeM = n.and_(isC, ins[3])
    return n.finalize({'outM': out, 'writeM': [writeM], 'addressM': A[:aw], 'pc': PC})


def build_cpu_serial(level=1, w=8, aw=12, k=4, ext=None):
    aA = max(w, aw)
    assert w % k == 0 and w // k >= 2 and aA <= 16
    P = w // k
    nb = (P - 1).bit_length()
    if ext is None:
        n = Net(level)
        inM, ins, reset = n.bus_in('inM', w), n.bus_in('inst', 16), n.input('reset')
        A = n.dff_bus(aA)
    else:
        n, inM, ins, reset, A = ext
    PC = n.dff_bus(aw)
    ring = [n.dff_bus(k) for _ in range(P)]
    sr = [n.dff_bus(k) for _ in range(P - 1)]
    cb, za, cnt = n.dff_bus(1)[0], n.dff_bus(1)[0], n.dff_bus(nb)
    with n.scope('phase'):
        first, last = eq_const(n, cnt, 0), eq_const(n, cnt, P - 1)
        cn = incrementer(n, cnt)
        if P & (P - 1):
            cn = [n.and_(b, n.not_(last)) for b in cn]
        for q, d in zip(cnt, cn):
            n.set_d(q, d)
    with n.scope('decode'):
        isC = ins[15]
        isA = n.not_(isC)
    with n.scope('mux_y'):
        yf = bus_mux(n, A[:w], inM, ins[12])
        y = mux_tree(n, [yf[i * k:(i + 1) * k] for i in range(P)], cnt)
    with n.scope('alu'):
        cin = n.and_(n.not_(first), cb)
        out, zr, ng, cout = alu_c(n, ring[0], y, ins[11], ins[10], ins[9], ins[8], ins[7], ins[6], cin)
        n.set_d(cb, cout)
        zrn = zr
        za_d = zrn if P == 2 else n.and_(zrn, n.or_(first, za))
        n.set_d(za, za_d)
        zr_tot = n.and_(za, zrn)
    with n.scope('dreg'):
        wr_d = n.and_(isC, ins[4])
        for i in range(P - 1):
            for q, d in zip(ring[i], ring[i + 1]):
                n.set_d(q, d)
        for q, h, o in zip(ring[P - 1], ring[0], out):
            n.set_d(q, n.mux(h, o, wr_d))
    with n.scope('result'):
        for q, d in zip(sr[0], out):
            n.set_d(q, d)
        for i in range(1, P - 1):
            for q, d in zip(sr[i], sr[i - 1]):
                n.set_d(q, d)
        res = [b for st in reversed(sr) for b in st] + out
    with n.scope('areg'):
        loadA = n.and_(n.or_(isA, n.and_(isC, ins[5])), last)
        register(n, A, loadA, bus_mux(n, ins[:aA], res + [ZERO] * (aA - w), isC))
    with n.scope('pc'):
        ngf = out[-1]
        pos = n.and_(n.not_(ngf), n.not_(zr_tot))
        jump = n.and_(isC, n.or_(n.or_(n.and_(ins[2], ngf), n.and_(ins[1], zr_tot)),
                                 n.and_(ins[0], pos)))
        nxt = bus_mux(n, incrementer(n, PC, last), A[:aw], n.and_(jump, last))
        nr = n.not_(n.and_(reset, last))
        for q, d in zip(PC, nxt):
            n.set_d(q, n.and_(d, nr))
    with n.scope('decode'):
        writeM = n.and_(n.and_(isC, ins[3]), last)
    outs = {'outM': res, 'writeM': [writeM], 'addressM': A[:aw], 'pc': PC}
    return outs if ext is not None else n.finalize(outs)


def build_ram(level=1, abits=3, wbits=16):
    n = Net(level)
    addr, din, load = n.bus_in('addr', abits), n.bus_in('din', wbits), n.input('load')
    words, h = 1 << abits, abits // 2
    with n.scope('decode'):
        lo = onehot(n, addr[:h])
        hi = onehot(n, addr[h:], base=load)
        we = [n.and_(hi[w >> h], lo[w & ((1 << h) - 1)]) for w in range(words)]
    with n.scope('cells'):
        q = [n.dff_bus(wbits) for _ in range(words)]
        for w in range(words):
            register(n, q[w], we[w], din)
    with n.scope('readmux'):
        dout = []
        for j in range(wbits):
            layer = [q[w][j] for w in range(words)]
            for k in range(abits):
                layer = [n.mux(layer[i], layer[i + 1], addr[k]) for i in range(0, len(layer), 2)]
            dout.append(layer[0])
    return n.finalize({'dout': dout})


def build_machine(level=2, w=8, aw=12, k=4, debug=False):
    aA = max(w, aw)
    n = Net(level)
    ins, reset = n.bus_in('inst', 16), n.input('reset')
    words, h = 1 << aw, aw // 2
    A = n.dff_bus(aA)
    addr = A[:aw]
    q = []
    for wd in range(words):
        with n.at(('cell', wd, 0)):
            q.append(n.dff_bus(w))
    for wd in range(words):
        for j in range(1, w):
            n.pos[q[wd][j]] = ('cell', wd, j)
    with n.scope('readmux'):
        dout = []
        for j in range(w):
            layer = [(q[wd][j], wd) for wd in range(words)]
            span = 1
            for kk in range(aw):
                nxt = []
                for i in range(0, len(layer), 2):
                    (a, lo), (b, _) = layer[i], layer[i + 1]
                    with n.at(('cell', lo + span, j)):
                        nxt.append((n.mux(a, b, addr[kk]), lo))
                layer, span = nxt, span * 2
            dout.append(layer[0][0])
    cpu_start = len(n.kind)
    cpu = build_cpu_serial(level, w, aw, k, ext=(n, dout, ins, reset, A))
    cpu_end = len(n.kind)
    with n.scope('decode'):
        lo = onehot(n, addr[:h])
        hi = onehot(n, addr[h:], base=cpu['writeM'][0])
        we = []
        for wd in range(words):
            with n.at(('word', wd)):
                we.append(n.and_(hi[wd >> h], lo[wd & ((1 << h) - 1)]))
    with n.scope('cells'):
        for wd in range(words):
            for j in range(w):
                with n.at(('cell', wd, j)):
                    n.set_d(q[wd][j], n.mux(q[wd][j], cpu['outM'][j], we[wd]))
    outs = {'pc': cpu['pc'], 'addressM': cpu['addressM'], 'outM': cpu['outM'], 'writeM': cpu['writeM']}
    if debug:
        outs['mem'] = [b for wd in range(words) for b in q[wd]]
    c = n.finalize(outs)
    c.cpu_range = (cpu_start, cpu_end)
    c.cpu_ids = {c.nid[wd] for wd in range(cpu_start, cpu_end) if wd in c.nid} | {c.nid[x] for x in ins + [reset] + A}
    c.q = q
    return c
