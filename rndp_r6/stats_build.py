import sys, collections
def stats(path):
    kinds = collections.Counter(); L = [0, 0]; segs = [0, 0]; vias = 0; rom = 0; romones = 0; romparts = []; ramparts = []
    xs = []; ys = []; cells = set()
    for ln in open(path):
        t = ln.split()
        if not t: continue
        if t[0] == 'place':
            k, x, y, ang, val = map(int, t[1:6]); kinds[k] += 1; xs.append(x); ys.append(y)
            if k == 2: romparts.append(val)
            if k == 4: ramparts.append(val)
        elif t[0] == 'track':
            l, x0, y0, x1, y1 = map(int, t[1:6]); L[l] += abs(x1 - x0) + abs(y1 - y0); segs[l] += 1
            xs += [x0, x1]; ys += [y0, y1]
        elif t[0] == 'via': vias += 1
        elif t[0] == 'rom':
            rom += 1; romones += bin(int(t[4])).count('1')
    return dict(nand=kinds[0], dff=kinds[1], romparts=romparts, ramparts=ramparts, romnz=rom, romones=romones, L0=L[0], L1=L[1], segs=sum(segs), vias=vias,
                w=max(xs) - min(xs) + 1, h=max(ys) - min(ys) + 1)
if __name__ == '__main__':
    for p in sys.argv[1:]: print(p, stats(p))
