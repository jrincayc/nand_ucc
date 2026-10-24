#!/usr/bin/env python3
"""maze.py -- floorplan + two-layer A* router for the engine, cost = number of arm commands (runs + vias) + tiny length term.
Grid cell (x,y), layer 0/1.  Pads (gate/arm pins) pierce both layers and block them for other nets.  Plane column tops are L0 terminals at y=0.
route_engine(nl, order, W, RX, pitch, R) -> (cmds, info)   cmds in world coordinates, plane NOT included."""
import heapq, sys
import elay

LEN = 0.02; RUN = 1.0; VIA = 1.0

def late_of(tok): return 2 if '@2' in tok else 1 if '@1' in tok else 0

class Grid:
    def __init__(self, x0, y0, w, h):
        self.x0, self.y0, self.w, self.h = x0, y0, w, h
        self.occ = [[[-1] * w for _ in range(h)] for _ in range(2)]        # net id owning copper in the cell on that layer
        self.pad = [[-1] * w for _ in range(h)]                              # net id of a pad (blocks both layers for others); -2 = blocked for all
        self.l0only = {}                                                     # (x,y) -> net : terminal reachable only on layer 0
    def ok(self, x, y, l, net):
        gx, gy = x - self.x0, y - self.y0
        if gx < 0 or gy < 0 or gx >= self.w or gy >= self.h: return False
        p = self.pad[gy][gx]
        if p != -1 and p != net: return False
        o = self.occ[l][gy][gx]
        return o == -1 or o == net

def search(G, net, tree, goals, goal_l0):
    """tree: set of (x,y,l) sources; goals: set of (x,y) cells (any layer) ; goal_l0: set of (x,y) cells requiring layer 0.  Returns list of states path."""
    tx = [g[0] for g in goals] + [g[0] for g in goal_l0]; ty = [g[1] for g in goals] + [g[1] for g in goal_l0]
    def h(x, y):
        d = min(abs(x - a) + abs(y - b) for a, b in zip(tx, ty)) if len(tx) < 6 else min(abs(x - a) + abs(y - b) for a, b in zip(tx, ty))
        return LEN * d
    pq = []; best = {}; par = {}
    for (x, y, l) in tree:
        s = (x, y, l, 0); best[s] = 0.0; heapq.heappush(pq, (h(x, y), 0.0, s)); par[s] = None
    while pq:
        f, g, s = heapq.heappop(pq)
        if best.get(s, 1e18) < g - 1e-12: continue
        x, y, l, d = s
        if ((x, y) in goals or ((x, y) in goal_l0 and l == 0)) and (x, y, l) not in tree:
            path = []; 
            while s is not None: path.append(s); s = par[s]
            return path[::-1]
        # via
        if G.ok(x, y, 1 - l, net) and (x, y) not in G.l0only:
            ns = (x, y, 1 - l, 0); ng = g + VIA
            if ng < best.get(ns, 1e18): best[ns] = ng; par[ns] = s; heapq.heappush(pq, (ng + h(x, y), ng, ns))
        for nd, dx, dy in ((1, 1, 0), (1, -1, 0), (2, 0, 1), (2, 0, -1)):
            nx, ny = x + dx, y + dy
            if not G.ok(nx, ny, l, net): continue
            if (nx, ny) in G.l0only and G.l0only[(nx, ny)] != net: continue
            if (nx, ny) in G.l0only and l != 0: continue
            ng = g + LEN + (0 if d == nd else RUN)
            ns = (nx, ny, l, nd)
            if ng < best.get(ns, 1e18): best[ns] = ng; par[ns] = s; heapq.heappush(pq, (ng + h(nx, ny), ng, ns))
    return None

def path_cmds(path, late, out):
    """convert state path to commands, return cells used [(x,y,l)], vias [(x,y)]"""
    cells = []; vias = []; i = 0; n = len(path)
    runs = []
    cur = None
    for k in range(1, n):
        a, b = path[k - 1], path[k]
        if a[2] != b[2]:
            if cur: runs.append(cur); cur = None
            runs.append(('via', a[0], a[1])); continue
        if cur and cur[0] == 'track' and cur[1] == b[2] and ((cur[2] == cur[4] == b[0] and b[0] == a[0]) or (cur[3] == cur[5] == b[1] and b[1] == a[1])) and (a[0], a[1]) == (cur[4], cur[5]):
            cur = ('track', cur[1], cur[2], cur[3], b[0], b[1])
        else:
            if cur: runs.append(cur)
            cur = ('track', b[2], a[0], a[1], b[0], b[1])
    if cur: runs.append(cur)
    for r in runs: out.append((r, late))
    for s in path: cells.append((s[0], s[1], s[2]))
    return runs

