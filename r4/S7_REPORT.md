# S7 report: gate-level CPU runs the whole program   (2026-10-22, rerun on the final image)
**Status: PASS (measured).**  Plan changed from "windows from checkpoints" to the whole run, because a dependency-free Rust gate-level simulator is fast enough.

## What was run
`gatesim_rs` (Rust, no crates; semantics of tools/netsim.py = one RNDP tick: settle with ROM/RAM reads combinational, sample RAM write and arm write, latch all DFFs; open inputs read 0) simulates `hd/m18/cpu_g1.nl` (3770 NAND incl. tie + 81 DFF) from reset, with 256 KiB RAM and the 28,167-byte R4 ROM (seed HD; includes the child-origin offset added for S8), until the 552,115th arm-register write; then resumed from its checkpoint to 1.0e9 ticks to reach the halt loop.

## Results (measured)
- Arm-register write log: 552,115 writes, **identical** to the Rust emulator's, in order, first to last (so the 69,683 PLACE/PROGRAM_ROM/TRACK/VIA commands, already identical to the Python reference in S5, are also what the real gates produce).
- Final RAM, all 262,144 bytes: identical to the emulator's except bytes 0x40..0x47 (the gate CPU keeps the saved PC there; the emulator keeps PC in a register) -- 0 other differences.
- Cost: 987,429,710 ticks to the last arm write for 33,415,317 instructions = 29.55 ticks/instruction average. 3870 s (65 min) on one core at 255,100 ticks/s; checkpoints every 100M ticks (resume tested: the resumed run gave the same RAM and arm log).
- At 29.6 ticks/instruction and ~21k ticks/s in rndp, the same run in rndp would take ~13 hours (estimate from the S8 plan figure of 21k ticks/s, not measured here); the Rust gate-level run is the practical full check.

## Limits
- gatesim is a new program tested only by this run and the 600-arm-write short test against the emulator; it is not independently cross-checked against netsim.py's C output on the full program (netsim.py is too slow in Python-driven form for this run; gate_vs_rtl.py in the test tarball compares netsim with the microcode model tick for tick on short programs).
- The netlist is cpu_g1.nl (the CPU), simulated alone; wires, RAM/ROM parts and arm timing of the physical rndp world are not part of this check (rndp replay of the CPU running is S8).
- Seed-HD run only; the improved-HD program (fixed point) was not run at gate level (same code, different data).
- History: the same check passed on the earlier 28,131-byte image (551,835 arm writes, 987,390,950 ticks) before the child-origin offset was added; it was repeated on the final image above.
