#!/usr/bin/env python3
"""directed_map.py -- directed lockstep tests for the 256 KiB RAM / 64 KiB ROM memory map (ROM_BITS=16 AB=18 RAM_BITS=18): high RAM, the arm window
at the top of the RAM, ROM mirror, auipc/jal/jalr/branch targets that wrap in 16 bits.  rvemu.py against cpu_rtl.py (and optionally the gate level)."""
import os, sys, tempfile
os.environ.setdefault('ROM_BITS', '16'); os.environ.setdefault('AB', '18'); os.environ.setdefault('RAM_BITS', '18')
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools'), HERE]
import rvasm, rvemu, lockstep_rtl
SRC = '''
    li x2, 0x50
    li x1, 0x12345678
    li x3, 0x2ABCD
    sw x1, 0(x3)            # high RAM
    lw x4, 0(x3)
    li x5, 0x3FFEC          # just below the arm window: RAM
    sw x1, 0(x5)
    lw x6, 0(x5)
    li x7, 0x3FFF0          # the arm window: write goes to the arm, read gives 0
    li x8, 0x5A5A5A5A
    sw x8, 0(x7)
    lw x9, 0(x7)
    sb x1, 15(x7)
    li x10, 0x3FFF8
    lbu x11, 0(x10)
    li x12, 0x40000         # the ROM (first bytes are this program)
    lw x13, 0(x12)
    li x14, 0x50000         # mirror of the ROM
    lw x15, 0(x14)
    lui x3, 0x40            # 0x40000
    auipc x4, 0             # 0x40000 | pc16
    jal x5, near
    addi x6, x6, 1
near:
    la x7, far
    jalr x1, 0(x7)
    addi x6, x6, 2
far:
    li x9, -1
    addi x9, x9, 1
    bne x9, x0, bad
    sb x4, 0(x2)
bad:
    end: j end
'''
with tempfile.TemporaryDirectory() as tmp:
    p = os.path.join(tmp, 'd.s'); open(p, 'w').write('\n'.join(l.split('#')[0].rstrip() for l in SRC.splitlines()) + '\n')
    a, img = rvasm.assemble([p], os.path.join(tmp, 'o'))
    r = lockstep_rtl.lockstep(bytes(img), label='directed map')
    if isinstance(r, str): print(r); print('FAIL'); sys.exit(1)
    m = rvemu.Machine(bytes(img)); m.run(10000)
    print('lockstep OK:', r[1], 'instructions;  x4 (auipc) =', hex(m.reg(4)), ' x6 =', hex(m.reg(6)), ' x13 =', hex(m.reg(13)), ' x15 =', hex(m.reg(15)), ' arm log', m.armlog[:6])
    import subprocess
    open(os.path.join(tmp, 'r.bin'), 'wb').write(bytes(img))
    rr = subprocess.run([os.path.join(HERE, '..', 'rvemu_rs', 'target', 'release', 'rvemu'), os.path.join(tmp, 'r.bin'), '--rom-bits', '16', '--ab', '18', '--ram-bytes', str(1 << 18), '--max', '10000', '--armlog', tmp + '/arm', '--dump-ram', tmp + '/ram'], capture_output=True, text=True)
    arm = [tuple(map(int, l.split())) for l in open(tmp + '/arm')]
    assert rr.returncode == 0 and arm == m.armlog and open(tmp + '/ram', 'rb').read() == bytes(m.ram) and f'instructions {m.icount} ' in rr.stderr, ('rust mismatch', rr.stderr)
    print('Rust emulator agrees')
    assert m.reg(4) >> 16 == 4 and m.reg(13) == m.reg(15) and m.reg(9) == 0 and m.reg(6) == 0x12345678
    print('PASS')
