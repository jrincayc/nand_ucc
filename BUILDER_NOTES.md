# Quine builder: working notes (milestone 2 complete)

Status 2026-10-13. **Milestone 2/4 reached:** a Hack-vN program builds a copy of its own machine (CPU + generated RAM + ROM + arm) through its arm, and the copy builds the next copy, verified in the RNDW world over three generations with 0 faults.

## Result (RAM 32 B, ram_abits 5)
| Item | Value |
|---|---|
| RAM | 32 B (variables use 30 B; high-water measured with RAM pre-filled with 1s, as built RAM powers up) |
| ROM image | 3,962 B = code and return table 2,226 + description stream 1,724 + output table 12 (fits the 4 KiB ROM) |
| Machine built | 2,550 NAND + 308 DFF (CPU 52 DFF; RAM cells 256 DFF) + 1 ROM (2x12) + 1 arm |
| Time per generation | about 7.65 M ticks (memory accesses); 137 s of wall clock in the simulator |
| Weighted cost, NAND + 6 DFF | 4,398 for the logic; adding ROM bits at f x 12.3 per bit: f=0.01 8.3k, f=0.1 43k, f=1 394k |

Verified (verify_quine.py): generation 1 is built by the harness driver from the reference commands with the real ROM image; generation 1's CPU runs the builder and builds generation 2; generation 2 builds generation 3; generation 3 had started generation 4 when stopped. Each completed generation has every part and all 5,311 wires of the reference machine at its arm-relative position, and a ROM byte-identical to the image. Faults: 0.

## Layout (arm-relative, spec v0.5)
Child arm at (0, +22) from its parent's arm, ROM at arm + (0, 9), node i at arm + (6 + 2i, 9), tie-high NAND = node n. Coordinates reach +-32,767, so the row (2 per node) limits RAM to about 128 B in one row.

## Design of the builder (isa/engine.py, blib.py)
- One tile engine walks the node list twice (MODE 0 places, MODE 1 wires): core + predecode (stream seg_a), a phantom tile of tie-high NANDs (the chain's "previous word" for word 0), then W word tiles.
- RAM word tile (60 nodes): head nwen, wen, ndec, dec; eight slices of 7 nodes (DFF cell, write gating t1 t2 o, read np acc nacc). Read data is an OR chain through the words, so every tile wires identically. The tile is described by 15 bytes of stream and replayed per word.
- Refs: Exp-Golomb (k=2) backward node distance; escapes (3-bit kind): ROM data bit, forward ref, tie, head line, WD[j] pointer, hiR/hiW/lo predecode pointers.
- Calls: return-table calling convention (8 B per call site plus 2 B table entry); five static return slots become four bytes.
- The ROM is copied byte by byte (non-zero bytes) with PROGRAM_ROM before any ROM wire; EN is the second-to-last wire group and the run wires are last.

## Where the bytes are
Stream 1,724 (core netlist 1,658); entropy bound for the core was 1,165 B. Annealing the node order gained 1.5%, so ordering is not the lever. Larger levers: a smaller core netlist (run the nandgen optimizer), a better code for the 52 forward D refs (about 137 B now), tighter code.

## Open items
- RAM 16 B would need the variables down to 16 B (now 30).
- Measure the same builder on ACC8 (not done).
- Self-improving CPU (Y) not started.
