#!/usr/bin/env python3
"""Cross-check rvasm.py encodings against llvm-mc (rv32e +c and no c), on random instructions.  Each case is one instruction at a fixed pc."""
import random, subprocess, sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import rvasm
random.seed(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
R = [f'x{i}' for i in range(16)]
def r(): return random.choice(R)
def rp(): return random.choice(R[8:])
def imm(n, signed=True):
    return random.randint(-(1 << (n - 1)), (1 << (n - 1)) - 1) if signed else random.randint(0, (1 << n) - 1)
def gen():
    k = random.random(); c = []
    for _ in range(1):
        pass
    t = random.choice(['alu', 'alui', 'sh', 'ld', 'st', 'br', 'jal', 'jalr', 'lui', 'li', 'mvlike', 'sp'])
    if t == 'alu': return f'{random.choice(list(rvasm.ALU_R))} {r()}, {r()}, {r()}' if random.random() < .5 else f'{random.choice(["sub","xor","or","and","add"])} {rp()}, {rp()}, {rp()}'
    if t == 'alui': 
        m = random.choice(list(rvasm.ALU_I)); a = r(); return f'{m} {a}, {a if random.random()<.6 else r()}, {imm(12) if random.random()<.5 else imm(6)}'
    if t == 'sh': 
        m = random.choice(list(rvasm.SHIFT_I)); a = r(); return f'{m} {a}, {a if random.random()<.7 else r()}, {random.randint(0,31)}'
    if t == 'ld': return f'{random.choice(list(rvasm.LOADS))} {r()}, {random.choice([imm(12), random.randrange(0,128,4), random.randrange(0,256,4)])}({random.choice([r(), "x2", rp()])})' 
    if t == 'st': return f'{random.choice(list(rvasm.STORES))} {r()}, {random.choice([imm(12), random.randrange(0,128,4), random.randrange(0,256,4)])}({random.choice([r(), "x2", rp()])})'
    if t == 'br': return f'{random.choice(list(rvasm.BRANCH))} {random.choice([rp(), r()])}, {random.choice([rp(), "x0", r()])}, {0x4000 + random.randrange(-200, 200, 2)}'
    if t == 'jal': return f'jal {random.choice(["x0","x1","x5"])}, {0x4000 + random.randrange(-3000, 3000, 2)}'
    if t == 'jalr': return f'jalr {random.choice(["x0","x1","x5"])}, {random.choice([0, 0, 4, -8])}({r()})'
    if t == 'lui': return f'lui {r()}, {random.choice([random.randint(0, 31), random.randint(0, 0xFFFFF)])}'
    if t == 'li': return f'li {r()}, {random.choice([imm(6), imm(12), imm(32)])}'
    if t == 'mvlike': return random.choice([f'mv {r()}, {r()}', f'not {r()}, {r()}', f'neg {r()}, {r()}', f'seqz {r()}, {r()}', f'snez {r()}, {r()}', 'nop', f'jr {r()}', f'ret', f'beqz {rp()}, {0x4000+random.randrange(-100,100,2)}', f'bnez {r()}, {0x4000+random.randrange(-100,100,2)}'])
    return random.choice([f'addi x2, x2, {random.randrange(-512,512,16)}', f'addi {rp()}, x2, {random.randrange(0,1024,4)}', f'lw {r()}, {random.randrange(0,256,4)}(x2)', f'sw {r()}, {random.randrange(0,256,4)}(x2)'])
def llvm(src_line, rvc, tmp):
    open(tmp + '/r.s', 'w').write(src_line + '\n')
    p = subprocess.run(['llvm-mc', '--triple=riscv32', f'-mattr=+e{",+c" if rvc else ""}', '-filetype=obj', '-o', tmp + '/r.o', tmp + '/r.s'], capture_output=True, text=True)
    if p.returncode: return 'ERR ' + p.stderr.strip().split('\n')[0]
    subprocess.run(['llvm-objcopy', '-O', 'binary', '-j', '.text', tmp + '/r.o', tmp + '/r.bin'], check=True)
    return open(tmp + '/r.bin', 'rb').read().hex()
def main():
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    bad = 0
    for rvc in (False, True):
        for i in range(n):
            ins = gen()
            if ins.split()[0] in rvasm.BRANCH or ins.split()[0] in ('jal', 'beqz', 'bnez'):
                # make target a pc-relative expression valid for both tools: use absolute address vs pc 0x4000 in rvasm, and '. + off' in llvm
                parts = ins.rsplit(',', 1); tgt = int(parts[1]); off = tgt - 0x4000
                ours = f'{parts[0]}, {tgt}'; theirs = f'{parts[0]}, .+{off}' if off >= 0 else f'{parts[0]}, .{off}'
            else: ours = theirs = ins
            tmp = tempfile.mkdtemp(); open(tmp + '/a.s', 'w').write((('.rvc\n' if rvc else '.norvc\n')) + ours + '\n')
            try: a, img = rvasm.assemble([tmp + '/a.s'], tmp + '/o'); mine = img.hex()
            except rvasm.AsmError as e: mine = 'ERR ' + str(e)
            if rvc and ins.split()[0] in list(rvasm.BRANCH) + ['jal', 'beqz', 'bnez']:
                # llvm-mc does not compress fixup-based branches/jal; check ours against the explicit c.* form (if we chose 16-bit) or the 32-bit form
                if len(mine) == 4:
                    f = [x.strip() for x in theirs.replace(',', ' ', 0).split(None, 1)]; mn = theirs.split()[0]; ops = [x.strip() for x in theirs.split(None, 1)[1].split(',')]
                    if mn == 'jal': ref = llvm(('c.j ' if ops[0] == 'x0' else 'c.jal ') + ops[1], True, tmp)
                    else: ref = llvm(('c.beqz ' if mn in ('beq', 'beqz') else 'c.bnez ') + ops[0] + ', ' + ops[-1], True, tmp)
                else: ref = llvm(theirs, False, tmp)
            else: ref = llvm(theirs, rvc, tmp)
            if mine != ref:
                if mine.startswith('ERR') and ref.startswith('ERR'): continue
                bad += 1; print(f'MISMATCH rvc={rvc}: {ins!r}\n   mine {mine}\n   llvm {ref}')
                if bad > 15: return 1
    print('xcheck_asm:', 'FAIL' if bad else f'PASS ({2*n} cases)'); return 1 if bad else 0
sys.exit(main())