def route_engine(nl, order, W, RX, pitch=(4, 4), R=24, gap=14, verbose=False, rseed=0, longfirst=True, priority=()):
    N = len(nl.nodes); cols = -(-N // R); px, py = pitch
    X0 = RX + 6; AY = 0; Y0 = AY - 4 * W
    gx0 = RX - 8; gy0 = AY + gap
    pos = {}
    for rank, k in enumerate(order):
        r = rank // cols; j = rank % cols; c = cols - 1 - j if r % 2 else j
        pos[k] = (gx0 + 2 + c * px, gy0 + r * py)
    arm = (gx0 - 6, gy0 + 2)                     # arm part origin (2 x 9)
    gw = cols * px + 40; gh = R * py + gap + 50
    G = Grid(gx0 - 10, 1, gw + 10, gh)
    cmds = []                                    # (command, late)
    # parts and pads
    nets = {}                                    # name -> dict(drv=[(x,y,kind)], sinks=[(x,y,kind,late)])
    def net(name): return nets.setdefault(name, dict(drv=None, sinks=[]))
    def padmark(x, y, nm):
        G.pad[y - G.y0][x - G.x0] = nm
    for k, (kind, ins) in enumerate(nl.nodes):
        x, y = pos[k]; cmds.append((('place', 1 if kind == 'D' else 0, x, y, 0, 0), 0))
        net(f'n{k}')['drv'] = (x + 1, y, 'pad'); padmark(x + 1, y, f'n{k}')
        for p, tok in enumerate(ins):
            b = tok.split('@')[0]
            if b == 'open': padmark(x, y + p, -2); continue
            net(b)['sinks'].append((x, y + p, 'pad', late_of(tok))); padmark(x, y + p, b)
    ax, ay = arm
    cmds.append((('place', 3, ax, ay, 0, 0), 0))
    for dy in range(9):
        for dx in range(2): padmark(ax + dx, ay + dy, -2)
    for name, tok in nl.ports:
        b = tok.split('@')[0]; late = late_of(tok)
        if name.startswith('arm_addr'): c = (ax, ay + int(name[8:]))
        elif name == 'arm_en': c = (ax, ay + 4)
        elif name.startswith('wdata'): c = (ax + 1, ay + int(name[5:]))
        elif name == 'ram_addr0': c = (RX - 3, gy0 - 6)
        else: raise KeyError(name)
        net(b)['sinks'].append((c[0], c[1], 'pad', late)); padmark(c[0], c[1], b)
    # external drivers: plane column tops (x_j, AY) ; x24 = ring out (RX, AY)
    for j in range(25):
        c = (X0 + 4 * j, AY) if j < 24 else (RX, AY)
        net(f'x{j}')['drv'] = (c[0], c[1], 'l0'); padmark(c[0], c[1], f'x{j}'); G.l0only[c] = f'x{j}'
    # route
    names = {}
    def nid(n): return names.setdefault(n, len(names))
    for n in nets: nid(n)
    # padmark used names; convert to ids
    for gy in range(G.h):
        for gx in range(G.w):
            p = G.pad[gy][gx]
            if isinstance(p, str): G.pad[gy][gx] = nid(p)
    G.l0only = {c: nid(n) for c, n in G.l0only.items()}
    hp = lambda n: sum(abs(s[0] - nets[n]['drv'][0]) + abs(s[1] - nets[n]['drv'][1]) for s in nets[n]['sinks']) if nets[n]['drv'] else 0
    # pin-escape reservations: cells beside every pad that only the owning net may use
    RL = max(1, (px - 2) // 2)
    def reserve(x, y, dxs, i):
        for k in range(1, RL + 1):
            cx = x + dxs * k; gx, gy = cx - G.x0, y - G.y0
            if G.pad[gy][gx] == -1 and G.occ[0][gy][gx] == -1: G.occ[0][gy][gx] = G.occ[1][gy][gx] = i
            else: break
    for n, d in nets.items():
        i = nid(n)
        if d['drv'] and d['drv'][2] == 'pad' and d['sinks']: reserve(d['drv'][0], d['drv'][1], +1, i)
        for (sx, sy, sk, late) in d['sinks']:
            if sk == 'pad': reserve(sx, sy, -1, i)
    order_nets = sorted(nets, key=lambda n: (0 if n in priority else 1, -hp(n) if longfirst else hp(n)))
    fails = 0; failed = set()
    for n in order_nets:
        d = nets[n]
        if d['drv'] is None or not d['sinks']: continue
        i = nid(n); dx, dy, dk = d['drv']
        tree = {(dx, dy, 0), (dx, dy, 1)} if dk == 'pad' else {(dx, dy, 0)}
        sinks = sorted(d['sinks'], key=lambda s: (s[3], abs(s[0] - dx) + abs(s[1] - dy)))
        for (sx, sy, sk, late) in sinks:
            # recompute nearest-first among remaining is skipped (sorted by distance from driver)
            path = search(G, i, tree, {(sx, sy)}, set())
            if path is None: fails += 1; failed.add(n); continue
            out = []; runs = path_cmds(path, late, out)
            for r in runs:
                if r[0] == 'via':
                    _, x, y = r; G.occ[0][y - G.y0][x - G.x0] = i; G.occ[1][y - G.y0][x - G.x0] = i; tree.add((x, y, 0)); tree.add((x, y, 1))
                else:
                    _, l, x0, y0, x1, y1 = r
                    for xx in range(min(x0, x1), max(x0, x1) + 1):
                        for yy in range(min(y0, y1), max(y0, y1) + 1):
                            G.occ[l][yy - G.y0][xx - G.x0] = i; tree.add((xx, yy, l))
            cmds += out
    # D0 long wire: virtual pin (RX-3, gy0-6) down to the ring input (RX, Y0)
    vx, vy = RX - 3, gy0 - 6
    cmds.append((('track', 1, vx, vy, vx, Y0), 0)); cmds.append((('via', vx, Y0), 0)); cmds.append((('track', 0, vx, Y0, RX, Y0), 0))
    return cmds, dict(failed=failed, fails=fails, X0=X0, Y0=Y0, AY=AY, gx0=gx0, gy0=gy0, arm=arm, pos=pos, grid=(G.x0, G.y0, G.w, G.h))
