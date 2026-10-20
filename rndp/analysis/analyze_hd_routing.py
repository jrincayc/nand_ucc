#!/usr/bin/env python3
"""Throwaway analysis of a core.hd-style hardware description for RNDP routing.

Usage: python3 -I analyze.py CORE_BODY_HD

Expands every body instance (modules -> NAND gates), builds the nets, classifies each net as
slice-local / slice-neighbour / broadcast / irregular, and prints counts.  The RAM tile (ram_word x 32)
is modelled separately from its known structure because it was left out of the input file.
No placement exists yet, so route-byte numbers are parametric, not measured.
"""
import re
import sys
from collections import Counter, defaultdict


# ---------------------------------------------------------------- parsing
def parse(path):
    mods, body, ports = {}, [], []
    lines = [l.split('#')[0].strip() for l in open(path)]
    i = 0
    while i < len(lines):
        l = lines[i]; i += 1
        if not l:
            continue
        w = l.split()
        if w[0] == 'module':
            name, n_in, n_out = w[1], int(w[2]), int(w[3])
            gates, outs = [], []
            while lines[i] != 'end':
                t = lines[i].split(); i += 1
                if not t:
                    continue
                if t[0] == 'out':
                    outs = [int(x[1:]) for x in t[1:]]
                else:
                    gates.append((t[3], t[4]))
            i += 1
            mods[name] = (n_in, n_out, gates, outs)
        elif w[0] == 'body':
            while lines[i] != 'end':
                t = lines[i].split(); i += 1
                if t:
                    body.append((t[0], t[2], t[3:]))
            i += 1
        elif w[0] == 'ports':
            while lines[i] != 'end':
                t = lines[i].split(); i += 1
                if t:
                    ports.append((t[0], t[2]))
            i += 1
    return mods, body, ports


# ---------------------------------------------------------------- expansion
EXTERNAL = re.compile(r'^(rom\d+|ramrd\d+|run)$')


def expand(mods, body):
    """Return gates [(gid, kind, ins, out_net, owner)] and out_nets {inst: [net per output]}."""
    out_nets = {}
    for name, typ, _ in body:
        if typ in ('nand', 'dff'):
            out_nets[name] = [name]
        else:
            n_in, n_out, gates, outs = mods[typ]
            out_nets[name] = [f'{name}/g{o}' for o in outs]

    def resolve(ref):
        if EXTERNAL.match(ref):
            return ref
        if ref in out_nets:
            return out_nets[ref][0]
        base, _, k = ref.rpartition('.')
        if base in out_nets and k.isdigit():
            return out_nets[base][int(k)]
        raise KeyError(ref)

    gates = []
    for name, typ, refs in body:
        ins = [resolve(r) for r in refs]
        if typ == 'nand':
            gates.append((name, 'nand', ins, name, name))
        elif typ == 'dff':
            gates.append((name, 'dff', ins, name, name))
        else:
            n_in, n_out, mg, outs = mods[typ]

            def sig(s):
                return ins[int(s[1:])] if s[0] == 'i' else f'{name}/g{int(s[1:])}'
            for k, (a, b) in enumerate(mg):
                gates.append((f'{name}/g{k}', 'nand', [sig(a), sig(b)], f'{name}/g{k}', name))
    return gates


# ---------------------------------------------------------------- slice classification
def group_of(owner):
    if owner in ('c.n', 'one', 'zero', 'reset'):
        return 'const'
    return owner.split('.')[0]


