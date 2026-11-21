#!/usr/bin/env python3
"""make_figs.py -- all RNDP figures of the replicator report.

Inputs are the seed worlds rebuilt from the repository (see report appendix B):
  r1/seed.build r2/seed.build r3/seed.build            (make_seed.py of rndp_r1, rndp_r2, r3)
  r2c/seed.build r3c/seed.build                        (rndp_layout/tools/make_seed.py on the stored .lay files)
  r4/emu.build                                         (r4 build_rom.py -> rvemu --armlog -> armlog2build.py)
  r5/e5_parent.pkl                                     (rndp_r5/e4 fp.py 10975 RSEED=2 + assemble.py 10975 2, E5_INV=19,21)
  r6/full.build                                        (rndp_r6/build_r6.sh)
  r2c/snap_*.state r2c/gen1.state                      (rndp run of the R2c quine)
Run from the work directory: python3 tools/make_figs.py OUTDIR
"""
import sys, os, io, base64, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R
from PIL import Image

OUT = sys.argv[1] if len(sys.argv) > 1 else 'report/figs'
os.makedirs(OUT, exist_ok=True)
ONLY = set(sys.argv[2:])
FONT = "font-family='Helvetica, Arial, sans-serif'"
INK, INK2 = '#0b0b0b', '#52514e'
_cache = {}


def W(path):
    if path not in _cache: _cache[path] = R.load(path)
    return _cache[path]


def want(name):
    return not ONLY or name in ONLY


def png_b64(im):
    b = io.BytesIO(); im.save(b, format='PNG', optimize=True); return base64.b64encode(b.getvalue()).decode()


def raster(world, f, window=None, rotate=False, margin=4):
    tmp = '/tmp/_fig.png'
    win, size = world.png(tmp, f=f, window=window, rotate=rotate, margin=margin)
    return Image.open(tmp).convert('RGB'), win


def text(x, y, s, size=12, color=INK, anchor='start', weight='normal'):
    return f"<text x='{x}' y='{y}' font-size='{size}' fill='{color}' text-anchor='{anchor}' font-weight='{weight}'>{s}</text>"


def scalebar(x, y, px_per_cell, cells, label):
    L = px_per_cell * cells
    return (f"<g><line x1='{x}' y1='{y}' x2='{x + L:.1f}' y2='{y}' stroke='{INK}' stroke-width='2'/>"
            f"<line x1='{x}' y1='{y - 4}' x2='{x}' y2='{y + 4}' stroke='{INK}' stroke-width='1.5'/>"
            f"<line x1='{x + L:.1f}' y1='{y - 4}' x2='{x + L:.1f}' y2='{y + 4}' stroke='{INK}' stroke-width='1.5'/>"
            + text(x + L / 2, y - 7, label, 11, INK2, 'middle') + "</g>")


def save(name, w, h, body):
    open(os.path.join(OUT, name), 'w').write(
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{w:.0f}' height='{h:.0f}' viewBox='0 0 {w:.0f} {h:.0f}' {FONT}>"
        f"<rect width='100%' height='100%' fill='#ffffff'/>{body}</svg>")
    print('wrote', name)


def img(x, y, im, w=None, h=None):
    w = w or im.size[0]; h = h or im.size[1]
    return (f"<image x='{x}' y='{y}' width='{w}' height='{h}' preserveAspectRatio='none' style='image-rendering:pixelated' "
            f"href='data:image/png;base64,{png_b64(im)}'/><rect x='{x}' y='{y}' width='{w}' height='{h}' fill='none' stroke='#bbb' stroke-width='0.75'/>")


def window_fig(name, world, win, scale, title):
    if want(name): world.svg(os.path.join(OUT, name), window=win, scale=scale, title=title); print('wrote', name)


