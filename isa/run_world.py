import subprocess, sys, random, os, time, re
import common, isahack, lockstep
from nl_machine import build_machine
from export_world import export

import os as _os
RNDW = _os.environ.get('RNDW', _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'rndw', 'target', 'release', 'rndw'))
ticks_needed = {'K1': 25600, 'K2': 28200, 'K3': 7700, 'K4': 87000}

def main(kernel, ram_abits=10, seed=1, extra=100):
    c = build_machine(2, ram_abits)
    rng = random.Random(f'{seed}-{kernel}')
    code = isahack.assemble(kernel, common.P)
    m = common.Machine(); m.load_rom(0, code)
    check = common.prepare(kernel, m, rng)
    rom = bytes(m.rom)
    pre = {a: v for a, v in enumerate(m.ram[:1 << ram_abits]) if v}
    text, meta = export(c, rom, pre)
    os.makedirs('world_out', exist_ok=True)
    seedf, outf = f'world_out/{kernel}_seed.txt', f'world_out/{kernel}_final.txt'
    open(seedf, 'w').write(text)
    # reference result
    ref = isahack.CPU(m)
    while ref.step(): pass
    t = time.time()
    steps = ticks_needed[kernel] + extra
    r = subprocess.run([RNDW, '--world', seedf, '--steps', str(steps), '--save', outf], capture_output=True, text=True)
    print(r.stdout[-600:], r.stderr[-300:])
    print(f'rndw run {time.time()-t:.0f}s')
    return c, meta, m, outf

if __name__ == '__main__':
    main(sys.argv[1])
