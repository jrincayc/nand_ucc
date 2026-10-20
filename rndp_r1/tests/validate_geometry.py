#!/usr/bin/env python3
"""validate_geometry.py HD [rom.bin] -- build the reference command list in the rndp simulator (--build) and check that
the nets of the built PCB equal the nets of the hardware description (partition equality over all pins)."""
import os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, '..', 'tools')]
import hd as H, ref_flatten as RF

OFS = (32, 32)
RNDP = os.environ.get('RNDP', '/home/claude/rndp/target/release/rndp')


def write_build(cmds, path, ofs=OFS):
    with open(path, 'w') as fh:
        for c in cmds:
            if c[0] == 'place': fh.write(f'place {c[1]} {c[2] + ofs[0]} {c[3] + ofs[1]} {c[4]} {c[5]}\n')
            elif c[0] == 'track': fh.write(f'track {c[1]} {c[2] + ofs[0]} {c[3] + ofs[1]} {c[4] + ofs[0]} {c[5] + ofs[1]}\n')
            elif c[0] == 'via': fh.write(f'via {c[1] + ofs[0]} {c[2] + ofs[1]}\n')
            elif c[0] == 'rom': fh.write(f'rom {c[1] + ofs[0]} {c[2] + ofs[1]} {c[3]} {c[4]}\n')
            else: raise ValueError(c)


def expected_keys(f):
    """pin (x,y) relative -> logical net key"""
    ex = {}
    def src_key(s):
        if s[0] == 'run': return ('n', f.tie)
        if s[0] == 'ramrd': return ('n', RF.ramrd_gate(f, s[1]))
        return s
    for i in range(f.n_nodes):
        k = RF.node_kind(f, i)
        if k == 'hole': continue
        x, y = RF.node_pos(f, i)
        ex[(x + 1, y)] = ('n', i)
        for p, s in enumerate(RF.node_ins(f, i)): ex[(x, y + p)] = src_key(s)
        if k in ('nand', 'tie') and len(RF.node_ins(f, i)) < 2 and k != 'dff':
            # unconnected input pins (tie) get unique keys
            for p in range(len(RF.node_ins(f, i)), 2): ex[(x, y + p)] = ('open', i, p)
    for j in range(8): ex[(-2 - j, 1)] = ('rom', j)
    P = dict(f.ports)
    for n, _ in f.ports:
        px, py, r = RF.port_sink(n); ex[(px, py)] = src_key(P[n])
    return ex


def main():
    hdf = sys.argv[1]
    rom = list(open(sys.argv[2], 'rb').read()) if len(sys.argv) > 2 else []
    hd = H.read(open(hdf).read()); f = RF.flatten(hd)
    t0 = time.time()
    cmds = RF.commands(f, rom)
    if os.environ.get('MUTATE'):
        m = int(os.environ['MUTATE']); print('negative control: dropping', cmds[m]); del cmds[m]
    out = '/tmp/claude-0/work'
    write_build(cmds, f'{out}/geom.build')
    print(f'{len(cmds)} commands generated in {time.time() - t0:.1f}s; extent {RF.extent(f)}', flush=True)
    t0 = time.time()
    r = subprocess.run([RNDP, '--build', f'{out}/geom.build', '--dump-pads', f'{out}/geom.pads', '--steps', '0'], capture_output=True, text=True)
    print(r.stdout[-1500:], r.stderr[-600:], f'[{time.time() - t0:.1f}s]')
    ex = expected_keys(f)
    seen = {}
    bad = 0; netkeys = {}; keynets = {}
    for line in open(f'{out}/geom.pads'):
        pi, kind, pin, x, y, net = line.split()
        x, y, net = int(x) - OFS[0], int(y) - OFS[1], int(net)
        key = ex.get((x, y))
        if key is None:
            if kind in ('rom', 'arm') or True:
                # pins we do not know about (e.g. ARM pins not mapped) are reported
                print('unmapped pin', kind, pin, x, y); bad += 1
            continue
        netkeys.setdefault(net, set()).add(key); keynets.setdefault(key, set()).add(net)
    for net, ks in netkeys.items():
        if len(ks) > 1:
            bad += 1
            if bad < 15: print('SHORT: net', net, 'joins', sorted(ks, key=str)[:6])
    for k, ns in keynets.items():
        if len(ns) > 1:
            bad += 1
            if bad < 15: print('OPEN: key', k, 'is split over nets', sorted(ns)[:6])
    print('pins checked', sum(len(v) for v in netkeys.values()), 'nets', len(netkeys), 'problems', bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
