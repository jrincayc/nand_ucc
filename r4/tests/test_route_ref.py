#!/usr/bin/env python3
"""test_route_ref.py -- tools/route_ref.py (array-style integer router) must give exactly the golden command list (rowchan.layout + lay.commands) for the old and new g1."""
import hashlib, os, random, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools')]
import lay, place_ref, route_ref
bad = 0
for name, g in (('hd/cpu_g1.nl', 'cpu_g1_hd'), ('hd/m18/cpu_g1.nl', 'cpu_g1_m18')):
    nl = lay.read_nl(os.path.join(HERE, '..', name)); N = len(nl.nodes)
    perm = list(range(N)); random.Random(12).shuffle(perm)
    def rn(t):
        m = re.match(r'^n(\d+)(.*)$', t); return f'n{perm[int(m.group(1))]}{m.group(2)}' if m else t
    new = [None] * N
    for k, (kind, ins) in enumerate(nl.nodes): new[perm[k]] = (kind, [rn(t) for t in ins])
    nl.nodes = new; nl.ports = [(n, rn(t)) for n, t in nl.ports]
    cmds, info = route_ref.route(nl, place_ref.order(nl, seed=1), 22, 14)
    text = '\n'.join(' '.join(str(x) for x in c) for c in cmds) + '\n'
    gold = open(os.path.join(HERE, '..', 'golden', g + '.cmds')).read()
    ok = text == gold; bad += 0 if ok else 1
    print(g, 'commands', len(cmds), 'intervals', info['NI'], 'board', info['W'], 'x', info['H'], 'IDENTICAL to golden' if ok else 'MISMATCH')
    if not ok:
        a = text.split('\n'); b = gold.split('\n')
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y: print('first difference at command', i, x, '|', y); break
print('RESULT', 'PASS' if not bad else 'FAIL'); sys.exit(1 if bad else 0)
