"""lay.py -- read the layout tool's .lay output and the .nl netlist; reference build commands; expected pin->net keys."""
import sys

class Lay: pass

def read_nl(path):
    nl = Lay(); nl.nodes = []; nl.ports = []; nl.rom = nl.ram = 0
    for line in open(path):
        w = line.split()
        if not w: continue
        if w[0] == 'rom': nl.rom = int(w[1])
        elif w[0] == 'ram': nl.ram = int(w[1])
        elif w[0] == 'n': nl.nodes.append((w[2], w[3:]))
        elif w[0] == 'p': nl.ports.append((w[1], w[2]))
    return nl

def read_lay(path):
    L = Lay(); L.parts = {}; L.sites = []; L.sinks = []
    for line in open(path):
        w = line.split()
        if w[0] == 'dims': L.W, L.H, L.px, L.py, L.cols, L.rows = int(w[1]), int(w[2]), int(w[4]), int(w[6]), int(w[8]), int(w[10])
        elif w[0] == 'part': L.parts[w[1]] = tuple(map(int, w[2:6]))        # x y rot abits
        elif w[0] == 'site': L.sites.append((int(w[2]), int(w[3]), w[4], int(w[5])))   # x y kind origid
        elif w[0] == 'sink':
            i = w.index(':'); who = w[1:3]; late = int(w[3]); drv = w[4]
            pts = [tuple(map(int, p.split(','))) for p in w[i + 1:]]
            L.sinks.append((who, late, drv, pts))
    return L

def rot_cell(c, w, h, rot):
    for _ in range(rot): c = (h - 1 - c[1], c[0]); w, h = h, w
    return c

def base_dims(kind, abits):
    return {'rom': (2, max(abits, 8)), 'arm': (2, 9), 'ram': (2, abits + 9)}[kind]

def pcell(L, part, dx, dy):
    x, y, rot, ab = L.parts[part]; bw, bh = base_dims(part, ab)
    c = rot_cell((dx, dy), bw, bh, rot); return (x + c[0], y + c[1])

def port_cell(L, nl, name):
    n = lambda p: int(name[len(p):])
    if name.startswith('rom_addr'): return pcell(L, 'rom', 0, n('rom_addr'))
    if name.startswith('arm_addr'): return pcell(L, 'arm', 0, n('arm_addr'))
    if name.startswith('wdata'): return pcell(L, 'arm', 1, n('wdata'))
    if name == 'arm_en': return pcell(L, 'arm', 0, 4)
    if name.startswith('ram_addr'): return pcell(L, 'ram', 0, n('ram_addr'))
    if name == 'ram_we': return pcell(L, 'ram', 0, nl.ram)
    if name.startswith('ram_din'): return pcell(L, 'ram', 0, nl.ram + 1 + n('ram_din'))
    raise KeyError(name)

def commands(L, nl, rom_bytes=()):
    cmds = []
    for (x, y, k, o) in L.sites:
        if k != 'E': cmds.append(('place', 1 if k == 'D' else 0, x, y, 0, 0))
    for name, kind in (('rom', 2), ('arm', 3), ('ram', 4)):
        if name in L.parts:
            x, y, rot, ab = L.parts[name]; cmds.append(('place', kind, x, y, rot, ab))
    rx, ry = L.parts['rom'][:2]
    for a, v in enumerate(rom_bytes):
        if v: cmds.append(('rom', rx, ry, a, v))
    order = sorted(range(len(L.sinks)), key=lambda i: (L.sinks[i][1], i))        # late sinks last (EN then RUN)
    for i in order:
        pts = L.sinks[i][3]
        for a, b in zip(pts, pts[1:]):
            if a[2] == b[2]: cmds.append(('track', a[2], a[0], a[1], b[0], b[1]))
            else: assert a[:2] == b[:2]; cmds.append(('via', a[0], a[1]))
    return cmds

def expected_keys(L, nl):
    ex = {}
    for (x, y, k, o) in L.sites:
        if k == 'E': continue
        kind, ins = nl.nodes[o]
        ex[(x + 1, y)] = ('n', o)
        for p, s in enumerate(ins):
            ex[(x, y + p)] = ('open', o, p) if s == 'open' else key(s)
    for name, s in nl.ports: ex[port_cell(L, nl, name)] = key(s)
    for j in range(8): ex.setdefault(pcell(L, 'rom', 1, j), ('rom', j))
    for i in range(nl.rom): ex.setdefault(pcell(L, 'rom', 0, i), ('unusedrom', i))
    for i in range(4): ex.setdefault(pcell(L, 'arm', 0, i), ('unusedarm', i))
    ex.setdefault(pcell(L, 'arm', 0, 4), ('unusedarm', 4))
    for j in range(8): ex.setdefault(pcell(L, 'arm', 1, j), ('unusedarm', 5 + j))
    if nl.ram:
        for c in range(8): ex.setdefault(pcell(L, 'ram', 1, c), ('ramo', c))
        for k in range(nl.ram + 9): ex.setdefault(pcell(L, 'ram', 0, k), ('unusedram', k))
    return ex

def key(s):
    s = s.split('@')[0]
    if s.startswith('ramo'): return ('ramo', int(s[4:]))
    if s.startswith('rom'): return ('rom', int(s[3:]))
    return ('n', int(s[1:]))
