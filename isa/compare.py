import common, importlib
ISAS = ['isa6502', 'isaz80', 'isahack', 'isaacc']
# hardware estimates: (NAND, DFF) component sums, +-25 % (see ISA_COMPARISON.md section 3)
HW = {'6502-lite': (1190, 76), 'Z80-lite': (1540, 100), 'Hack-vN': (800, 54), 'ACC8': (900, 64), 'SUBLEQ(b)': (750, 80)}
CRAM = 6.27 + 6       # NAND-equivalents per RAM bit (3 NAND cell + 3 read mux, DFF at 6) from nandgen 4 KiB RAM
res = {}
for n in ISAS:
    mod = importlib.import_module(n)
    res[mod.NAME] = {r[0]: r for r in common.report(mod)}
    assert all(r[4] == 'PASS' for r in res[mod.NAME].values()), mod.NAME
print(f'{"ISA":10} {"HW NAND":>7} {"DFF":>4} {"HW w6":>6} | code bytes K1..K4 (sum) | memory accesses K1..K4 (sum)')
for n, k in res.items():
    nand, dff = HW[n]
    cb = [k[x][1] for x in common.KERNELS]; ac = [k[x][3] for x in common.KERNELS]
    print(f'{n:10} {nand:7} {dff:4} {nand + 6 * dff:6} | {cb} {sum(cb)} | {ac} {sum(ac)}')
print()
print('total cost = HW(w6) + code_bytes*8*CRAM*f  for ROM-cost fraction f of a RAM bit')
for n, k in res.items():
    nand, dff = HW[n]; hw = nand + 6 * dff
    s = sum(k[x][1] for x in common.KERNELS)
    print(f'{n:10}', ' '.join(f'f={f}: {hw + s * 8 * CRAM * f:8.0f}' for f in (0, 0.5, 1)))
print()
print('with CPU description in ROM (1.65 B per gate, from xz of nandgen netlists): total = (NAND+DFF)*1.65*8*CRAM*f + code*8*CRAM*f + HW(w6)')
for n, k in res.items():
    nand, dff = HW[n]; hw = nand + 6 * dff
    s = sum(k[x][1] for x in common.KERNELS)
    d = (nand + dff) * 1.65
    print(f'{n:10} desc {d:6.0f} B  code {s:4} B ', ' '.join(f'f={f}: {hw + (s + d) * 8 * CRAM * f:8.0f}' for f in (0.1, 0.5, 1)))
