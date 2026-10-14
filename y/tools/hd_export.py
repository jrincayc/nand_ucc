#!/usr/bin/env python3
"""hd_export.py -- writes the readable seed description hd/core.hd (the textbook Hack-vN-AB machine).
It reuses the nandgen helper functions (bus_mux, adder_c, ...) and nl_hackvn.hackvn_core through a Net-like object
that emits one *instance of a library cell per call* instead of gates (nandgen level 0 semantics: no folding,
no sharing).  Dead instances are removed.  The library modules are the textbook expansions, written below.
usage: python3 hd_export.py OUT.hd [ram_abits]      (HACK_AB selects the address width, default 14)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, '..', 'isa'), HERE]
from contextlib import contextmanager
import nandgen as ng
from nandgen import ONE, ZERO
import hd as H
import common
from nl_hackvn import hackvn_core, AB


# ------------------------------------------------------------------------------------------- textbook library
class MB:
    """Module builder: textbook (level 0) expansions of the cells, as gate lists."""
    def __init__(self, name, n_in, n_out):
        self.m = H.Module(name, n_in, n_out)
    def nand(self, a, b, why=''):
        self.m.gates.append((a, b)); self.m.comments.append(why); return self.m.n_in + len(self.m.gates) - 1
    def not_(self, a, why=''): return self.nand(a, a, why or 'not')
    def and_(self, a, b, why=''): return self.not_(self.nand(a, b, 'nand of the and'), why or 'and = not(nand)')
    def or_(self, a, b, why=''):
        return self.nand(self.not_(a, 'not a'), self.not_(b, 'not b'), why or 'or = nand(not a, not b)')
    def xor(self, a, b):
        return self.or_(self.and_(a, self.not_(b, 'not b'), 'a and not b'), self.and_(self.not_(a, 'not a'), b, 'not a and b'), 'xor = (a and not b) or (not a and b)')
    def done(self, *outs): self.m.outs = list(outs); return self.m


def textbook_library():
    lib = []
    b = MB('not', 1, 1); lib.append(b.done(b.not_(0)))
    b = MB('and', 2, 1); lib.append(b.done(b.and_(0, 1)))
    b = MB('or', 2, 1); lib.append(b.done(b.or_(0, 1)))
    b = MB('xor', 2, 1); lib.append(b.done(b.xor(0, 1)))
    b = MB('mux', 3, 1)                       # i0 = a (sel=0), i1 = b (sel=1), i2 = sel
    lib.append(b.done(b.or_(b.and_(0, b.not_(2, 'not sel'), 'a and not sel'), b.and_(1, 2, 'b and sel'), 'mux = or(...)')))
    b = MB('ha', 2, 2)                        # outputs: sum, carry
    s = b.xor(0, 1); c = b.and_(0, 1, 'carry = a and b'); lib.append(b.done(s, c))
    b = MB('fa', 3, 2)                        # outputs: sum, carry
    s1 = b.xor(0, 1); c1 = b.and_(0, 1, 'c1 = a and b')
    s2 = b.xor(s1, 2); c2 = b.and_(s1, 2, 'c2 = s1 and cin')
    lib.append(b.done(s2, b.or_(c1, c2, 'carry = c1 or c2')))
    return lib


def ram_tile_module():
    """One RAM byte: write-enable/decode head and 8 bit slices (chain-read RAM v2 of machine_row.py)."""
    m = H.Module('ram_word', 19, 16, 'tile')
    I_HIW, I_HIR, I_LO, I_WD, I_PREV = 0, 1, 2, 3, 11
    def add(kind, *ins, why=''):
        m.gates.append((kind,) + ins); m.comments.append(why); return m.n_in + len(m.gates) - 1
    nwen = add('nand', I_HIW, I_LO, why='write enable, active low = nand(hiW, lo)')
    wen = add('nand', nwen, nwen, why='write enable')
    ndec = add('nand', I_HIR, I_LO, why='read select, active low = nand(hiR, lo)')
    dec = add('nand', ndec, ndec, why='read select')
    nacc, acc = [], []
    for j in range(8):
        d = m.n_in + len(m.gates)                       # the DFF is the next gate; its D input is 'o' = d + 3
        add('dff', d + 3, why=f'bit {j} storage')
        t1 = add('nand', d, nwen, why=f'bit {j}: keep path')
        t2 = add('nand', I_WD + j, wen, why=f'bit {j}: write path')
        o = add('nand', t1, t2, why=f'bit {j}: next value')
        np_ = add('nand', dec, d, why=f'bit {j}: selected bit, inverted')
        a = add('nand', I_PREV + j, np_, why=f'bit {j}: chain value (or of this bit with the previous words)')
        n = add('nand', a, a, why=f'bit {j}: inverted chain value, passed to the next word')
        acc.append(a); nacc.append(n)
    m.outs = nacc + acc
    return m


# ------------------------------------------------------------------------------------------- HD-emitting Net
class HDNet:
    level = 0
    DFF_NAMES = ['pc', 'a', 'd', 'irlo', 'irhi', 'st']

    def __init__(self):
        self.insts = []                       # dict(name, type, ins=[wire|const], outs=[wire])
        self.desc = {}                        # wire -> ('rom', j) | ('ramrd', j) | ('run',) | ('dff', k) | ('out', inst, o)
        self.dffs = []                        # dict(name, d=wire|const)
        self._w = 0; self._scope = ['top']; self.buses = {}; self._cnt = {}; self._ndffbus = 0

    def _wire(self, d):
        w = self._w; self._w += 1; self.desc[w] = d; return w
    @contextmanager
    def scope(self, name):
        self._scope.append(name)
        try: yield
        finally: self._scope.pop()
    @contextmanager
    def at(self, key): yield
    def input(self, name):
        w = self._wire(('run',) if name == 'run' else (name,)); self.buses[name] = [w]; return w
    def bus_in(self, name, n):
        ws = [self._wire((name[:-0] if False else ('rom' if name == 'romdata' else 'ramrd'), j)) for j in range(n)]
        self.buses[name] = ws; return ws
    def dff_bus(self, n):
        base = self.DFF_NAMES[self._ndffbus]; self._ndffbus += 1
        ws = []
        for j in range(n):
            self.dffs.append(dict(name=f'{base}.{j}', d=None))
            ws.append(self._wire(('dff', len(self.dffs) - 1)))
        return ws
    def set_d(self, q, d): self.dffs[self.desc[q][1]]['d'] = d
    def _cell(self, typ, ins, nout=1, name=None):
        sc = self._scope[-1]; k = self._cnt.get((sc, typ), 0); self._cnt[(sc, typ)] = k + 1
        inst = dict(name=name or f'{sc}.{typ}{k}', type=typ, ins=list(ins), outs=[])
        self.insts.append(inst)
        for o in range(nout): inst['outs'].append(self._wire(('out', len(self.insts) - 1, o)))
        return inst['outs'] if nout > 1 else inst['outs'][0]
    def _raw(self, a, b): return self._cell('nand', [a, b])
    def nand_named(self, name, a, b): return self._cell('nand', [a, b], name=name)
    def nand(self, a, b): return self._cell('nand', [a, b])
    def not_(self, a): return self._cell('not', [a])
    def and_(self, a, b): return self._cell('and', [a, b])
    def or_(self, a, b): return self._cell('or', [a, b])
    def xor(self, a, b): return self._cell('xor', [a, b])
    def mux(self, a, b, sel): return self._cell('mux', [a, b, sel])
    def half_adder(self, a, b): return tuple(self._cell('ha', [a, b], 2))
    def full_adder(self, a, b, c): return tuple(self._cell('fa', [a, b, c], 2))


def export_hd(ram_abits=5, library=None):
    n = HDNet()
    romdata = n.bus_in('romdata', 8)
    n.bus_in('ramrd', 8)
    run = n.input('run')
    ramrd = n.buses['ramrd']
    reset = n.nand_named('reset', run, run)            # run feeds exactly one gate (both pins)
    box = {}
    def get_rdata(addr):
        with n.scope('decode'):
            hiz = ONE
            for b in addr[ram_abits:AB]: hiz = n.and_(hiz, n.not_(b))
            box['ram_sel'] = hiz
            arm = n.not_(addr[AB - 1])
            for b in addr[4:AB - 1]: arm = n.and_(arm, b)
            box['arm_sel'] = arm
            return [n.nand(n.nand(hiz, ramrd[j]), n.nand(addr[AB - 1], romdata[j])) for j in range(8)]
    s = hackvn_core(n, reset, get_rdata)
    addr, we = s['addr'], s['we']
    with n.scope('decode'):
        we_ram = n.and_(we, box['ram_sel'])
        arm_en = n.and_(we, box['arm_sel'])
    # ---- RAM: predecode trees (explicit instances) and the per-byte tile chain
    W, h = 1 << ram_abits, ram_abits // 2
    assert h >= 2 and ram_abits - h >= 2, 'ram_abits >= 4'
    A, WD = addr[:ram_abits], s['wdata']
    pre = {}
    with n.scope('ram'):
        nA = [n.not_(a) for a in A]
        def tree(ks, label):
            sel = [None]
            for step, k in enumerate(ks):
                last = step == len(ks) - 1
                nxt0 = [(n.and_(x, nA[k]) if x is not None else nA[k]) for x in sel]
                nxt1 = [(n.and_(x, A[k]) if x is not None else A[k]) for x in sel]
                sel = nxt0 + nxt1
            return sel
        lo = tree(range(h), 'lo'); hiR = tree(range(h, ram_abits), 'hiR')
        hiW = [n.and_(x, we_ram) for x in hiR]
    ports = dict(rom_addr=addr[:AB - 1], arm_addr=addr[:4], wdata=WD, arm_en=[arm_en])   # EN last: its wire is the last before RUN
    return n, dict(ram_abits=ram_abits, W=W, h=h, lo=lo, hiR=hiR, hiW=hiW, WD=WD, ports=ports, ramrd=ramrd, we_ram=we_ram)


def build_hd(ram_abits=5, with_ram=True):
    n, R = export_hd(ram_abits)
    # ---- liveness: ports + DFF D inputs (+ the predecode lines when the RAM is present)
    live, stack = set(), []
    def need(w):
        if w >= 0: stack.append(w)
    for ws in R['ports'].values():
        for w in ws: need(w)
    for w in R['hiR'] + R['hiW'] + R['lo']: need(w)
    for w in R['WD']: need(w)
    for d in n.dffs: need(d['d'])
    seen_w = set()
    while stack:
        w = stack.pop()
        if w in seen_w: continue
        seen_w.add(w); d = n.desc[w]
        if d[0] == 'out':
            inst = n.insts[d[1]]; live.add(d[1])
            for x in inst['ins']: need(x)
        elif d[0] == 'dff':
            need(n.dffs[d[1]]['d'])
    # ---- constants (explicit instances at the start of the body)
    const_used = set(); usable = {}
    def refs_of(inst): return inst['ins']
    for i in live:
        for x in n.insts[i]['ins']:
            if x in (ONE, ZERO): const_used.add(x)
    for d in n.dffs:
        if d['d'] in (ONE, ZERO): const_used.add(d['d'])
    for ws in R['ports'].values():
        for w in ws:
            if w in (ONE, ZERO): const_used.add(w)
    hd = H.HD(); hd.params['ab'] = AB; hd.params['ram_abits'] = ram_abits
    hd.modules = (textbook_library() if True else []) + ([ram_tile_module()] if with_ram else [])
    names = {}
    def refname(w):
        if w == ONE: return 'one'
        if w == ZERO: return 'zero'
        d = n.desc[w]
        if d[0] == 'rom': return f'rom{d[1]}'
        if d[0] == 'ramrd': return f'ramrd{d[1]}'
        if d[0] == 'run': return 'run'
        if d[0] == 'dff': return n.dffs[d[1]]['name']
        inst = n.insts[d[1]]
        return inst['name'] if len(inst['outs']) == 1 else f'{inst["name"]}.{d[2]}'
    for d in n.dffs:
        hd.body.append(H.Inst(d['name'], 'dff', [refname(d['d'])], 'register bit'))
    # constants: one = nand(rom0, nand(rom0, rom0)) as nandgen level 0 builds it; zero = not(one)
    if ONE in const_used or ZERO in const_used:
        hd.body.append(H.Inst('c.n', 'nand', ['rom0', 'rom0'], 'constant helper'))
        hd.body.append(H.Inst('one', 'nand', ['rom0', 'c.n'], 'constant 1 = nand(x, not x)'))
    if ZERO in const_used:
        hd.body.append(H.Inst('zero', 'nand', ['one', 'one'], 'constant 0'))
    for i, inst in enumerate(n.insts):
        if i in live: hd.body.append(H.Inst(inst['name'], inst['type'], [refname(x) for x in inst['ins']]))
    if with_ram:
        hd.chain = dict(module='ram_word', count=R['W'], rules=[])
        hd.chain['lists'] = dict(hiW=[refname(w) for w in R['hiW']], hiR=[refname(w) for w in R['hiR']], lo=[refname(w) for w in R['lo']])
        hd.chain['rules'] = [(0, 'pick', ['hiW', 'hi', R['h']]), (1, 'pick', ['hiR', 'hi', R['h']]), (2, 'pick', ['lo', 'lo', (1 << R['h']) - 1])] + \
                            [(3 + j, 'bcast', [refname(R['WD'][j])]) for j in range(8)] + \
                            [(11 + j, 'prev', [j]) for j in range(8)]
    names_of = lambda ws: [refname(w) for w in ws]
    for key, ws in R['ports'].items():
        for j, w in enumerate(ws): hd.ports.append((f'{key}{j}' if len(ws) > 1 else key, refname(w)))
    return hd, n, R


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '-'
    rab = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    hd, n, R = build_hd(rab)
    txt = H.write(hd)
    (sys.stdout.write(txt) if out == '-' else open(out, 'w').write(txt))
    print(f'# AB={AB} ram_abits={rab}: {len(hd.body)} body instances, {len(hd.modules)} modules', file=sys.stderr)
