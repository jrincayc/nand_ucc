#!/usr/bin/env python3
"""hdmod_export.py OUT.hd -- write the textbook module seed of the Replicator 4 CPU as an HD file: the seven library modules, then a body of
module instances (datapath), flat nand instances (the fixed PLA / expander tiles, marked in the comments) and dffs, then the ports."""
import os, sys
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]
import cpu_gen, modnet, seed_stats, hd as hdlib
from hdexport import PORT_ORDER


def build_seed():
    m = modnet.ModNet(); net, ports, state = cpu_gen.build(net=m)
    return m, ports, state


def export(path):
    m, ports, state = build_seed()
    roots = seed_stats.roots_of(ports, state)
    used = sorted(m.used_nodes(roots))
    region = {}
    for lo, hi, lab in m.regions:
        for n in range(lo, hi): region[n] = lab
    h = hdlib.HD(); RB = int(os.environ.get('ROM_BITS', '14'))
    AB = int(os.environ.get('AB', RB)); RA = int(os.environ.get('RAM_BITS', '8'))
    h.params.update(ab=AB + 1, ram_abits=RA, ram_part=1)
    h.modules = list(modnet.LIB.modules)
    dffs = [n for n in used if m.kind[n][0] == 'dff']
    name = {}; nb = 0
    for n in dffs: name[n] = f'n{nb}'; nb += 1
    order = []; seen_inst = set()
    for n in used:
        k = m.kind[n]
        if k[0] == 'nand': name[n] = f'n{nb}'; nb += 1; order.append(n)
        elif k[0] == 'mod' and k[4] not in seen_inst:
            seen_inst.add(k[4]); base = f'n{nb}'; nb += 1; order.append(n)
            outs = m.insts[k[4]][2]
            for j, o in enumerate(outs): name[o] = base if len(outs) == 1 else f'{base}.{j}'
    def ref(s):
        if m.kind[s][0] == 'in': return m.kind[s][1]
        return name[s]
    for n in dffs: h.body.append(hdlib.Inst(name[n], 'dff', [ref(m.kind[n][1])], m.names.get(n, '')))
    for n in order:
        k = m.kind[n]
        if k[0] == 'nand': h.body.append(hdlib.Inst(name[n], 'nand', [ref(k[1]), ref(k[2])], region.get(n, '')))
        else:
            t, ins, outs = m.insts[k[4]]
            h.body.append(hdlib.Inst(name[outs[0]].split('.')[0], t, [ref(s) for s in ins], ''))
    h.ports = [(p, ref(ports[p])) for p in PORT_ORDER]
    open(path, 'w').write(hdlib.write(h))
    return m, ports, state, roots


if __name__ == '__main__':
    export(sys.argv[1] if len(sys.argv) > 1 else 'hd/cpu_mod.hd')
