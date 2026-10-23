# S5 report: whole program on the Rust emulator   (2026-10-22)
**Status: PASS (measured).** `ROM_BITS=16 AB=18 RAM_BITS=18 python3 tests/test_pipeline.py` (and with `HDFILE=cpu_mod_improved.hd`).

## What runs
One hand-written RV32EC program (kernels/start,main,improve,hdflat,build_graph,lpa_level,chain,place_order,route1-3 + HD data), 28,131 ROM bytes, on `rvemu_rs`:
seed HD in ROM -> in-world flatten -> improve each module -> write improved HD -> flatten again -> graph -> LPA placement order -> route -> arm commands (PLACE, TRACK, VIA, PROGRAM_ROM incl. the improved HD).

## Measured results
| item | seed HD | improved HD (child) |
|---|---|---|
| NAND (incl. tie node) | 4719 | 3770 |
| DFF | 81 | 81 |
| RAM address bits | 18 | 18 |
| ROM address bits | 16 | 16 |
| instructions executed (emulator) | 33,414,247 | 32,287,077 |
- Arm command log: 69,683 commands (3,854 place, 24,947 ROM bytes, 40,882 track/via) -- identical to the Python reference, command for command, in both runs.
- Board 872 x 786, router error flag V_ERR = 0.
- Fixed point (measured): running the program whose HD is the improved one rebuilds a child ROM image equal to its own image. With the seed HD the child differs (expected, since it carries the improved HD).
- trace_check (measured): all 28,131 ROM bytes covered exactly once by a listing line with a source file:line; 0 mismatch.
- Emulator wall time 0.6 s; the 33M instructions are cheap in Rust, so the S8 week-long budget is for the gate-level steps, not this one.

## Lessons / bugs found
- `.equ TL` and `.equ ORD` silently overrode each other between memmap.s and memmap_imp.s and hung lpa_level. Renamed ITL/IORD; rvasm now errors on duplicate `.equ`.
- Placement scratch overlays SRC/KINDA/PTAB, so the HD is flattened a second time after placement; MT lives in low RAM (0x400).
- Unaligned zero_range wrote into the arm window; start now aligned.
- trace_check "uncovered 28131" was a harness fault: AB was not set and the rom.lst truncated long data directives ("..."). rvasm now lists every byte (continuation lines).
- Mutation test of the improver (current tests/mutate_improve.py, re-run today in a fresh tree): 9 of 9 mutants killed. Two earlier mutants were dropped, not killed: "outputs not protected in saved" is redundant (FO already counts every output) and "GMAX 6 -> 5" gives identical results on all 255 three-variable SOP modules and 6000 random modules tried (not proven equivalent in general). An earlier version of this report said 8/11 with three survivors; that was an older script version.

## Not yet done
S6 rndp replay, S7 gate-level checkpoint windows (Rust netsim), S8 long run; clang lockstep in the new map.
