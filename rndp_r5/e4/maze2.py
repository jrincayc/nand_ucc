#!/usr/bin/env python3
"""maze2.py -- floorplan + PathFinder router (Rust mrouter).  Coordinates are block-relative: x in [0,255], y in [0,255] above the plane top (AY = y 0)."""
import subprocess, sys, os, collections
HERE = os.path.dirname(os.path.abspath(__file__))
def late_of(tok): return 2 if '@2' in tok else 1 if '@1' in tok else 0

def route_engine(nl, order, W, RX=20, pitch=(5, 5), R=30, gap=30, iters=int(os.environ.get('RITERS','60')), tag=os.environ.get('RTAG','m2')):
    N = len(nl.nodes); cols = -(-N // R); px, py = pitch
    X0 = RX + 6; AY = 0; Y0 = AY - 4 * W
    gx0 = RX - 8; gy0 = AY + gap
    pos = {}
    for rank, k in enumerate(order):
        r = rank // cols; j = rank % cols; c = cols - 1 - j if r % 2 else j
        pos[k] = (gx0 + 2 + c * px, gy0 + r * py)
    ax, ay = gx0 - 6, gy0 + 2
    gridx0 = max(0, gx0 - 10); gridy0 = 0
    gw = gx0 + 2 + cols * px + 14 - gridx0; gh = gy0 + R * py + 6
    assert gridx0 + gw <= 512 and gridy0 + gh <= 512, ('layout does not fit 512x512', gridx0 + gw, gridy0 + gh)
    cmds = []
    nets = collections.OrderedDict()
    def net(name): return nets.setdefault(name, dict(drv=None, sinks=[]))
    pads = {}; l0 = {}
    def padmark(x, y, nm): pads[(x, y)] = nm
    for k, (kind, ins) in enumerate(nl.nodes):
        x, y = pos[k]; cmds.append((('place', 1 if kind == 'D' else 0, x, y, 0, 0), 0))
        net(f'n{k}')['drv'] = (x + 1, y, 0); padmark(x + 1, y, f'n{k}')
        for p, tok in enumerate(ins):
            b = tok.split('@')[0]
            if b == 'open': padmark(x, y + p, '#'); continue
            net(b)['sinks'].append((x, y + p, late_of(tok))); padmark(x, y + p, b)
    portpad = {}
    for idx, nm_ in enumerate([f'arm_addr{i}' for i in range(4)] + ['arm_en'] + [f'wdata{j}' for j in range(8)] + ['ram_addr0']):
        portpad[nm_] = (gridx0, gy0 + 2 + 3 * idx)
    for name, tok in nl.ports:
        b = tok.split('@')[0]; late = late_of(tok)
        if name in portpad: c = portpad[name]
        else: raise KeyError(name)
        net(b)['sinks'].append((c[0], c[1], late)); padmark(c[0], c[1], b)
    for j in range(25):
        c = (X0 + 4 * j, AY) if j < 24 else (RX, AY)
        net(f'x{j}')['drv'] = (c[0], c[1], 1); padmark(c[0], c[1], f'x{j}'); l0[c] = f'x{j}'
    ids = {n: i for i, n in enumerate(nets)}
    prob = [f'grid {gridx0} {gridy0} {gw} {gh}']
    for (x, y), nm in pads.items(): prob.append(f'pad {x} {y} {-2 if nm == "#" else ids[nm]}')
    for (x, y), nm in l0.items(): prob.append(f'l0 {x} {y} {ids[nm]}')
    for n, d in nets.items():
        if d['drv'] is None or not d['sinks']: continue
        prob.append(f'net {ids[n]} {len(d["sinks"])}'); prob.append('d %d %d %d' % d['drv'])
        for s in d['sinks']: prob.append('s %d %d %d' % s)
    pf = f'/tmp/{tag}.prob'; of = f'/tmp/{tag}.out'
    open(pf, 'w').write('\n'.join(prob) + '\n')
    r = subprocess.run([os.path.join(HERE, 'mrouter/mrouter'), pf, of, '--iters', str(iters)], capture_output=True, text=True)
    sys.stderr.write(r.stderr[-600:])
    inv = {i: n for n, i in ids.items()}; fails = 0; cur = collections.defaultdict(list)
    for line in open(of):
        t = line.split()
        if t[2] == 'FAIL': fails += 1; continue
        if t[2] == 'END': continue
        nid_, s, kind = int(t[0]), int(t[1]), t[2]; late = int(t[3])
        if kind == 'T': cmds.append((('track', int(t[4]), int(t[5]), int(t[6]), int(t[7]), int(t[8])), late))
        else: cmds.append((('via', int(t[4]), int(t[5])), late))
    return cmds, dict(fails=fails, X0=X0, Y0=Y0, AY=AY, gx0=gx0, gy0=gy0, portpad=portpad, pos=pos, grid=(gridx0, gridy0, gw, gh), RX=RX)