# --------------------------------------------------------------------------- primer
def primer():
    s = 34; ox, oy = 30, 40
    w = R.World()
    w.add_part(0, 3, 3); w.add_part(1, 13, 3)
    w.add_seg(0, 4, 3, 13, 3)                      # NAND Y -> DFF D on layer 0
    w.add_seg(1, 8, 0, 8, 7); w.vias.append((8, 7)); w.add_seg(0, 8, 7, 3, 7); w.add_seg(0, 3, 7, 3, 4)  # layer-1 net crosses, via, back on L0 into B
    w.add_seg(0, 14, 3, 17, 3)                     # Q out
    w.add_seg(0, 3, 3, 1, 3); w.add_seg(0, 1, 3, 1, 1)  # A input
    body = [f"<g transform='translate({ox},{oy})'>"]
    gx0, gy0, gx1, gy1 = 0, 0, 18, 9
    for gx in range(gx0, gx1 + 2):
        body.append(f"<line x1='{(gx - gx0) * s}' y1='0' x2='{(gx - gx0) * s}' y2='{(gy1 - gy0 + 1) * s}' stroke='#eceae4' stroke-width='1'/>")
    for gy in range(gy0, gy1 + 2):
        body.append(f"<line x1='0' y1='{(gy - gy0) * s}' x2='{(gx1 - gx0 + 1) * s}' y2='{(gy - gy0) * s}' stroke='#eceae4' stroke-width='1'/>")
    for k, px, py, pw, ph in w.parts:
        body.append(f"<rect x='{px * s}' y='{py * s}' width='{pw * s}' height='{ph * s}' fill='{R.PART_FILL[k]}' fill-opacity='0.85' stroke='#333' stroke-width='1'/>")
    for L in (0, 1):
        for l, ax, ay, bx, by in w.segs:
            if l == L:
                body.append(f"<line x1='{(ax + .5) * s}' y1='{(ay + .5) * s}' x2='{(bx + .5) * s}' y2='{(by + .5) * s}' stroke='{R.L_COL[L]}' stroke-width='{0.5 * s}' stroke-linecap='square' stroke-opacity='{0.9 if L == 0 else 0.8}'/>")
    for vx, vy in w.vias:
        body.append(f"<circle cx='{(vx + .5) * s}' cy='{(vy + .5) * s}' r='{0.32 * s}' fill='{R.VIA_COL}'/>")
    for lab, cx, cy in (('A', 3, 3), ('B', 3, 4), ('Y', 4, 3), ('D', 13, 3), ('Q', 14, 3)):
        body.append(text((cx + .5) * s, (cy + .5) * s + 5, lab, 14, '#fff', 'middle', 'bold'))
    ann = [
        (3.2, 5.6, 'NAND (2 x 2): inputs A, B; output Y'),
        (12.2, 5.6, 'DFF (2 x 2): input D; output Q'),
        (9.1, 1.0, 'layer-1 track crosses the layer-0 track'),
        (9.1, 1.55, 'without connecting (different layers)'),
        (9.6, 8.15, 'via: joins the two layers'),
        (5.0, 2.45, 'layer-0 track: Y drives D'),
    ]
    for x, y, t in ann:
        body.append(text(x * s, y * s, t, 13, INK))
    body.append('</g>')
    H = (gy1 + 1) * s + oy + 40
    body.append(R.legend_svg(ox, H - 30, kinds=(0, 1), fs=12))
    body.insert(0, text(ox, 24, 'The RNDP world in one picture: parts on a grid, copper on two layers', 15, INK, weight='bold'))
    save('fig_rndp_primer.svg', (gx1 + 1) * s + 2 * ox, H, ''.join(body))


