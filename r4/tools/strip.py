#!/usr/bin/env python3
"""strip.py NL OUT.lay -- reference place and route for R4 ("strip"): NORMATIVE for the in-world implementation.

Placement: node k (netlist order) at base column X=3k, row Y0: B-gap column X, gate columns X+1 (pins A (X+1,Y0), B (X+1,Y0+1), DFF D (X+1,Y0))
and X+2 (Y / Q at (X+2,Y0)).  ROM, ARM, RAM follow at the right end as upright blocks (rotation 0, pins in two columns), each with a
staircase of horizontal layer-0 stubs, one column per pin, left for the first pin column, right for the second.
Routing: ONE single-sided channel above the row, tracks on layer 0, every pin reaches the channel by a layer-1 vertical stub in its own
column (a NAND's B pin first goes left one cell to the gap column, a part pin along its staircase row).  No two stubs share a column, so
there are no vertical constraints: the left-edge algorithm gives density-optimal tracks.  A via joins stub and track.
Output: the layout tool's .lay format (dims / part / site / sink lines), so tests/validate_layout.py builds and checks it in rndp."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE]
import lay

PITCH = 3


def layout(nl):
    N = len(nl.nodes); R = nl.rom; Q = nl.ram
    # ---- columns of every pin: net -> list of (kind, who, pin, col, rows) ; a pin is described by its stub
    parts = {}; xs = PITCH * N + 4
    def block(name, w_l, w_r):
        nonlocal xs
        x = xs + w_l + 1; parts[name] = x; xs = x + 2 + w_r + 1
    block('rom', R, 8); block('arm', 5, 8); block('ram', Q + 9, 8)
    W = xs
    pins = {}                                   # net key -> dict(driver=(col, stub), sinks=[(col, stub, late, who)])
    def netof(tok):
        b = tok.split('@')[0]
        return ('ramo', int(b[4:])) if b.startswith('ramo') else ('rom', int(b[3:])) if b.startswith('rom') else ('n', int(b[1:]))
    def add(key, role, entry):
        d = pins.setdefault(key, dict(driver=None, sinks=[]))
        if role == 'drv': d['driver'] = entry
        else: d['sinks'].append(entry)
    # a stub = list of (dx, dy, layer) points relative to the row origin, from the pin cell to the foot of the vertical (layer 1) , then the vertical goes up
    for k, (kind, ins) in enumerate(nl.nodes):
        X = PITCH * k
        add(('n', k), 'drv', (X + 2, [(X + 2, 0, 1)], 0, f'n{k}'))
        for p, s in enumerate(ins):
            if s == 'open': continue
            late = 2 if '@2' in s else 1 if '@1' in s else 0
            if p == 0: st = [(X + 1, 0, 1)]
            else: st = [(X + 1, 1, 0), (X, 1, 0), (X, 1, 1)]          # B: layer 0 one cell left, via, then up the gap column
            add(netof(s), 'snk', ((X + 1) if p == 0 else X, st, late, f'n{k}.{p}'))
    xr, xa, xm = parts['rom'], parts['arm'], parts['ram']
    for j in range(8): add(('rom', j), 'drv', (xr + 2 + j, [(xr + 1, j, 0), (xr + 2 + j, j, 0), (xr + 2 + j, j, 1)], 0, f'rom{j}'))
    for c in range(8): add(('ramo', c), 'drv', (xm + 2 + c, [(xm + 1, c, 0), (xm + 2 + c, c, 0), (xm + 2 + c, c, 1)], 0, f'ramo{c}'))
    def left(x, row): return (x - 1 - row, [(x, row, 0), (x - 1 - row, row, 0), (x - 1 - row, row, 1)])
    def port(name, s):
        late = 2 if '@2' in s else 1 if '@1' in s else 0
        def a(x, row): c, st = left(x, row); add(netof(s), 'snk', (c, st, late, name))
        if name.startswith('rom_addr'): a(xr, int(name[8:]))
        elif name.startswith('arm_addr'): a(xa, int(name[8:]))
        elif name == 'arm_en': a(xa, 4)
        elif name.startswith('wdata'): c = xa + 2 + int(name[5:]); add(netof(s), 'snk', (c, [(xa + 1, int(name[5:]), 0), (c, int(name[5:]), 0), (c, int(name[5:]), 1)], late, name))
        elif name.startswith('ram_addr'): a(xm, int(name[8:]))
        elif name == 'ram_we': a(xm, Q)
        elif name.startswith('ram_din'): a(xm, Q + 1 + int(name[7:]))
        else: raise KeyError(name)
    for name, s in nl.ports: port(name, s)
    # ---- left-edge track assignment
    nets = []
    for key, d in pins.items():
        assert d['driver'] is not None, key
        cols = [d['driver'][0]] + [s[0] for s in d['sinks']]
        if not d['sinks']: continue
        nets.append((min(cols), max(cols), key))
    nets.sort(key=lambda t: (t[0], t[1], str(t[2])))
    ends = []; track = {}
    for lo, hi, key in nets:
        for t, e in enumerate(ends):
            if e < lo: ends[t] = hi; track[key] = t; break
        else: ends.append(hi); track[key] = len(ends) - 1
    T = len(ends); Y0 = T + 1
    hmax = max(2, R, Q + 9, 9)
    H = Y0 + hmax
    # ---- emit
    out = [f'dims {W} {H} px {PITCH} py 2 cols {N} rows 1']
    out.append(f'part rom {xr} {Y0} 0 {R}'); out.append(f'part arm {xa} {Y0} 0 0')
    if Q: out.append(f'part ram {xm} {Y0} 0 {Q}')
    for k, (kind, ins) in enumerate(nl.nodes): out.append(f'site {k} {PITCH * k + 1} {Y0} {kind} {k}')
    ntrk = nvia = 0
    for key, d in pins.items():
        if not d['sinks']: continue
        ty = Y0 - 1 - track[key]; dcol, dst, _, dwho = d['driver']
        lo = hi = dcol
        def stubpts(st, col):
            pts = [(c, Y0 + r, l) for c, r, l in st]
            return pts + [(col, ty, 1), (col, ty, 0)]
        order = sorted(d['sinks'], key=lambda s: abs(s[0] - dcol))
        first = True
        for col, st, late, who in order:
            pts = stubpts(st, col)
            if first:
                # to the driver: along the track, via, down the driver stub (reversed), ends on the driver pad
                pts += [(dcol, ty, 0), (dcol, ty, 1)] if dcol != col else []
                pts += [(c, Y0 + r, l) for c, r, l in reversed(dst)] if True else []
                first = False
            elif col < lo: pts.append((lo, ty, 0))
            elif col > hi: pts.append((hi, ty, 0))
            lo, hi = min(lo, col), max(hi, col)
            out.append(f'sink {who} - {late} {dwho} : ' + ' '.join(f'{x},{y},{l}' for x, y, l in pts))
    return '\n'.join(out) + '\n', dict(W=W, H=H, tracks=T, nets=len(nets), area=W * H)


if __name__ == '__main__':
    nl = lay.read_nl(sys.argv[1]); text, st = layout(nl)
    open(sys.argv[2], 'w').write(text)
    print(st)
