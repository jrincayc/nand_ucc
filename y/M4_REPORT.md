# M4 report -- the assembly builder (flattener)

Status: done. `python3 tests/test_m4.py` passes (20 checks), the builder reproduces itself in the Rust RNDW simulator with 0 faults, and 60 of 60 random mutants of the builder were caught. No improver in ROM yet. Stopping for your review before M5.

## What it is
`src/builder.asm` (782 lines, hand-written, every line commented) plus `src/macros.asm` (144 lines). It reads the hardware description that `hd2asm.py` emits (`hd/*_data.asm`) and builds a copy of the machine through the arm: PLACE every part, copy the ROM image with PROGRAM_ROM, WIRE everything, wire the child's arm EN, wire RUN last. It is a direct transcription of `tools/ref_flatten.py: commands()`, and its main loops are the ones in spec section 5 (walk the body twice, MODE 0 places, MODE 1 wires; then the RAM tile chain). The object code is 4,112 bytes; the description is 2,914 bytes (ram_abits 5) to 3,028 (ram_abits 7).

## Results
| check | result |
|---|---|
| Builder vs reference flattener (behavioural model, RAM preloaded with random bytes) | exactly the same command set for seed and improved descriptions at ram_abits 5, 6, 7 (e.g. 31,427 commands for improved r7); PLACE, then PROGRAM_ROM, then WIRE; EN and the two RUN wires last |
| trace_check on builder + macros + data | PASS: no unexplained ROM byte, all 2,023 instructions re-decoded, every line commented |
| RAM use | highest byte written 125, so 126 bytes of variables; needs ram_abits >= 7 |
| RNDW end to end (ram_abits 7 seed, ROM image 7,303 B, 9,815 nodes) | the driver built generation 1; generation 1 ran the builder and built generation 2: all 9,817 parts, all 18,576 wires and the 5,945 ROM bytes of generation 2 equal the reference, **0 faults**; generation 2 had started building generation 3 (6,413 parts placed) when the 36.1 M tick run ended |
| Time per generation | 31.06 M ticks (computed from the instruction mix; consistent with the run), about 3,200 ticks per node; X was 2,700. 32 minutes of simulator wall time |
| Mutation check (single-field changes to random builder instructions) | 60 of 60 killed |

## Things you should know
1. **Bugs found by the tests, now fixed**: a loop counter shared between the source decoder and `put5` (the run never ended); the x of the last RAM column overflowed 8 bits at 128 tiles (only the ram_abits 7 case showed it); the assembler numbered `\@` labels differently on nested macro lines. None reached the RNDW run.
2. **Assembler changes (asm.py)**: macros may now call macros, the `\@` number is fixed per expansion, and `ROM_BASE`, `ARM_BASE`, `AB` are predefined. test_m2 still passes.
3. **Data format changes** (made while writing the builder, spec v1.4 section 4): gates are (kind, a, b) triples everywhere, NAND/DFF have records of their own, chain rules are fixed 5-byte records, ports carry their sink pin, EN is the last port, HD starts at ROM offset 0x1000.
4. **The RAM question matters more than I had said.** The improver only touches the combinational modules, which save 912 NAND whatever the RAM size. The RAM tiles are not improved. Weighted cost (NAND + 6 DFF), seed -> improved:

   | ram_abits (RAM) | seed | improved | saving |
   |---|---|---|---|
   | 5 (32 B) | 5,545 | 4,633 | 16% |
   | 6 (64 B) | 8,759 | 7,847 | 10% |
   | 7 (128 B) | 15,205 | 14,293 | 6% |

   The builder alone needs 128 B as written. The improver needs more (spec estimate 130 to 190 B, shared where possible). So as it stands the headline number for Y would be a 6% (or worse) total saving, against 46% for the core logic alone (1,958 -> 1,053 NAND). Both numbers are honest; the second is the one that measures the improver, the first the machine.
5. **ROM size.** Code 4.1 KB + data 3.1 KB = 7.2 KB of the 8 KiB (AB=14). The improver (my guess: 2 to 3 KB in this style) will not fit. Options: (a) AB=15, 16 KiB ROM: +72 NAND +2 DFF, nothing else changes; (b) compact the builder first: return-table calls and cheaper constants should save around 400 B, not enough on its own; (c) both. The ROM image is also the thing the f-weighted metric counts, so a larger image is not free.

## Decisions I need from you
A. AB=15 for Y (recommended unless you prefer to see how far compaction goes), or compact first?
B. RAM: accept 128 B and report core-only and total savings; or spend M5 effort on squeezing the variables (builder to about 64 B, improver sharing buffers); or let the improver also rewrite the RAM tile (the tile is a flat NAND+DFF module; its combinational part is 6 NAND per bit and might have a 5-NAND form, which my improver cannot see because it only handles 3-input combinational modules)?

## Next (M5, after your answers)
The improver in assembly, checked gate list for gate list against `tools/ref_improve.py` (V4), then M6 integration (seed -> g1 -> g2 in RNDW).

Files: src/{macros,builder}.asm, tools/{asm,hd2asm,hd_export}.py (changed), tests/{test_m4,run_builder,run_y_world,verify_y_world,mutate_builder,dbg}.py, hd/*.
