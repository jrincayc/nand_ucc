#!/usr/bin/env python3
"""Route the irregular GLUE region of core.hd (address-compare chain, control, RAM decode, constants, reductions).

Usage: python3 -I glue_router.py CORE_BODY_HD OUT_DIR [layers]

Every net that leaves the region gets one port on any boundary cell.  This is the best available proxy for the
'irregular' links of the earlier analysis: nets are longer and less regular than inside a bit slice.
Uses the same placement, router and rules as slice_router.py (X0/Y0 reset because there are no bus columns).
"""
import json
import math
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_hd_routing as A
import slice_router as SR

GLUE = re.compile(r'^(decode\..*|control\..*|top\..*|ram\..*|alu\.or\d+|alu\.not24|pc\.(not|and|or)\d+|'
                  r'areg\.(and0|or0|and1)|dreg\.and0|ir\.or0|c\.n|one|zero|reset)$')


def extract_region(path):
    mods, body, _ = A.parse(path)
    gates = A.expand(mods, body)
    nets = A.analyse(gates)
    sg = [g for g in gates if GLUE.match(g[4])]
    gidx = {g[0]: k for k, g in enumerate(sg)}
    out = []
    for name, v in nets.items():
        drv_in = v['driver'] is not None and v['driver'][0] in gidx
        pads = [(gidx[v['driver'][0]], 'Y')] if drv_in else []
        outside = 0 if drv_in or v['driver'] is None else 1
        for gid, owner, pin in v['sinks']:
            if gid in gidx:
                pads.append((gidx[gid], pin))
            else:
                outside += 1
        if not pads:
            continue
        kind = 'internal'
        # ram.and*/g1 feed the RAM tile, which is not in core_body.hd: treat them as outputs leaving the region
        feeds_ram_tile = drv_in and not v['sinks'] and re.match(r'^ram\.and\d+/g1$', name)
        if drv_in and (any(s[0] not in gidx for s in v['sinks']) or feeds_ram_tile):
            kind = 'out_any'
        elif not drv_in:
            kind = 'in_any'
        if kind == 'internal' and len(pads) < 2:
            continue
        d_owner = v['driver'][1] if v['driver'] else None
        s_owners = {o for _, o, _ in v['sinks']}
        out.append(dict(name=name, pads=pads, kind=kind, mod_internal=bool(d_owner) and s_owners == {d_owner}))
    return sg, out


def main(core, outdir, L=2, pitches='3x3,4x3,3x4,4x4,5x5', nseeds=6):
    os.makedirs(outdir, exist_ok=True)
    plist = [tuple(int(v) for v in p.split('x')) for p in pitches.split(',')]
    SR.X0, SR.Y0 = 2, 2
    sg, nets = extract_region(core)
    kinds = Counter(n['kind'] for n in nets)
    n = len(sg)
    print(f'glue region: {n} NAND, {len(nets)} nets, kinds {dict(kinds)}; layers {L}')
    best = None
    for (px, py) in plist:
        cols = max(2, round(math.sqrt(n * 1.15 * py / px)))
        rows = math.ceil(n * 1.15 / cols)
        found = []
        for seed in range(1, nseeds + 1):
            res = SR.attempt(sg, nets, rows, cols, px, py, 2, 6, L, seed, passes=10, iters=60000)
            segs, links, vias, length = SR.stats(res, sg, nets)
            print(f'pitch {px}x{py} seed {seed}: area {res["W"]}x{res["H"]}={res["W"] * res["H"]} '
                  f'failed {len(res["failed"])}', flush=True)
            if not res['failed']:
                found.append((res['W'] * res['H'], seed, res))
        if found:
            found.sort(key=lambda t: t[0])
            best = (px, py, found[0])
            break
    if not best:
        print('no pitch routed')
        return
    px, py, (area, seed, res) = best
    segs, links, vias, length = SR.stats(res, sg, nets)
    print(f'\nBEST: pitch {px}x{py} seed {seed}: {res["W"]}x{res["H"]} = {area} cells '
          f'({area / (4 * n):.2f}x NAND area), copper length {length}')
    print(f'{"class":16s} {"links":>6s} {"segments":>9s} {"vias":>5s} {"seg/link":>9s} {"via/link":>9s}')
    for c in ('module-internal', 'inter-instance'):
        print(f'{c:16s} {links[c]:6d} {segs[c]:9d} {vias[c]:5d} {segs[c] / max(1, links[c]):9.2f} '
              f'{vias[c] / max(1, links[c]):9.2f}')
    ts, tv, tl = sum(segs.values()), sum(vias.values()), sum(links.values())
    print(f'all: links {tl}, segments {ts}, vias {tv}, explicit bytes (5/seg + 2/via) {5 * ts + 2 * tv} '
          f'= {(5 * ts + 2 * tv) / tl:.1f} per link')
    # per-link length of inter-instance nets (cells)
    lens = []
    for r in res['router'].rn:
        if r['mod_internal'] or r.get('bus'):
            continue
        L_ = sum(abs(a - c) + abs(b - d) + 1 for (_, a, b, c, d) in r['segs'])
        lens.append((L_ / max(1, r['links']), len(r['segs']) / max(1, r['links'])))
    lens.sort()
    print(f'inter-instance nets: {len(lens)}; median copper cells per link {lens[len(lens) // 2][0]:.1f}, '
          f'max {lens[-1][0]:.1f}')
    js = os.path.join(outdir, 'routes.json')
    json.dump(SR.to_json(res, sg, nets, -1, L), open(js, 'w'))
    SR.svg(res, sg, os.path.join(outdir, 'glue.svg'))
    print('wrote', js)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 2,
         sys.argv[4] if len(sys.argv) > 4 else '3x3,4x3,3x4,4x4,5x5',
         int(sys.argv[5]) if len(sys.argv) > 5 else 6)
