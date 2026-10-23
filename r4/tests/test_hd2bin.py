#!/usr/bin/env python3
"""test_hd2bin.py -- hd2bin.py on the seed HD (cpu_mod.hd) and the improved HD (cpu_mod_improved.hd): assemble the data, decode it with the independent decoder,
and compare with the HD objects (modules in slot form, body references, ports)."""
import os, sys, tempfile
os.environ.update(ROM_BITS='16', AB='18', RAM_BITS='18')
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools')]
import rvasm, hd2bin, hd as H
bad = 0
for name in ('cpu_mod.hd', 'cpu_mod_improved.hd'):
    h = H.read(open(os.path.join(HERE, '..', 'hd', 'm18', name)).read()); d = tempfile.mkdtemp()
    open(d + '/data.s', 'w').write(hd2bin.text(h))
    _, img = rvasm.assemble([d + '/data.s'], d + '/o')
    sym = {}
    for l in open(d + '/o/symbols.txt'):
        if '=' in l: k, v = l.split('='); sym[k.strip()] = int(v.strip(), 0)
    mods, body, ports = hd2bin.decode(bytes(img), sym, 1 << 18)
    ok = len(mods) == len(h.modules) and all(m == (x.n_in, x.n_out, x.gates, [o for o in x.outs]) for m, x in zip(mods, h.modules))
    e = hd2bin.encode(h)
    ok &= [list(b) for b in e['body']] == [[t] + r for t, r in body] and e['ports'] == ports
    ok &= len(body) == len(h.body) and len(ports) == len(h.ports)
    print(f'{name}: {len(mods)} modules, {len(body)} body instances, {len(ports)} ports, {len(img)} bytes of data:', 'decoded == HD' if ok else 'MISMATCH'); bad += not ok
print('RESULT', 'PASS' if not bad else 'FAIL'); sys.exit(bad)
