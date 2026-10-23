#!/usr/bin/env python3
"""trace_check.py OUTDIR -- every byte of rom.bin must be produced by exactly one listing line that names a source file:line
(builder.s or cpu_data.asm), and the listing bytes must reproduce rom.bin exactly."""
import sys, re, os
import os
ROM_BASE = 1 << int(os.environ.get('AB', os.environ.get('ROM_BITS', '14')))
d = sys.argv[1]; rom = open(os.path.join(d, 'rom.bin'), 'rb').read()
cover = [0] * len(rom); img = bytearray(len(rom)); bad = 0
for ln in open(os.path.join(d, 'rom.lst')):
    f = [x.strip() for x in ln.rstrip('\n').split('|')]
    if len(f) < 4: continue
    m = re.match(r'([0-9A-F]+)\s+((?:[0-9A-F]{2} ?)+)$', f[0])
    if not m: continue
    a = int(m.group(1), 16) - ROM_BASE; bs = bytes.fromhex(m.group(2).replace(' ', ''))
    if not re.match(r'[\w.]+\.(s|asm):\d+$', f[1]): bad += 1; print('no source ref', ln); continue
    for i, b in enumerate(bs):
        if a + i >= len(rom): bad += 1; print('beyond rom', ln); break
        cover[a + i] += 1; img[a + i] = b
unc = [i for i, c in enumerate(cover) if c == 0]; dup = [i for i, c in enumerate(cover) if c > 1]
print(f'{len(rom)} bytes, uncovered {len(unc)}, multiply covered {len(dup)}, mismatch {sum(1 for i in range(len(rom)) if cover[i] and img[i] != rom[i])}, bad lines {bad}')
sys.exit(1 if unc or dup or bad or img != rom else 0)
