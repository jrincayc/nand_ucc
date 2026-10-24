"""fmt3.py -- data-word format F3 (9-bit mirrors).  word bits:
 cmd (bit21=1): dx[8:0] len[14:9] orient[15] dy[17:16] c[19:18]      A.x += dx (mod 512), A.y += dy, B = A + len (orient 0: x, 1: y), CMD code c -> {0,1,4,5}
 H   (bit20=1): delta9[8:0] kind[10:9] val[11]                         A.y += delta9 (mod 512); writes arm KIND, VAL registers
 Hi bytes written by the interpreter: A.x hi = Cx | ax8, A.y hi = Cy | ay8, B.x hi = Cx | (ax+lenx)8, B.y hi = Cy | (ay+leny)8   (Cx, Cy even constants)"""
import collections
def pc(v): return bin(v).count('1')
LENMAX = 63
def norm(c):
    if c[0] == 'track' and (c[3], c[2]) > (c[5], c[4]): return ('track', c[1], c[4], c[5], c[2], c[3])
    return c
def key(c):
    if c[0] == 'place': return (0, c[1], c[3], c[2])
    if c[0] == 'via': return (2, 0, c[2], c[1])
    return (1, c[1], c[3], c[2])
def encode(body):
    groups = collections.defaultdict(list)
    for c in map(norm, body): groups[key(c)[:2]].append(c)
    words = []; Ax = 0; Ay = 0; stats = collections.Counter()
    for g in sorted(groups):
        lst = sorted(groups[g], key=key)
        c0 = lst[0]; kind = c0[1] if c0[0] == 'place' else 0; val = c0[1] if c0[0] == 'track' else 0
        def H(delta):
            words.append(1 << 20 | delta | kind << 9 | val << 11); stats['H'] += 1
        for c in lst:
            if c[0] == 'place': x, y, ln, o, code = c[2], c[3], 0, 0, 1
            elif c[0] == 'via': x, y, ln, o, code = c[1], c[2], 0, 0, 3
            else: x, y = c[2], c[3]; o = 0 if c[3] == c[5] else 1; ln = abs(c[4] - c[2]) + abs(c[5] - c[3]); code = 2
            first = True
            while True:
                dy = (y - Ay) & 511
                if dy > 3 or (first and c is lst[0]): H(dy); Ay = (Ay + dy) & 511; dy = 0
                part = min(ln, LENMAX); dx = (x - Ax) & 511
                words.append(1 << 21 | dx | part << 9 | o << 15 | dy << 16 | code << 18); stats['cmd'] += 1
                if not first: stats['split'] += 1
                Ax = (Ax + dx) & 511; Ay = (Ay + dy) & 511; first = False
                if ln <= LENMAX: break
                ln -= LENMAX
                if o: y += LENMAX
                else: x += LENMAX
    return words, stats
def decode(words, Cx=0, Cy=0):
    """reference semantics; returns arm writes (reg, value)"""
    Ax = 0; Ay = 0; wr = []
    for w in words:
        if w >> 21 & 1:
            dx = w & 511; ln = w >> 9 & 63; o = w >> 15 & 1; dy = w >> 16 & 3; c = w >> 18 & 3
            Ax = (Ax + dx) & 511; Ay = (Ay + dy) & 511
            bx = Ax + (0 if o else ln); by = Ay + (ln if o else 0)
            wr += [(0, Ax & 255), (2, Ay & 255), (4, bx & 255), (6, by & 255)]
            wr += [(1, Cx | Ax >> 8), (3, Cy | Ay >> 8), (5, Cx | (bx >> 8) & 1), (7, Cy | (by >> 8) & 1), (15, (c & 1) | (c >> 1) << 2)]
        elif w >> 20 & 1:
            Ay = (Ay + (w & 511)) & 511; wr += [(2, Ay & 255), (8, w >> 9 & 3), (10, w >> 11 & 1)]
    return wr
