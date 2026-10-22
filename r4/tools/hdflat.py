#!/usr/bin/env python3
"""hdflat.py -- HD (module library + body) -> plain NAND/DFF Net, independent of ModNet.  Expansion order = body order, so the result
must be gate-for-gate identical to ModNet.flatten()."""
import os, sys
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]
import hd as hdlib
from netlist import Net
INPUTS = [f'rom{i}' for i in range(8)] + [f'ramrd{i}' for i in range(8)] + ['run']


def flatten(h, order=None):
    """HD -> (Net, ports).  The body may list instances in any order (forward references are resolved by repeated passes).
    If `order` is a list it receives, for every non-input, non-constant node of the Net, its placement key (body index, gate index within the
    instance), indexed by node number."""
    F = Net(); sig = {}
    used = {r for it in h.body for r in it.refs} | {r for _, r in h.ports}
    for nm in INPUTS:
        if nm in used: sig[nm] = F.inp(nm)
    key = {}
    for bi, it in enumerate(h.body):
        if it.type == 'dff': sig[it.name] = F.dff(it.comment or None); key[sig[it.name]] = (bi, 0)
    todo = [bi for bi, it in enumerate(h.body) if it.type != 'dff']
    while todo:
        rest = []
        for bi in todo:
            it = h.body[bi]
            if not all(r in sig for r in it.refs): rest.append(bi); continue
            ins = [sig[r] for r in it.refs]
            if it.type == 'nand':
                F.kind.append(('nand', ins[0], ins[1])); sig[it.name] = len(F.kind) - 1; key[sig[it.name]] = (bi, 0)
            else:
                m = h.module(it.type); loc = list(ins)
                for gi, x in enumerate(m.gates):       # slot form: None = hole (no gate, the slot number is still taken)
                    if x is None: loc.append(None); continue
                    F.kind.append(('nand', loc[x[0]], loc[x[1]])); loc.append(len(F.kind) - 1); key[len(F.kind) - 1] = (bi, gi)
                if m.n_out == 1: sig[it.name] = loc[m.outs[0]]
                else:
                    for j, o in enumerate(m.outs): sig[f'{it.name}.{j}'] = loc[o]
        if len(rest) == len(todo): raise ValueError('unresolvable references (combinational loop?) at body ' + h.body[rest[0]].name)
        todo = rest
    for it in h.body:
        if it.type == 'dff': F.kind[sig[it.name]][1] = sig[it.refs[0]]
    if order is not None: order[:] = [key.get(n) for n in range(len(F.kind))]
    return F, {p: sig[r] for p, r in h.ports}


def state_of(F):
    """the DFFs of the flattened CPU by their names (from the HD comments) -> the state dict netsim expects"""
    by = {nm: n for n, nm in F.names.items() if nm}
    g = lambda nm: by[nm]
    return dict(upc=[g(f'upc{i}') for i in range(7)], k=[g(f'k{i}') for i in range(2)], ir=[[g(f'ir{j}_{i}') for i in range(8)] for j in range(4)],
                ar=[g(f'ar{i}') for i in range(len([x for x in by if x.startswith('ar') and x[2:].isdigit()]))],
                A=[g(f'a{i}') for i in range(8)], R=[g(f'r{i}') for i in range(8)], C=g('c'), Z=g('z'), SA=g('sa'), SB=g('sb'), live=g('live'))
