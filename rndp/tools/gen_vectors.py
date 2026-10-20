"""netlists + random-input traces from nandgen.Sim (same protocol as nandgen/rndw/tools/gen_vectors.py).
usage: python3 gen_vectors.py OUTDIR [ticks] [seed]   (designs overridable: DESIGNS env = comma list)"""
import os, random, sys
import nandgen as ng


def trace(c, ticks, rng):
    sim = ng.Sim(c)
    reset = c.buses['reset'][0] if 'reset' in c.buses else None
    watch = []
    for name in sorted(c.outs):
        watch += c.outs[name]
    watch += list(range(c.n_in, c.n_in + c.n_dff))
    lines = ['rndw-vectors 1', f'n_in {c.n_in}', 'watch ' + ' '.join(map(str, watch))]
    for _ in range(ticks):
        bits = []
        for w in range(c.n_in):
            b = rng.getrandbits(1)
            if w == reset:
                b = 1 if rng.random() < 1 / 32 else 0
            sim.v[w] = b
            bits.append(b)
        sim.eval()
        outb = [sim.v[w] for w in watch]
        lines.append('t ' + ''.join(map(str, bits)) + ' ' + ''.join(map(str, outb)))
        sim.tick()
    return '\n'.join(lines) + '\n'


DESIGNS = {
    'alu_w8_l2': lambda: ng.build_alu(2, 8),
    'cpu_w8_aw12_l2': lambda: ng.build_cpu(2, 8, 12),
    'cpu_serial_w8_aw12_k4_l2': lambda: ng.build_cpu_serial(2, 8, 12, 4),
    'cpu_serial_w8_aw12_k4_l0': lambda: ng.build_cpu_serial(0, 8, 12, 4),
    'cpu_serial_w8_aw8_k2_l1': lambda: ng.build_cpu_serial(1, 8, 8, 2),
    'ram_a4_w8_l2': lambda: ng.build_ram(2, 4, 8),
    'machine_w8_aw6_k4_l2': lambda: ng.build_machine(2, 8, 6, 4),
}

if __name__ == '__main__':
    out = sys.argv[1]
    ticks = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    os.makedirs(out, exist_ok=True)
    for name, build in DESIGNS.items():
        c = build()
        rng = random.Random(f'{seed}-{name}')
        open(os.path.join(out, name + '.netlist.txt'), 'w').write(c.to_text())
        open(os.path.join(out, name + '.vec'), 'w').write(trace(c, ticks, rng))
        print(f'{name}: in {c.n_in} dff {c.n_dff} gates {len(c.gates)} ticks {ticks}')
