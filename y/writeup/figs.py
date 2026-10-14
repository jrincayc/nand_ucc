"""figs.py -- draws the write-up figures (SVG, no dependencies) from data/*.json and the saved RNDW states."""
import json, os, html, sys
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, 'data'); F = os.path.join(HERE, 'figs')
BG, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e3e2de'
C = dict(blue='#2a78d6', orange='#eb6834', aqua='#1baf7a', yellow='#eda100', magenta='#e87ba4', green='#008300', violet='#6250d6', gray='#b9b8b2')
esc = html.escape

class Svg:
    def __init__(s, w, h, title):
        s.w, s.h, s.p = w, h, []
        s.title = title
    def rect(s, x, y, w, h, fill, rx=2, stroke=None, extra=''):
        s.p.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w,0):.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"' + (f' stroke="{stroke}" stroke-width="1"' if stroke else '') + f' {extra}/>')
    def text(s, x, y, t, size=12, fill=INK, anchor='start', weight='normal'):
        s.p.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{esc(str(t))}</text>')
    def line(s, x1, y1, x2, y2, stroke=GRID, w=1, dash=''):
        s.p.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{w}"' + (f' stroke-dasharray="{dash}"' if dash else '') + '/>')
    def save(s, name):
        body = '\n'.join(s.p)
        open(os.path.join(F, name), 'w').write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {s.w} {s.h}" width="{s.w}" font-family="system-ui, -apple-system, Segoe UI, Helvetica, Arial, sans-serif" role="img" aria-label="{esc(s.title)}">\n<title>{esc(s.title)}</title>\n<rect width="{s.w}" height="{s.h}" fill="{BG}"/>\n{body}\n</svg>\n')

M = json.load(open(os.path.join(D, 'measure.json'))); R = json.load(open(os.path.join(D, 'routines.json')))
S = M['seed']['syms']

# ------------------------------------------------------------------ ROM map
def rom_map():
    segs = [('builder code', 0, S['irdb'], C['blue']), ('improver code', S['irdb'], S['vtab'], C['orange']), ('improver tables', S['vtab'], S['mtab'] + 40, C['yellow']),
            ('HD: directory + records', S['hd_dir'], S['hd_mods_end'], C['aqua']), ('HD: body (instances)', S['hd_body'], S['hd_chain'], C['violet']),
            ('HD: chain + ports', S['hd_chain'], M['seed']['image'], C['magenta'])]
    W, H = 900, 300; s = Svg(W, H, 'ROM map of the Y machine, 16 KiB'); X0, X1 = 30, W - 30; sc = (X1 - X0) / 16384
    s.text(30, 24, 'ROM: 16,384 bytes (AB = 15), image 16,350 B', 15, INK, weight='bold')
    s.text(30, 42, 'bar = byte address from ROM_BASE; each segment is labelled with its size in bytes', 11, INK2)
    for name, a, b, col in segs:
        s.rect(X0 + a * sc, 60, max((b - a) * sc, 1.5), 46, col, rx=0)
    s.rect(X0 + M['seed']['image'] * sc, 60, 34 * sc, 46, GRID, rx=0)
    s.line(X0, 112, X1, 112, GRID)
    for k in range(0, 17, 2): s.line(X0 + k * 1024 * sc, 106, X0 + k * 1024 * sc, 118, INK2); s.text(X0 + k * 1024 * sc, 132, f'{k} KiB', 10, INK2, 'middle')
    rows = [(n, b - a, c) for n, a, b, c in segs] + [('free', 34, GRID)]
    y = 168
    for n, sz, col in rows:
        s.rect(40, y - 11, 14, 14, col, rx=2); s.text(62, y, n, 13); s.text(330, y, f'{sz:,} B', 13, INK2, 'end'); s.text(350, y, f'{100*sz/16384:.1f}%', 13, INK2); y += 21
    s.text(440, 168, 'the improver is 61% of the code and 48% of the whole ROM;', 12, INK2)
    s.text(440, 186, 'the description (HD) is 20%, of which the body of 471 instances is 2,581 B.', 12, INK2)
    s.text(440, 214, 'the HD is data that the ROM also copies into every child,', 12, INK2)
    s.text(440, 232, 'except the records, which the builder re-programs after improving them.', 12, INK2)
    s.save('fig_rom_map.svg')

