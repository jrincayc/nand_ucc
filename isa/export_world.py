"""Export the Hack-vN machine as an RNDW seed world (rndw-state 1) with a kernel in the ROM."""
import math, sys
import common
import isahack
from nl_machine import build_machine

KIND = {'NAND': 0, 'DFF': 1, 'ROM': 2, 'ARM': 3}
OX, OY = 300, 300            # machine origin on the grid (keeps K4's PLACE region 100..1700 x 50..60 clear)


def export(c, rom_bytes, ram_preload=None, rom_abits=12, child_rom=True, W=4096, H=4096):
    ram_preload = ram_preload or {}
    nin, nd, ng = c.n_in, c.n_dff, len(c.gates)
    tie = nd + ng                                     # tie-high NAND part id
    T = nd + ng + 1
    cols = math.ceil(math.sqrt(T))
    pos = lambda s: (OX + 3 * (s % cols), OY + 3 * (s // cols))
    parts = [None] * T
    for s in range(T):
        parts[s] = ('DFF' if s < nd else 'NAND',) + pos(s)
    rx, ry = OX + 3 * cols + 6, OY
    ax, ay = rx, OY + 20
    ROM_ID, ARM_ID = T, T + 1
    parts.append(('ROM', rx, ry)); parts.append(('ARM', ax, ay))
    if child_rom:
        parts.append(('ROM', 0, 0))
    lines = ['rndw-state 1', f'cfg {W} {H} {rom_abits} 5000000', 'tick 0', 'faults 0']
    for i, (k, x, y) in enumerate(parts):
        lines.append(f'part {i} {KIND[k]} {x} {y} 0')
    for a, v in enumerate(rom_bytes):
        if v: lines.append(f'rom {ROM_ID} {a} {v}')
    # producer sites of netlist wires
    romdata_ids = c.buses['romdata']; run_id = c.buses['run'][0]

    def out_site(w):
        if w in romdata_ids:
            return (rx + 1, ry + romdata_ids.index(w))
        if w == run_id:
            x, y = parts[tie][1:]; return (x + 1, y)
        s = w - nin if w >= nin else None
        x, y = parts[s][1:]
        return (x + 1, y)
    wires = []
    tags = []
    for i, d in enumerate(c.dffd):
        x, y = parts[i][1:]; wires.append((out_site(d), (x, y)))
    for g, (a, b) in enumerate(c.gates):
        x, y = parts[nd + g][1:]
        wires.append((out_site(a), (x, y))); wires.append((out_site(b), (x, y + 1)))
    for i, w in enumerate(c.outs['rom_addr']): wires.append((out_site(w), (rx, ry + i)))
    for i, w in enumerate(c.outs['arm_addr']): wires.append((out_site(w), (ax, ay + i)))
    wires.append((out_site(c.outs['arm_en'][0]), (ax, ay + 4)))
    for j, w in enumerate(c.outs['wdata']): wires.append((out_site(w), (ax + 1, ay + j)))
    for (ox, oy), (ix, iy) in wires:
        lines.append(f'wire {ox} {oy} {ix} {iy}')
    # initial state: post-reset (sF0 = 1, PC = 0x1000), RAM preload
    init = set()
    st = c.outs['st']; init.add(st[0] - nin)
    pc = c.outs['pc']; init.add(pc[12] - nin)
    mem = c.outs['mem']
    for a, v in ram_preload.items():
        for b in range(8):
            if (v >> b) & 1: init.add(mem[8 * a + b] - nin)
    for p in sorted(init): lines.append(f'dff {p} 1')
    meta = dict(nd=nd, ng=ng, tie=tie, ROM_ID=ROM_ID, ARM_ID=ARM_ID, child_id=(T + 2 if child_rom else None),
                mem_ids=[w - nin for w in mem], n_seed_parts=len(parts))
    return '\n'.join(lines) + '\n', meta
