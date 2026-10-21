#!/usr/bin/env python3
"""validate_layout.py NL LAY [rom.bin] -- build the layout in the rndp simulator and check that the pin nets equal the netlist (no shorts, no opens)."""
import os, subprocess, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools')]
import lay
OFS = (32, 32); RNDP = os.environ.get('RNDP', '/home/claude/rndp/target/release/rndp')

def write_build(cmds, path):
    with open(path, 'w') as fh:
        for c in cmds:
            if c[0] == 'place': fh.write(f'place {c[1]} {c[2] + OFS[0]} {c[3] + OFS[1]} {c[4]} {c[5]}\n')
            elif c[0] == 'track': fh.write(f'track {c[1]} {c[2] + OFS[0]} {c[3] + OFS[1]} {c[4] + OFS[0]} {c[5] + OFS[1]}\n')
            elif c[0] == 'via': fh.write(f'via {c[1] + OFS[0]} {c[2] + OFS[1]}\n')
            elif c[0] == 'rom': fh.write(f'rom {c[1] + OFS[0]} {c[2] + OFS[1]} {c[3]} {c[4]}\n')

def check(nl, L, rom=(), cmds=None, quiet=False):
    cmds = cmds if cmds is not None else lay.commands(L, nl, rom)
    out = os.environ.get('GEOM_OUT') or tempfile.mkdtemp(prefix='rndp_lay_'); os.makedirs(out, exist_ok=True)
    write_build(cmds, f'{out}/geom.build')
    r = subprocess.run([RNDP, '--build', f'{out}/geom.build', '--dump-pads', f'{out}/geom.pads', '--steps', '0', '--layers', '2'], capture_output=True, text=True)
    if not quiet: print(r.stdout[-900:], r.stderr[-300:])
    ex = lay.expected_keys(L, nl); bad = 0; netkeys = {}; keynets = {}
    for line in open(f'{out}/geom.pads'):
        pi, kind, pin, x, y, net = line.split(); x, y, net = int(x) - OFS[0], int(y) - OFS[1], int(net)
        k = ex.get((x, y))
        if k is None: print('unmapped pin', kind, pin, x, y); bad += 1; continue
        netkeys.setdefault(net, set()).add(k); keynets.setdefault(k, set()).add(net)
    for net, ks in netkeys.items():
        if len(ks) > 1:
            bad += 1
            if bad < 15: print('SHORT: net', net, 'joins', sorted(ks, key=str)[:6])
    for k, ns in keynets.items():
        if len(ns) > 1:
            bad += 1
            if bad < 15: print('OPEN: key', k, 'is split over nets', sorted(ns)[:6])
    print('commands', len(cmds), 'pins checked', sum(len(v) for v in netkeys.values()), 'nets', len(netkeys), 'problems', bad)
    return bad

if __name__ == '__main__':
    nl = lay.read_nl(sys.argv[1]); L = lay.read_lay(sys.argv[2])
    rom = list(open(sys.argv[3], 'rb').read()) if len(sys.argv) > 3 else []
    sys.exit(1 if check(nl, L, rom) else 0)
