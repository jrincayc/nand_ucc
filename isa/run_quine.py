"""Run the quine in the RNDW world: the driver builds generation 1 from the reference commands (with the real
builder ROM image); generation 1 then runs the builder program and builds generation 2, which builds 3, ...
usage: run_quine.py AB STEPS [--resume STATE] """
import sys, os, subprocess, time
import common
import engine, machine_row as MR, builder as B
from script_world import to_script, reg_writes

import os as _os
RNDW = _os.environ.get('RNDW', _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'rndw', 'target', 'release', 'rndw'))
OUT = 'world_out'

def seed(ab):
    a, plan, V, sl = engine.make_program(ab)
    code = a.assemble()
    assert len(code) <= 4096, len(code)
    cmds = MR.commands(plan.R, plan.outs, code, 0, MR.STRIDE)
    return code, plan, cmds

def main():
    ab, steps = int(sys.argv[1]), int(sys.argv[2])
    os.makedirs(OUT, exist_ok=True)
    code, plan, cmds = seed(ab)
    nw = reg_writes(cmds)
    sf = f'{OUT}/quine_seed.script'; open(sf, 'w').write(to_script(cmds))
    args = [RNDW, '--width', '65536', '--height', '4096', '--save', f'{OUT}/quine_final.txt']
    if '--resume' in sys.argv:
        args += ['--world', sys.argv[sys.argv.index('--resume') + 1], '--steps', str(steps)]
    else:
        args += ['--script', sf, '--steps', str(nw + steps)]
    t = time.time()
    r = subprocess.run(args, capture_output=True, text=True)
    print(r.stdout[-1500:], r.stderr[-500:])
    print(f'wall {time.time()-t:.0f}s, script regwrites {nw}, ROM image {len(code)} B')

if __name__ == '__main__':
    main()
