#!/usr/bin/env python3
"""Independent checker for slice_router.py output (does not import the router).

Usage: python3 -I check_routes.py CORE_BODY_HD routes.json

Rebuilds connectivity from the copper geometry alone, using the RNDP spec v0.2 rules, and compares it with the netlist
re-derived from core_body.hd:
  * segments are orthogonal and in bounds, layer < L; parts are 2x2, in bounds, non-overlapping;
  * cells of one segment are connected consecutively; segments connect only by sharing a (layer,x,y) cell;
    adjacent cells of different segments do NOT connect;
  * a via joins every layer at its cell; a pad is copper on every layer in its own cell;
  * partition test: two pads of the slice are in the same copper component  <=>  they are on the same netlist net;
  * every net that leaves the slice has a bus track spanning the full height or a port on the right boundary.
Only the pad-to-net mapping comes from the netlist; the router's own bookkeeping is never consulted.
"""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_hd_routing as A

PAD_OFF = {'0': (0, 0), '1': (0, 1), 'Y': (1, 0)}


class UF:
    def __init__(self):
        self.p = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def main(core, jpath):
    d = json.load(open(jpath))
    W, H, L = d['W'], d['H'], d['L']
    errs = []
    # ---- netlist (independent re-derivation)
    mods, body, _ = A.parse(core)
    gates = {g[0]: g for g in A.expand(mods, body)}
    # ---- parts
    occ_part = {}
    gate_pin_cell = {}
    for g in d['gates']:
        ox, oy = g['origin']
        if not (0 <= ox and ox + 1 < W and 0 <= oy and oy + 1 < H):
            errs.append(f'part {g["gid"]} out of bounds')
        for dx in (0, 1):
            for dy in (0, 1):
                c = (ox + dx, oy + dy)
                if c in occ_part:
                    errs.append(f'parts overlap at {c}')
                occ_part[c] = g['gid']
        for pin, (dx, dy) in PAD_OFF.items():
            gate_pin_cell[(g['gid'], pin)] = (ox + dx, oy + dy)
    # ---- copper
    uf = UF()
    nseg = nvia = 0
    copper_cells = set()
    for net in d['nets']:
        for (l, x1, y1, x2, y2) in net['segs']:
            nseg += 1
            if not (0 <= l < L):
                errs.append(f'bad layer in {net["name"]}')
            if x1 != x2 and y1 != y2:
                errs.append(f'diagonal segment in {net["name"]}')
            if not (0 <= x1 < W and 0 <= x2 < W and 0 <= y1 < H and 0 <= y2 < H):
                errs.append(f'segment out of bounds in {net["name"]}')
            dx = (x2 > x1) - (x2 < x1)
            dy = (y2 > y1) - (y2 < y1)
            x, y = x1, y1
            while True:
                copper_cells.add((l, x, y))
                uf.find((l, x, y))
                if (x, y) == (x2, y2):
                    break
                uf.union((l, x, y), (l, x + dx, y + dy))      # consecutive cells of ONE segment only
                x, y = x + dx, y + dy
        for (x, y) in net['vias']:
            nvia += 1
            for l in range(L):
                copper_cells.add((l, x, y))
                uf.union((0, x, y), (l, x, y))
    # pads and carry ports pierce every layer
    pad_node = {}
    for (gid, pin), (x, y) in gate_pin_cell.items():
        for l in range(L):
            uf.union((0, x, y), (l, x, y))
        pad_node[(gid, pin)] = (0, x, y)
    port_cells = []
    for net in d['nets']:
        for p in net['ports']:
            if p[0] == 'carry':
                for l in range(L):
                    uf.union((0, p[1], p[2]), (l, p[1], p[2]))
                port_cells.append((net['name'], (0, p[1], p[2]), 'carry'))
            else:
                port_cells.append((net['name'], (p[3], p[1], p[2]), 'edge'))
    # ---- netlist pad -> net name
    net_of_pad = {}
    for gid in {g['gid'] for g in d['gates']}:
        g = gates[gid]
        net_of_pad[(gid, '0')] = g[2][0]
        net_of_pad[(gid, '1')] = g[2][1]
        net_of_pad[(gid, 'Y')] = g[3]
    # ---- partition test over all pads of the slice
    comp_nets = defaultdict(set)
    net_comps = defaultdict(set)
    for pad, node in pad_node.items():
        r = uf.find(node)
        comp_nets[r].add(net_of_pad[pad])
        net_comps[net_of_pad[pad]].add(r)
    shorts = {r: s for r, s in comp_nets.items() if len(s) > 1}
    opens = {n: c for n, c in net_comps.items() if len(c) > 1}
    for r, s in shorts.items():
        errs.append(f'SHORT between nets {sorted(s)}')
    for n, c in opens.items():
        errs.append(f'OPEN net {n} split into {len(c)} pieces')
    # ---- external connections exist
    gid_set = {g['gid'] for g in d['gates']}
    from_netlist = A.analyse(list(gates.values()))
    port_by_net = defaultdict(list)
    for n, node, kind in port_cells:
        port_by_net[n].append((node, kind))
    for jn in d['nets']:
        name = jn['name']
        v = from_netlist[name]
        outside = (v['driver'] is not None and v['driver'][0] not in gid_set) or any(
            s[0] not in gid_set for s in v['sinks'])
        if not outside:
            continue
        if jn['bus']:
            full = any(abs(s[2] - s[4]) == H - 1 and s[1] == s[3] for s in jn['segs'])
            if not full:
                errs.append(f'bus {name} does not span the cell')
        else:
            if not jn['ports']:
                errs.append(f'net {name} leaves the slice but has no port')
            for p in jn['ports']:
                node = (0, p[1], p[2]) if p[0] == 'carry' else (p[3], p[1], p[2])
                comp = uf.find(node)
                pads_here = [pd for pd, nd in pad_node.items() if uf.find(nd) == comp]
                if not pads_here:
                    errs.append(f'port of {name} not connected to any pad')
                on_lr = p[0] == 'edge' and p[1] in (0, W - 1)
                on_tb = p[0] == 'edge' and p[2] in (0, H - 1) and jn['kind'].endswith('_any')
                if p[0] == 'edge' and not (on_lr or on_tb):
                    errs.append(f'edge port of {name} not on boundary')
    # ---- floating copper (copper component with no pad)
    pad_comps = {uf.find(n) for n in pad_node.values()}
    float_cells = {c for c in copper_cells if uf.find(c) not in pad_comps}
    if float_cells:
        errs.append(f'{len(float_cells)} copper cells in components with no pad')
    # ---- report
    print(f'checked: {len(d["gates"])} parts, {nseg} segments, {nvia} vias, {len(copper_cells)} copper cells, '
          f'{len(net_comps)} nets, {len(pad_node)} pads')
    print(f'shorts: {len(shorts)}   opens: {len(opens)}   floating copper cells: {len(float_cells)}')
    if errs:
        print('FAIL')
        for e in errs[:20]:
            print('  ', e)
        sys.exit(1)
    print('PASS: connectivity from geometry equals the netlist; no shorts, no opens')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