def slice_of(owner):
    """(group, stage, bit) for bit-sliced instances; None for control / glue."""
    m = re.match(r'^(pc|a|d)\.(\d+)$', owner)
    if m:
        return (m.group(1) + 'reg', 0, int(m.group(2)))
    m = re.match(r'^pc\.mux(\d+)$', owner)
    if m:
        n = int(m.group(1)); return ('pcmux', n // 15, n % 15)
    m = re.match(r'^addr\.(mux|ha)(\d+)$', owner)
    if m:
        return ('addr' + m.group(1), 0, int(m.group(2)))
    m = re.match(r'^areg\.mux(\d+)$', owner)
    if m:
        n = int(m.group(1)); return ('areg', n % 3, n // 3)
    m = re.match(r'^dreg\.mux(\d+)$', owner)
    if m:
        return ('dreg', 0, int(m.group(1)))
    m = re.match(r'^alu\.(mux|not|fa|and)(\d+)$', owner)
    if m:
        kind, n = m.group(1), int(m.group(2))
        if kind == 'fa' or kind == 'and':
            return ('alu' + kind, 0, n)
        if n == 24 and kind == 'not':
            return None                       # zero-flag reduction output
        return ('alu' + kind, n // 8, n % 8)
    m = re.match(r'^decode\.nand(\d+)$', owner)
    if m:
        n = int(m.group(1)); return ('rdmux', n % 3, n // 3)
    m = re.match(r'^ir\.mux(\d+)$', owner)
    if m:
        return ('irmux', 0, int(m.group(1)))
    return None                               # decode chain, control, ram decode, ir/st flops, reductions, consts


def analyse(gates):
    nets = defaultdict(lambda: {'driver': None, 'sinks': []})
    for gid, kind, ins, out, owner in gates:
        nets[out]['driver'] = (gid, owner)
        for pin, n in enumerate(ins):
            nets[n]['sinks'].append((gid, owner, pin))
    return nets


def classify(net_name, net):
    drv = net['driver']
    members = []
    if drv:
        members.append(drv[1])
    members += [s[1] for s in net['sinks']]
    sl = [slice_of(o) for o in members]
    if all(s is not None for s in sl):
        bits = {s[2] for s in sl}
        if len(bits) == 1:
            return 'slice-local'
        if len(bits) == 2 and max(bits) - min(bits) == 1:
            return 'slice-neighbour'
    # broadcast: non-sliced (or external) driver, many sinks, all sinks sliced
    drv_sl = slice_of(drv[1]) if drv else None
    if drv_sl is None and len(net['sinks']) >= 3 and all(slice_of(s[1]) is not None for s in net['sinks']):
        return 'broadcast'
    return 'irregular'


def fan_bucket(n):
    for hi, lab in ((1, '1'), (2, '2'), (3, '3'), (4, '4'), (8, '5-8'), (16, '9-16')):
        if n <= hi:
            return lab
    return '17+'


def main(path):
    mods, body, ports = parse(path)
    gates = expand(mods, body)
    n_nand = sum(1 for g in gates if g[1] == 'nand')
    n_dff = sum(1 for g in gates if g[1] == 'dff')
    print(f'instances in body: {len(body)}   gates: {len(gates)}   NAND: {n_nand}   DFF: {n_dff}')

    by_group = Counter()
    dff_by_group = Counter()
    for gid, kind, ins, out, owner in gates:
        by_group[group_of(owner)] += 1
        if kind == 'dff':
            dff_by_group[group_of(owner)] += 1
    print('\ngates by group (incl. DFF):')
    for k, v in sorted(by_group.items(), key=lambda kv: -kv[1]):
        print(f'  {k:8s} {v:5d}   (DFF {dff_by_group[k]})')

    nets = analyse(gates)
    # a net with no sink at all (dangling output) still needs no copper
    live = {k: v for k, v in nets.items() if v['sinks']}
    print(f'\nnets with at least one sink: {len(live)}  (external sources: '
          f'{sorted(k for k in live if EXTERNAL.match(k))})')
    # pin pads: every gate input is a pad, even when both inputs of a NAND share a net
    total_sink_pads = sum(len(v['sinks']) for v in live.values())
    print(f'sink pads: {total_sink_pads}   driver pads (gates): {len(gates)}')

    fan = Counter(fan_bucket(len(v['sinks'])) for v in live.values())
    print('\nfan-out distribution (sink pads per net):')
    for lab in ('1', '2', '3', '4', '5-8', '9-16', '17+'):
        print(f'  {lab:5s} {fan.get(lab, 0):5d}')

    # same-net double pins (nand x x): one net reaches two pads of the same gate
    dbl = sum(1 for v in live.values() for gid, c in Counter(s[0] for s in v['sinks']).items() if c > 1)
    print(f'\ngates with both inputs on one net (nand x x): {dbl}')

    cls = defaultdict(list)
    for k, v in live.items():
        cls[classify(k, v)].append(k)
    print('\nnet classes (heuristic, by bit-slice index; no placement exists yet):')
    print(f'  {"class":16s} {"nets":>6s} {"sink pads":>10s} {"connections":>12s}')
    conn_total = 0
    for c in ('slice-local', 'slice-neighbour', 'broadcast', 'irregular'):
        ks = cls.get(c, [])
        pads = sum(len(live[k]['sinks']) for k in ks)
        print(f'  {c:16s} {len(ks):6d} {pads:10d} {pads:12d}')
        conn_total += pads
    print(f'  {"total":16s} {len(live):6d} {total_sink_pads:10d} {conn_total:12d}')
    print('  (connection = one driver-to-sink-pad link; a net with s sinks needs at least s links)')

    # ---- refined view: module-internal nets (routed once per module template) vs inter-instance nets,
    # counting distinct sink GATES (a nand x x inverter needs one track in plus a pad-to-pad stub)
    def internal(v):
        d = v['driver']
        return d is not None and all(s[1] == d[1] for s in v['sinks'])

    def links(v):
        return len({s[0] for s in v['sinks']})
    print('\nrefined: inter-instance nets only (module-internal nets belong to the module template):')
    print(f'  {"class":16s} {"nets":>6s} {"gate links":>11s}')
    tot_n = tot_l = 0
    for c in ('slice-local', 'slice-neighbour', 'broadcast', 'irregular'):
        ks = [k for k in cls.get(c, []) if not internal(live[k])]
        ln = sum(links(live[k]) for k in ks)
        tot_n += len(ks); tot_l += ln
        print(f'  {c:16s} {len(ks):6d} {ln:11d}')
    print(f'  {"total":16s} {tot_n:6d} {tot_l:11d}')
    int_nets = [k for k in live if internal(live[k])]
    print(f'  module-internal nets: {len(int_nets)} (inside {len(body)} instances; templates: '
          f'{sorted({t for _, t, _ in body if t in mods})})')
    # inverter stubs: gates whose two inputs are the same net
    stub_inter = 0
    for k, v in live.items():
        if internal(v):
            continue
        c = Counter(s[0] for s in v['sinks'])
        stub_inter += sum(1 for g, n in c.items() if n > 1)
    print(f'  gates with both inputs on one INTER-instance net (need a pad-to-pad stub): {stub_inter}')
    irr_inter = [k for k in cls.get('irregular', []) if not internal(live[k])]
    c_links = sum(links(live[k]) for k in irr_inter)
    print(f'  irregular inter-instance gate links: {c_links}')
    print('  explicit route bytes ~= links * segments_per_link * bytes_per_segment (parametric, NOT measured)')
    print('    segs/link \\ bytes/seg:      4       6       8')
    for s in (2, 3, 4):
        print(f'    {s:>19d}   ' + '  '.join(f'{c_links * s * b:6d}' for b in (4, 6, 8)))
    print('  irregular inter-instance nets by driver group:')
    dg = Counter(group_of(live[k]['driver'][1]) if live[k]['driver'] else 'external' for k in irr_inter)
    for g, c in dg.most_common():
        ln = sum(links(live[k]) for k in irr_inter
                 if (group_of(live[k]['driver'][1]) if live[k]['driver'] else 'external') == g)
        print(f'    {g:10s} nets {c:4d}  gate links {ln:4d}')

    irr = sorted(cls.get('irregular', []), key=lambda k: -len(live[k]['sinks']))
    print('\nirregular nets by group of driver:')
    drv_groups = Counter(group_of(live[k]['driver'][1]) if live[k]['driver'] else 'external' for k in irr)
    for g, c in drv_groups.most_common():
        pads = sum(len(live[k]['sinks']) for k in irr
                   if (group_of(live[k]['driver'][1]) if live[k]['driver'] else 'external') == g)
        print(f'  {g:10s} nets {c:4d}  sink pads {pads:5d}')

    print('\nhighest fan-out nets (all classes):')
    top = sorted(live, key=lambda k: -len(live[k]['sinks']))[:20]
    for k in top:
        print(f'  {len(live[k]["sinks"]):4d}  {k:22s} {classify(k, live[k])}')

    # parametric route-byte estimate for the irregular class only
    c_irr = sum(len(live[k]['sinks']) for k in irr)
    print(f'\nirregular connections C = {c_irr}')
    print('explicit route bytes ~= C * segments_per_connection * bytes_per_segment   (parametric, NOT measured)')
    print('  segments/conn \\ bytes/seg:      4        6        8')
    for s in (2, 3, 4):
        print(f'  {s:>25d}   ' + '  '.join(f'{c_irr * s * b:7d}' for b in (4, 6, 8)))

    # ------------------------------------------------------------ RAM tile model
    print('\n--- RAM (32 words x 8 bits, tile ram_word modelled from its structure) ---')
    word_nand = 4 + 8 * 6
    word_dff = 8
    print(f'per word: {word_nand} NAND + {word_dff} DFF;  x32: {32 * word_nand} NAND + {32 * word_dff} DFF')
    ext_pins_per_word = 1 + 1 + 2 + 8 + 8          # i0, i1, i2 (2 pads), i3..i10, i11..i18
    print(f'external pad connections per word: {ext_pins_per_word};  total {32 * ext_pins_per_word}')
    print('  8 data buses x 32 words, 8 write-select nets x 4 words, 8 read-select nets x 4 words,')
    print('  4 low-select nets x 8 words (2 pads each), and 31 x 8 word-to-word chain links:')
    print('  all described by the chain rules (bcast / pick / prev), i.e. rule-generated.')
    tile_internal = {'g0': 8, 'g1': 8, 'g3': 8}    # fan-out inside one word
    print(f'  in-word nets with fan-out 8: {sorted(tile_internal)}; per-bit nets fan-out 1-2')


if __name__ == '__main__':
    main(sys.argv[1])
