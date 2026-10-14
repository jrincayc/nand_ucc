# M5 report -- the improver in ROM, integrated with the builder

Status: DONE, stop for your review before M6 (RNDW end-to-end runs, audits) and M7 (write-up).

## Result
* `src/improver.asm` (about 1.5k lines, every line commented, trace_check clean) implements the normative `tools/ref_improve.py` (stable compaction, chain cuts, truth-table cones, exhaustive iterative-deepening NAND search with GMAX=6, rewrite, output partition, slot-form layout with skip entries).
  `tests/test_m5_improver.py`: 84 cases (every library module, unlisted xnor / and3 / maj, random modules, hole-inserted records, fixed-point re-runs): the assembly output equals the reference byte for byte, bad = 0.
* `src/builder.asm` now runs the improver. `tests/test_m5.py` (integration): the ROM image of g0 (seed) runs on the behavioural Hack-vN model and the decoded arm writes equal `ref_flatten.commands(flatten(improved HD), image of g1)` for RAM 32, 64, 128 and 256 columns (r5, r6, r7, r8): 22k to 61k commands, missing 0, extra 0.
  The improved machine (g1) run on the same test builds the same machine again: the child image equals its own image (fixed point) for r5, r7 and r8.
* Cost of the improvement: all library modules together save 946 NAND (the RAM tiles are unchanged because the tile is a `tile`, not an improvable module). Weighted cost (NAND + 6 DFF, tie NAND included):
  r5 5,629 -> 4,683, r6 8,843 -> 7,897, r7 15,289 -> 14,343, r8 28,119 -> 27,173.

## RAM the improver really needs (your question)
* The improver alone: highest byte written 172, so **173 B** on the module-level test (`test_m5_improver.py`). Earlier stand-alone measurement of the working set alone was about 154 B; the 40 B result buffer sits above the overlaid temporaries.
* The integrated builder + improver: highest byte written **196, so 197 B**.
  The builder's variables and the improver's variables overlay each other (never live together); only the persistent block (29 B) and the 40 B result buffer (RECB) are separate. That is `src/ram.asm`, the single RAM map.
* A power-of-two RAM therefore means **256 B (ram_abits = 8)**. 128 B does not fit: the gate arrays (two tables of 32 entries), the 40 B record/scratch buffer and the loop variables already exceed 128 B.
  Cost of the jump from 128 to 256 B: RAM tile = about 100 weighted NAND per byte, i.e. about 13k. The improver saves 946, so **the improvement is a small fraction of what the larger RAM costs**. This is the honest finding for the data point: the improver is cheap in logic but not in state. (See "options" below.)

## Instruction counts (behavioural model)
| machine | g0 builds g1 (improver finds gains) | g1 builds g1 (fixed point) |
|---|---|---|
| r5 | 15.9 M | 9.8 M |
| r7 | 22.8 M | 16.7 M |
| r8 (256 B RAM, 61k commands) | 31.7 M | 25.6 M |
The improver runs twice per build (once per phase, per module type). One pass over the library is about 3 M instructions when it finds gains (fa alone 2.76 M); verifying a fixed point costs about the same.

## ROM space
Code (builder + improver + tables) ends at 0x3260 of the 16 KiB ROM; the hardware description starts at 0x32E0. The r8 image is **16,350 of 16,384 bytes**: 34 B margin. AB=15 is the maximum, so there is no more room: any further code (M6 audit hooks, features) must be paid for with HD or code savings.

## Design as built
* Phase 0 (place): ROM and arm are placed first; then for each module type t = 0..15 the improver runs on t, the (improved or original) record of t is programmed into the child ROM at the same address, and the body is walked placing only the instances of type t (other instances are stepped over by their slot count). Then the tie node and the RAM tiles are placed and the rest of the ROM (everything outside the record area) is copied.
* Phase 1 (wire): the same groups again (the improver recomputes the same record), wiring the instances of type t from the improved record; then tiles, ports, EN, RUN.
* Records have a fixed extent (4 + 3 slots + outputs), so the child's records sit at the same addresses and the directory is copied unchanged. Holes are skip entries; node numbering is unchanged, so no reference in the body, chain or ports ever changes.
* All PROGRAM_ROM commands come before the first WIRE (ROM lock respected); PLACE and PROGRAM_ROM interleave (allowed). `test_m5.py` checks this order instead of the old strict PLACE-then-ROM order.
* W = 256 does not fit a byte, so the chain record stores W-1 and the tile loop tests for the last tile. The PICKHI division was only correct for k < 128 (signed 8-bit compares); it now splits k = 128 + r. The encoder asserts the divisor is at most 64.

## Layout changes (hd2asm.py)
HD at ROM_BASE+0x32E0 (tables page at +0x3280, directory +0x3300, records +0x3320 with a 0x1C0 area, body +0x34E0). `hd_mods`/`hd_mods_end` labels delimit the record area.

## Tooling fixes
trace_check C3 accepts a macro call inside a macro body; every data line of the improver tables has a comment. `tests/test_m4.py` is removed (superseded by `test_m5.py`).

## Not done in M5 (M6 scope)
* Mutation test of the improver and builder (the M4 mutation script is not yet re-run on the larger image).
* Running g0 -> g1 -> g1 inside the Rust RNDW simulator (`run_y_world.py` / `verify_y_world.py` need the 256 B RAM `--rom-bits 14` update and a longer run; the behavioural runs above are at the arm-command level).
* Audit rules (ROM only textbook modules; unlisted-module run through the whole pipeline).

## Options you may want to weigh before M6
1. Accept RAM 256 B (as measured). Simplest; the 13k cost dwarfs the 946 saving, which makes the "lower limit" interesting: the self-improving core is dominated by its working memory.
2. Cut the improver's state (module limit 12 gates instead of 26 would save about 28 B but `fa` has 25 gates, so the library would need `fa` split; still above 128 B).
3. A non power-of-two RAM (about 200 B) needs address-decode changes in the chain: not tried.
