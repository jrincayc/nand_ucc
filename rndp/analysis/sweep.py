#!/usr/bin/env python3
"""Sweeps over layer count and router cost weights for the ALU bit slice.  Usage: python3 -I sweep.py CORE_BODY_HD OUTDIR"""
import json
import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slice_router as SR


def prep(core, bit=3):
    sg, nets = SR.extract(core, bit)
    buses = sorted([n for n in nets if n['kind'] == 'bus'], key=lambda n: n['name'])
    for k, n in enumerate(buses):
        n['bus_idx'] = k
    return sg, nets


def sites(n, px, py):
    cols = max(2, round(math.sqrt(n * 1.15 * py / px)))
    rows = math.ceil(n * 1.15 / cols)
    return rows, cols


def metrics(res):
    segs, links, vias, length = SR.stats(res, None, None)
    rt = res['router']
    nbus = sum(1 for r in rt.rn if r.get('bus'))
    tot_s = sum(segs.values()) + nbus
    tot_v = sum(vias.values())
    tot_l = sum(links.values())
    paths = sum(1 for r in rt.rn for _ in r['segs'])
    return dict(segs=tot_s, vias=tot_v, links=tot_l, length=length,
                explicit=5 * tot_s + 2 * tot_v,
                seg_link_int=segs['module-internal'] / max(1, links['module-internal']),
                seg_link_inter=segs['inter-instance'] / max(1, links['inter-instance']))


def best_area(sg, nets, L, bend=2, via=6, seeds=range(1, 11), pitches=None):
    n = len(sg)
    pitches = pitches or [(3, 3), (4, 3), (3, 4), (4, 4), (5, 4), (4, 5), (5, 5), (6, 6)]
    for (px, py) in pitches:
        R, C = sites(n, px, py)
        found = []
        for seed in seeds:
            res = SR.attempt(sg, nets, R, C, px, py, bend, via, L, seed, passes=8)
            if not res['failed']:
                found.append((res['W'] * res['H'], seed, res))
        if found:
            found.sort(key=lambda t: t[0])
            return (px, py), found[0][1], found[0][2], len(found), len(list(seeds))
    return None


def main(core, outdir):
    os.makedirs(outdir, exist_ok=True)
    sg, nets = prep(core)
    print('=== sweep 1: layer count (bend 2, via 6; smallest pitch that routes, best of 10 seeds) ===')
    print(f'{"L":>2s} {"pitch":>6s} {"area":>10s} {"x NAND area":>11s} {"routed/seeds":>12s} {"segs":>5s} {"vias":>5s} '
          f'{"len":>5s} {"bytes":>6s}')
    for L in (2, 3, 4):
        r = best_area(sg, nets, L)
        if not r:
            print(f'{L:>2d} none routed')
            continue
        (px, py), seed, res, nok, nseeds = r
        m = metrics(res)
        print(f'{L:>2d} {px}x{py:>3d} {res["W"]}x{res["H"]}={res["W"] * res["H"]:>5d} '
              f'{res["W"] * res["H"] / (4 * len(sg)):>10.2f}x {nok:>5d}/{nseeds:<5d}  {m["segs"]:>5d} {m["vias"]:>5d} '
              f'{m["length"]:>5d} {m["explicit"]:>6d}')
        js = os.path.join(outdir, f'routes_L{L}.json')
        json.dump(SR.to_json(res, sg, nets, 3, L), open(js, 'w'))
        p = subprocess.run([sys.executable, '-I', os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                              'check_routes.py'), core, js],
                           capture_output=True, text=True)
        print('     checker:', p.stdout.strip().split('\n')[-1])
    print('\n=== sweep 2: cost weights at L=2, pitch 4x3, 10 seeds each (segments vs vias trade-off) ===')
    print(f'{"bend":>4s} {"via":>4s} {"ok":>6s} {"segs":>5s} {"vias":>5s} {"len":>5s} {"bytes":>6s} '
          f'{"seg/link int":>12s} {"seg/link inter":>14s}')
    n = len(sg)
    R, C = sites(n, 4, 3)
    for bend in (0, 2, 6):
        for via in (2, 6, 20):
            best = None
            ok = 0
            for seed in range(1, 11):
                res = SR.attempt(sg, nets, R, C, 4, 3, bend, via, 2, seed, passes=8)
                if res['failed']:
                    continue
                ok += 1
                m = metrics(res)
                if best is None or m['explicit'] < best['explicit']:
                    best = m
            if best:
                print(f'{bend:>4d} {via:>4d} {ok:>3d}/10 {best["segs"]:>5d} {best["vias"]:>5d} {best["length"]:>5d} '
                      f'{best["explicit"]:>6d} {best["seg_link_int"]:>12.2f} {best["seg_link_inter"]:>14.2f}')
            else:
                print(f'{bend:>4d} {via:>4d}  0/10 none')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
