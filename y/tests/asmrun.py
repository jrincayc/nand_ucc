"""asmrun.py -- helpers to run improver.asm routines on the behavioural machine and compare with ref_improve.py."""
import os, sys, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
for d in ('tools', 'isa', 'tests'):
    sys.path.insert(0, os.path.join(HERE, '..', d))
import common, isahack as H
from machine_lockstep import MR
import run_builder as RB

SRC = os.path.join(HERE, '..', 'src')


def build(driver, files=('macros.asm', 'ram.asm', 'improver.asm')):
    """driver: asm text appended after the improver (it must start with label `main` placed at ROM_BASE via .org)."""
    d = tempfile.mkdtemp(); p = os.path.join(d, 'driver.asm'); open(p, 'w').write(driver)
    fl = [os.path.join(SRC, f) for f in files] + [p]
    # the driver comes FIRST in ROM (reset vector): assemble driver with .org ROM_BASE, then the library
    r = subprocess.run([sys.executable, os.path.join(HERE, '..', 'tools', 'asm.py'), '-o', d, p] + [os.path.join(SRC, f) for f in files], capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stdout + r.stderr)
    syms = {}
    for l in open(os.path.join(d, 'symbols.txt')):
        if '=' in l:
            k, v = l.split('=', 1); syms[k.strip()] = int(v.strip(), 0)
    return open(os.path.join(d, 'rom.bin'), 'rb').read(), syms


def run(image, syms, pokes=(), rom_patch=None, ramn=256, max_instr=50_000_000):
    m = MR(ramn); img = bytearray(image)
    if rom_patch:
        for a, bs in rom_patch.items():
            off = a - common.ROM_BASE
            if off + len(bs) > len(img): img += bytes(off + len(bs) - len(img))
            img[off:off + len(bs)] = bs
    m.load_rom(0, bytes(img))
    for a, v in pokes: m.ram[a] = v
    hwm = [0]; ow = m.wr
    def wr(a, v):
        if a < ramn: hwm[0] = max(hwm[0], a)
        ow(a, v)
    m.wr = wr
    cpu = H.CPU(m); n = 0
    while n < max_instr:
        if not cpu.step(): break
        n += 1
    else: raise RuntimeError('did not halt')
    m.hw = hwm[0]
    return m, n
