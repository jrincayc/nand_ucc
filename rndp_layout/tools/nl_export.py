#!/usr/bin/env python3
"""nl_export.py TOOLSDIR HD OUT.nl -- flatten a hardware description (R2/R3 flat form) into the layout tool's netlist file.
   rom A / ram B                      ROM address bits, RAM address bits (0 = no RAM part)
   n <k> <N|D> <src> [<src>]          node k (dense, holes removed); src = n<k> | rom<j> | ramo<c> | open ; suffix @1 = EN-late, @2 = RUN-late
   p <name> <src>                     fixed-part sink pin (rom_addr<i> arm_addr<i> wdata<j> arm_en ram_addr<i> ram_we ram_din<j>)
RUN sources are the tie node's net, routed last (suffix @2); the arm_en port is routed just before them (@1)."""
import sys
tools, hdf, out = sys.argv[1:4]
sys.path[:0] = [tools]
import hd as H, ref_flatten as RF
hd = H.read(open(hdf).read()); f = RF.flatten(hd)
assert not f.W, 'tiles not supported'
idx = {}
for i in range(f.n_nodes):
    if RF.node_kind(f, i) != 'hole': idx[i] = len(idx)
def src(s, late_run=True):
    if s[0] == 'n': return f'n{idx[s[1]]}'
    if s[0] == 'rom': return f'rom{s[1]}'
    if s[0] == 'ramrd': return f'ramo{s[1]}'
    if s[0] == 'run': return f'n{idx[f.tie]}@2'
    raise ValueError(s)
L = [f'rom {f.rom_abits}', f'ram {f.ram_abits if f.ram_part else 0}']
for i in range(f.n_nodes):
    k = RF.node_kind(f, i)
    if k == 'hole': continue
    ins = [src(s) for s in RF.node_ins(f, i)]
    if k == 'tie': ins = ['open', 'open']
    L.append(f'n {idx[i]} {"D" if k == "dff" else "N"} ' + ' '.join(ins))
for n, s in f.ports: L.append(f'p {n} {src(s)}' + ('@1' if n == 'arm_en' else ''))
open(out, 'w').write('\n'.join(L) + '\n')
print(f'{len(idx)} nodes, {len(f.ports)} ports, tie n{idx[f.tie]}')
