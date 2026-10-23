#!/usr/bin/env python3
"""E3: ISA re-ranking under the R5 price list (a MODEL, not a netlist study).  Inputs are the ISA study's numbers (nandgen/ISA_COMPARISON.md: Hack-vN and ACC8 are measured netlists, CPU only;
6502-lite, Z80-lite, SUBLEQ are its component-sum ESTIMATES) and the E1/E2 measurements.  The kernel byte counts are K1-K4 of that study, a proxy for the quine program, not the program itself.
Cost of one irregular gate in the quine = itself + the ROM-logic that describes it: bits_per_gate / 8 bytes * ROM_PER_BYTE.   Metric units = NAND + 6 DFF."""
ROM_PER_BYTE = 5.5          # E1: plane ROM, real code, 4.2-6.0 NAND per byte (self-derivable construction)
RING_UNITS_PER_BIT = 6.5    # E2: recirculating ring incl. position counter (6.1-7.1)
STATE_BITS = 100            # quine state (coordinates, counters, ROM address, temporaries) [J]
isas = [  # name, NAND, DFF, code bytes K1-K4, source
    ('Hack-vN', 705, 52, 670, 'measured netlist'), ('ACC8', 1203, 62, 288, 'measured netlist'),
    ('6502-lite', 1190, 76, 401, 'estimate'), ('Z80-lite', 1540, 100, 217, 'estimate'), ('SUBLEQ', 750, 80, 236, 'estimate; K1 only, others unwritten')]
print(f'ROM {ROM_PER_BYTE}/byte, state ring {RING_UNITS_PER_BIT}/bit x {STATE_BITS} bits')
for bits in (13, 26, 55):
    mult = bits / 8 * ROM_PER_BYTE
    print(f'\n-- description cost {bits} bits/gate (13 = xz of netlist, needs a decompressor; 26 = R4 module HD; 55 = R3c routed layout data): {mult:.0f} extra units per irregular gate or DFF')
    print(f'{"ISA":10s} {"CPU raw":>8s} {"CPU+descr":>10s} {"code ROM":>9s} {"state":>6s} {"total":>8s}  {"descr share":>11s}  source')
    rows = []
    for n, nand, dff, code, src in isas:
        raw = nand + 6 * dff; descr = (nand + dff) * mult; rom = code * ROM_PER_BYTE; st = STATE_BITS * RING_UNITS_PER_BIT
        rows.append((raw + descr + rom + st, n, raw, descr, rom, st, src))
    for tot, n, raw, descr, rom, st, src in sorted(rows):
        print(f'{n:10s} {raw:8.0f} {raw + descr:10.0f} {rom:9.0f} {st:6.0f} {tot:8.0f}  {descr / tot:10.0%}  {src}')
print('\nBreak-even: how many irregular gates must a serial/sequencer design save to beat Hack-vN?  (Hack-vN 757 gates+DFF)')
for bits in (13, 26, 55):
    mult = bits / 8 * ROM_PER_BYTE; print(f'  {bits} bits/gate: each gate removed saves {1 + mult:.0f} units; Hack-vN total {705 + 6 * 52 + 757 * mult + 670 * ROM_PER_BYTE + STATE_BITS * RING_UNITS_PER_BIT:.0f}')
