"""blk.py -- shared helpers for the R6 formula generators: a build under construction (parts, tracks, vias, logical pin nets) and the AND-chain decoder line."""
import json
class G:
    def __init__(s):
        s.B = []; s.pins = {}; s.n = 0; s.gate_list = []
    def newnet(s): s.n += 1; return s.n
    def trk(s, L, x0, y0, x1, y1):
        if (x0, y0) != (x1, y1): s.B.append(f'track {L} {x0} {y0} {x1} {y1}')
    def via(s, x, y): s.B.append(f'via {x} {y}')
    def pin(s, x, y, net):
        assert (x, y) not in s.pins, (x, y); s.pins[(x, y)] = net
    def nand(s, x, y, ins):
        s.B.append(f'place 0 {x} {y} 0 0'); n = s.newnet(); s.pin(x, y, ins[0]); s.pin(x, y + 1, ins[1]); s.pin(x + 1, y, n); return n
    def dff(s, x, y, d):
        s.B.append(f'place 1 {x} {y} 0 0'); n = s.newnet(); s.pin(x, y, d); s.pin(x + 1, y, n); return n
    def save(s, path, extra):
        open(path, 'w').write('\n'.join(s.B) + '\n')
        d = dict(extra); d['pins'] = [[x, y, n] for (x, y), n in s.pins.items()]; json.dump(d, open(path + '.pins.json', 'w'))

def and_line(g, y, v, i0, nbits, XG, lit):
    """AND of nbits address literals as a chain of NAND/NOT; lit(i, bit, row) -> (bus x, net) and records the bus extent.  Output NOT at (XG+8*(nbits-2)+4, y), pin Y at +5.  Returns (net, x of Y pad)."""
    lits = [lit(i0 + k, (v >> k) & 1, y + 2 + max(0, k - 1)) for k in range(nbits)]
    prev = None
    for k in range(nbits - 1):
        Xk = XG + 8 * k
        if k == 0:
            (xb0, n0), (xb1, n1) = lits[0], lits[1]
            g.via(xb0, y); g.trk(0, xb0, y, Xk, y)
            g.via(xb1, y + 2); g.trk(0, xb1, y + 2, Xk, y + 2); g.trk(0, Xk, y + 2, Xk, y + 1)
            ins = [n0, n1]
        else:
            xb, n1 = lits[k + 1]
            g.trk(0, Xk - 3, y, Xk, y)
            g.via(xb, y + 2 + k); g.trk(0, xb, y + 2 + k, Xk, y + 2 + k); g.trk(0, Xk, y + 2 + k, Xk, y + 1)
            ins = [prev, n1]
        nd = g.nand(Xk, y, ins)
        g.trk(0, Xk + 1, y, Xk + 4, y); g.trk(0, Xk + 3, y, Xk + 3, y + 1); g.trk(0, Xk + 3, y + 1, Xk + 4, y + 1)
        prev = g.nand(Xk + 4, y, [nd, nd])
    return prev, XG + 8 * (nbits - 2) + 5

def inverters(g, XB, INVY, nbits):
    """address inputs a_i (external) and their inverters; buses: a_i at x=XB+4i-1, na_i at XB+4i+1 (layer 1, drawn later up to bus_extent)."""
    ab, nab = [], []
    for i in range(nbits):
        x = XB + 4 * i; a = g.newnet(); ab.append(a)
        nab.append(g.nand(x, INVY, [a, a]))
        g.via(x - 1, INVY + 1); g.trk(0, x - 1, INVY + 1, x - 1, INVY); g.trk(0, x - 1, INVY, x, INVY); g.trk(0, x - 1, INVY + 1, x, INVY + 1)
    return ab, nab
