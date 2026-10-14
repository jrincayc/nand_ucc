# M6 report -- RNDW end to end, audits, behaviour, mutation

Status: done. Stopping for your review before M7 (write-up).

## RNDW end to end (Rust simulator, ram_abits 8 = 256 B RAM, ROM 16 KiB, image 16,350 B)
The driver builds generation 1 (the textbook seed) from the reference commands. Then, in the simulated world only:
* generation 1 runs its ROM (builder + improver) and builds generation 2, through its own arm;
* generation 2 runs the same ROM program and builds generation 3.

| generation | parts | wires | ROM bytes | equals reference |
|---|---|---|---|---|
| 1 (seed, 15,495 NAND + 2,104 DFF) | 17,601 | 33,119 | 13,221 | yes |
| 2 (improved, 14,549 NAND + 2,104 DFF) | 16,655 | 31,227 | 13,176 | yes, every part, wire and ROM byte |
| 3 (built by generation 2) | 16,655 | 31,227 | 13,176 | yes: identical to generation 2 |

* **0 faults** at 200,196,267 ticks (generation 3 finished; 4 ROMs and 5 arms exist in the world).
* The improvement is a real change of the hardware: generation 2 is 946 NAND smaller than generation 1 and has the same ISA; generation 3 equals generation 2 (fixed point, in RNDW and not only in the model).
* Weighted cost (NAND + 6 DFF): generation 1 28,119, generation 2 27,173 (-3.4%). The 946 NAND are -6.1% of the NAND, -29% of the logic that is not RAM.
* The part counts are exactly the predicted flatten of the improved description. The saved state of the run was checked by `tests/verify_y_world.py` against `ref_flatten.commands` for each generation (log: `tests/m6_world_log.txt`).
* Time: ticks for one generation are estimated, not measured: the builder is 31.7 M instructions for generation 1 (improver finds gains) and 25.6 M for generation 2 and later, at about 2.6 ticks per instruction (demo program on the gate-level netlist, 131 instructions in 336 ticks), so about 80 M and 65 M ticks. Both are consistent with the run (generation 2 finished building generation 3 before tick 200 M). Simulator wall time: about 2.7 h for the first 110 M ticks (two runs sharing 2 cores) and 4 h for the following 90 M.
* One run was lost (session restart); the final check resumed from the saved state of the first run (`--world`), which restores the DFF contents, and went on for 90 M ticks.

## Audits (tests/test_m6_audit.py, all pass)
* A. The seed library is textbook (gate counts not 1, and 2, or 3, xor 9, mux 8, ha 11, fa 25; no holes).
* B. None of the improved gate lists of the five changed modules appears anywhere in the seed ROM image: the answers are computed, not stored.
* C. The improver is general: xnor (10 gates), and3 (4), maj (12) are added to the library and used in the body; the assembly builder + improver on the model builds exactly the reference improved child (22,174 commands, 21.4 M instructions): xnor 10 -> 5, maj 12 -> 6, and3 stays 4 (already minimal).

## Behaviour (tests/test_m6_behaviour.py)
The improved 256 B machine (what the ROM builds) runs the demo program (131 instructions, 336 ticks, identical to the seed) and 30 random Hack-vN-AB programs in lockstep with the instruction-set model: 30/30.

## Mutation (tests/mutate_m6.py)
60 single-bit changes to instructions that the seed build actually executes (builder and improver, 5,916 distinct executed words): 60 of 60 killed (an observable difference in the arm write log, a crash, or no halt). Caveat: "log differs" counts any change of order as killed, a slightly stricter oracle than set equality; and unexecuted words (dead code) cannot be tested this way.

## Things you should know
1. The ROM is 34 B from full (16,350 of 16,384): there is no room for any more code or description at AB=15.
2. W = 256 and the signed 8-bit compare bug (tile index >= 128) were found by M5 tests and fixed there; the RNDW run exercises tiles 128 to 255.
3. Not done: a measured (not estimated) ticks-per-generation figure; a run where the improver finds nothing to change on a different library (covered in the model by test_m5 "improved r8" and the audit, not in RNDW).
4. The data point's headline, as I would put it: the improver costs 197 B of RAM and about 7 KB of ROM and saves 946 NAND; at 256 B RAM that is 3.4% of the machine's weighted cost, but each generation is also a verified exact copy of its parent.

Files: tests/{run_y_world,verify_y_world,test_m6_audit,test_m6_behaviour,mutate_m6}.py, tests/m6_world_log.txt.
