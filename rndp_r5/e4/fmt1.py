"""fmt1.py -- compress the engine layout command list into 22-bit data words (format F1) and count words / ones.
word: dx[7:0] (mod 256 add to A.x lo), len[14:8] (7b), orient[15] (0=H,1=V), dy[17:16] (2b, 3 = never used for cmd words), c[20:18] CMD code, H[21] (escape: byte0 = dy8, byte1 = hi)
Sorted within class group (kind/layer), deltas relative to previous command of the group (A.x lo / A.y lo mirror)."""
import collections, sys
import elay, eplace, eroute
def pc(v): return bin(v).count('1')
def compress(cmds, nlate):
    t = nlate[1] + nlate[2]; body = cmds[:len(cmds) - t]; tail = cmds[len(cmds) - t:]
    def norm(c):
        if c[0] == 'track' and (c[3], c[2]) > (c[5], c[4]): return ('track', c[1], c[4], c[5], c[2], c[3])
        return c
    def key(c):
        if c[0] == 'place': return (0, c[1], c[3], c[2])
        if c[0] == 'via': return (2, 0, c[2], c[1])
        return (1, c[1], c[3], c[2])
    groups = collections.defaultdict(list)
    for c in map(norm, body): groups[key(c)[:2]].append(c)
    words = []; ones = 0; esc = 0; splits = 0
    for g, lst in sorted(groups.items()):
        lst.sort(key=key); px = py = 0
        words.append(('hdr', g)); 
        for c in lst:
            if c[0] == 'place': x, y, ln, o, code = c[2], c[3], 0, 0, 1
            elif c[0] == 'via': x, y, ln, o, code = c[1], c[2], 0, 0, 5
            else:
                x, y = c[2], c[3]; o = 0 if c[3] == c[5] else 1; ln = abs(c[4] - c[2]) + abs(c[5] - c[3]); code = 4
            dy = y - py
            if not (0 <= dy <= 2): words.append(('esc', dy)); esc += 1; ones += pc(dy & 255) + 2; dy = 0
            first = True
            while True:
                part = min(ln, 127)
                dx = (x - px) & 255 if first else 0
                w = dx | part << 8 | o << 15 | (dy if first else 0) << 16 | code << 18
                words.append(('cmd', w)); ones += pc(w)
                if first: px, py = x, y; first = False
                else: splits += 1
                if ln <= 127: break
                ln -= 127; x += 0 if o else 127; y += 127 if o else 0     # next piece starts at the end of the previous one
                px, py = x, y; dy = 0
                # (the continuation word moves A to the piece start: dx/dy are carried by the mirror update)
        # note: continuation words need dx=127 (H) or dy=127 (V): approximated as one extra word each
    return words, ones, esc, splits, tail
if __name__ == '__main__':
    nl = elay.read_nl('/tmp/eng.nl'); cmds, info = eroute.route(nl, eplace.order(nl, seed=1), R=14, Z=8)
    words, ones, esc, splits, tail = compress(cmds, info['nlate'])
    print('words', len(words), 'escapes', esc, 'splits', splits, 'ones', ones, 'ones/word', ones / len(words), 'tail cmds', len(tail))
