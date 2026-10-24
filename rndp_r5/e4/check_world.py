#!/usr/bin/env python3
"""check_world.py W SEED -- build the parent world in rndp (--build), dump pads, and compare world nets with the logical design (engine netlist + plane + arm pins)."""
import sys, json, pickle, subprocess, collections, os
import elay, plane as PL, spec2 as S
W = int(sys.argv[1]); SEED = sys.argv[2]
d = json.load(open('/tmp/e4_rows.json')); X0, RX, BX, AYP, Y0P = d['X0'], d['RX'], d['BX'], d['AYP'], d['Y0P']
parent, _ = pickle.load(open('/tmp/e4_parent.pkl', 'rb'))
OX, OY = 16, 13200
def off(c):
    if c[0] == 'place': return ('place', c[1], c[2] + OX, c[3] + OY, c[4], c[5])
    if c[0] == 'track': return ('track', c[1], c[2] + OX, c[3] + OY, c[4] + OX, c[5] + OY)
    return ('via', c[1] + OX, c[2] + OY)
open('/tmp/e4_parent.build', 'w').write('\n'.join(PL.to_lines([off(c) for c in parent])) + '\n')
rn = os.path.expanduser('~/rndp/target/release/rndp') if False else '/home/claude/rndp/target/release/rndp'
r = subprocess.run([rn, '--build', '/tmp/e4_parent.build', '--rom', 'off', '--ram', 'off', '--width', '2048', '--height', '50000', '--dump-pads', '/tmp/e4_parent.pads', '--steps', '0'], capture_output=True, text=True)
print(r.stdout[-1500:], r.stderr[-500:])
nl = elay.read_nl(f'/tmp/fp_{W}_{SEED}.nl')
bits = [S.bits(w) for w in d['srows']]
pins = PL.logical_nets(bits, X0, Y0P, RX, probes=False)     # plane pins (P frame)
# column top nets
alias = {}
for j in range(24):
    z = f'zin{j}'
    for r_ in range(W):
        if bits[r_][j]: z = f'z{j}_{r_}'
    alias[f'x{j}'] = z
alias['x24'] = f'tok{W - 1}'
# engine placement: first N parts of the parent body in node order
N = len(nl.nodes)
plc = [c for c in parent if c[0] == 'place'][-0:]                       # find engine places by block frame
eng = [c for c in parent if c[0] == 'place' and c[1] in (0, 1) and c[3] >= AYP and c[2] >= BX]
# node order = order of placement commands in the parent (body is emitted in node order right after plane)
npl = len([c for c in parent if c[0] == 'place'])
bodystart = len(PL.plane(bits, X0, Y0P, RX))
places = [c for c in parent[bodystart:] if c[0] == 'place'][:N]
assert len(places) == N and all(c[1] == (1 if nl.nodes[k][0] == 'D' else 0) for k, c in enumerate(places))
def nm(tok, k=None, p=None):
    b = tok.split('@')[0]
    if b == 'open': return f'open{k}_{p}'
    return alias.get(b, b)
for k, (kind, ins) in enumerate(nl.nodes):
    _, _, x, y, _, _ = places[k]
    pins[(x + 1, y)] = f'n{k}'
    for p, tok in enumerate(ins): pins[(x, y + p)] = nm(tok, k, p)
# arm pins and the start wire
ports = dict(nl.ports)
armn = {}
for i in range(4): armn[(0, i)] = nm(ports[f'arm_addr{i}'])
armn[(0, 4)] = nm(ports['arm_en'])
for j in range(8): armn[(1, j)] = nm(ports[f'wdata{j}'])
pins.update(armn)
pins[(RX, Y0P)] = nm(ports['ram_addr0'])                                 # ring start = D0 net
# world pads
worldnet = {}; lognets = collections.defaultdict(set); worldn = collections.defaultdict(set); unm = []
got = set()
for l in open('/tmp/e4_parent.pads'):
    pi, kind, pin, x, y, net = l.split(); k = (int(x) - OX, int(y) - OY); got.add(k)
    if k not in pins: unm.append((kind, pin, k, net)); continue
    lognets[pins[k]].add(int(net)); worldn[int(net)].add(pins[k])
missing = [k for k in pins if k not in got]
opens = {n: s for n, s in lognets.items() if len(s) > 1}; shorts = {n: s for n, s in worldn.items() if len(s) > 1}
print('declared', len(pins), 'dumped', len(got), 'missing', len(missing), 'undeclared', len(unm), 'opens', len(opens), 'shorts', len(shorts))
for u in unm[:5]: print('undeclared', u)
for k in missing[:5]: print('missing', k, pins[k])
for n, s in list(opens.items())[:5]: print('OPEN', n, sorted(s)[:4])
for n, s in list(shorts.items())[:5]: print('SHORT', n, sorted(s)[:4])
