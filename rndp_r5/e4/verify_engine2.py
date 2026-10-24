#!/usr/bin/env python3
"""verify_engine2.py -- gate-level engine2 (engsim) vs engine2_model on the test ring of test2_model."""
import subprocess, sys
sys.argv = [sys.argv[0]] + (sys.argv[1:3] if len(sys.argv) > 2 else [sys.argv[1] if len(sys.argv) > 1 else '60'])
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    import test3_model as T
import engine2_net as E2, engine_net as EN, engine2_model as EM
rows, M = T.rows, T.M
writes, cyc = EM.run(rows, M)
N, sp = E2.build(len(rows), M=M); info = EN.export_nl(N, sp, '/tmp/eng2.nl'); print('NAND', info['nand'], 'DFF', info['dff'])
open('/tmp/rows2.txt', 'w').write('\n'.join(str(w) for w in rows))
subprocess.run(['./engsim/engsim', '/tmp/eng2.nl', '/tmp/rows2.txt', '--cycles', str(cyc + 100), '--armlog', '/tmp/arm2.log'], check=True)
got = [tuple(map(int, l.split())) for l in open('/tmp/arm2.log')]
print('model', len(writes), 'gate', len(got), 'equal', got == writes)
if got != writes:
    for i, (a, b) in enumerate(zip(got, writes)):
        if a != b: print('first diff', i, a, b); break
