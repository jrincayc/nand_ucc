import subprocess, sys, random, os, time
import common, isahack
import machine_row as MR
from script_world import to_script, reg_writes
from verify_world import parse

import os as _os
RNDW = _os.environ.get('RNDW', _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'rndw', 'target', 'release', 'rndw'))
TICKS = {'K2': 28200, 'K4': 87000}

def run(kernel, ram_abits, seed=1):
    # keep the kernels' RAM buffers inside the small RAM
    common.P.update(K2_OUT=0x0038, K2_M=30, K3_VAL=0x0080)
    R, outs, core_end, c = MR.build(ram_abits)
    rng = random.Random(f'{seed}-{kernel}')
    m = common.Machine(); m.load_rom(0, isahack.assemble(kernel, common.P))
    common.prepare(kernel, m, rng)
    cmds = MR.commands(R, outs, bytes(m.rom))
    nw = reg_writes(cmds)
    written = set(); w0 = m.wr
    m.wr = lambda a, v: (written.add(a & 0x1FFF), w0(a, v))[1]
    ref = isahack.CPU(m)
    while ref.step(): pass
    os.makedirs('world_out', exist_ok=True)
    sf, of = f'world_out/row_{kernel}.script', f'world_out/row_{kernel}_final.txt'
    open(sf, 'w').write(to_script(cmds))
    t = time.time()
    r = subprocess.run([RNDW, '--script', sf, '--steps', str(nw + 20 + TICKS[kernel] + 100), '--save', of,
                        '--width', '65536', '--height', '4096'], capture_output=True, text=True)
    parts, dff, rom, faults, tick = parse(of)
    ram = bytearray(1 << ram_abits)
    for a in range(len(ram)):
        ram[a] = sum(((14 + R.q[a][b]) in dff) << b for b in range(8))
    wr = sorted(a for a in written if a < len(ram))
    same = all(ram[a] == m.ram[a] for a in wr)
    untouched = sorted(set(ram[a] for a in range(len(ram)) if a not in written))
    ok = faults == 0 and same
    msg = f'faults={faults} ticks={tick} nodes={len(R.kind)} cmds={len(cmds)} regwrites={nw}; {len(wr)} written cells {"match" if same else "DIFFER"}; untouched hold {untouched}; {time.time()-t:.0f}s'
    if kernel == 'K4':
        P = common.P
        new = parts[14 + len(R.kind) + 3:]
        ax, ay = [(x, y) for k, x, y in parts if k == 3][1]  # child arm origin (v0.5: offsets are relative to it)
        exp = [(1, ax + P['K4_X0'] + 24 * (w & 63) + 3 * j, ay + P['K4_Y0'] + 4 * (w >> 6)) for w in range(P['K4_NW']) for j in range(8)]
        ok &= new == exp; msg += f'; placed {len(new)} {"match" if new == exp else "MISMATCH"}'
    print(kernel, f'RAM {1<<ram_abits}B', 'PASS' if ok else 'FAIL', msg, flush=True)
    return ok

if __name__ == '__main__':
    ab = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    for k in (sys.argv[2:] or ['K2', 'K4']): run(k, ab)
