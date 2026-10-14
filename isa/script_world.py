"""Reference child construction: the exact PLACE / PROGRAM_ROM / WIRE sequence (spec section 7 order)
that builds a Hack-vN machine through an arm, written as a rndw driver script."""
import math
from export_world import OX, OY


def layout(c, ram_abits_unused=None, rom_abits=12, ox=OX, oy=OY):
    nin, nd, ng = c.n_in, c.n_dff, len(c.gates)
    T = nd + ng + 1
    cols = math.ceil(math.sqrt(T))
    pos = lambda s: (ox + 3 * (s % cols), oy + 3 * (s // cols))
    parts = [('dff' if s < nd else 'nand',) + pos(s) for s in range(T)]
    tie = T - 1
    rx, ry = ox + 3 * cols + 6, oy
    ax, ay = rx, oy + 20
    parts += [('rom', rx, ry), ('arm', ax, ay)]
    romdata, run_id = c.buses['romdata'], c.buses['run'][0]

    def out_site(w):
        if w in romdata: return (rx + 1, ry + romdata.index(w))
        if w == run_id: return (parts[tie][1] + 1, parts[tie][2])
        x, y = parts[w - nin][1:]; return (x + 1, y)
    wires, run_wires, en_wire = [], [], None
    for i, d in enumerate(c.dffd):
        x, y = parts[i][1:]; wires.append((out_site(d), (x, y)))
    for g, (a, b) in enumerate(c.gates):
        x, y = parts[nd + g][1:]
        for pin, w in ((0, a), (1, b)):
            wire = (out_site(w), (x, y + pin))
            (run_wires if w == run_id else wires).append(wire)
    for i, w in enumerate(c.outs['rom_addr']): wires.append((out_site(w), (rx, ry + i)))
    for i, w in enumerate(c.outs['arm_addr']): wires.append((out_site(w), (ax, ay + i)))
    for j, w in enumerate(c.outs['wdata']): wires.append((out_site(w), (ax + 1, ay + j)))
    en_wire = (out_site(c.outs['arm_en'][0]), (ax, ay + 4))
    return dict(parts=parts, wires=wires, run_wires=run_wires, en_wire=en_wire, rom_at=(rx, ry), arm_at=(ax, ay),
                tie=tie, cols=cols)


def commands(c, rom_bytes, **kw):
    L = layout(c, **kw)
    cmds = []
    for k, x, y in L['parts']: cmds.append(('place', k, x, y))
    rx, ry = L['rom_at']
    for a, v in enumerate(rom_bytes):
        if v: cmds.append(('rom', rx, ry, a, v))
    for (o, i) in L['wires']: cmds.append(('wire',) + o + i)
    cmds.append(('nop', 3))                       # let the reset state settle before EN is attached
    o, i = L['en_wire']; cmds.append(('wire',) + o + i)
    cmds.append(('nop', 3))
    for (o, i) in L['run_wires']: cmds.append(('wire',) + o + i)
    return cmds, L


def to_script(cmds):
    out = []
    for cm in cmds:
        out.append(' '.join(str(v) for v in cm))
    return '\n'.join(out) + '\n'


def reg_writes(cmds):
    """Register writes the driver issues (same shadow logic: skip unchanged non-CMD registers)."""
    shadow = [None] * 16; n = 0; kinds = {'nand': 0, 'dff': 1, 'rom': 2, 'arm': 3}
    def w(r, v):
        nonlocal n
        if r != 15 and shadow[r] == v: return
        shadow[r] = v; n += 1
    def w16(lo, v): w(lo, v & 255); w(lo + 1, (v >> 8) & 255)
    for cm in cmds:
        if cm[0] == 'place': w16(0, cm[2]); w16(2, cm[3]); w(8, kinds[cm[1]]); w(9, 0); w(15, 1)
        elif cm[0] == 'wire': w16(0, cm[1]); w16(2, cm[2]); w16(4, cm[3]); w16(6, cm[4]); w(15, 2)
        elif cm[0] == 'rom': w16(0, cm[1]); w16(2, cm[2]); w16(4, cm[3]); w(10, cm[4]); w(15, 3)
        elif cm[0] == 'nop': n += cm[1]
    return n