# --------------------------------------------------------------------------- anatomy (diagram)
def anatomy():
    b = [text(20, 26, 'Anatomy of every replicator in this report', 15, INK, weight='bold')]

    def box(x, y, w, h, fill, title, lines):
        o = f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='6' fill='{fill}' stroke='#555' stroke-width='1'/>" + text(x + 10, y + 20, title, 13, INK, weight='bold')
        for i, l in enumerate(lines): o += text(x + 10, y + 38 + 16 * i, l, 12, INK2)
        return o

    def arrow(x1, y1, x2, y2, lab=None, lx=0, ly=0):
        o = f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='#444' stroke-width='1.6' marker-end='url(#ah)'/>"
        if lab: o += text((x1 + x2) / 2 + lx, (y1 + y2) / 2 + ly, lab, 11, INK2, 'middle')
        return o
    b.append("<defs><marker id='ah' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='7' markerHeight='7' orient='auto'><path d='M0 0L10 5L0 10z' fill='#444'/></marker></defs>")
    b.append(f"<rect x='14' y='44' width='500' height='300' rx='10' fill='#f6f5f1' stroke='#999' stroke-dasharray='0'/>")
    b.append(text(26, 64, 'parent machine (built of NAND, DFF and copper)', 12, INK2))
    b.append(box(30, 80, 210, 120, '#e3f1e7', 'program store (ROM)', ['builder code', 'description of the machine', '(netlist, modules or layout)', 'X-R4: a ROM part; R5, R6: gates']))
    b.append(box(290, 80, 210, 80, '#e6ecf4', 'CPU', ['Hack-vN(-AB), RV32EC,', 'or a pruned sequencer (R5)']))
    b.append(box(290, 190, 210, 60, '#efe8f7', 'RAM', ['part, or NAND/DFF tiles']))
    b.append(box(30, 230, 210, 96, '#f7e3e1', 'ARM (robot arm)', ['memory-mapped, write-only', 'PLACE, PROGRAM_ROM,', 'WIRE (RNDW) / TRACK, VIA (RNDP)']))
    b.append(arrow(240, 120, 288, 120, 'fetch', 0, -6))
    b.append(arrow(395, 160, 395, 188))
    b.append(arrow(290, 140, 242, 260)); b.append(text(276, 214, 'register', 11, INK2, 'end')); b.append(text(276, 228, 'writes', 11, INK2, 'end'))
    b.append(f"<rect x='560' y='44' width='330' height='300' rx='10' fill='#ffffff' stroke='#999' stroke-dasharray='5 4'/>")
    b.append(text(574, 64, 'child machine (being built, held in reset)', 12, INK2))
    steps = ['1. PLACE every part', '2. PROGRAM_ROM: copy the image (if a ROM part)', '3. lay every wire / copper track and via',
             '4. connect the child arm EN', '5. connect RUN last: the child starts', '   ... and builds the grandchild']
    for i, t in enumerate(steps): b.append(text(578, 96 + 26 * i, t, 13, INK))
    b.append(arrow(240, 290, 556, 200, 'arm commands', 0, 22))
    b.append(text(20, 372, 'Quine check: the child equals the parent shifted by a constant offset (parts, copper or wires, vias, ROM bytes).', 12, INK2))
    b.append(text(20, 390, 'Improvers (Y, R4) instead build a smaller or re-laid-out child, which then rebuilds itself unchanged (a fixed point).', 12, INK2))
    save('fig_anatomy.svg', 905, 402, ''.join(b))


# --------------------------------------------------------------------------- R1 vs R2 to scale
def r1_r2_scale():
    f = 20
    a, wa = raster(W('r1/seed.build'), f, rotate=True)
    c, wc = raster(W('r2/seed.build'), f, rotate=True)
    pad = 30; y1 = 50; y2 = y1 + a.size[1] + 60
    b = [text(pad, 24, 'R1 and R2 drawn to the same scale (dedicated-lane layouts, rotated 90 degrees)', 15, INK, weight='bold'),
         text(pad, y1 - 8, f'R1: 8,809 NAND + 1,080 DFF, RAM as 128 gate tiles; board 4,581 x 29,698 cells (136.0 M)', 12, INK2),
         img(pad, y1, a),
         text(pad, y2 - 8, f'R2: 2,034 NAND + 56 DFF, RAM part; board 4,222 x 6,318 cells (26.7 M)', 12, INK2),
         img(pad, y2, c),
         scalebar(pad + 10, y2 + c.size[1] + 34, 1 / f, 5000, '5,000 cells'),
         text(pad, y2 + c.size[1] + 62, 'One pixel = 20 x 20 cells. Orange: layer-0 copper; blue: layer-1 copper; parts are too small to see at this scale.', 11, INK2)]
    save('fig_r1_r2_scale.svg', a.size[0] + 2 * pad, y2 + c.size[1] + 76, ''.join(b))


# --------------------------------------------------------------------------- overview with labels
def overview(name, world, f, title, sub, labels=(), rotate=False, bar=None, foot=None, maxw=None):
    im, win = raster(world, f, rotate=rotate)
    pad = 24; y0 = 56 if sub else 40
    b = [text(pad, 24, title, 15, INK, weight='bold')]
    if sub: b.append(text(pad, 44, sub, 12, INK2))
    b.append(img(pad, y0, im))
    for (lx, ly, t, anchor) in labels:
        b.append(f"<text x='{pad + lx}' y='{y0 + ly}' font-size='12' fill='{INK}' text-anchor='{anchor}' stroke='#fff' stroke-width='3' paint-order='stroke' font-weight='bold'>{t}</text>")
    h = y0 + im.size[1] + 16
    if bar:
        b.append(scalebar(pad + 10, h + 14, 1 / f, bar, f'{bar:,} cells')); h += 30
    if foot:
        b.append(text(pad, h + 12, foot, 11, INK2)); h += 22
    save(name, max(im.size[0] + 2 * pad, 560), h + 6, ''.join(b))


