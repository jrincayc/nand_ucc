"""fmt2.py -- data-word format F2 + encoder + reference decoder (the semantics of the interpreter micro-rows).
word bits: cmd  : dx[7:0] len[13:8] orient[14] dy[16:15] c[18:17] (bit19=bit20=0) Cmd[21]=1
           Hy   : delta_y9 [8:0], bit20=1               (Ay += delta mod 512)
           Hk   : kind [7:0], val [15:8], bit19=1       (writes arm regs 8 and 10)
mirrors: Ax 8 bits (layout x in one 256 block), Ay 9 bits.  c: 0 none, 1 place, 2 track, 3 via -> CMD register value {0,1,4,5} = c0 | c1<<2."""
import collections, sys
import elay, eplace, eroute
from arm import Arm
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
    def H(delta): words.append(1 << 20 | delta); stats['Hy'] += 1
    for g in sorted(groups):
        lst = sorted(groups[g], key=key)
        kind, val = (lst[0][1], 0) if lst[0][0] == 'place' else (0, lst[0][1] if lst[0][0] == 'track' else 0)
        words.append(1 << 19 | kind | val << 8); stats['Hk'] += 1
        for c in lst:
            if c[0] == 'place': x, y, ln, o, code = c[2], c[3], 0, 0, 1
            elif c[0] == 'via': x, y, ln, o, code = c[1], c[2], 0, 0, 3
            else: x, y = c[2], c[3]; o = 0 if c[3] == c[5] else 1; ln = abs(c[4] - c[2]) + abs(c[5] - c[3]); code = 2
            first = True
            while True:
                dy = (y - Ay) & 511
                if dy > 3: H(dy); Ay = (Ay + dy) & 511; dy = 0
                part = min(ln, LENMAX); dx = (x - Ax) & 255
                words.append(1 << 21 | dx | part << 8 | o << 14 | dy << 15 | code << 17); stats['cmd'] += 1
                if not first: stats['split'] += 1
                Ax = (Ax + dx) & 255; Ay = (Ay + dy) & 511; first = False
                if ln <= LENMAX: break
                ln -= LENMAX
                if o: y += LENMAX
                else: x += LENMAX
    return words, stats
def decode(words, hi=(0, 0, 0, 0)):
    """reference semantics of the interpreter; returns the list of arm writes (reg, value)"""
    Ax = 0; Ay = 0; wr = []
    for w in words:
        if w >> 21 & 1:
            dx = w & 255; ln = w >> 8 & 63; o = w >> 14 & 1; dy = w >> 15 & 3; c = w >> 17 & 3
            Ax = (Ax + dx) & 255; Ay = (Ay + dy) & 511
            wr += [(0, Ax), (1, 0), (2, Ay & 255), (3, Ay >> 8)]
            bx = Ax + (0 if o else ln); by = Ay + (ln if o else 0)
            wr += [(4, bx & 255), (5, bx >> 8), (6, by & 255), (7, by >> 8), (15, (c & 1) | (c >> 1) << 2)]
        elif w >> 20 & 1:
            Ay = (Ay + (w & 511)) & 511; wr += [(2, Ay & 255), (3, Ay >> 8)]
        elif w >> 19 & 1:
            wr += [(8, w & 255), (10, w >> 8 & 255)]
    return wr
if __name__ == '__main__':
    nl = elay.read_nl('/tmp/eng.nl'); cmds, info = eroute.route(nl, eplace.order(nl, seed=1), R=22, Z=14)
    t = info['nlate'][1] + info['nlate'][2]; body = cmds[:len(cmds) - t]
    words, st = encode(body)
    ones = sum(pc(w) for w in words)
    print('words', len(words), dict(st), 'ones', ones, 'ones/word', round(ones / len(words), 2))
    a = Arm(); 
    for r, v in decode(words): a.write(r, v)
    got = collections.Counter(a.cmds); exp = collections.Counter()
    for c in map(norm, body):
        if c[0] == 'place': exp[('place', c[1], c[2], c[3], 0, 0)] += 1
        elif c[0] == 'via': exp[('via', c[1], c[2])] += 1
        else: exp[('track', c[1], c[2], c[3], c[4], c[5])] += 1
    # split tracks appear as several tracks: merge check by comparing covered unit segments
    def cells(cs):
        s = collections.Counter()
        for c in cs.elements():
            if c[0] == 'track':
                _, l, x0, y0, x1, y1 = c
                for xx in range(x0, x1 + 1):
                    for yy in range(y0, y1 + 1): s[('t', l, xx, yy)] += 1
            else: s[c] += 1
        return set(s)
    print('faults', a.faults, 'arm writes', a.writes, 'cmds got', len(a.cmds), 'exp', sum(exp.values()))
    print('same non-track cmds', all(got[k] == exp[k] for k in exp if k[0] != 'track') and all(k in exp for k in got if k[0] != 'track'))
    print('same covered track cells', cells(got) == cells(exp))