# ------------------------------------------------------------------ RAM map
def ram_map():
    W, H = 900, 330; s = Svg(W, H, 'RAM map of the Y machine, 256 bytes'); X0, X1 = 30, W - 30; sc = (X1 - X0) / 256
    s.text(30, 24, 'RAM: 256 bytes (ram_abits = 8); highest byte ever written: 196', 15, INK, weight='bold')
    bw = set(M['seed']['ram_builder']); iw = set(M['seed']['ram_improver'])
    s.text(30, 42, 'each cell = one byte.  top row: bytes written by the builder.  bottom row: bytes written by the improver (seed build, both phases)', 11, INK2)
    for y, ws, col in ((56, bw, C['blue']), (82, iw, C['orange'])):
        a = 0
        while a < 256:
            on = a in ws; b = a
            while b < 256 and (b in ws) == on: b += 1
            s.rect(X0 + a * sc, y, (b - a) * sc, 22, col if on else GRID, rx=0); a = b
    s.text(X0 - 4, 72, 'B', 10, INK2, 'end'); s.text(X0 - 4, 98, 'I', 10, INK2, 'end')
    regs = [('0..127 temporaries (builder and improver overlay)', 0, 128, C['aqua']), ('128..167 RECB (40 B)', 128, 168, C['violet']), ('168..196 persistent (29 B)', 168, 197, C['magenta']), ('197..255 never used (59 B)', 197, 256, GRID)]
    for n, a, b, col in regs: s.rect(X0 + a * sc, 116, (b - a) * sc, 16, col, rx=0)
    for k in range(0, 257, 32): s.line(X0 + k * sc, 132, X0 + k * sc, 140, INK2); s.text(X0 + k * sc, 153, k, 10, INK2, 'middle')
    y = 190
    for n, a, b, col in regs:
        s.rect(40, y - 11, 14, 14, col, rx=2); s.text(62, y, n, 13); y += 22
    s.text(40, y + 8, f'builder writes {len(bw)} distinct bytes, improver writes {len(iw)}, {len(bw & iw)} are used by both (the overlay).', 12, INK2)
    s.text(40, y + 26, 'stand-alone improver (test driver): high-water byte 172 -> 173 B.  quine builder X (for comparison): 30 B of 32.', 12, INK2)
    s.save('fig_ram_map.svg')

# ------------------------------------------------------------------ instructions
def instr():
    groups = [('byte reads, 16-bit adds, 5-byte copies (rdb, add16, put5)', ['rdb', 'add16', 'put5'], C['blue']),
              ('wiring logic (decref, resolve, emit, gates)', ['decref', 'resolve', 'emit', 'gates'], C['aqua']),
              ('group walk, skipping, ROM copy, tiles, ports, misc', ['start', 'group', 'phase_done', 'tile_loop', 'tiles_done', 'rom_loop', 'pass2_tail', 'skiprefs', 'progrec', 'lookup'], C['violet']),
              ('improver: exhaustive NAND search', ['search'], C['orange']),
              ('improver: cones and cuts', ['cone', 'nextcut', 'bt', 'bs', 'keycmp'], C['yellow']),
              ('improver: compaction, load, rewrite, layout, other', ['compact', 'ins', 'load', 'rewrite', 'partition', 'layout', 'improve_type', 'irdb'], C['magenta'])]
    W, H = 900, 380; s = Svg(W, H, 'Instructions executed by one build'); X0, X1 = 150, W - 40; mx = 33e6; sc = (X1 - X0) / mx
    s.text(30, 24, 'Instructions executed per generation (behavioural model, 256 B RAM)', 15, INK, weight='bold')
    s.text(30, 42, 'gen 1 -> gen 2: the improver finds gains.  gen 2 -> gen 3: it searches and finds nothing (fixed point).', 11, INK2)
    for r, (t, lab) in enumerate((('seed', 'gen 1 builds gen 2'), ('child', 'gen 2 builds gen 3'))):
        y = 70 + r * 52; x = X0; s.text(X0 - 10, y + 22, lab, 12, INK, 'end')
        for name, ks, col in groups:
            v = sum(R[t]['instr'].get(k, 0) for k in ks); w = v * sc
            s.rect(x, y, max(w - 2, 0.5), 32, col, rx=0); x += w
        tot = M[t]['instr']; s.text(x + 6, y + 21, f'{tot/1e6:.1f} M', 12, INK, weight='bold')
    y = 190
    for name, ks, col in groups:
        v1, v2 = (sum(R[t]['instr'].get(k, 0) for k in ks) for t in ('seed', 'child'))
        s.rect(40, y - 11, 14, 14, col, rx=2); s.text(62, y, name, 12); s.text(650, y, f'{v1/1e6:5.2f} M', 12, INK2, 'end'); s.text(740, y, f'{v2/1e6:5.2f} M', 12, INK2, 'end'); y += 24
    s.text(650, 176, 'gen 1->2', 11, INK2, 'end'); s.text(740, 176, 'gen 2->3', 11, INK2, 'end')
    s.text(40, y + 20, f"improver share: {M['seed']['improver_instr']/M['seed']['instr']:.0%} of the first build, {M['child']['improver_instr']/M['child']['instr']:.0%} of the fixed-point build.", 12, INK2)
    s.text(40, y + 38, 'at about 2.6 clock ticks per instruction: roughly 82 M and 66 M ticks per generation.', 12, INK2)
    s.save('fig_instructions.svg')

