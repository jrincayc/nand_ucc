#!/usr/bin/env python3
"""hd2nl.py HD OUT.nl [ram_abits] -- flatten a (module) HD with hdflat and write the layout netlist (.nl, format of rndp_layout/tools/nl_export.py).
Node order = hdflat order (dffs first, then the logic in body order, holes absent); the RUN input becomes a tie node with open inputs (last node)."""
import os, sys
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]
import hd as hdlib, hdflat


def convert(h, ram_abits=8):
    key = []
    F, ports = hdflat.flatten(h, key)
    ids = {}
    for n in sorted((n for n in range(2, len(F.kind)) if F.kind[n][0] != 'in'), key=lambda n: key[n]): ids[n] = len(ids)   # placement order = body order
    tie = len(ids)
    runusers = [ids[n] for n in ids if F.kind[n][0] == 'dff' and F.kind[F.kind[n][1]][0:2] == ('in', 'run')]
    def src(s):
        k = F.kind[s]
        if k[0] == 'in':
            nm = k[1]
            if nm == 'run': return f'n{tie}@2'
            return f'rom{nm[3:]}' if nm.startswith('rom') else f'ramo{nm[5:]}'
        return f'n{ids[s]}'
    rb = len([p for p in ports if p.startswith('rom_addr')])
    L = [f'rom {rb}', f'ram {ram_abits}']
    for n in sorted(ids, key=ids.get):
        k = F.kind[n]
        if k[0] == 'dff': L.append(f'n {ids[n]} D {src(k[1])}')
        else: L.append(f'n {ids[n]} N {src(k[1])} {src(k[2])}')
    L.append(f'n {tie} N open open')
    for p, s in ports.items(): L.append(f'p {p} {src(s)}' + ('@1' if p == 'arm_en' else ''))
    return '\n'.join(L) + '\n', len(ids) + 1


if __name__ == '__main__':
    h = hdlib.read(open(sys.argv[1]).read())
    text, n = convert(h, int(sys.argv[3]) if len(sys.argv) > 3 else 8)
    open(sys.argv[2], 'w').write(text); print(n, 'nodes (incl. tie)')
