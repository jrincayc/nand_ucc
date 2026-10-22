#!/usr/bin/env python3
"""lockstep_rtl.py -- run the microcoded CPU model (cpu_rtl) against rvemu on clang-compiled random C programs and on random instruction streams.
After every instruction compares pc, x1..x15, the user RAM (0x50..0xFF) and the arm-window writes."""
import os, random, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools'), HERE]
import rvemu, cpu_rtl, xcheck_clang as xc


def lockstep(rom, maxinstr=200000, label=''):
    m = rvemu.Machine(rom); c = cpu_rtl.CPU(rom); nt = 0
    while not m.halted and m.icount < maxinstr:
        ins, comp = m.step()
        nt += cpu_rtl.run_until_fetch(c)
        pc = c.ram[0x40] | c.ram[0x41] << 8
        bad = []
        if pc != ((rvemu.ROM_BASE | m.pc) & 0xFFFF): bad.append(f'pc {pc:#x} vs {(rvemu.ROM_BASE | m.pc) & 0xFFFF:#x}')
        for i in range(1, 16):
            if c.ram[4 * i:4 * i + 4] != bytes(m.ram[4 * i:4 * i + 4]): bad.append(f'x{i}: {bytes(c.ram[4*i:4*i+4]).hex()} vs {bytes(m.ram[4*i:4*i+4]).hex()}')
        if c.ram[0x50:] != m.ram[0x50:]: bad.append('ram differs at ' + hex(0x50 + next(i for i in range(len(c.ram) - 0x50) if c.ram[0x50 + i] != m.ram[0x50 + i])))
        if c.arm != m.armlog: bad.append(f'arm {c.arm[-2:]} vs {m.armlog[-2:]}')
        if bad:
            return f'{label}: instr {m.icount} ({ins:#x}{" c" if comp else ""}) at pc {rvemu.ROM_BASE + (m.pc):#x}: ' + '; '.join(bad)
    return None, m.icount, nt


def clang_rom(seed, march, opt, tmp):
    rng = random.Random(seed); src = xc.gen(rng)
    c, o, e, b = (os.path.join(tmp, x) for x in ('t.c', 't.o', 't.elf', 't.bin'))
    open(c, 'w').write(src); open(os.path.join(tmp, 's.S'), 'w').write(xc.START); open(os.path.join(tmp, 'l.ld'), 'w').write(xc.LD)
    base = ['clang', '--target=riscv32', f'-march={march}', '-mabi=ilp32e', opt, '-ffreestanding', '-fno-pic', '-mno-relax', '-nostdlib', '-fno-builtin', '-w']
    subprocess.run(base + ['-c', c, '-o', o], check=True); subprocess.run(base + ['-c', os.path.join(tmp, 's.S'), '-o', os.path.join(tmp, 's.o')], check=True)
    subprocess.run(['ld.lld', '-T', os.path.join(tmp, 'l.ld'), os.path.join(tmp, 's.o'), o, '-o', e], check=True)
    subprocess.run(['llvm-objcopy', '-O', 'binary', e, b], check=True)
    return open(b, 'rb').read()


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        for seed in range(n):
            for march, opt in (('rv32ec', '-Os'), ('rv32e', '-O1')):
                r = lockstep(clang_rom(seed, march, opt, tmp), label=f'clang seed {seed} {march} {opt}')
                if isinstance(r, str): print(r); bad += 1
                else: print(f'seed {seed} {march} {opt}: {r[1]} instructions, {r[2]} ticks ({r[2] / r[1]:.1f}/instr)')
    sys.exit(1 if bad else 0)
