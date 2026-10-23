#!/usr/bin/env python3
"""cmp_gate.py EMU.armlog GATE.armlog [EMU.ram GATE.ram] -- the gate-level run must equal the emulator: same arm-register write sequence, and (if given) same final RAM
except bytes 0x40..0x47 (the gate CPU keeps the saved PC there; the emulator keeps it in a register)."""
import sys
a = open(sys.argv[1]).read().split('\n'); b = open(sys.argv[2]).read().split('\n')
n = min(len(a), len(b)); d = next((i for i in range(n) if a[i] != b[i]), None)
print('arm writes: emulator', len(a) - 1, 'gate', len(b) - 1, 'first difference:', d)
ok = d is None and len(a) == len(b)
if len(sys.argv) > 4:
    x = open(sys.argv[3], 'rb').read(); y = open(sys.argv[4], 'rb').read()
    dif = [i for i in range(min(len(x), len(y))) if x[i] != y[i] and not 0x40 <= i < 0x48]
    print('RAM bytes', len(x), len(y), 'differences outside 0x40-0x47:', len(dif), dif[:8]); ok = ok and not dif and len(x) == len(y)
print('RESULT', 'PASS' if ok else 'FAIL'); sys.exit(0 if ok else 1)
