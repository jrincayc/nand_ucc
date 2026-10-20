#!/usr/bin/env python3
"""Throwaway placement + router for one ALU bit slice of core.hd under the RNDP copper rules (spec v0.2).

Usage: python3 -I slice_router.py CORE_BODY_HD OUT_DIR [bit] [layers]

Rules implemented (RNDP_SPEC v0.2 sections 4-6):
  * NAND = 2x2 part, pads A (0,0), B (0,1), Y (1,0); a pad is copper on every layer in its own cell.
  * copper cells of different nets may never share a cell on a layer; adjacent cells never connect;
    two segments connect only by sharing a cell; a via occupies its cell on every layer.
  * copper may run under any part (only the pad cells of other nets are blocked).
  * orthogonal segments only.
The router FINDS routes (the world would only check them).  Output: routes.json for check_routes.py, an SVG, stats.
"""
import heapq
import json
import math
import os
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_hd_routing as A   # parse / expand / analyse / slice_of

PAD_OFF = {0: (0, 0), 1: (0, 1), 'Y': (1, 0)}
BUS_X0 = 1            # bus columns x = 1..8
CARRY_X = 9
X0 = 11               # first gate column
Y0 = 1


# ------------------------------------------------------------------ slice extraction
def slice_owners(i):
    return {f'alu.mux{i}', f'alu.mux{8 + i}', f'alu.not{i}', f'alu.mux{16 + i}', f'alu.mux{24 + i}',
            f'alu.not{8 + i}', f'alu.mux{32 + i}', f'alu.fa{i}', f'alu.and{i}', f'alu.mux{40 + i}',
            f'alu.not{16 + i}', f'alu.mux{48 + i}'}


def extract(path, bit):
    mods, body, _ = A.parse(path)
    gates = A.expand(mods, body)
    nets = A.analyse(gates)
    own = slice_owners(bit)
    sg = [g for g in gates if g[4] in own]
    gidx = {g[0]: k for k, g in enumerate(sg)}
    out = []                                  # logical nets restricted to this slice
    for name, v in nets.items():
        drv_in = v['driver'] is not None and v['driver'][0] in gidx
        pads = []
        if drv_in:
            pads.append((gidx[v['driver'][0]], 'Y'))
        sinks_out = 0
        for gid, owner, pin in v['sinks']:
            if gid in gidx:
                pads.append((gidx[gid], pin))
            else:
                sinks_out += 1
        if not pads:
            continue
        kind = 'internal'
        if drv_in and sinks_out:
            kind = 'out_top' if name.startswith(f'alu.fa{bit}/') else 'out_right'
        elif not drv_in:
            drv_owner = v['driver'][1] if v['driver'] else None
            other_bits = any((A.slice_of(o) or ('', 0, bit))[0].startswith('alu') and (A.slice_of(o)[2] != bit)
                             for _, o, _ in v['sinks'] if A.slice_of(o))
            if drv_owner and drv_owner.startswith('alu.fa'):
                kind = 'in_bottom'
            elif other_bits:
                kind = 'bus'
            else:
                kind = 'in_left'
        if kind == 'internal' and len(pads) < 2:
            continue
        # same classification as analyze: module-internal if driver owner == all sink owners
        d_owner = v['driver'][1] if v['driver'] else None
        s_owners = {o for _, o, _ in v['sinks']}
        mod_internal = bool(d_owner) and s_owners == {d_owner}
        out.append(dict(name=name, pads=pads, kind=kind, mod_internal=mod_internal))
    return sg, out


# ------------------------------------------------------------------ placement
def hpwl_points(net, origin, W, H):
    pts = [(origin[g][0] + PAD_OFF[p][0], origin[g][1] + PAD_OFF[p][1]) for g, p in net['pads']]
    cy = pts[0][1]
    k = net['kind']
    if k == 'in_left':
        pts.append((0, cy))
    elif k == 'out_right':
        pts.append((W - 1, cy))
    elif k == 'out_top':
        pts.append((CARRY_X, H - 1))
    elif k == 'in_bottom':
        pts.append((CARRY_X, 0))
    elif k == 'bus':
        pts.append((BUS_X0 + net['bus_idx'], cy))
    return pts


