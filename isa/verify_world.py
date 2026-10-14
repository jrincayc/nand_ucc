import sys, re
import common
from run_world import main

def parse(path):
    parts, dff, rom, faults, tick = [], set(), {}, None, None
    for l in open(path):
        t = l.split()
        if not t: continue
        if t[0] == 'part': parts.append((int(t[2]), int(t[3]), int(t[4])))
        elif t[0] == 'dff': dff.add(int(t[1]))
        elif t[0] == 'rom': rom.setdefault(int(t[1]), {})[int(t[2])] = int(t[3])
        elif t[0] == 'faults': faults = int(t[1])
        elif t[0] == 'tick': tick = int(t[1])
    return parts, dff, rom, faults, tick

def verify(kernel):
    c, meta, m, outf = main(kernel)
    parts, dff, rom, faults, tick = parse(outf)
    ok = faults == 0
    msgs = [f'faults={faults} tick={tick}']
    mem = meta['mem_ids']
    ram = bytearray(len(mem) // 8)
    for a in range(len(ram)):
        ram[a] = sum(((mem[8 * a + b] in dff) << b) for b in range(8))
    if bytes(ram) != bytes(m.ram[:len(ram)]):
        bad = [a for a in range(len(ram)) if ram[a] != m.ram[a]]
        ok = False; msgs.append(f'RAM differs at {len(bad)} cells, first {bad[:5]}')
    else:
        msgs.append(f'RAM matches reference ({len(ram)} bytes)')
    if kernel == 'K1':
        child = rom.get(meta['child_id'], {})
        exp = {p: m.peek(common.ROM_BASE + p) for p in range(common.P['K1_N']) if m.peek(common.ROM_BASE + p)}
        if child != exp: ok = False; msgs.append(f'child ROM differs: {len(child)} vs {len(exp)} nonzero cells')
        else: msgs.append(f'child ROM holds the first {common.P["K1_N"]} ROM bytes ({len(exp)} nonzero cells)')
    if kernel == 'K4':
        new = parts[meta['n_seed_parts']:]
        P = common.P
        exp = [(1, P['K4_X0'] + 24 * (w & 63) + 3 * j, P['K4_Y0'] + 4 * (w >> 6)) for w in range(P['K4_NW']) for j in range(8)]
        if new != exp: ok = False; msgs.append(f'placed {len(new)} parts, expected {len(exp)}; first diff {next((i for i,(a,b) in enumerate(zip(new,exp)) if a!=b), None)}')
        else: msgs.append(f'{len(new)} DFFs placed at the expected coordinates')
    print(kernel, 'PASS' if ok else 'FAIL', '; '.join(msgs))
    return ok

if __name__ == '__main__':
    sys.exit(0 if all([verify(k) for k in (sys.argv[1:] or common.KERNELS)]) else 1)
