"""M2 tests: asm.py + trace_check.py.   usage: HACK_AB=14 python3 test_m2.py"""
import os, sys, random, shutil, tempfile, subprocess, copy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, '..', 'tools'), os.path.join(HERE, '..', 'isa')]
import asm, trace_check as tc
import common, isahack as H, lockstep
from nl_hackvn import build_hackvn
from fuzz_hack import gen
from test_hackvn import ref_state, net_state
EX = os.path.join(HERE, '..', 'examples')
tmp = tempfile.mkdtemp(prefix='m2_')
ok = True
def check(name, cond, extra=''):
    global ok
    print(('PASS ' if cond else 'FAIL ') + name + (' ' + extra if extra else '')); ok &= bool(cond)

def run_asm(text_or_paths, name='t'):
    if isinstance(text_or_paths, str):
        p = os.path.join(tmp, name + '.asm'); open(p, 'w').write(text_or_paths); paths = [p]
    else: paths = text_or_paths
    items, syms, mem = asm.assemble(paths)
    out = os.path.join(tmp, name + '_out'); rom = asm.write_outputs(out, items, syms, mem)
    return rom, out, paths

# ---- 1. demo program: assemble, audit, run in the behavioural model and in lockstep with the gate-level CPU
rom, out, paths = run_asm([os.path.join(EX, 'demo.asm')], 'demo')
r = subprocess.run([sys.executable, os.path.join(HERE, '..', 'tools', 'trace_check.py'), out] + paths, capture_output=True, text=True)
check('demo: trace_check passes', r.returncode == 0, r.stdout.strip().splitlines()[-1])
m = common.Machine(); m.load_rom(0, rom); cpu = H.CPU(m)
n = 0
while cpu.step(): n += 1
check('demo: model result SUM=55 CNT=0 OUT=11 22', (m.ram[0x10], m.ram[0x11], m.ram[0x12], m.ram[0x13]) == (55, 0, 0x11, 0x22), f'{n} instructions')
c = build_hackvn(2)
i, t = lockstep.run_image(H, c, ref_state, net_state, rom, seed=0)
check('demo: gate-level CPU in lockstep with model', True, f'{i} instructions, {t} ticks')

# ---- 2. round trip against the verified Python assembler: disassemble -> text -> asm.py -> identical bytes
def disasm_text(img):
    lines = []
    for k in range(0, len(img) - 1, 2):
        d = tc.decode(img[k], img[k + 1]); w = img[k] | img[k + 1] << 8
        if isinstance(d, tuple) and d[1] <= asm.AMASK: s = f'@{d[1]}'
        elif isinstance(d, str): s = d
        else: s = f'.word {w:#06x}'
        lines.append(f'    {s}   // word {k // 2}')
    if len(img) % 2: lines.append(f'    .byte {img[-1]}   // odd trailing byte')
    return '\n'.join(lines) + '\n'
images = {k: H.assemble(k, common.P) for k in common.KERNELS}
for s in range(30): images[f'fuzz{s}'] = gen(random.Random(s), 800)
bad = 0
for name, img in images.items():
    rom2, _, _ = run_asm(disasm_text(img), 'rt')
    if rom2 != img: bad += 1; print('  roundtrip mismatch', name)
check(f'round trip: {len(images)} images (K1-K4 + 30 fuzz, {sum(map(len, images.values()))} bytes) reassemble byte-identically', bad == 0)

# ---- 3. every comp x dest x jump combination, both spellings of the commutative forms
cnt = 0; comb_ok = True
for comp in tc.COMP_TXT.values():
    for a in (0, 1):
        cc = comp.replace('A', 'M') if a else comp
        for dest in ('', 'M', 'D', 'MD', 'A', 'AM', 'AD', 'AMD', 'DM', 'MA'):
            for jmp in H.JUMP:
                text = (dest + '=' if dest else '') + cc + (';' + jmp if jmp else '')
                ref = H.Asm(); ref.C(dest, cc, jmp); ref_word = ref.items[0][1]
                rom3, _, _ = run_asm(f'    {text}   // t\n', 'c')
                if int.from_bytes(rom3, 'little') != ref_word: print('  mismatch', text); comb_ok = False; ok = False
                cnt += 1
check(f'all comp x dest x jump combinations match isahack.Asm.C ({cnt} lines)', comb_ok)
for t in ('A+D', 'M+D', 'A&D', 'M|D'):
    rom3, _, _ = run_asm(f'    D={t}   // commutative\n', 'c')
    rom4, _, _ = run_asm(f'    D={t[2]}{t[1]}{t[0]}   // normal order\n', 'c')
    check(f'commutative spelling {t}', rom3 == rom4)

