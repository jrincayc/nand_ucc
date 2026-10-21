#!/usr/bin/env python3
"""randprog.py -- random RV32EC instruction streams (assembled with rvasm) run in lockstep on cpu_rtl and rvemu.
usage: randprog.py [first_seed [count [n_instr]]]"""
import os, random, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools'), HERE]
import rvasm, lockstep_rtl

CONSTS = [0, 1, 2, 3, -1, -2, 0x7FFFFFFF, 0x80000000, 0x7FFFFFFE, 0x80000001, 0xFF, 0x100, 0xFFFF, 0x8000, 0x7F, 0x80, 255, 0xFFFFFF00, 0x12345678, 0xDEADBEEF]
RR = [f'x{i}' for i in range(1, 16) if i != 2]
RC = [f'x{i}' for i in range(8, 16)]


def gen(rng, n):
    L = []; lab = [0]
    def newlab(): lab[0] += 1; return f'L{lab[0]}'
    def r(): return rng.choice(RR if rng.random() < .6 else RC)
    def rd(): return rng.choice(RR + ['x0'] if rng.random() < .1 else RR)
    def val(): return rng.choice(CONSTS) if rng.random() < .6 else rng.getrandbits(32)
    L.append('li x2, 0x50')
    for i in range(3, 16): L.append(f'li x{i}, {val() & 0xFFFFFFFF}')
    L.append('li x1, 7')
    for _ in range(n):
        t = rng.choice(['alu'] * 5 + ['alui'] * 5 + ['shr', 'shi', 'sl', 'lui', 'auipc', 'ld', 'st', 'br', 'br', 'jal', 'jalr', 'sp', 'cx'])
        if t == 'alu': L.append(f'{rng.choice(["add","sub","slt","sltu","xor","or","and"])} {rd()}, {r()}, {r()}')
        elif t == 'alui': L.append(f'{rng.choice(["addi","slti","sltiu","xori","ori","andi"])} {rd()}, {r()}, {rng.choice([rng.randint(-2048, 2047), rng.randint(-8, 8), -1, 2047, -2048])}')
        elif t == 'shr': L.append(f'{rng.choice(["sll","srl","sra"])} {rd()}, {r()}, {r()}')
        elif t == 'shi': L.append(f'{rng.choice(["slli","srli","srai"])} {rd()}, {r()}, {rng.choice([0, 1, 31, rng.randint(0, 31), rng.randint(0, 31)])}')
        elif t == 'sl': L.append(f'{rng.choice(["slli","srli","srai"])} {rng.choice(RC)}, {rng.choice(RC)}, {rng.randint(1, 31)}')
        elif t == 'lui': L.append(f'lui {rd()}, {rng.randint(0, 0xFFFFF)}')
        elif t == 'auipc': L.append(f'auipc {rd()}, {rng.randint(0, 0xFFFFF)}')
        elif t in ('ld', 'st'):
            m = rng.choice(['lb', 'lbu', 'lh', 'lhu', 'lw']) if t == 'ld' else rng.choice(['sb', 'sh', 'sw'])
            off = rng.randint(-100, 100)
            region = rng.choice(['ram'] * 5 + ['rom', 'arm', 'gap', 'big'])
            if region == 'ram': a = rng.randint(0x50, 0xF8)
            elif region == 'rom': a = 0x4000 + rng.randint(0, 200)
            elif region == 'arm': a = rng.randint(0x3FEC, 0x3FFF)
            elif region == 'gap': a = rng.randint(0x100, 0x3FE0)
            else: a = rng.choice([0x7FFC, 0x8100, 0x1_0000, 0x40000050 + 0x10])
            L.append(f'li x1, {(a - off) & 0xFFFFFFFF}')
            L.append(f'{m} {r() if t == "st" else rd()}, {off}(x1)')
        elif t == 'br':
            lb = newlab(); L.append(f'{rng.choice(["beq","bne","blt","bge","bltu","bgeu"])} {r()}, {rng.choice([r(), r(), "x0"])}, {lb}')
            for _ in range(rng.randint(1, 3)): L.append(f'addi {rd()}, {r()}, {rng.randint(-5, 5)}')
            L.append(f'{lb}:')
        elif t == 'jal':
            lb = newlab(); L.append(f'jal {rng.choice(["x0", "x1", "x5", "x6"])}, {lb}')
            for _ in range(rng.randint(1, 2)): L.append('addi x7, x7, 1')
            L.append(f'{lb}:')
        elif t == 'jalr':
            lb = newlab(); p = lb + 'p'
            L.append(f'{p}: auipc x4, 0'); L.append(f'addi x4, x4, {lb} - {p} + {rng.choice([0, 1])}'); L.append(f'jalr {rng.choice(["x0", "x3", "x5", "x4"])}, 0(x4)')
            for _ in range(rng.randint(1, 2)): L.append('addi x7, x7, 1')
            L.append(f'{lb}:')
        elif t == 'sp':
            off = rng.randrange(0, 160, 4)
            L.append(rng.choice([f'lw {rng.choice(RR)}, {off}(x2)', f'sw {r()}, {off}(x2)', f'addi {rng.choice(RC)}, x2, {rng.randrange(4, 1000, 4)}']))
        else: L.append(rng.choice([f'mv {rd()}, {r()}', f'neg {rd()}, {r()}', f'not {rd()}, {r()}', f'seqz {rd()}, {r()}', f'snez {rd()}, {r()}', 'nop', f'li {rd()}, {rng.randint(-32, 31)}', f'lui {rng.choice(RC)}, {rng.randint(1, 31)}', 'fence']))
    L.append('end: j end')
    return '\n'.join(L) + '\n'


if __name__ == '__main__':
    s0 = int(sys.argv[1]) if len(sys.argv) > 1 else 0; cnt = int(sys.argv[2]) if len(sys.argv) > 2 else 20; n = int(sys.argv[3]) if len(sys.argv) > 3 else 150
    bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        for seed in range(s0, s0 + cnt):
            rng = random.Random(seed); src = gen(rng, n); p = os.path.join(tmp, 'p.s'); open(p, 'w').write(src)
            try: a, img = rvasm.assemble([p], os.path.join(tmp, 'o'))
            except rvasm.AsmError as e: print(f'seed {seed}: asm error {e}'); bad += 1; continue
            r = lockstep_rtl.lockstep(img, label=f'seed {seed}')
            if isinstance(r, str): print(r); bad += 1; open(f'/tmp/fail_{seed}.s', 'w').write(src)
    print('randprog:', 'FAIL' if bad else 'PASS', f'({cnt} programs)'); sys.exit(1 if bad else 0)
