"""layrom.py -- independent decoder of the compact layout data in a ROM image (same command order as the builder).  decode(rom, symbols.txt) -> commands."""
def symbols(path):
    d = {}
    for line in open(path):
        if '=' in line:
            k, v = line.split('='); d[k.strip()] = int(v.strip(), 0)
    return d

def s16(v): return v - 65536 if v >= 32768 else v

def decode(rom, symfile):
    S = symbols(symfile);     at = lambda lab: S[lab] - S['start']          # offset inside the image (start = ROM_BASE)
    cmds = []
    dx = S['CHILD_DX']
    for k in ('GX0', 'GY0', 'ROM_X', 'ROM_Y', 'ARM_X', 'ARM_Y', 'RAM_X', 'RAM_Y'): S[k] = s16(S[k] & 0xFFFF)
    cmds.append(('place', 2, dx + S['ROM_X'], S['ROM_Y'], S['ROM_ROT'], S['ROM_AB']))
    cmds.append(('place', 3, dx + S['ARM_X'], S['ARM_Y'], S['ARM_ROT'], 0))
    kp = at('lay_kinds'); kinds = []; ns = S['ROWS'] * S['COLS']
    if 'RA_rdb' in S:                                  # Hack builder: exception list of (plain NAND count, kind)
        while len(kinds) < ns:
            n, k = rom[kp], rom[kp + 1]; kp += 2; kinds += [0] * n + [k]
        kinds = kinds[:ns]
    else:
        for i in range(ns): kinds.append((rom[kp + i // 4] >> (2 * (i % 4))) & 3)
    for r in range(S['ROWS']):
        for c in range(S['COLS']):
            k = kinds[r * S['COLS'] + c]
            if k != 2: cmds.append(('place', k, dx + S['GX0'] + c * S['PX'], S['GY0'] + r * S['PY'], 0, 0))
    cmds.append(('place', 4, dx + S['RAM_X'], S['RAM_Y'], S['RAM_ROT'], S['RAM_AB']))
    for a in range(len(rom)):
        if rom[a] and a < S['lay_end'] - S['start']: cmds.append(('rom', dx + S['ROM_X'], S['ROM_Y'], a, rom[a]))
    p = [at('lay_paths')]
    def path(x, y):
        b = rom[p[0]]; p[0] += 1; n = b & 15
        if n == 0:
            n = rom[p[0]]; p[0] += 1
            if n == 0: return
        layer = (b >> 6) & 1
        while True:
            d = (b >> 4) & 3; nx, ny = x, y
            if d == 0: nx += n
            elif d == 1: nx -= n
            elif d == 2: ny += n
            else: ny -= n
            cmds.append(('track', layer, x, y, nx, ny)); x, y = nx, ny
            if b & 0x80: return
            b = rom[p[0]]; p[0] += 1; n = b & 15
            if n == 0: n = rom[p[0]]; p[0] += 1
            if (b >> 6) & 1: cmds.append(('via', x, y)); layer ^= 1
    for r in range(S['ROWS']):
        for c in range(S['COLS']):
            k = kinds[r * S['COLS'] + c]
            if k == 2: continue
            x, y = dx + S['GX0'] + c * S['PX'], S['GY0'] + r * S['PY']
            path(x, y)
            if k == 0: path(x, y + 1)
    q = at('lay_port_starts')
    for i in range(S['NPORTS']):
        x = s16(rom[q + 4 * i] | rom[q + 4 * i + 1] << 8); y = s16(rom[q + 4 * i + 2] | rom[q + 4 * i + 3] << 8); path(x, y)
    q = at('lay_run_starts')
    for i in range(S['NRUN']):
        x = s16(rom[q + 4 * i] | rom[q + 4 * i + 1] << 8); y = s16(rom[q + 4 * i + 2] | rom[q + 4 * i + 3] << 8); path(x, y)
    return cmds
