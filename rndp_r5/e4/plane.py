#!/usr/bin/env python3
"""plane.py -- E4 token-ring ROM plane, tile design v2 (pad-touch sbar, 7 commands per 1-cell, 1 per 0-cell, 8 per ring row).
Rows r=0..W-1 (pitch 4, y = Y0+4r), columns j=0..B-1 (pitch 4, x = X0+4j), ring at x = RX..RX+4 (default X0-6).
Ring row: DFF (RX,y) [D (RX,y) Q (RX+1,y)], inverter NAND (RX+3,y+2) [A (RX+3,y+2) B (RX+3,y+3) Y (RX+4,y+2)]; sbar_r = NOT Q_r on layer 1 along y+2.
Q_r also drives D_{r+1} at (RX,y+4) (for r=W-1 that lands at (RX, Y0+4W) = the ring output the engine closes).
Column cell, bit 1: INV (x+2,y) rot0; NAND (x,y+2) rot2 [in0 (x+1,y+3) in1 (x+1,y+2) out (x,y+3)]; the L1 sbar line touches in1's pad (no via).
  z_in enters at (x,y); z_out leaves (x,y+3)->(x,y+4).  Bit 0: plain track (x,y)-(x,y+4).  z_out = z_in OR s_r.  Undriven z_in reads 0.
Column outputs are the track ends at (X0+4j, Y0+4W)."""
import sys

def cell_cmds(x, y, bit):
    if not bit: return [('track', 0, x, y, x, y + 4)]
    return [('place', 0, x + 2, y, 0, 0), ('place', 0, x, y + 2, 2, 0),
            ('track', 0, x, y, x + 2, y), ('track', 0, x + 2, y, x + 2, y + 1),
            ('track', 0, x + 3, y, x + 3, y + 3), ('track', 0, x + 3, y + 3, x + 1, y + 3),
            ('track', 0, x, y + 3, x, y + 4)]

def row_cmds(RX, y, xl):
    return [('place', 1, RX, y, 0, 0), ('place', 0, RX + 3, y + 2, 0, 0),
            ('track', 0, RX + 1, y, RX + 1, y + 3), ('track', 0, RX + 1, y + 2, RX + 3, y + 2), ('track', 0, RX + 3, y + 2, RX + 3, y + 3),
            ('track', 0, RX + 1, y + 3, RX, y + 3), ('track', 0, RX, y + 3, RX, y + 4),
            ('track', 1, RX + 4, y + 2, xl, y + 2)]

def plane(bits, X0, Y0, RX=None):
    W = len(bits); B = len(bits[0]); RX = X0 - 6 if RX is None else RX; xl = X0 + 4 * (B - 1) + 1; cmds = []
    for r in range(W):
        y = Y0 + 4 * r; cmds += row_cmds(RX, y, xl)
        for j in range(B): cmds += cell_cmds(X0 + 4 * j, y, bits[r][j])
    return cmds

def to_lines(cmds):
    out = []
    for c in cmds:
        if c[0] == 'place': out.append(f'place {c[1]} {c[2]} {c[3]} {c[4]} {c[5]}')
        elif c[0] == 'track': out.append(f'track {c[1]} {c[2]} {c[3]} {c[4]} {c[5]}')
        else: out.append(f'via {c[1]} {c[2]}')
    return out

def logical_nets(bits, X0, Y0, RX=None, probes=True):
    W = len(bits); B = len(bits[0]); RX = X0 - 6 if RX is None else RX; pins = {}
    for r in range(W):
        y = Y0 + 4 * r
        pins[(RX, y)] = f'tok{r - 1}' if r else 'start'
        pins[(RX + 1, y)] = f'tok{r}'; pins[(RX + 3, y + 2)] = f'tok{r}'; pins[(RX + 3, y + 3)] = f'tok{r}'; pins[(RX + 4, y + 2)] = f'sbar{r}'
    for j in range(B):
        z = f'zin{j}'
        for r in range(W):
            if not bits[r][j]: continue
            x = X0 + 4 * j; y = Y0 + 4 * r
            pins[(x + 2, y)] = z; pins[(x + 2, y + 1)] = z               # INV A, B
            pins[(x + 3, y)] = f'n{j}_{r}'; pins[(x + 1, y + 3)] = f'n{j}_{r}'     # INV Y, NAND in0
            pins[(x + 1, y + 2)] = f'sbar{r}'                             # NAND in1
            z = f'z{j}_{r}'; pins[(x, y + 3)] = z                         # NAND out
        if probes: pins[(X0 + 4 * j, Y0 + 4 * W)] = z; pins[(X0 + 4 * j + 1, Y0 + 4 * W)] = f'probeQ{j}'
    if probes: pins[(RX, Y0 + 4 * W)] = f'tok{W - 1}'; pins[(RX + 1, Y0 + 4 * W)] = 'probeQring'
    return pins

def probe_cmds(bits, X0, Y0, RX=None):
    W = len(bits); B = len(bits[0]); RX = X0 - 6 if RX is None else RX
    return [('place', 1, X0 + 4 * j, Y0 + 4 * W, 0, 0) for j in range(B)] + [('place', 1, RX, Y0 + 4 * W, 0, 0)]

def simulate(bits, ticks=None):
    """intended-netlist simulation: returns [(tick, word)]; token injected by start at tick 0 sits on row r during tick r+1."""
    W = len(bits); B = len(bits[0]); ticks = ticks or W + 3
    Q = [0] * W; out = []
    for t in range(ticks):
        start = 1 if t == 0 else 0; word = []
        for j in range(B):
            z = 0
            for r in range(W):
                if bits[r][j]: z = 1 - ((1 - z) & (1 - (1 - Q[r])) if False else ((1 - z) & Q_not(Q[r])))
            word.append(z)
        out.append((t, word)); Q = [start] + Q[:-1]
    return out
def Q_not(q): return 1 - q

if __name__ == '__main__':
    import random, json
    W, B = int(sys.argv[1]), int(sys.argv[2]); random.seed(int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    bits = [[random.randint(0, 1) for _ in range(B)] for _ in range(W)]
    cmds = plane(bits, 20, 10) + probe_cmds(bits, 20, 10); open('plane_test.build', 'w').write('\n'.join(to_lines(cmds)) + '\n')
    json.dump(dict(bits=bits, X0=20, Y0=10), open('plane_test.json', 'w')); print(len(cmds), 'commands')
