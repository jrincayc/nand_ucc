#!/usr/bin/env python3
"""render.py -- draw RNDP worlds (build files, rndp-state files, or R5 command pickles) as SVG windows or PNG overviews.

  load(path, offset=(0,0)) -> World          (parts, segments, vias)
  World.svg(out, window=None, scale=4, title=None, legend=True)
  World.png(out, f=1, window=None, rotate=False)   f = cells per pixel (box-downsampled, presence-based)

Colours are fixed across all figures of the report:
  NAND slate, DFF yellow, ROM green, RAM purple, ARM red, copper layer 0 orange, layer 1 blue, vias black.
"""
import sys, pickle
import numpy as np
from PIL import Image

KIND_NAMES = {0: 'NAND', 1: 'DFF', 2: 'ROM', 3: 'ARM', 4: 'RAM', 5: 'SOURCE'}
PART_FILL = {0: '#8a99ab', 1: '#f2b632', 2: '#3a9d5d', 3: '#c0392b', 4: '#8e6cc2', 5: '#999999'}
L_COL = {0: '#e8833a', 1: '#3b82c4'}
VIA_COL = '#1a1a1a'


def hex2rgb(h):
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def footprint(kind, rot, val):
    if kind in (0, 1): w, h = 2, 2
    elif kind == 2: w, h = 2, max(val, 8)
    elif kind == 3: w, h = 2, 9
    elif kind == 4: w, h = 2, val + 9
    else: w, h = 1, 1
    if rot % 2: w, h = h, w
    return w, h