# ---- 4. assembler error cases
errs = {'unknown comp': 'D=D+D', 'bad dest': 'X=D', 'bad jump': 'D;JXX', 'mixed A and M': 'D=A+M',
        'A value too big': '@0x5000', 'negative A': '@-1', 'undefined symbol': '@nowhere',
        'duplicate label': 'x:\n    D=A\nx:\n    D=A', 'byte range': '.byte 300', 'outside ROM': '.org 0x10\n    D=A',
        'overlap': '    D=A\n    .org 0x%x\n    D=A' % asm.ROM_BASE, 'unknown directive': '.frob 1',
        'macro arity': '.macro M1 a\n    @\\a\n.endm\n    M1', 'unterminated macro': '.macro M2\n'}
for name, src in errs.items():
    try: run_asm(src + '\n', 'e'); check(f'error case: {name}', False, 'accepted')
    except asm.AsmError as e: check(f'error case: {name}', True, str(e).split('\n')[0][:60])
    except Exception as e: check(f'error case: {name}', False, repr(e))

# ---- 5. trace_check must catch tampering
def audit(out, paths):
    return subprocess.run([sys.executable, os.path.join(HERE, '..', 'tools', 'trace_check.py'), out] + paths, capture_output=True, text=True)
def fresh(name):
    d = os.path.join(tmp, name); shutil.rmtree(d, ignore_errors=True); shutil.copytree(out, d); return d
src_copy = os.path.join(tmp, 'demo_copy.asm'); shutil.copy(paths[0], src_copy)
rom_c, out_c, paths_c = run_asm([src_copy], 'democopy')
def expect_fail(name, code, mutate):
    d = os.path.join(tmp, 'tamper_' + name); shutil.rmtree(d, ignore_errors=True); shutil.copytree(out_c, d)
    shutil.copy(os.path.join(tmp, 'demo_copy.asm.orig'), src_copy) if os.path.exists(os.path.join(tmp, 'demo_copy.asm.orig')) else shutil.copy(paths[0], src_copy)
    mutate(d); r = audit(d, [src_copy])
    check(f'trace_check catches: {name}', r.returncode != 0 and code in r.stdout, [l for l in r.stdout.splitlines() if code in l][:1].__repr__())
def flip_rom(d):
    p = os.path.join(d, 'rom.bin'); b = bytearray(open(p, 'rb').read()); b[5] ^= 0x10; open(p, 'wb').write(bytes(b))
def extra_rom_byte(d):
    p = os.path.join(d, 'rom.bin'); b = bytearray(open(p, 'rb').read()); b += b'\x00' * 20 + b'\x77'; open(p, 'wb').write(bytes(b))
def drop_lst_line(d):
    p = os.path.join(d, 'rom.lst'); L = open(p).read().split('\n'); del L[7]; open(p, 'w').write('\n'.join(L))
def strip_comment(d):
    p = os.path.join(d, 'rom.lst'); L = open(p).read().split('\n'); L[3] = L[3].split('//')[0]; open(p, 'w').write('\n'.join(L))
def edit_source_after(d):
    s = open(src_copy).read().replace('D=M                 // D = CNT', 'D=A                 // D = CNT'); open(src_copy, 'w').write(s)
def wrong_bytes_same_text(d):                       # listing and rom.bin agree with each other but not with the source text
    p = os.path.join(d, 'rom.lst'); s = open(p).read().replace('2002  10 EC', '2002  10 E4'); open(p, 'w').write(s)
    q = os.path.join(d, 'rom.bin'); b = bytearray(open(q, 'rb').read()); b[3] = 0xE4; open(q, 'wb').write(bytes(b))
def add_unlisted_source(d):
    open(src_copy, 'a').write('    D=A   // an added line the listing never saw\n')
def uncommented_source(d):
    s = open(src_copy).read().replace('D=A                 // D = 10', 'D=A'); open(src_copy, 'w').write(s)
shutil.copy(paths[0], os.path.join(tmp, 'demo_copy.asm.orig'))
expect_fail('flipped rom.bin byte', 'C1', flip_rom)
expect_fail('extra non-zero byte in rom.bin', 'C2', extra_rom_byte)
expect_fail('deleted listing line', 'C6', drop_lst_line)
expect_fail('listing comment removed', 'C4', strip_comment)
expect_fail('source edited after assembling', 'C3', edit_source_after)
expect_fail('bytes changed consistently in lst and rom.bin', 'C5', wrong_bytes_same_text)
expect_fail('source line added after assembling', 'C6', add_unlisted_source)
expect_fail('source comment removed after assembling', 'C3', uncommented_source)
shutil.rmtree(tmp, ignore_errors=True)
print('ALL PASS' if ok else 'SOME FAILED'); sys.exit(0 if ok else 1)
