#!/usr/bin/env python3
"""run_builder.py OUTDIR HD -- run the assembled Replicator 3 builder on the instruction-level RV32EC model (rvemu) and compare the arm
commands it issues with the reference flattener (tools/ref_flatten.commands, offset CHILD_DX)."""
import os, sys, time, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, '..', 'tools'), HERE]
import rvemu, hd as H, ref_flatten as RF


def s16(v): return v - 65536 if v >= 32768 else v


def run(outdir, maxn):
    rom = open(os.path.join(outdir, 'rom.bin'), 'rb').read()
    m = rvemu.Machine(rom, 256)
    hi = [0]; bad = []
    ow = m.wb
    def wb(a, v):
        a &= 0x7FFF
        if (a >> 4) == 0x3FF and (a & 15) not in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15): bad.append(('arm reg', a & 15))
        elif a < 256: hi[0] = max(hi[0], a)
        elif a < 0x3FF0: bad.append(('write outside RAM', a))
        ow(a, v)
    m.wb = wb
    t0 = time.time()
    m.run(maxn)
    return m, rom, time.time() - t0, hi[0], bad


def decode(armlog):
    regs = [0] * 16; cmds = []
    for r, v in armlog:
        regs[r] = v
        if r != 15: continue
        w = lambda i: regs[i] | regs[i + 1] << 8
        ax, ay, bx, by = s16(w(0)), s16(w(2)), s16(w(4)), s16(w(6))
        if v == 1: cmds.append(('place', regs[8], ax, ay, regs[9], regs[10]))
        elif v == 3: cmds.append(('rom', ax, ay, w(4), regs[10]))
        elif v == 4: cmds.append(('track', regs[10], ax, ay, bx, by))
        elif v == 5: cmds.append(('via', ax, ay))
        else: cmds.append(('?', v))
    return cmds


def norm(c):
    if c[0] == 'track':
        a, b = (c[2], c[3]), (c[4], c[5])
        if b < a: a, b = b, a
        return ('track', c[1]) + a + b
    if c[0] == 'place' and c[1] in (0, 1): return ('place', c[1], c[2], c[3])
    return tuple(c)


if __name__ == '__main__':
    outdir, hdf = sys.argv[1], sys.argv[2]
    maxn = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 10**9
    m, rom, dt, hi, bad = run(outdir, maxn)
    print(f'halted={m.halted}: {m.icount} instructions, {dt:.0f}s; RAM high-water {hi:#x}; bad writes {len(bad)} {bad[:3]}')
    got = decode(m.armlog)
    hd = H.read(open(hdf).read()); f = RF.flatten(hd)
    ref = RF.commands(f, rom, RF.CHILD_DX)
    print('got', dict(collections.Counter(c[0] for c in got)), 'ref', dict(collections.Counter(c[0] for c in ref)))
    g, r = collections.Counter(map(norm, got)), collections.Counter(map(norm, ref))
    miss, extra = r - g, g - r
    print(f'missing {sum(miss.values())}  extra {sum(extra.values())}')
    for c in list(miss)[:8]: print('  missing', c)
    for c in list(extra)[:8]: print('  extra  ', c)
    kinds = [c[0] for c in got]
    last_rom = max((i for i, k in enumerate(kinds) if k == 'rom'), default=-1)
    first_wire = min((i for i, k in enumerate(kinds) if k in ('track', 'via')), default=10**9)
    print('ROM before wires:', last_rom < first_wire)
    ok = m.halted and not miss and not extra and not bad and last_rom < first_wire
    print('RESULT', 'PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)