def folded(name, world, f, n, title, sub):
    x0, y0, x1, y1 = world.bbox(); x0 -= 4; x1 += 4; y0 -= 4; y1 += 4
    step = (y1 - y0 + n) // n
    pad = 24; gap = 26; top = 62; b = [text(pad, 24, title, 15, INK, weight='bold'), text(pad, 44, sub, 12, INK2)]
    x = pad; hmax = 0
    for i in range(n):
        im, _ = raster(world, f, window=(x0, y0 + i * step, x1, min(y1, y0 + (i + 1) * step - 1)))
        b.append(img(x, top, im)); b.append(text(x + im.size[0] / 2, top + im.size[1] + 16, str(i + 1), 11, INK2, 'middle'))
        x += im.size[0] + gap; hmax = max(hmax, im.size[1])
    b.append(scalebar(pad + 10, top + hmax + 44, 1 / f, 1000, '1,000 cells'))
    save(name, x + pad, top + hmax + 60, ''.join(b))


def compact_scale():
    ims = [(raster(W('r2c/seed.build'), 1, margin=2)[0], 'R2c (Hack-vN-AB, pitch 5)', '240 x 259 cells'),
           (raster(W('r3c/seed.build'), 1, margin=2)[0], 'R3c (RV32EC, pitch 6)', '342 x 355 cells'),
           (raster(W('r4/emu.build'), 1, margin=2)[0], 'R4 (RV32EC improver, in-world router)', '871 x 785 cells')]
    pad = 24; x = pad; y0 = 70; b = [text(pad, 24, 'The three placed-and-routed boards at the same scale (1 pixel = 1 cell)', 15, INK, weight='bold'),
                                       text(pad, 44, 'R2c and R3c were laid out offline by the project’s PathFinder router and stored in ROM; R4 computes its own layout in the world.', 12, INK2)]
    for im, t, s in ims:
        b.append(text(x, y0 - 6, t, 12, INK, weight='bold')); b.append(text(x, y0 + im.size[1] + 16, s, 11, INK2)); b.append(img(x, y0, im)); x += im.size[0] + 30
    H = y0 + max(i[0].size[1] for i in ims) + 30
    b.append(R.legend_svg(pad, H, kinds=(0, 1, 2, 3, 4)))
    save('fig_compact_scale.svg', x, H + 24, ''.join(b))


# --------------------------------------------------------------------------- R2c quine snapshots
def r2c_quine():
    pick = [('r2c/s1.state', 'tick 40: the seed (parent only, held in reset)'),
            ('r2c/snap_000005000000.state', 'tick 5 M: child placed and ROM programmed, copper about 40 % laid'),
            ('r2c/snap_000010000000.state', 'tick 10 M: child complete and running; it has placed the grandchild'),
            ('r2c/snap_000015000000.state', 'tick 15 M: grandchild copper about 55 % laid'),
            ('r2c/gen1.state', 'tick 20 M: grandchild complete; great-grandchild placed')]
    win = (30, 30, 30 + 4 * 262 + 6, 300)
    pad = 24; y = 50; b = [text(pad, 24, 'R2c copying itself, re-run in rndp for this report (each machine is 262 cells to the right of its parent)', 15, INK, weight='bold')]
    for p, lab in pick:
        im, _ = raster(R.load(p), 1, window=win)
        b.append(text(pad, y + 4, lab, 12, INK, weight='bold')); b.append(img(pad, y + 12, im)); y += im.size[1] + 34
    b.append(R.legend_svg(pad, y - 10, kinds=(0, 1, 2, 3, 4)))
    save('fig_r2c_quine.svg', im.size[0] + 2 * pad, y + 20, ''.join(b))


