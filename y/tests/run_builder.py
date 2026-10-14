"""run_builder.py -- assemble builder.asm + macros.asm + an HD data file, run the image on the behavioural Hack-vN model, decode the arm
register writes into PLACE / PROGRAM_ROM / WIRE commands and compare with the reference flattener (V5)."""
import os, sys, subprocess, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
for d in ('tools', 'isa', 'tests', '.'):
    sys.path.insert(0, os.path.join(HERE, '..', d))
import common, isahack as H
import hd as HDM, ref_flatten as RF
from machine_lockstep import MR

KIND = {0: 'nand', 1: 'dff', 2: 'rom', 3: 'arm'}


def assemble(files, outdir):
    r = subprocess.run([sys.executable, os.path.join(HERE, '..', 'tools', 'asm.py'), '-o', outdir] + files, capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stdout + r.stderr)
    return open(os.path.join(outdir, 'rom.bin'), 'rb').read()


def run_model(image, ramn=256, max_instr=60_000_000, report=2_000_000):
    m = MR(ramn); m.load_rom(0, image)
    cpu = H.CPU(m); n = 0; t0 = time.time()
    while n < max_instr:
        if not cpu.step(): break
        n += 1
        if report and n % report == 0: print(f'   {n/1e6:.0f}M instr, {len(m.armlog)} arm writes, {time.time()-t0:.0f}s', flush=True)
    return m, n


def decode_arm(armlog):
    regs = [0] * 16; cmds = []
    s16 = lambda lo, hi: (lo | hi << 8) - (65536 if hi & 128 else 0)
    for r, v in armlog:
        regs[r] = v
        if r != 15: continue
        ax, ay = s16(regs[0], regs[1]), s16(regs[2], regs[3])
        if v == 1: cmds.append(('place', KIND[regs[8]], ax, ay))
        elif v == 2: cmds.append(('wire', ax, ay, s16(regs[4], regs[5]), s16(regs[6], regs[7])))
        elif v == 3: cmds.append(('rom', ax, ay, regs[4] | regs[5] << 8, regs[10]))
        else: raise AssertionError(f'bad CMD {v}')
    return cmds


def compare(cmds, ref):
    a, b = set(cmds), set(ref)
    ok = len(cmds) == len(a) and a == b
    print(f'commands: built {len(cmds)} ({len(a)} distinct), reference {len(ref)}; missing {len(b - a)}, extra {len(a - b)}')
    for x in list(b - a)[:5]: print('   missing', x)
    for x in list(a - b)[:5]: print('   extra  ', x)
    # order constraints of RNDW (spec section 7)
    kinds = [c[0] for c in cmds]
    last_place = max(i for i, k in enumerate(kinds) if k == 'place'); first_rom = kinds.index('rom'); last_rom = len(kinds) - 1 - kinds[::-1].index('rom')
    first_wire = kinds.index('wire')
    order = last_place < first_rom and last_rom < first_wire
    print(f'order: all PLACE before PROGRAM_ROM, all PROGRAM_ROM before any WIRE: {order}')
    tail = cmds[-3:] == ref[-3:]
    print(f'last three commands (EN wire, then the two RUN wires) identical to the reference: {tail}')
    return ok and order and tail


if __name__ == '__main__':
    hdfile, datafile = sys.argv[1], sys.argv[2]
    out = tempfile.mkdtemp(); image = assemble([os.path.join(HERE, '..', 'src', 'macros.asm'), os.path.join(HERE, '..', 'src', 'builder.asm'), datafile], out)
    print('image', len(image), 'bytes')
    hd = HDM.read(open(hdfile).read()); f = RF.flatten(hd)
    ref = RF.commands(f, image, 0, RF.STRIDE)
    m, n = run_model(image)
    print('instructions', n, 'arm writes', len(m.armlog))
    cmds = decode_arm(m.armlog)
    print('PASS' if compare(cmds, ref) else 'FAIL')
