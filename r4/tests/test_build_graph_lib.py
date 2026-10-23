"""test_build_graph_lib.py -- netlist packing for the placement kernels and a random netlist generator."""
import os as _o, sys as _s; _s.path[:0] = [_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "..", "tools")]
import struct, random, place_ref, route_ref
class NL: pass
def pack(nl, ram):
    """write SRC / PSRC / V_N / V_NP of a netlist into the RAM image"""
    N = len(nl.nodes); src = []
    for kind, ins in nl.nodes:
        for p in range(2):
            t = ins[p] if p < len(ins) else 'open'; d = place_ref.net_id(t, N); src.append(0xFFFF if d is None else d | (route_ref.late_of(t) << 14))
    psrc = [d for d in (place_ref.net_id(t, N) for _, t in nl.ports) if d is not None and d < N]
    struct.pack_into('<%dH' % len(src), ram, 0x26000, *src); struct.pack_into('<%dH' % len(psrc), ram, 0x2A000, *psrc); struct.pack_into('<II', ram, 0x68, N, len(psrc))
    return src
def rand_nl(rng, N):
    nl = NL(); nodes = []
    for k in range(N):
        ins = []
        for p in range(2):
            r = rng.random()
            if r < .08: ins.append('open')
            elif r < .16: ins.append(f'rom{rng.randrange(8)}')
            elif r < .22: ins.append(f'ramo{rng.randrange(8)}')
            elif r < .27: ins.append(f'n{k}')
            else: ins.append(f'n{rng.randrange(N)}' + rng.choice(['', '', '@1', '@2']))
        if rng.random() < .15: ins[1] = ins[0]
        nodes.append((rng.choice('ND'), ins))
    nl.nodes = nodes; nl.ports = [(f'p{i}', f'n{rng.randrange(N)}' + rng.choice(['', '@1'])) for i in range(rng.randint(0, min(N, 400)))] + [('ramport', 'ramo1')]
    if rng.random() < .5:
        hub = rng.randrange(N)
        for k in range(N):
            if rng.random() < .5: nodes[k][1][0] = f'n{hub}'              # big net (> 12 pins)
    return nl