# --------------------------------------------------------------------------- charts
def chart():
    rows = [  # name, world, NAND, DFF, area cells (None for RNDW), area label
        ('X (RNDW quine)', 'RNDW', 2550, 308, None),
        ('Y g1 (RNDW improver seed)', 'RNDW', 15495, 2104, None),
        ('Y g2 = g3 (improved)', 'RNDW', 14549, 2104, None),
        ('R1', 'RNDP', 8809, 1080, 4581 * 29698),
        ('R2', 'RNDP', 2034, 56, 4222 * 6318),
        ('R2c', 'RNDP', 2034, 56, 240 * 259),
        ('R3', 'RNDP', 2922, 77, 6040 * 9046),
        ('R3c', 'RNDP', 2938, 78, 342 * 355),
        ('R4 (improved child)', 'RNDP', 3770, 81, 871 * 785),
        ('R5 (E5)', 'RNDP', 132214, 11052, 429 * 44260),
        ('R6', 'RNDP', 134797, 1080, 1696 * 7840),
    ]
    import math
    C_N, C_D, C_A = '#2a78d6', '#eb6834', '#2a78d6'
    lab_w = 200; pw = 330; gap = 70; rh = 26; top = 92
    x1 = lab_w; x2 = lab_w + pw + gap
    H = top + rh * len(rows) + 60
    Wt = x2 + pw + 40
    b = [text(20, 24, 'Size of every replicator: gate counts and board area', 15, INK, weight='bold'),
         text(20, 44, 'Logarithmic axes. ROM and RAM parts (used by X, Y, R1-R4) are not counted here; see the tables.', 12, INK2)]

    def lx(v, lo, hi): return (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * pw
    lo1, hi1 = 10, 1e6; lo2, hi2 = 1e4, 1e9
    # panel titles + legend
    b.append(text(x1, 70, 'NAND and DFF count', 12, INK, weight='bold'))
    b.append(f"<circle cx='{x1 + 150}' cy='66' r='5' fill='{C_N}'/>" + text(x1 + 159, 70, 'NAND', 11, INK2))
    b.append(f"<circle cx='{x1 + 210}' cy='66' r='5' fill='{C_D}'/>" + text(x1 + 219, 70, 'DFF', 11, INK2))
    b.append(text(x2, 70, 'board bounding box (cells)', 12, INK, weight='bold'))
    for (lo, hi, x0) in ((lo1, hi1, x1), (lo2, hi2, x2)):
        e = int(math.log10(lo))
        while 10 ** e <= hi:
            xx = x0 + lx(10 ** e, lo, hi)
            b.append(f"<line x1='{xx:.1f}' y1='{top - 8}' x2='{xx:.1f}' y2='{top + rh * len(rows) - 6}' stroke='#e6e4de' stroke-width='1'/>")
            lab = {1: '10', 2: '100', 3: '1K', 4: '10K', 5: '100K', 6: '1M', 7: '10M', 8: '100M', 9: '1G'}[e]
            b.append(text(xx, top + rh * len(rows) + 10, lab, 11, INK2, 'middle')); e += 1
    for i, (nm, world, n, d, a) in enumerate(rows):
        y = top + rh * i + 6
        if i == 3:
            b.append(f"<line x1='16' y1='{y - 13}' x2='{Wt - 16}' y2='{y - 13}' stroke='#bdbab2' stroke-width='1'/>")
        b.append(text(lab_w - 12, y + 4, nm, 12, INK, 'end'))
        xn, xd = x1 + lx(n, lo1, hi1), x1 + lx(d, lo1, hi1)
        b.append(f"<line x1='{min(xn, xd):.1f}' y1='{y}' x2='{max(xn, xd):.1f}' y2='{y}' stroke='#cfccc4' stroke-width='2'/>")
        b.append(f"<circle cx='{xd:.1f}' cy='{y}' r='5' fill='{C_D}' stroke='#fff' stroke-width='2'><title>{nm}: {d:,} DFF</title></circle>")
        b.append(f"<circle cx='{xn:.1f}' cy='{y}' r='5' fill='{C_N}' stroke='#fff' stroke-width='2'><title>{nm}: {n:,} NAND</title></circle>")
        if a:
            xa = x2 + lx(a, lo2, hi2)
            b.append(f"<line x1='{x2}' y1='{y}' x2='{xa:.1f}' y2='{y}' stroke='{C_A}' stroke-width='2' stroke-opacity='0.35'/>")
            b.append(f"<circle cx='{xa:.1f}' cy='{y}' r='5' fill='{C_A}' stroke='#fff' stroke-width='2'><title>{nm}: {a:,} cells</title></circle>")
            b.append(text(xa + 10, y + 4, f'{a / 1e6:.2f} M' if a >= 1e6 else f'{a / 1e3:.0f} K', 11, INK2))
        else:
            b.append(text(x2 + 4, y + 4, 'RNDW: wires have no geometry', 11, '#8a877f'))
    save('fig_sizes.svg', Wt, H, ''.join(b))


def main():
    if want('fig_rndp_primer.svg'): primer()
    if want('fig_anatomy.svg'): anatomy()
    if want('fig_r1_r2_scale.svg'): r1_r2_scale()
    window_fig('fig_r1_zoom.svg', W('r1/seed.build'), (10, 5, 130, 95), 7,
               'R1, top-left corner: ROM (green), arm (red), DFFs on the diagonal, one lane per input pin')
    window_fig('fig_r2c_board.svg', W('r2c/seed.build'), None, 4, 'R2c: the whole compact board, 240 x 259 cells (pitch 5)')
    window_fig('fig_r2c_zoom.svg', W('r2c/seed.build'), (30, 30, 140, 120), 7, 'R2c, top-left corner: ROM, arm and the first NAND sites')
    if want('fig_r2c_quine.svg'): r2c_quine()
    if want('fig_r3_overview.svg'):
        overview('fig_r3_overview.svg', W('r3/seed.build'), 8, 'R3: the RV32EC quine, dedicated-lane layout',
                 '2,922 NAND + 77 DFF, ROM and RAM parts; board 6,040 x 9,046 cells (1 pixel = 8 x 8 cells)', bar=1000)
    window_fig('fig_r3c_board.svg', W('r3c/seed.build'), None, 3, 'R3c: the whole compact RV32EC board, 342 x 355 cells (pitch 6)')
    if want('fig_compact_scale.svg'): compact_scale()
    window_fig('fig_r4_zoom.svg', W('r4/emu.build'), (86, -735, 260, -640), 5,
               'R4, top-left of the board: gate rows, stubs on layer 1, channel tracks on layer 0')
    if want('fig_r5_overview.svg'): folded('fig_r5_overview.svg', W('r5/e5_parent.pkl'), 8, 8,
               'R5 (E5): the whole board, cut into 8 pieces (read left to right; 1 pixel = 8 x 8 cells)',
               '132,214 NAND + 11,052 DFF, no ROM or RAM parts; 429 x 44,260 cells. The engine block is at the bottom of the last piece.')
    window_fig('fig_r5_engine.svg', W('r5/e5_parent.pkl'), (-10, 32200, 425, 32620), 2,
               'R5: the engine block (981 NAND + 77 DFF, routed at pitch 9) above the top of the plane')
    window_fig('fig_r5_plane.svg', W('r5/e5_parent.pkl'), (138, 0, 260, 70), 7,
               'R5: a few rows of the plane: token-ring DFF and inverter per row, an INV + NAND pair per stored 1-bit')
    if want('fig_r6_overview.svg'):
        overview('fig_r6_overview.svg', W('r6/full.build'), 4, 'R6: the whole board, rotated 90 degrees (1 pixel = 4 x 4 cells)',
                 '134,797 NAND + 1,080 DFF, no ROM or RAM parts; 1,696 x 7,840 cells', rotate=True, bar=1000,
                 labels=[(78, 345, 'core (R2c layout, 2,034 NAND + 56 DFF)', 'start'), (30, 110, 'column-select (lo) lines, one row each', 'start'),
                         (1100, 150, 'ROM plane: the 16,006-byte image as gates', 'middle'), (1000, 398, 'RAM block: 128 select lines + 128 tiles of 8 DFF', 'middle')])
    window_fig('fig_r6_decoder.svg', W('r6/full.build'), (555, 1500, 700, 1590), 6,
               'R6: address-decoder lines of two ROM-plane strips (AND chains of 6 NAND + 6 NOT) and the literal buses')
    window_fig('fig_r6_plane.svg', W('r6/full.build'), (700, 1505, 860, 1600), 6,
               'R6: ROM plane cells: a NAND gadget for each stored 1-bit, pass slots for 0-bits')
    window_fig('fig_r6_ram.svg', W('r6/full.build'), (55, 320, 250, 450), 5,
               'R6: RAM block: select lines (left) and two of the 128 routed word tiles (8 DFF each)')
    if want('fig_sizes.svg'): chart()


if __name__ == '__main__':
    main()
