#!/usr/bin/env python3
"""run_builder.py -- run the assembled Replicator 1 builder on the behavioural machine (ramn = 128 bytes of RAM) and compare the
arm commands it issues with the reference flattener (tools/ref_flatten.commands, offset CHILD_DX).
usage: HACK_AB=15 python3 tests/run_builder.py OUTDIR HD [--max N]"""
import os, sys, time, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, '..', 'tools'), os.path.join(HERE, '..', 'isa'), HERE]
import common, isahack, machine_model, hd as H, ref_flatten as RF


class M(machine_model.MR):
    def __init__(self, ramn):
        super().__init__(ramn); self.hi = 0; self.bad = []
    def wr(self, a, v):
        a &= common.AMASK
        if a < common.ARM_BASE:
            if a >= self.ramn: self.bad.append(a)
            else: self.hi = max(self.hi, a)
        super().wr(a, v)


def s16(v): return v - 65536 if v >= 32768 else v


def run(outdir, maxn):
    rom = open(os.path.join(outdir, 'rom.bin'), 'rb').read()
    m = M(128); m.load_rom(0, rom)
    cpu = isahack.CPU(m)
    t0 = time.time(); n = 0
    while n < maxn:
        n += 1
        if not cpu.step(): break
        if n % 5000000 == 0: print(f'  {n/1e6:.0f}M instr, {len(m.armlog)} arm writes, {time.time()-t0:.0f}s', flush=True)
    else:
        print('STEP LIMIT'); 
    return m, cpu, n, rom, time.time() - t0


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
    if c[0] == 'place' and c[1] in (0, 1): return ('place', c[1], c[2], c[3])   # angle / val are not part of a NAND/DFF
    return tuple(c)


if __name__ == '__main__':
    outdir, hdf = sys.argv[1], sys.argv[2]
    maxn = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 10**9
    m, cpu, n, rom, dt = run(outdir, maxn)
    print(f'halted={n < maxn}: {n} instructions, {m.accesses} memory accesses, {dt:.0f}s; RAM high-water {m.hi} ({m.hi+1} bytes); out-of-RAM writes {len(m.bad)}')
    got = decode(m.armlog)
    hd = H.read(open(hdf).read()); f = RF.flatten(hd)
    ref = RF.commands(f, rom, RF.CHILD_DX)
    print('got', collections.Counter(c[0] for c in got), 'ref', collections.Counter(c[0] for c in ref))
    g, r = collections.Counter(map(norm, got)), collections.Counter(map(norm, ref))
    miss, extra = r - g, g - r
    print(f'missing {sum(miss.values())}  extra {sum(extra.values())}')
    for c in list(miss)[:8]: print('  missing', c)
    for c in list(extra)[:8]: print('  extra  ', c)
    # ordering: ROM programmed before any wire; RUN sinks last, after EN
    kinds = [c[0] for c in got]
    last_rom = max((i for i, k in enumerate(kinds) if k == 'rom'), default=-1)
    first_wire = min((i for i, k in enumerate(kinds) if k in ('track', 'via')), default=10**9)
    print('ROM before wires:', last_rom < first_wire)
    ok = not miss and not extra and not m.bad and last_rom < first_wire
    print('RESULT', 'PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)
