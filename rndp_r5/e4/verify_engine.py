#!/usr/bin/env python3
"""verify_engine.py -- lockstep check: gate-level engine netlist (engsim) vs engine_model arm-write sequence."""
import subprocess, sys
import spec as S, pattern as PT, engine_model as EM, engine_net as EN
exec(open('test_model.py').read().split("# the plane content")[0].split("X0, RX, xoff")[0]) if False else None
import importlib
src = open('test_model.py').read().split("# the plane content")[0]
ns = {}; exec(src, ns); rows = ns['rows']; W = len(rows)
writes, cyc = EM.run(rows)
N, sp = EN.build(W); info = EN.export_nl(N, sp, '/tmp/eng.nl'); print(info['nand'], info['dff'])
open('/tmp/rows.txt', 'w').write('\n'.join(str(sum(b << i for i, b in enumerate(S.pack(**r)))) for r in rows))
subprocess.run(['r5/e4/engsim/engsim' if False else './engsim/engsim', '/tmp/eng.nl', '/tmp/rows.txt', '--cycles', str(cyc + 100), '--armlog', '/tmp/arm.log'], check=True)
got = [tuple(map(int, l.split())) for l in open('/tmp/arm.log')]
print('model', len(writes), 'gate', len(got), 'equal', got == writes)
if got != writes:
    for i, (a, b) in enumerate(zip(got, writes)):
        if a != b: print('first diff', i, a, b); break