# ------------------------------------------------------------------ cost vs RAM
def cost():
    data = [(5, 5629, 4683), (6, 8843, 7897), (7, 15289, 14343), (8, 28119, 27173)]
    W, H = 900, 360; s = Svg(W, H, 'Weighted cost of the machine by RAM size'); X0, X1, Y0, Y1 = 90, W - 30, 70, 290; mx = 30000
    s.text(30, 24, 'Weighted cost (NAND + 6 DFF) of the whole machine, seed vs improved', 15, INK, weight='bold')
    s.text(30, 42, 'the improver saves 946 NAND at every RAM size; the RAM it needs to run (256 B) is what makes the machine big', 11, INK2)
    for v in range(0, 30001, 10000):
        y = Y1 - (Y1 - Y0) * v / mx; s.line(X0, y, X1, y); s.text(X0 - 8, y + 4, f'{v:,}', 11, INK2, 'end')
    bw = 44
    for i, (ra, a, b) in enumerate(data):
        cx = X0 + 90 + i * 190
        for j, (v, col) in enumerate(((a, C['blue']), (b, C['aqua']))):
            h = (Y1 - Y0) * v / mx; x = cx + (j - 1) * (bw + 3)
            s.rect(x, Y1 - h, bw, h, col, rx=3); s.text(x + bw / 2, Y1 - h - 5, f'{v:,}', 11, INK, 'middle')
        s.text(cx, Y1 + 18, f'RAM {2**ra} B', 12, INK, 'middle'); s.text(cx, Y1 + 34, f'-{100*(a-b)/a:.1f}%', 12, INK2, 'middle')
        if ra < 8: s.text(cx, Y1 + 50, 'too small for the improver', 10, C['orange'], 'middle')
    s.rect(X0 + 20, 76, 12, 12, C['blue'], 2); s.text(X0 + 38, 87, 'seed (textbook)', 11); s.rect(X0 + 150, 76, 12, 12, C['aqua'], 2); s.text(X0 + 168, 87, 'improved', 11)
    s.save('fig_cost_vs_ram.svg')

# ------------------------------------------------------------------ core row from the saved state
def load_state(path):
    parts = {}
    for l in open(path):
        t = l.split()
        if t and t[0] == 'part': parts[(int(t[2]), int(t[3]), int(t[4]))] = int(t[1])
    return parts

