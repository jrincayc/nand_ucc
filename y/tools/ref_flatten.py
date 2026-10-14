#!/usr/bin/env python3
"""ref_flatten.py -- reference flattener (Python) for the HD of section 4/5 of Y_SPEC.md.  The ROM program must
reproduce its command sequence exactly (as a set, wires in any order).  Also converts the flat machine to a nandgen
`Compiled` netlist so that the existing lockstep/fast-simulation tools can run it.

Layout (relative to the issuing arm's child origin (ox, oy)):  arm at (ox,oy); ROM at (ox,oy+ARM_H);
core node i at (ox+6+2i, oy+9); tie-high = node n_core, last of the row; RAM tile k (one RAM byte per column),
node j at (ox+6+2k, oy+13+2j).   Pins: NAND A(0,0) B(0,1) Y(1,0); DFF D(0,0) Q(1,0)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', 'isa')]
import hd as H

ARM_H = 9
STRIDE = 140
CORE_Y, TILE_Y0 = 9, 13


class Flat:
    pass


def flatten(hd):
    f = Flat(); f.hd = hd
    ab = hd.params['ab']; f.rom_abits = ab - 1
    f.kind, f.ins = [], []                      # core nodes 0..n_core-1: 'nand'|'dff' ; ins: list of src
    names = {}                                  # instance name -> list of output node ids
    pend = []                                   # (node, [ref strings], module, inst) resolved after all nodes exist
    for inst in hd.body:
        base = len(f.kind)
        if inst.type in ('nand', 'dff'):
            f.kind.append(inst.type); f.ins.append(None); names[inst.name] = [base]
            pend.append((base, inst, None))
        else:
            m = hd.module(inst.type)
            for g in range(m.n_gates()): f.kind.append('hole' if m.gates[g] is None else 'nand'); f.ins.append(None)
            outs = [base + (o - m.n_in) for o in m.outs]
            names[inst.name] = outs
            for k, o in enumerate(outs): names[f'{inst.name}.{k}'] = [o]
            pend.append((base, inst, m))
    f.n_core = len(f.kind); f.tie = f.n_core
    f.names = names
    f.W = hd.chain['count'] if hd.chain else 0
    f.tile = hd.module(hd.chain['module']) if hd.chain else None
    f.TG = f.tile.n_gates() if f.tile else 0
    f.n_nodes = f.n_core + 1 + f.W * f.TG

    def tile_id(k, j): return f.n_core + 1 + k * f.TG + j

    def resolve(ref):
        if ref == 'run': return ('run',)
        if ref == 'tie': return ('n', f.tie)
        if ref.startswith('rom') and ref[3:].isdigit(): return ('rom', int(ref[3:]))
        if ref.startswith('ramrd') and ref[5:].isdigit():
            return ('n', tile_id(f.W - 1, f.tile.outs[8 + int(ref[5:])] - f.tile.n_in))
        if ref not in names: raise H.HDError(f'unknown reference {ref}')
        o = names[ref]
        if len(o) != 1: raise H.HDError(f'{ref} has several outputs; use {ref}.k')
        return ('n', o[0])
    f.resolve = resolve
    for base, inst, m in pend:
        src = [resolve(r) for r in inst.refs]
        if m is None:
            if len(src) != (1 if inst.type == 'dff' else 2): raise H.HDError(f'{inst.name}: wrong ref count')
            f.ins[base] = src
        else:
            if len(src) != m.n_in: raise H.HDError(f'{inst.name}: wrong ref count')
            for g, x in enumerate(m.gates):
                if x is None: continue
                a, b = x
                f.ins[base + g] = [src[s] if s < m.n_in else ('n', base + s - m.n_in) for s in (a, b)]
    # ---- tiles
    f.tkind, f.tins = [], []
    if f.tile:
        t = f.tile; ch = hd.chain
        rule = {i: (kind, args) for i, kind, args in ch['rules']}
        assert sorted(rule) == list(range(t.n_in)), 'every tile input needs exactly one rule'
        for k in range(f.W):
            def tin(s):
                kind, args = rule[s]
                if kind == 'bcast': return resolve(args[0])
                if kind == 'prev':
                    return ('n', f.tie) if k == 0 else ('n', tile_id(k - 1, t.outs[args[0]] - t.n_in))
                if kind == 'pick':
                    lst = ch['lists'][args[0]]
                    idx = (k >> args[2]) if args[1] == 'hi' else (k & args[2])
                    return resolve(lst[idx])
                raise H.HDError(f'bad rule {kind}')
            for g, x in enumerate(t.gates):
                sgn = lambda s: tin(s) if s < t.n_in else ('n', tile_id(k, s - t.n_in))
                if x[0] == 'dff': f.tkind.append('dff'); f.tins.append([sgn(x[1])])
                else: f.tkind.append('nand'); f.tins.append([sgn(x[1]), sgn(x[2])])
    # ---- ports
    f.ports = [(n, resolve(r)) for n, r in hd.ports]
    return f


def node_kind(f, i):
    if i < f.n_core: return f.kind[i]
    if i == f.tie: return 'tie'
    return f.tkind[i - f.n_core - 1]


def node_ins(f, i):
    if i < f.n_core: return f.ins[i]
    if i == f.tie: return []
    return f.tins[i - f.n_core - 1]


def node_pos(f, i, ox=0, oy=STRIDE):
    if i <= f.n_core: return (ox + 6 + 2 * i, oy + CORE_Y)
    k, j = divmod(i - f.n_core - 1, f.TG)
    return (ox + 6 + 2 * k, oy + TILE_Y0 + 2 * j)


def counts(f):
    from collections import Counter
    c = Counter(node_kind(f, i) for i in range(f.n_nodes))
    return dict(nand=c['nand'] + c['tie'], dff=c['dff'], nodes=f.n_nodes)


def commands(f, rom_bytes, ox=0, oy=STRIDE):
    """Reference build sequence (spec v0.5 section 7 order).  Entries: ('place', kind, x, y), ('rom', rx, ry, addr, val),
    ('wire', x1, y1, x2, y2).  The ARM is placed last; run wires are last."""
    rom_h = max(f.rom_abits, 8); y0 = oy + ARM_H
    rx, ry, ax, ay = ox, y0, ox, oy
    cmds = [('place', 'dff' if node_kind(f, i) == 'dff' else 'nand', *node_pos(f, i, ox, oy)) for i in range(f.n_nodes) if node_kind(f, i) != 'hole']
    cmds.append(('place', 'rom', rx, ry)); cmds.append(('place', 'arm', ax, ay))
    for a, v in enumerate(rom_bytes):
        if v: cmds.append(('rom', rx, ry, a, v))
    def out_site(s):
        if s[0] == 'rom': return (rx + 1, ry + s[1])
        if s[0] == 'run': return out_site(('n', f.tie))
        x, y = node_pos(f, s[1], ox, oy); return (x + 1, y)
    run_wires = []
    for i in range(f.n_nodes):
        k = node_kind(f, i)
        if k in ('tie', 'hole'): continue
        x, y = node_pos(f, i, ox, oy)
        for pin, s in enumerate(node_ins(f, i)):
            w = ('wire',) + out_site(s) + (x, y + pin)
            (run_wires if s[0] == 'run' else cmds).append(w)
    P = dict(f.ports)
    for n, s in f.ports:
        if n.startswith('rom_addr'): cmds.append(('wire',) + out_site(s) + (rx, ry + int(n[8:])))
        elif n.startswith('arm_addr'): cmds.append(('wire',) + out_site(s) + (ax, ay + int(n[8:])))
        elif n.startswith('wdata'): cmds.append(('wire',) + out_site(s) + (ax + 1, ay + int(n[5:])))
    cmds.append(('wire',) + out_site(P['arm_en']) + (ax, ay + 4))
    cmds += run_wires
    return cmds


def to_compiled(f):
    """nandgen.Compiled for simulation.  Inputs: romdata[8], run, tie (tie must be held at 1: it is the unwired NAND of the
    real machine).  The ROM address and arm interface are outputs.  RAM bits are DFFs named in c.ram_q[k][j]."""
    import nandgen as ng
    inputs = [('rom', j) for j in range(8)] + [('run',)]
    n_in = len(inputs)
    dff_nodes = [i for i in range(f.n_nodes) if node_kind(f, i) == 'dff']
    nand_nodes = [i for i in range(f.n_nodes) if node_kind(f, i) in ('nand',)]
    wire = {}
    for k, s in enumerate(inputs): wire[s] = k
    # tie node = constant 1: model as an extra input
    n_in += 1; wire[('tie',)] = n_in - 1
    for k, i in enumerate(dff_nodes): wire[('n', i)] = n_in + k
    base = n_in + len(dff_nodes)
    # topological order of NAND nodes
    order, state = [], {}
    def src_w(s):
        if s == ('run',): return wire[('run',)]
        if s[0] == 'n' and s[1] == f.tie: return wire[('tie',)]
        return wire.get(s)
    sys.setrecursionlimit(100000)
    def visit(i):
        st = state.get(i)
        if st == 2: return
        if st == 1: raise H.HDError(f'combinational loop through node {i}')
        state[i] = 1
        for s in node_ins(f, i):
            if s[0] == 'n' and node_kind(f, s[1]) == 'nand': visit(s[1])
        state[i] = 2; order.append(i)
    for i in nand_nodes: visit(i)
    for k, i in enumerate(order): wire[('n', i)] = base + k
    c = ng.Compiled()
    c.n_in, c.n_dff = n_in, len(dff_nodes)
    c.gates = [tuple(src_w(s) if src_w(s) is not None else wire[s] for s in node_ins(f, i)) for i in order]
    c.dffd = [src_w(node_ins(f, i)[0]) for i in dff_nodes]
    c.gate_tags = ['x'] * len(order); c.dff_tags = ['x'] * len(dff_nodes)
    c.buses = {'romdata': list(range(8)), 'run': [8], 'tie': [n_in - 1]}
    def w_of(s): return src_w(s)
    c.outs = {}
    for key in ('rom_addr', 'arm_addr', 'wdata'):
        c.outs[key] = [w_of(s) for n, s in f.ports if n.startswith(key)]
    c.outs['arm_en'] = [w_of(dict(f.ports)['arm_en'])]
    named = {}
    for nm, ids in f.names.items():
        if nm.split('.')[0] in ('pc', 'a', 'd', 'irlo', 'irhi', 'st') and len(ids) == 1 and nm.count('.') == 1 and nm.split('.')[1].isdigit(): named.setdefault(nm.split('.')[0], []).append((int(nm.split('.')[1]), ids[0]))
    for key, lst in named.items(): c.outs[key] = [wire[('n', i)] for _, i in sorted(lst)]
    c.nid = {}; c.hint = {}
    c.ram_q = [[wire[('n', f.n_core + 1 + k * f.TG + g)] for g, x in enumerate(f.tile.gates) if x[0] == 'dff'] for k in range(f.W)] if f.tile else []
    return c


if __name__ == '__main__':
    hd = H.read(open(sys.argv[1]).read()); f = flatten(hd)
    print(counts(f), 'ports', len(f.ports))
