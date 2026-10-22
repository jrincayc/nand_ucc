#!/usr/bin/env python3
"""seed_stats.py -- gate counts of the flat optimised CPU (R3c generator) and of the textbook module seed (ModNet)."""
import os, sys
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]
import cpu_gen, modnet
from netlist import Net
def flat(x):
    for y in x:
        if isinstance(y, list): yield from flat(y)
        else: yield y
def roots_of(ports, state): return list(ports.values()) + list(flat(v if isinstance(v, list) else [v] for v in state.values()))
if __name__ == '__main__':
    net, ports, state = cpu_gen.build()
    u = net.used_nodes(roots_of(ports, state))
    print('flat optimised (R3c generator):', sum(1 for n in u if net.kind[n][0] == 'nand'), 'NAND', sum(1 for n in u if net.kind[n][0] == 'dff'), 'DFF')
    m = modnet.ModNet(); mn, mp, ms = cpu_gen.build(net=m)
    byt, fl_n, dff, gates = m.counts(roots_of(mp, ms))
    print('module seed: instances', dict(sorted(byt.items())), '| flat-tile NAND', fl_n, '| DFF', dff, '| total NAND', gates)
    for lo, hi, lab in m.regions:
        print('  region', lab, 'nodes', hi - lo)
