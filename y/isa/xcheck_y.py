"""Cross-check the AB-wide netlists in the Rust RNDW simulator against nandgen.Sim with random inputs.
RNDW env var = path of the rndw binary; GENVEC = directory containing gen_vectors.py."""
import os, random, subprocess, sys
sys.path.insert(0, os.environ.get('GENVEC', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'rndw', 'tools')))
import gen_vectors as gv
from nl_hackvn import build_hackvn, AB
from nl_core import build_core
rndw = os.environ.get('RNDW', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'rndw', 'target', 'release', 'rndw'))
os.makedirs('xcheck', exist_ok=True); rc = 0
for name, c in ((f'hackvn_ab{AB}', build_hackvn(2)), (f'core_ab{AB}_r5', build_core(2, 5)), (f'core_ab{AB}_r5_L0', build_core(0, 5))):
    open(f'xcheck/{name}.netlist.txt', 'w').write(c.to_text())
    open(f'xcheck/{name}.vec', 'w').write(gv.trace(c, 4000, random.Random(name)))
    r = subprocess.run([rndw, '--netlist', f'xcheck/{name}.netlist.txt', '--vectors', f'xcheck/{name}.vec'], capture_output=True, text=True)
    print(name, 'NAND', len(c.gates), 'DFF', c.n_dff, '|', ' '.join(r.stdout.strip().splitlines()[-2:]), r.stderr.strip()[-200:])
    rc |= r.returncode
sys.exit(rc)