class World:
    def __init__(self):
        self.parts = []   # (kind, x, y, w, h)
        self.segs = []    # (layer, x0, y0, x1, y1) normalised x0<=x1, y0<=y1
        self.vias = []    # (x, y)

    def add_part(self, kind, x, y, rot=0, val=0):
        w, h = footprint(kind, rot, val); self.parts.append((kind, x, y, w, h))

    def add_seg(self, l, x0, y0, x1, y1):
        self.segs.append((l, min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))

    def bbox(self):
        xs = [p[1] for p in self.parts] + [p[1] + p[3] - 1 for p in self.parts] + [s[1] for s in self.segs] + [s[3] for s in self.segs] + [v[0] for v in self.vias]
        ys = [p[2] for p in self.parts] + [p[2] + p[4] - 1 for p in self.parts] + [s[2] for s in self.segs] + [s[4] for s in self.segs] + [v[1] for v in self.vias]
        return min(xs), min(ys), max(xs), max(ys)

    def counts(self):
        c = {}
        for p in self.parts: c[KIND_NAMES[p[0]]] = c.get(KIND_NAMES[p[0]], 0) + 1
        return c

    # ---------------------------------------------------------------- SVG
    def svg(self, out, window=None, scale=4.0, title=None, legend=True, margin=2, grid=False, pad_px=None):
        if window is None:
            x0, y0, x1, y1 = self.bbox(); x0 -= margin; y0 -= margin; x1 += margin; y1 += margin
        else:
            x0, y0, x1, y1 = window
        s = scale
        W = (x1 - x0 + 1) * s; H = (y1 - y0 + 1) * s
        top = 0
        if title: top = 22
        leg_h = 22 if legend else 0
        o = [f"<svg xmlns='http://www.w3.org/2000/svg' width='{W:.0f}' height='{H + top + leg_h:.0f}' viewBox='0 0 {W:.1f} {H + top + leg_h:.1f}' font-family='Helvetica, Arial, sans-serif'>",
             f"<rect width='100%' height='100%' fill='#ffffff'/>"]
        if title:
            o.append(f"<text x='4' y='16' font-size='13' fill='#222'>{title}</text>")
        o.append(f"<g transform='translate(0,{top})'>")
        o.append(f"<rect x='0' y='0' width='{W:.1f}' height='{H:.1f}' fill='#fbfaf7' stroke='#ccc' stroke-width='0.5'/>")
        if grid and s >= 6:
            for gx in range(x0, x1 + 2):
                o.append(f"<line x1='{(gx - x0) * s:.1f}' y1='0' x2='{(gx - x0) * s:.1f}' y2='{H:.1f}' stroke='#eee' stroke-width='0.5'/>")
            for gy in range(y0, y1 + 2):
                o.append(f"<line x1='0' y1='{(gy - y0) * s:.1f}' x2='{W:.1f}' y2='{(gy - y0) * s:.1f}' stroke='#eee' stroke-width='0.5'/>")

        def inwin(ax, ay, bx, by):
            return not (bx < x0 or ax > x1 or by < y0 or ay > y1)
        sw = max(0.35, 0.5 * s)
        # parts
        sk = 0.6 if s >= 3 else 0.0
        for k, px, py, w, h in self.parts:
            if not inwin(px, py, px + w - 1, py + h - 1): continue
            o.append(f"<rect x='{(px - x0) * s:.2f}' y='{(py - y0) * s:.2f}' width='{w * s:.2f}' height='{h * s:.2f}' fill='{PART_FILL[k]}' fill-opacity='0.85'"
                     + (f" stroke='#333' stroke-width='{sk}'" if sk else '') + "/>")
        # copper, one path per layer
        for L in (0, 1):
            d = []
            for l, ax, ay, bx, by in self.segs:
                if l != L or not inwin(ax, ay, bx, by): continue
                cax, cay, cbx, cby = max(ax, x0 - 1), max(ay, y0 - 1), min(bx, x1 + 1), min(by, y1 + 1)
                d.append(f"M{(cax - x0 + .5) * s:.1f} {(cay - y0 + .5) * s:.1f}L{(cbx - x0 + .5) * s:.1f} {(cby - y0 + .5) * s:.1f}")
            if d:
                o.append(f"<path d='{''.join(d)}' stroke='{L_COL[L]}' stroke-width='{sw:.2f}' stroke-linecap='square' fill='none' stroke-opacity='{0.9 if L == 0 else 0.8}'/>")
        r = max(0.4, 0.32 * s)
        vs = [f"M{(vx - x0 + .5) * s - r:.1f} {(vy - y0 + .5) * s:.1f}a{r:.1f} {r:.1f} 0 1 0 {2 * r:.1f} 0a{r:.1f} {r:.1f} 0 1 0 {-2 * r:.1f} 0"
              for vx, vy in self.vias if x0 <= vx <= x1 and y0 <= vy <= y1]
        if vs: o.append(f"<path d='{''.join(vs)}' fill='{VIA_COL}'/>")
        o.append('</g>')
        if legend:
            o.append(legend_svg(0, top + H + 4, kinds=sorted({p[0] for p in self.parts if inwin(p[1], p[2], p[1] + p[3] - 1, p[2] + p[4] - 1)})))
        o.append('</svg>')
        open(out, 'w').write('\n'.join(o))
        return (x0, y0, x1, y1)

    # ---------------------------------------------------------------- PNG
    def png(self, out, f=1, window=None, rotate=False, margin=4, mark=None):
        """Box-downsampled presence image: each pixel shows which kinds of thing exist in its f x f cells."""
        if window is None:
            x0, y0, x1, y1 = self.bbox(); x0 -= margin; y0 -= margin; x1 += margin; y1 += margin
        else:
            x0, y0, x1, y1 = window
        Wp = (x1 - x0) // f + 1; Hp = (y1 - y0) // f + 1
        part = np.full((Hp, Wp), -1, dtype=np.int8)
        prio = {0: 1, 1: 2, 4: 3, 2: 4, 3: 5, 5: 0}
        pr = np.zeros((Hp, Wp), dtype=np.int8)
        cu = [np.zeros((Hp, Wp), dtype=np.float32) for _ in (0, 1)]
        via = np.zeros((Hp, Wp), dtype=np.float32)
        for k, px, py, w, h in self.parts:
            ax, ay, bx, by = max(px, x0), max(py, y0), min(px + w - 1, x1), min(py + h - 1, y1)
            if ax > bx or ay > by: continue
            sl = (slice((ay - y0) // f, (by - y0) // f + 1), slice((ax - x0) // f, (bx - x0) // f + 1))
            m = pr[sl] < prio[k]
            part[sl][m] = k; pr[sl][m] = prio[k]
        for l, ax, ay, bx, by in self.segs:
            ax, ay, bx, by = max(ax, x0), max(ay, y0), min(bx, x1), min(by, y1)
            if ax > bx or ay > by: continue
            cu[l][(ay - y0) // f:(by - y0) // f + 1, (ax - x0) // f:(bx - x0) // f + 1] += 1.0
        for vx, vy in self.vias:
            if x0 <= vx <= x1 and y0 <= vy <= y1: via[(vy - y0) // f, (vx - x0) // f] += 1
        img = np.ones((Hp, Wp, 3), dtype=np.float32) * hex2rgb('#ffffff')
        for k, col in PART_FILL.items():
            img[part == k] = hex2rgb(col)
        # copper density -> alpha (saturating); f>1 means a pixel covers f*f cells
        for L in (0, 1):
            a = np.clip(cu[L] / max(1.0, f * 0.6), 0, 1)[..., None] * (0.9 if L == 0 else 0.8)
            img = img * (1 - a) + hex2rgb(L_COL[L]) * a
        if f <= 2:
            a = np.clip(via, 0, 1)[..., None] * 0.9
            img = img * (1 - a) + hex2rgb(VIA_COL) * a
        im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
        if rotate: im = im.transpose(Image.Transpose.ROTATE_90)
        im.save(out, optimize=True)
        return (x0, y0, x1, y1), im.size


def legend_svg(x, y, kinds=(0, 1, 2, 3, 4), copper=True, fs=11):
    o = [f"<g transform='translate({x},{y})' font-size='{fs}' fill='#333'>"]
    cx = 4
    for k in kinds:
        if k == 5: continue
        o.append(f"<rect x='{cx}' y='2' width='11' height='11' fill='{PART_FILL[k]}' stroke='#333' stroke-width='0.5'/><text x='{cx + 15}' y='12'>{KIND_NAMES[k]}</text>")
        cx += 22 + 7 * len(KIND_NAMES[k])
    if copper:
        for L in (0, 1):
            o.append(f"<line x1='{cx}' y1='8' x2='{cx + 16}' y2='8' stroke='{L_COL[L]}' stroke-width='4'/><text x='{cx + 20}' y='12'>copper layer {L}</text>")
            cx += 110
        o.append(f"<circle cx='{cx + 5}' cy='8' r='3.5' fill='{VIA_COL}'/><text x='{cx + 13}' y='12'>via</text>")
    o.append('</g>')
    return ''.join(o)


def load(path, offset=(0, 0)):
    w = World(); ox, oy = offset
    if path.endswith('.pkl'):
        data = pickle.load(open(path, 'rb'))
        cmds = data[0] if isinstance(data, tuple) else data
        for c in cmds:
            if c[0] == 'place': w.add_part(c[1], c[2] + ox, c[3] + oy, c[4], c[5] if len(c) > 5 else 0)
            elif c[0] == 'track': w.add_seg(c[1], c[2] + ox, c[3] + oy, c[4] + ox, c[5] + oy)
            elif c[0] == 'via': w.vias.append((c[1] + ox, c[2] + oy))
        return w
    for line in open(path):
        t = line.split()
        if not t: continue
        if t[0] == 'place':
            v = [int(a) for a in t[1:]]
            w.add_part(v[0], v[1] + ox, v[2] + oy, v[3] if len(v) > 3 else 0, v[4] if len(v) > 4 else 0)
        elif t[0] == 'part':      # state file: part ID KIND X Y ROT VAL
            v = [int(a) for a in t[1:]]
            w.add_part(v[1], v[2] + ox, v[3] + oy, v[4], v[5])
        elif t[0] in ('track', 'seg'):
            v = [int(a) for a in t[1:]]
            w.add_seg(v[0], v[1] + ox, v[2] + oy, v[3] + ox, v[4] + oy)
        elif t[0] == 'via':
            w.vias.append((int(t[1]) + ox, int(t[2]) + oy))
    return w


if __name__ == '__main__':
    w = load(sys.argv[1]); print(w.counts(), len(w.segs), len(w.vias), w.bbox())
