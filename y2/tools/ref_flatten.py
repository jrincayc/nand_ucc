#!/usr/bin/env python3
"""ref_flatten.py -- reference flattener for RNDP replicator 1 (Y machine, hardware description -> PCB build commands).

Geometry = the "dedicated-lane" layout (RNDP spec, replicator 1).  All coordinates are RELATIVE to the issuing arm's origin.
The child's arm is placed at (CHILD_DX, 0); its coordinates are the parent's plus that offset.

  ARM  rotation 1 at (0,0):   occupies x 0..8, y 0..1.  pins: ADDRi (8-i,0)  EN (4,0)  DATAj (8-j,1)
  ROM  rotation 1 at (-15,0): occupies x -15..-2, y 0..1 (14 address bits).  pins: ADDRi (-2-i,0)  DATAj (-2-j,1)
  node g of the core diagonal (core nodes 0..n_core-1, tie = n_core):   NAND/DFF at (X0+2g, Y0+3g)
  RAM tile k, gate j:  global id g = n_core+1+TG*k+j ;  at (XT+2j, Y0+3g)   with XT = x(tie)+8   (tiles are stacked in y)
  NAND pins: A (x,y) B (x,y+1) Y (x+1,y);  DFF pins: D (x,y) Q (x+1,y).

Wiring one sink: driver output pin (tc,dr), sink pad (px,py), lane row r:
   TRACK layer1 (tc,dr)-(tc,r) ; VIA (tc,r) ; TRACK layer0 (px,r)-(tc,r) ; [if r != py] TRACK layer0 (px,r)-(px,py)
   NAND/DFF input pin p:  r = y-1+2p.   ARM/ROM sinks: see PORT_* below.
Special driver sites: ROM data j -> (-2-j, 1).  RAM read bit c (output 8+c of the last tile) -> the real pin is first extended
   along its row to the out column XR+c:  TRACK layer0 (xpin,ypin)-(XR+c,ypin), VIA (XR+c,ypin);  driver site = (XR+c, ypin).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE]
import hd as H

X0, Y0 = 10, 13
ROM_X, ROM_Y, ROM_ROT = -15, 0, 1
ARM_ROT = 1
CHILD_DX = 4700
TILE_GAP = 8             # XT = x(tie) + TILE_GAP
OUTCOL_GAP = 124         # XR = XT + OUTCOL_GAP
KIND = {'nand': 0, 'dff': 1, 'rom': 2, 'arm': 3}


class Flat:
    pass


def flatten(hd):
    f = Flat(); f.hd = hd
    ab = hd.params['ab']; f.rom_abits = ab - 1
    f.kind, f.ins = [], []
    names = {}
    pend = []
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
    f.tile_id = tile_id

    def resolve(ref):
        if ref == 'run': return ('run',)
        if ref == 'tie': return ('n', f.tie)
        if ref.startswith('rom') and ref[3:].isdigit(): return ('rom', int(ref[3:]))
        if ref.startswith('ramrd') and ref[5:].isdigit(): return ('ramrd', int(ref[5:]))
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
    f.ports = [(n, resolve(r)) for n, r in hd.ports]
    # geometry constants derived from the machine
    f.tie_x = X0 + 2 * f.tie; f.tie_y = Y0 + 3 * f.tie
    f.ram_part = bool(hd.params.get('ram_part')); f.ram_abits = hd.params.get('ram_abits', 0)
    f.RX, f.RY = f.tie_x + 8, f.tie_y + 3          # origin of the RAM part (replicator 2)
    f.XT = f.tie_x + TILE_GAP
    f.XR = f.XT + OUTCOL_GAP
    return f


def node_kind(f, i):
    if i < f.n_core: return f.kind[i]
    if i == f.tie: return 'tie'
    return f.tkind[i - f.n_core - 1]


def node_ins(f, i):
    if i < f.n_core: return f.ins[i]
    if i == f.tie: return []
    return f.tins[i - f.n_core - 1]


def node_pos(f, i):
    if i <= f.n_core: return (X0 + 2 * i, Y0 + 3 * i)
    k, j = divmod(i - f.n_core - 1, f.TG)
    return (f.XT + 2 * j, Y0 + 3 * i)


def counts(f):
    from collections import Counter
    c = Counter(node_kind(f, i) for i in range(f.n_nodes))
    return dict(nand=c['nand'] + c['tie'], dff=c['dff'], nodes=f.n_nodes)


def extent(f):
    """bounding box of parts (x0,y0,x1,y1), relative coordinates."""
    if f.ram_part: return (ROM_X, -19, f.RX + 3 + 8, f.RY + f.ram_abits + 9)
    xs = [node_pos(f, i)[0] for i in range(f.n_nodes)]
    ys = [node_pos(f, i)[1] for i in range(f.n_nodes)]
    return (ROM_X, -19, f.XR + 8, max(ys) + 1)


# port sink geometry (arm-relative): (px, py, r)
def port_sink(name, f=None):
    if name.startswith('ram_'):
        a = f.ram_abits
        k = int(name[8:]) if name.startswith('ram_addr') else a if name == 'ram_we' else a + 1 + int(name[7:])
        return (f.RX, f.RY + k, f.RY + k)
    if name.startswith('rom_addr'):
        i = int(name[8:]); return (-2 - i, 0, -6 - i)
    if name.startswith('arm_addr'):
        i = int(name[8:]); return (8 - i, 0, -1 - i)
    if name.startswith('wdata'):
        j = int(name[5:]); return (8 - j, 1, 2 + j)
    if name == 'arm_en': return (4, 0, -5)
    raise KeyError(name)


def out_site(f, s):
    """(tc, dr): driver site for the lane scheme."""
    if s[0] == 'rom': return (-2 - s[1], 1)
    if s[0] == 'run': return (f.tie_x + 1, f.tie_y)
    if s[0] == 'ramrd' and f.ram_part: return (f.RX + 3 + s[1], f.RY + s[1])
    if s[0] == 'ramrd':
        g = ramrd_gate(f, s[1]); return (f.XR + s[1], Y0 + 3 * g)
    x, y = node_pos(f, s[1]); return (x + 1, y)


def ramrd_gate(f, c):
    """global id of the last-tile node that is output 8+c of the tile."""
    return f.tile_id(f.W - 1, f.tile.outs[8 + c] - f.tile.n_in)


def sink_cmds(site, px, py, r):
    tc, dr = site
    c = [('track', 1, tc, dr, tc, r), ('via', tc, r), ('track', 0, px, r, tc, r)]
    if r != py: c.append(('track', 0, px, r, px, py))
    return c


def commands(f, rom_bytes, dx=0):
    cmds = _commands(f, rom_bytes)
    return [shift(c, dx) for c in cmds]


def shift(c, dx):
    if c[0] == 'place': return ('place', c[1], c[2] + dx, c[3], c[4], c[5])
    if c[0] == 'track': return ('track', c[1], c[2] + dx, c[3], c[4] + dx, c[5])
    if c[0] == 'via': return ('via', c[1] + dx, c[2])
    if c[0] == 'rom': return ('rom', c[1] + dx, c[2], c[3], c[4])
    raise ValueError(c)


def _commands(f, rom_bytes):
    cmds = []
    for i in range(f.n_nodes):
        k = node_kind(f, i)
        if k == 'hole': continue
        x, y = node_pos(f, i)
        cmds.append(('place', 1 if k == 'dff' else 0, x, y, 0, 0))
    cmds.append(('place', KIND['rom'], ROM_X, ROM_Y, ROM_ROT, f.rom_abits))
    cmds.append(('place', KIND['arm'], 0, 0, ARM_ROT, 0))
    if f.ram_part: cmds.append(('place', 4, f.RX, f.RY, 0, f.ram_abits))
    for a, v in enumerate(rom_bytes):
        if v: cmds.append(('rom', ROM_X, ROM_Y, a, v))
    # RAM read bits: extend the real pin to the out column
    for c in range(8 if f.ram_part else 0):
        cmds.append(('track', 0, f.RX + 1, f.RY + c, f.RX + 3 + c, f.RY + c)); cmds.append(('via', f.RX + 3 + c, f.RY + c))
    for c in range(0 if f.ram_part else 8):
        g = ramrd_gate(f, c); x, y = node_pos(f, g)
        cmds.append(('track', 0, x + 1, y, f.XR + c, y)); cmds.append(('via', f.XR + c, y))
    run_cmds = []
    for i in range(f.n_nodes):
        k = node_kind(f, i)
        if k in ('tie', 'hole'): continue
        x, y = node_pos(f, i)
        for p, s in enumerate(node_ins(f, i)):
            cs = sink_cmds(out_site(f, s), x, y + p, y - 1 + 2 * p)
            (run_cmds if s[0] == 'run' else cmds).extend(cs)
    P = dict(f.ports)
    order = [n for n, _ in f.ports]
    assert order[-1] == 'arm_en'
    for n in order:
        px, py, r = port_sink(n, f)
        cmds.extend(sink_cmds(out_site(f, P[n]), px, py, r))
    cmds.extend(run_cmds)
    f.n_run_cmds = len(run_cmds)
    return cmds


def netlist_pins(f):
    """for the validation: list of (part_key, pin, x, y, net_key) ; part_key = ('n', node) | 'rom' | 'arm'."""
    pins = []
    for i in range(f.n_nodes):
        k = node_kind(f, i)
        if k == 'hole': continue
        x, y = node_pos(f, i)
        pins.append((x + 1, y, ('n', i)))                         # output pin
        for p, s in enumerate(node_ins(f, i)):
            pins.append((x, y + p, s if s[0] != 'run' else ('n', f.tie)))
    for j in range(8): pins.append((-2 - j, 1, ('rom', j)))
    P = dict(f.ports)
    for n in [n for n, _ in f.ports]:
        px, py, r = port_sink(n); s = P[n]
        pins.append((px, py, s))
    for i in range(14): pins.append((-2 - i, 0, ('romaddr', i)))   # placeholder, replaced below
    return pins


if __name__ == '__main__':
    hd = H.read(open(sys.argv[1]).read()); f = flatten(hd)
    print(counts(f), 'ports', len(f.ports), 'extent', extent(f), 'XT', f.XT, 'XR', f.XR)
    cm = commands(f, [])
    from collections import Counter
    print(Counter(c[0] for c in cm))