def anneal(sg, nets, R, C, px, py, W, H, seed, iters):
    rnd = random.Random(seed)
    n = len(sg)
    S = R * C
    site_of = list(range(S))
    rnd.shuffle(site_of)
    gate_at = [None] * S
    for g in range(n):
        gate_at[site_of[g]] = g
    pos = lambda s: (X0 + (s % C) * px, Y0 + (s // C) * py)
    origin = [pos(site_of[g]) for g in range(n)]
    gnets = defaultdict(list)
    for k, net in enumerate(nets):
        for g, _ in net['pads']:
            gnets[g].append(k)

    def cost_of(k):
        pts = hpwl_points(nets[k], origin, W, H)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (max(xs) - min(xs)) + (max(ys) - min(ys))

    ncost = [cost_of(k) for k in range(len(nets))]
    total = sum(ncost)
    T0, T1 = 6.0, 0.08
    for it in range(iters):
        T = T0 * (T1 / T0) ** (it / iters)
        g = rnd.randrange(n)
        s2 = rnd.randrange(S)
        s1 = site_of[g]
        if s1 == s2:
            continue
        h = gate_at[s2]
        aff = set(gnets[g]) | (set(gnets[h]) if h is not None else set())
        old = sum(ncost[k] for k in aff)
        # apply
        site_of[g] = s2
        gate_at[s2] = g
        gate_at[s1] = h
        origin[g] = pos(s2)
        if h is not None:
            site_of[h] = s1
            origin[h] = pos(s1)
        newc = {k: cost_of(k) for k in aff}
        d = sum(newc.values()) - old
        if d <= 0 or rnd.random() < math.exp(-d / T):
            for k, v in newc.items():
                ncost[k] = v
            total += d
        else:                                   # undo
            site_of[g] = s1
            gate_at[s1] = g
            gate_at[s2] = h
            origin[g] = pos(s1)
            if h is not None:
                site_of[h] = s2
                origin[h] = pos(s2)
    return origin, total


# ------------------------------------------------------------------ router
class Router:
    def __init__(self, W, H, L, bend, via):
        self.W, self.H, self.L, self.bend, self.via = W, H, L, bend, via

    def setup(self, sg, nets, origin):
        W, H, L = self.W, self.H, self.L
        self.occ = [[[-1] * W for _ in range(H)] for _ in range(L)]
        self.rn = []
        # every pad cell of every part is blocked for foreign copper, even when its net is not routed here
        for g in range(len(sg)):
            for (dx, dy) in PAD_OFF.values():
                for l in range(L):
                    self.occ[l][origin[g][1] + dy][origin[g][0] + dx] = -2
        for k, net in enumerate(nets):
            r = dict(id=k, name=net['name'], kind=net['kind'], edge=None, pads=[], tree=set(),
                     segs=[], vias=[], ports=[], mod_internal=net['mod_internal'], links=0, ok=True)
            cells = []
            for g, p in net['pads']:
                c = (origin[g][0] + PAD_OFF[p][0], origin[g][1] + PAD_OFF[p][1])
                cells.append(c)
                for l in range(L):
                    assert self.occ[l][c[1]][c[0]] in (-1, -2, k), 'pad overlap'
                    self.occ[l][c[1]][c[0]] = k
            r['padcells'] = cells
            if net['kind'] == 'bus':
                bx = BUS_X0 + net['bus_idx']
                for y in range(H):
                    self.occ[1][y][bx] = k
                    r['tree'].add((bx, y, 1))
                r['segs'].append((1, bx, 0, bx, H - 1))
                r['pads'] = list(cells)
                r['bus'] = True
            else:
                start = cells[0]
                for l in range(L):
                    r['tree'].add((start[0], start[1], l))
                r['pads'] = list(cells[1:])
                if net['kind'] in ('in_bottom', 'out_top'):
                    py = 0 if net['kind'] == 'in_bottom' else H - 1
                    for l in range(L):
                        self.occ[l][py][CARRY_X] = k
                    r['pads'].append((CARRY_X, py))
                    r['ports'].append(('carry', CARRY_X, py))
                elif net['kind'] in ('in_any', 'out_any'):
                    r['edge'] = 'ANY'
                elif net['kind'] == 'in_left':
                    r['edge'] = 'L'
                elif net['kind'] == 'out_right':
                    r['edge'] = 'R'
            r['links'] = len(r['pads']) + (1 if r['edge'] else 0)
            self.rn.append(r)

    def find_path(self, r):
        occ, W, H, L = self.occ, self.W, self.H, self.L
        nid = r['id']
        targets = set(r['pads'])
        edge = r['edge']
        tree = r['tree']
        heap, dist, parent = [], {}, {}
        for (x, y, l) in tree:
            st = (x, y, l, 2)
            dist[st] = 0
            parent[st] = None
            heap.append((0, x, y, l, 2))
        heapq.heapify(heap)
        bend, via = self.bend, self.via
        while heap:
            c, x, y, l, d = heapq.heappop(heap)
            st = (x, y, l, d)
            if dist.get(st, 1 << 60) < c:
                continue
            if (x, y, l) not in tree:
                if ((x, y) in targets or (edge == 'L' and x == 0) or (edge == 'R' and x == W - 1)
                        or (edge == 'ANY' and (x in (0, W - 1) or y in (0, H - 1)))):
                    path = []
                    while st is not None:
                        path.append(st[:3])
                        st = parent[st]
                    path.reverse()
                    return path, (x, y)
            for dx, dy, dt in ((1, 0, 0), (-1, 0, 0), (0, 1, 1), (0, -1, 1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < W and 0 <= ny < H):
                    continue
                o = occ[l][ny][nx]
                if o != -1 and o != nid:
                    continue
                nc = c + 1 + (bend if (d != 2 and d != dt) else 0)
                ns = (nx, ny, l, dt)
                if nc < dist.get(ns, 1 << 60):
                    dist[ns] = nc
                    parent[ns] = st
                    heapq.heappush(heap, (nc, nx, ny, l, dt))
            for l2 in range(L):
                if l2 == l:
                    continue
                if all(occ[k][y][x] in (-1, nid) for k in range(L)):
                    nc = c + via
                    ns = (x, y, l2, 2)
                    if nc < dist.get(ns, 1 << 60):
                        dist[ns] = nc
                        parent[ns] = st
                        heapq.heappush(heap, (nc, x, y, l2, 2))
        return None, None

    def commit(self, r, path, end):
        occ, L, nid = self.occ, self.L, r['id']
        segs, vias = [], []
        run = [path[0]]
        for a, b in zip(path, path[1:]):
            if a[:2] == b[:2]:                       # via
                if len(run) >= 2:
                    segs.append(run)
                vias.append((a[0], a[1]))
                for k in range(L):
                    occ[k][a[1]][a[0]] = nid
                    r['tree'].add((a[0], a[1], k))
                run = [b]
            else:
                if len(run) >= 2:
                    d0 = (run[1][0] - run[0][0], run[1][1] - run[0][1])
                    d1 = (b[0] - a[0], b[1] - a[1])
                    if d0 != d1 and not (d0 == (-d1[0], -d1[1])):
                        segs.append(run)
                        run = [a]
                run.append(b)
        if len(run) >= 2:
            segs.append(run)
        for run in segs:
            r['segs'].append((run[0][2], run[0][0], run[0][1], run[-1][0], run[-1][1]))
        r['vias'].extend(vias)
        for (x, y, l) in path:
            if occ[l][y][x] == -1:
                occ[l][y][x] = nid
            r['tree'].add((x, y, l))
        if end in r['pads']:
            r['pads'].remove(end)
            for k in range(L):
                r['tree'].add((end[0], end[1], k))
        else:
            r['edge'] = None
            r['ports'].append(('edge', path[-1][0], path[-1][1], path[-1][2]))

    def route_all(self, order):
        failed = []
        for k in order:
            r = self.rn[k]
            while r['pads'] or r['edge']:
                path, end = self.find_path(r)
                if path is None:
                    r['ok'] = False
                    failed.append(k)
                    break
                self.commit(r, path, end)
        return failed


# ------------------------------------------------------------------ one attempt
def attempt(sg, nets, R, C, px, py, bend, via, L, seed, passes=6, iters=40000):
    W = X0 + (C - 1) * px + 2 + 1
    H = Y0 + (R - 1) * py + 2 + 1
    origin, hp = anneal(sg, nets, R, C, px, py, W, H, seed, iters)
    rnd = random.Random(seed + 1)
    # initial order: short nets first
    est = []
    for k, net in enumerate(nets):
        pts = hpwl_points(net, origin, W, H)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        est.append((max(xs) - min(xs)) + (max(ys) - min(ys)))
    order = sorted(range(len(nets)), key=lambda k: est[k])
    best = None
    for ps in range(passes):
        rt = Router(W, H, L, bend, via)
        rt.setup(sg, nets, origin)
        failed = rt.route_all(order)
        if best is None or len(failed) < len(best[1]):
            best = (rt, failed)
        if not failed:
            break
        front = list(dict.fromkeys(failed))
        rest = [k for k in order if k not in front]
        rnd.shuffle(rest)
        rest.sort(key=lambda k: est[k] + rnd.random() * 6)
        order = front + rest
    rt, failed = best
    return dict(W=W, H=H, origin=origin, router=rt, failed=failed, hpwl=hp)


def stats(res, sg, nets, bits_label=''):
    rt = res['router']
    segs = vias = 0
    seg_by = Counter()
    link_by = Counter()
    via_by = Counter()
    length = 0
    for r in rt.rn:
        cls = 'bus' if r.get('bus') else ('module-internal' if r['mod_internal'] else 'inter-instance')
        ns = len(r['segs']) - (1 if r.get('bus') else 0)       # the pre-laid bus segment is not per-link
        seg_by[cls] += ns
        link_by[cls] += r['links']
        via_by[cls] += len(r['vias'])
        for (l, x1, y1, x2, y2) in r['segs']:
            length += abs(x1 - x2) + abs(y1 - y2) + 1
    return seg_by, link_by, via_by, length


def to_json(res, sg, nets, bit, L):
    rt = res['router']
    out = dict(W=res['W'], H=res['H'], L=L, bit=bit, gates=[], nets=[])
    for g in range(len(sg)):
        out['gates'].append(dict(gid=sg[g][0], origin=res['origin'][g]))
    for r, net in zip(rt.rn, nets):
        out['nets'].append(dict(name=r['name'], kind=r['kind'], pads=[[g, str(p)] for g, p in net['pads']],
                                segs=r['segs'], vias=r['vias'], ports=r['ports'], bus=bool(r.get('bus'))))
    return out


def svg(res, sg, path):
    rt = res['router']
    S = 12
    W, H = res['W'], res['H']
    col = {0: '#d33', 1: '#36c', 2: '#3a3'}
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W * S}" height="{H * S}" '
         f'viewBox="0 0 {W} {H}" style="background:#fff">']
    for g, org in enumerate(res['origin']):
        o.append(f'<rect x="{org[0]}" y="{H - 1 - org[1] - 1}" width="2" height="2" fill="#ddd" stroke="#888" '
                 f'stroke-width="0.05"/>')
    for r in rt.rn:
        for (l, x1, y1, x2, y2) in r['segs']:
            o.append(f'<line x1="{x1 + .5}" y1="{H - 1 - y1 + .5}" x2="{x2 + .5}" y2="{H - 1 - y2 + .5}" '
                     f'stroke="{col[l % 3]}" stroke-width="0.35" stroke-linecap="square" opacity="0.8"/>')
        for (x, y) in r['vias']:
            o.append(f'<circle cx="{x + .5}" cy="{H - 1 - y + .5}" r="0.32" fill="#000"/>')
    for g, org in enumerate(res['origin']):
        for p, (dx, dy) in PAD_OFF.items():
            o.append(f'<rect x="{org[0] + dx + .25}" y="{H - 1 - (org[1] + dy) + .25}" width="0.5" height="0.5" '
                     f'fill="#111"/>')
    o.append('</svg>')
    open(path, 'w').write('\n'.join(o))


def main():
    core, outdir = sys.argv[1], sys.argv[2]
    bit = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    L = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    os.makedirs(outdir, exist_ok=True)
    sg, nets = extract(core, bit)
    buses = [n for n in nets if n['kind'] == 'bus']
    for k, n in enumerate(sorted(buses, key=lambda n: n['name'])):
        n['bus_idx'] = k
    nb = len(buses)
    kinds = Counter(n['kind'] for n in nets)
    print(f'slice bit {bit}: {len(sg)} NAND, {len(nets)} nets, kinds {dict(kinds)}; buses: '
          f'{[n["name"] for n in sorted(buses, key=lambda n: n["bus_idx"])]}')
    assert nb <= 8 and BUS_X0 + nb <= CARRY_X
    n = len(sg)
    results = []
    configs = []
    for (px, py) in ((3, 3), (4, 3), (3, 4), (4, 4), (5, 4), (4, 5), (5, 5), (6, 6)):
        cols = max(2, round(math.sqrt(n * 1.15 * py / px)))
        rows = math.ceil(n * 1.15 / cols)
        configs.append((px, py, rows, cols))
    for (px, py, R, C) in configs:
        for seed in (1, 2):
            res = attempt(sg, nets, R, C, px, py, bend=2, via=6, L=L, seed=seed)
            ok = not res['failed']
            segs, links, vias, length = stats(res, sg, nets)
            print(f'pitch {px}x{py} sites {R}x{C} seed {seed}: area {res["W"]}x{res["H"]}={res["W"] * res["H"]} '
                  f'failed nets {len(res["failed"])}  segs {sum(segs.values())} vias {sum(vias.values())}', flush=True)
            if ok:
                results.append((res['W'] * res['H'], px, py, seed, res))
        if results:
            break                                  # smallest pitch that routes
    if not results:
        print('no configuration routed')
        return
    results.sort(key=lambda t: t[0])
    area, px, py, seed, res = results[0]
    segs, links, vias, length = stats(res, sg, nets)
    print(f'\nBEST: pitch {px}x{py}, seed {seed}, bounding box {res["W"]} x {res["H"]} = {area} cells '
          f'(NAND pad+body cells {4 * n}; {area / (4 * n):.2f}x)')
    print(f'layers {L}; total copper length (cells, incl. bus) {length}')
    print(f'{"class":16s} {"links":>6s} {"segments":>9s} {"vias":>5s} {"seg/link":>9s}')
    for c in ('module-internal', 'inter-instance', 'bus'):
        if c == 'bus':
            print(f'{c:16s} {links[c]:6d} {"(1/net)":>9s} {vias[c]:5d}')
        else:
            print(f'{c:16s} {links[c]:6d} {segs[c]:9d} {vias[c]:5d} {segs[c] / max(1, links[c]):9.2f}')
    tot_l = links['module-internal'] + links['inter-instance'] + links['bus']
    tot_s = sum(segs.values()) + sum(1 for r in res['router'].rn if r.get('bus'))
    tot_v = sum(vias.values())
    print(f'all: links {tot_l}, segments {tot_s}, vias {tot_v}')
    # byte encodings: explicit TRACK = 5 B/segment, 2 B/via; turtle path = 3 B/path + 1 B/segment + 1 B/via
    paths = 0
    for r in res['router'].rn:
        paths += len(r['segs'])
    print(f'bytes, explicit (5 B/seg + 2 B/via): {5 * tot_s + 2 * tot_v};  '
          f'per link {(5 * tot_s + 2 * tot_v) / tot_l:.1f}')
    json.dump(to_json(res, sg, nets, bit, L), open(os.path.join(outdir, 'routes.json'), 'w'))
    svg(res, sg, os.path.join(outdir, 'slice.svg'))
    print('wrote routes.json and slice.svg')


if __name__ == '__main__':
    main()
