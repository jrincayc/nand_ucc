"""Cross-check the new netlists in the Rust RNDW simulator against nandgen.Sim with random inputs."""
import os, random, subprocess, sys
sys.path.insert(0, '/home/claude/ref')
import gen_vectors as gv
from nl_hackvn import build_hackvn
from nl_acc8 import build_acc8
os.makedirs('xcheck', exist_ok=True)
rc = 0
for name, b in (('hackvn', build_hackvn), ('acc8', build_acc8)):
    c = b(2)
    open(f'xcheck/{name}.netlist.txt', 'w').write(c.to_text())
    open(f'xcheck/{name}.vec', 'w').write(gv.trace(c, 4000, random.Random(name)))
    r = subprocess.run(['/home/claude/rndw/target/release/rndw', '--netlist', f'xcheck/{name}.netlist.txt',
                        '--vectors', f'xcheck/{name}.vec'], capture_output=True, text=True)
    print(name, r.stdout.strip().splitlines()[-3:], r.stderr.strip()[-200:])
    rc |= r.returncode
sys.exit(rc)
