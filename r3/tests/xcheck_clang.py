#!/usr/bin/env python3
"""xcheck_clang.py [N] -- cross-check rvemu.py against clang.  Random self-contained C programs are compiled for rv32ec (clang, ld.lld),
run on the model, and the checksum they store at 0x80 is compared with the same program compiled and run natively.
Also exercises the compressed encodings clang chooses (-Os) and, with -mno-relax / no C (-march=rv32e), the plain 32-bit forms."""
import os, random, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools')]
import rvemu

LD = '''ENTRY(_start)
SECTIONS { . = 0x4000; .text : { *(.text.start) *(.text*) } .rodata : { *(.rodata*) } /DISCARD/ : { *(.comment) *(.riscv.attributes) *(.eh_frame) }
 .bss 0x50 (NOLOAD) : { *(.bss*) *(COMMON) } }
'''
START = '''.section .text.start
.globl _start
_start: li sp, 256
 call main
 j .
'''

def gen(rng, n=60):
    ops = ['+', '-', '&', '|', '^']
    L = ['#include <stdint.h>', 'volatile uint32_t *const OUT = (volatile uint32_t *)0x80;', '__attribute__((noinline)) uint32_t f(uint32_t a, uint32_t b, int32_t c, uint16_t d, uint8_t e) {',
         ' uint32_t x = a ^ 0x9E3779B9u; int32_t y = c; uint16_t h = d; uint8_t q = e; uint32_t s = b; int16_t t = (int16_t)d;']
    for i in range(n):
        k = rng.randrange(14)
        if k == 0: L.append(f' x = x {rng.choice(ops)} (s {rng.choice(ops)} {rng.randrange(1<<32)}u);')
        elif k == 1: L.append(f' y = y {rng.choice(ops)} (int32_t)(x >> {rng.randrange(32)});')
        elif k == 2: L.append(f' s = (s << {rng.randrange(32)}) {rng.choice(ops)} (x >> {rng.randrange(32)});')
        elif k == 3: L.append(f' y = (y >> {rng.randrange(32)}) {rng.choice(ops)} {rng.randrange(-2048, 2048)};')
        elif k == 4: L.append(f' h = (uint16_t)(h {rng.choice(ops)} (uint16_t)(x >> {rng.randrange(17)}));')
        elif k == 5: L.append(f' q = (uint8_t)(q {rng.choice(ops)} (uint8_t)(s >> {rng.randrange(25)}));')
        elif k == 6: L.append(f' t = (int16_t)(t {rng.choice(ops)} (int16_t)(y >> {rng.randrange(16)}));')
        elif k == 7: L.append(f' if ((int32_t)x < y) s += h; else x -= q;')
        elif k == 8: L.append(f' if (x < s) y ^= t; else s = ~s;')
        elif k == 9: L.append(f' x += (x == s) + (y != (int32_t)x) + (uint32_t)(y < {rng.randrange(-100, 100)}) ;')
        elif k == 10: L.append(f' for (uint8_t i = 0; i < {rng.randrange(1, 6)}; i++) {{ x = (x << 1) ^ (x >> 31) ^ i; s += x; }}')
        elif k == 11: L.append(f' {{ volatile uint8_t buf[6]; buf[0] = q; buf[1] = (uint8_t)h; buf[2] = (uint8_t)(h >> 8); buf[3] = (uint8_t)x; buf[4] = (uint8_t)t; buf[5] = (uint8_t)(t >> 8); x += *(volatile uint16_t *)&buf[0]; y += (int8_t)buf[3] + *(volatile int16_t *)&buf[4]; }}')
        elif k == 12: L.append(f' x = (x >> {rng.randrange(1, 32)}) | (x << {rng.randrange(1, 32)});')
        else: L.append(f' y = (int32_t)(((int64_t)0) + (int32_t)(x & 0x7FFFFFF) - (int32_t)(s >> 5));')
    L.append(' return x ^ s ^ (uint32_t)y ^ ((uint32_t)h << 8) ^ q ^ ((uint32_t)(int32_t)t << 3);\n}')
    L.append('int main(void) { uint32_t r = 0; ')
    for _ in range(4): L.append(f' r = r * 0 + f(r ^ {rng.randrange(1<<32)}u, {rng.randrange(1<<32)}u, {rng.randrange(-2**31, 2**31)}, {rng.randrange(1<<16)}, {rng.randrange(256)}) + r;')
    L.append(' *OUT = r; return 0; }')
    return '\n'.join(L)

def run(seed, march, opt, tmp):
    rng = random.Random(seed); src = gen(rng)
    c, o, e, b = (os.path.join(tmp, x) for x in ('t.c', 't.o', 't.elf', 't.bin'))
    open(c, 'w').write(src); open(os.path.join(tmp, 's.S'), 'w').write(START); open(os.path.join(tmp, 'l.ld'), 'w').write(LD)
    base = ['clang', '--target=riscv32', f'-march={march}', '-mabi=ilp32e', opt, '-ffreestanding', '-fno-pic', '-mno-relax', '-nostdlib', '-fno-builtin', '-w']
    subprocess.run(base + ['-c', c, '-o', o], check=True)
    subprocess.run(base + ['-c', os.path.join(tmp, 's.S'), '-o', os.path.join(tmp, 's.o')], check=True)
    subprocess.run(['ld.lld', '-T', os.path.join(tmp, 'l.ld'), os.path.join(tmp, 's.o'), o, '-o', e], check=True)
    subprocess.run(['llvm-objcopy', '-O', 'binary', e, b], check=True)
    rom = open(b, 'rb').read()
    m = rvemu.Machine(rom, 256); m.run(10**7)
    got = m.rd(0x80, 4)
    # native
    nsrc = src.replace('volatile uint32_t *const OUT = (volatile uint32_t *)0x80;', 'uint32_t OUTV; uint32_t *const OUT = &OUTV;').replace('int main(void)', 'int main2(void)')
    nsrc = '#include <stdio.h>\n' + nsrc + '\nint main(void){ main2(); printf("%u\\n", OUTV); return 0; }\n'
    open(os.path.join(tmp, 'n.c'), 'w').write(nsrc)
    subprocess.run(['clang', '-O0', '-w', '-o', os.path.join(tmp, 'n'), os.path.join(tmp, 'n.c')], check=True)
    want = int(subprocess.run([os.path.join(tmp, 'n')], capture_output=True, text=True, check=True).stdout)
    return got, want, m, len(rom)

if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    bad = 0; tot = 0; comp = 0
    with tempfile.TemporaryDirectory() as tmp:
        for seed in range(n):
            for march, opt in (('rv32ec', '-Os'), ('rv32e', '-O1'), ('rv32ec', '-O1')):
                try: got, want, m, ln = run(seed, march, opt, tmp)
                except rvemu.Illegal as ex: print('seed', seed, march, opt, 'ILLEGAL', ex); bad += 1; continue
                tot += 1
                if got != want: bad += 1; print('seed', seed, march, opt, 'MISMATCH', hex(got), hex(want))
    print(f'{tot} programs, {bad} failures')
    sys.exit(1 if bad else 0)
