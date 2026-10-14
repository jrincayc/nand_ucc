import subprocess, sys, random, os, time
import common, isahack
from nl_machine import build_machine
from script_world import commands, to_script, reg_writes
from verify_world import parse

import os as _os
RNDW = _os.environ.get('RNDW', _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'rndw', 'target', 'release', 'rndw'))
TICKS = {'K1': 25600, 'K2': 28200, 'K3': 7700, 'K4': 87000}

def main(kernel, ram_abits=10, seed=1):
    c = build_machine(2, ram_abits)
    rng = random.Random(f'{seed}-{kernel}')
    code = isahack.assemble(kernel, common.P)
    m = common.Machine(); m.load_rom(0, code)
    check = common.prepare(kernel, m, rng)
    cmds, L = commands(c, bytes(m.rom))
    nw = reg_writes(cmds)
    written = set(); w0 = m.wr
    m.wr = lambda a, v: (written.add(a & 0x1FFF), w0(a, v))[1]
    ref = isahack.CPU(m)
    while ref.step(): pass
    m.written = written
    os.makedirs('world_out', exist_ok=True)
    sf, of = f'world_out/{kernel}_child.script', f'world_out/{kernel}_child_final.txt'
    open(sf, 'w').write(to_script(cmds))
    steps = nw + 20 + TICKS[kernel] + 100
    t = time.time()
    r = subprocess.run([RNDW, '--script', sf, '--steps', str(steps), '--save', of, '--width', '4096', '--height', '4096'],
                       capture_output=True, text=True)
    print(r.stdout[-700:], r.stderr[-300:])
    print(f'commands {len(cmds)}, register writes {nw}, run {time.time()-t:.0f}s')
    return c, m, of, L

if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 10)


def verify(kernel, ram_abits=10):
    c, m, of, L = main(kernel, ram_abits)
    parts, dff, rom, faults, tick = parse(of)
    off = 14                                           # driver arm + 13 sources come first
    mem = [w - c.n_in + off for w in c.outs['mem']]
    ram = bytearray(len(mem) // 8)
    for a in range(len(ram)):
        ram[a] = sum(((mem[8 * a + b] in dff) << b) for b in range(8))
    w = sorted(a for a in m.written if a < len(ram))
    same = all(ram[a] == m.ram[a] for a in w)
    untouched = [ram[a] for a in range(len(ram)) if a not in m.written]
    ok = faults == 0 and same
    msgs = [f'faults={faults} tick={tick} RAM: {len(w)} cells written by the program {"match" if same else "DIFFER"}; '
            f'{len(untouched)} untouched cells hold {sorted(set(untouched))}']
    if kernel == 'K4':
        new = parts[off + len(L['parts']) + 0:]
        P = common.P
        exp = [(1, P['K4_X0'] + 24 * (w & 63) + 3 * j, P['K4_Y0'] + 4 * (w >> 6)) for w in range(P['K4_NW']) for j in range(8)]
        ok &= new == exp; msgs.append(f'{len(new)} placed, {"match" if new == exp else "MISMATCH"}')
    print(kernel, 'PASS' if ok else 'FAIL', '; '.join(msgs))
    return ok