def core_row():
    sys.path[:0] = [os.path.join(HERE, '..', 'tools')]
    import hd as H
    hd = H.read(open(os.path.join(HERE, '..', 'hd', 'core_r8.hd')).read())
    st = load_state('/home/claude/w6/A/final.txt')
    node = 0; inst = []
    for i in hd.body:
        n = 1 if i.type in ('nand', 'dff') else hd.module(i.type).n_gates(); inst.append((i.type, i.name, node, n)); node += n
    n_core = node
    pset = {(x, y) for (k, x, y) in st}
    occ = {g: [((6 + 2 * k, 140 * g + 9) in pset) for k in range(n_core)] for g in (1, 2)}
    cols = {'nand': C['gray'], 'dff': C['green'], 'not': C['yellow'], 'and': C['violet'], 'or': C['magenta'], 'mux': C['orange'], 'ha': C['aqua'], 'fa': C['blue'], 'xor': C['blue']}
    W, H = 1000, 420; s = Svg(W, H, 'Core row of generation 1 and generation 2 from the saved RNDW state')
    s.text(30, 24, 'The core row of the CPU: one square per node slot, from the saved RNDW world (tick 110 M)', 15, INK, weight='bold')
    s.text(30, 42, 'generation 1 = textbook seed; generation 2 = built by generation 1.  Empty slots in generation 2 are the gates the improver removed.', 11, INK2)
    def draw(y0, lo, hi, x0, x1, ttl, mark_hi=None):
        sc = (x1 - x0) / (hi - lo)
        s.text(x0, y0 - 6, ttl, 12, INK, weight='bold')
        for r, g in enumerate((1, 2)):
            y = y0 + r * 34
            s.text(x0 - 6, y + 18, f'gen {g}', 11, INK2, 'end')
            for (ty, nm, a, n) in inst:
                if a + n <= lo or a >= hi: continue
                k = max(a, lo); e = min(a + n, hi)
                while k < e:
                    on = occ[g][k]; j = k
                    while j < e and occ[g][j] == on: j += 1
                    s.rect(x0 + (k - lo) * sc, y, max((j - k) * sc - (0.5 if sc > 3 and j - k == 1 else 0), 0.3), 26, cols.get(ty, C['gray']) if on else BG, rx=0, stroke=None if on else GRID)
                    k = j
        return sc
    draw(80, 0, n_core, 70, 970, f'whole core row: {n_core} nodes (the 256 RAM tiles are a separate block)')
    draw(190, 788, 788 + 25 * 4, 70, 970, 'zoom: four full adders (alu.fa0 .. fa3), 25 slots each in gen 1')
    draw(300, 452 + 0, 452 + 80, 70, 970, 'zoom: first 80 nodes of the ALU (muxes: 8 slots each in gen 1, 4 used in gen 2)')
    lx = 70; ly = 405
    for k in ('not', 'and', 'or', 'mux', 'ha', 'fa', 'dff', 'nand'):
        s.rect(lx, ly - 10, 12, 12, cols[k], 2); s.text(lx + 16, ly, k, 11); lx += 80
    s.rect(lx, ly - 10, 12, 12, BG, 2, stroke=GRID); s.text(lx + 16, ly, 'empty slot', 11)
    s.save('fig_core_row.svg')
    return {g: sum(1 for k in range(n_core) if occ[g][k]) for g in (1, 2)}, n_core

# ------------------------------------------------------------------ world stripes (schematic from the state)
def stripes():
    st = load_state('/home/claude/w6/C/final.txt')
    import collections
    W, H = 1000, 380; s = Svg(W, H, 'World layout: one stripe per generation')
    s.text(30, 24, 'The world after generation 2 has built generation 3 (tick 200 M): one 140-cell stripe per generation', 15, INK, weight='bold')
    s.text(30, 42, 'schematic (not to scale): per stripe the arm, the ROM, the core row (2,239 nodes, 2 cells each) and the RAM block (256 columns x 60 rows)', 11, INK2)
    kinds = {0: 'nand', 1: 'dff', 2: 'rom', 3: 'arm'}
    for g in (1, 2, 3, 4):
        y = 70 + (g - 1) * 75; oy = 140 * g
        cnt = collections.Counter()
        for (k, x, yy) in st.keys():
            if oy <= yy < oy + 140: cnt[k] += 1
        s.text(30, y + 14, f'gen {g}', 13, INK, weight='bold'); s.text(30, y + 32, f'y = {oy}', 11, INK2)
        s.rect(100, y, 18, 18, C['yellow'], 2); s.text(109, y + 33, 'arm', 10, INK2, 'middle')
        s.rect(124, y, 30, 18, C['violet'], 2); s.text(139, y + 33, 'ROM', 10, INK2, 'middle')
        s.rect(165, y + 6, 640, 6, C['blue'], 0); s.text(485, y + 33, 'core row', 10, INK2, 'middle')
        s.rect(830, y - 4, 120, 46, C['aqua'], 3); s.text(890, y + 52, 'RAM tiles', 10, INK2, 'middle')
        nn, dd = cnt[0], cnt[1]
        s.text(165, y + 52, f'{nn:,} NAND + {dd:,} DFF placed in this stripe' + ('' if g < 4 else ' (generation 4: all parts placed, wiring in progress at tick 200 M)'), 11, INK2)
    s.save('fig_world_stripes.svg')

if __name__ == '__main__':
    rom_map(); ram_map(); instr(); cost()
    print(core_row()); stripes()
