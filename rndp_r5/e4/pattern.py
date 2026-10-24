#!/usr/bin/env python3
"""pattern.py -- compiles the per-row plane-dump pattern (the 'microcode' that lives in the plane) into instruction words.
For the dumped row rr: preamble (A.x hi, B.x hi, A.y hi, B.y hi), the ring tile (8 commands), and for every column j a bit-1 group (cond: captured bit j == 1)
and a bit-0 group (captured bit j == 0).  Arm register persistence is exploited inside a group only (groups can be skipped), starting from the preamble state."""
import itertools, sys
import spec as S
import plane as PL

def ylo(n, k): return ('lo', n, k)
def yhi(n): return ('hi', n)

def cmd_regs(cmd):
    """required register values for a command with symbolic y: x ints (arm-relative), y = (n,k)."""
    t = cmd[0]
    if t == 'place':
        _, kind, x, y, rot, val = cmd
        return {S.AXL: ('c', x & 255), S.AXH: ('c', (x >> 8) & 255), S.AYL: ylo(*y), S.AYH: yhi(y[0]), S.KIND: ('c', kind), S.ANGLE: ('c', rot), S.VAL: ('c', val)}, 1
    if t == 'track':
        _, layer, x0, y0, x1, y1 = cmd
        return {S.AXL: ('c', x0 & 255), S.AXH: ('c', (x0 >> 8) & 255), S.AYL: ylo(*y0), S.AYH: yhi(y0[0]), S.BXL: ('c', x1 & 255), S.BXH: ('c', (x1 >> 8) & 255),
                S.BYL: ylo(*y1), S.BYH: yhi(y1[0]), S.VAL: ('c', layer)}, 4
    raise ValueError(t)

def to_word(reg, key):
    if key[0] == 'c': return dict(reg=reg, src=S.SRC_CONST, d=key[1])
    if key[0] == 'lo': return dict(reg=reg, src=S.SRC_YLO if key[1] == 0 else S.SRC_YLO1, d=key[2])
    if key[0] == 'hi': return dict(reg=reg, src=S.SRC_YHI if key[1] == 0 else S.SRC_YHI1, d=0)

ORDER = (S.AXL, S.AXH, S.AYL, S.AYH, S.BXL, S.BXH, S.BYL, S.BYH, S.KIND, S.ANGLE, S.VAL)

def compile_seq(cmds, state, restore=None):
    """cmds in the given order -> (words, final_state).  restore: registers whose preamble value must hold at the end (re-written if changed)."""
    st = dict(state); out = []
    for c in cmds:
        need, code = cmd_regs(c)
        for r in ORDER:
            if r in need and st.get(r) != need[r]:
                out.append(to_word(r, need[r])); st[r] = need[r]
        out.append(dict(reg=S.CMD, src=S.SRC_CONST, d=code))
    if restore:
        for r, key in restore.items():
            if st.get(r) != key: out.append(to_word(r, key)); st[r] = key
    return out, st

def best_order(cmds, state, restore):
    best = None
    for perm in itertools.permutations(range(len(cmds))):
        w, _ = compile_seq([cmds[i] for i in perm], state, restore)
        if best is None or len(w) < len(best[0]): best = (w, perm)
    return best[0]

def tile_cmds(geom, j=None):
    """symbolic commands of the ring tile (j None) or of the column-j cell (bit given by geom['bit'])."""
    raise NotImplementedError

def sym(cmds_local, X0shift):
    """convert plane.py commands for a tile at row origin y=0 (local) into symbolic form: x + xoff, y -> (n,k) with n = k//4, k%4."""
    out = []
    for c in cmds_local:
        if c[0] == 'place':
            _, kind, x, y, rot, val = c; out.append(('place', kind, x + X0shift, (y // 4, y % 4), rot, val))
        elif c[0] == 'track':
            _, l, x0, y0, x1, y1 = c; out.append(('track', l, x0 + X0shift, (y0 // 4, y0 % 4), x1 + X0shift, (y1 // 4, y1 % 4)))
    return out

def build_pattern(X0, RX, xoff, B=S.B):
    """-> list of instruction dicts (ph=PH_P), in execution order.  X0, RX: plane column origin and ring x in machine-local coordinates; xoff = DX - AX."""
    xh = {((X0 + xoff + 4 * j + u) >> 8) & 255 for j in range(B) for u in range(4)} | {((RX + xoff + u) >> 8) & 255 for u in range(5)}
    assert len(xh) == 1, ('plane spans two x high bytes', xh)
    xhi = xh.pop()
    pre = {S.AXH: ('c', xhi), S.BXH: ('c', xhi), S.AYH: yhi(0), S.BYH: yhi(0)}
    words = [dict(to_word(r, k), ph=S.PH_P, cen=0, cpol=0, ccol=0) for r, k in pre.items()]
    # ring tile
    ring = sym(PL.row_cmds(RX, 0, X0 + 4 * (B - 1) + 1), xoff)
    w = best_order(ring, pre, pre)
    words += [dict(x, ph=S.PH_P, cen=0, cpol=0, ccol=0) for x in w]
    for j in range(B):
        x = X0 + 4 * j
        for bit in (1, 0):
            cmds = sym(PL.cell_cmds(x, 0, bit), xoff)
            w = best_order(cmds, pre, pre)
            words += [dict(x_, ph=S.PH_P, cen=1, cpol=bit, ccol=j) for x_ in w]
    return words

if __name__ == '__main__':
    X0, RX, xoff = 150, 144, 0
    w = build_pattern(X0, RX, xoff)
    print(len(w), 'pattern words (ring + 24 columns x 2 variants)')
    import collections
    print(collections.Counter(x['reg'] for x in w))
