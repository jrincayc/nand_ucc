# Quine child-building program: design draft v0.1 (for review before coding)

Date: 2026-10-13. Goal: a Hack-vN machine whose ROM program builds, through its own ARM, a second machine identical to itself (CPU, RAM, ROM, ARM, tie-high, all wires), programs the child's ROM with its own program, and releases the child with the last wire. The child then does the same.

## 1. Stage A is done: a scripted reference construction
`script_world.py` generates the exact PLACE / PROGRAM_ROM / WIRE sequence (spec section 7 order) for the Hack-vN machine and `run_child.py` plays it through a driven arm in the Rust simulator. After the last wire the child starts and runs kernels correctly: K2 and K4 pass on the built child with 0 faults (K4 places its 1,040 DFFs at the right coordinates). This fixes the target the real program must reproduce, and it found three facts:

1. **`run` must feed exactly one gate.** nandgen's double-inverter elimination had fanned `run` out to about 13 gates, so wiring them one by one released parts of the CPU early and left the one-hot state register at all zeros (a dead CPU). Fix (now in `nl_machine.py`): `reset = NAND(run, run)` built raw, so `run` has one consumer with two pins; the child is released by the last wire. Cost: 1 NAND. This is the hardware cost of the "held in reset" requirement in spec section 7.
2. **A built child powers up with every RAM bit = 1** (half-built mux gates read as 1 while wiring is in progress). The program must not assume zeroed RAM. The kernels already initialize what they use.
3. **EN is attached only after the reset state has settled** (3 idle ticks before the EN wire and before the run wire), so the child's ARM never fires on garbage.

## 2. Size of the target (reference stream, Hack-vN, level 2)
| RAM | NAND | DFF | parts | wires | arm commands | register writes (unchanged registers skipped) |
|---|---|---|---|---|---|---|
| 32 B | 2,386 | 308 | 2,697 | 5,105 | 7,961 | 26,787 |
| 64 B | 3,998 | 564 | 4,565 | 8,585 | 13,309 | 45,113 |
| 128 B | 7,228 | 1,076 | 8,307 | 15,557 | 24,023 | 88,023 |
| 256 B | 13,656 | 2,100 | 15,759 | 29,437 | 45,355 | 175,961 |
| 1 KiB | 52,178 | 8,244 | 60,425 | 112,625 | 173,209 | 697,897 |

The register writes are a floor on the ticks the real program needs; the program will cost several times more (it spends instructions computing each coordinate). At about 10-20k ticks/s in the simulator, a 128 B child at 10x overhead is roughly a minute.

## 3. The RAM cannot be stored as data
Relative-reference encoding of the node list: CPU alone 757 nodes, 1,462 input references, 1,828 B with fixed 10-bit references (order-0 entropy bound 1,094 B). The same encoding for a machine with 64 B RAM is about 14 KB, more than the whole 4 KiB ROM. So the RAM (and the read mux tree and write decode, which are regular) must be produced by loops in the program; only the irregular CPU is data.

## 4. Proposed architecture
- **Layout:** all nodes in one row, node s at x = X0 + 3s, y = Y0 (pitch 3, 2x2 parts; 8,307 nodes = 25k wide for 128 B RAM, up to 256 B fits in 65,536). Producer coordinates are then x - 3*offset: no division or table. ROM and ARM sit after the end of the row. A child is placed one stripe lower: **Y0' = Y0 + 22**, X0 unchanged, so thousands of generations fit.
- **Quine up to one patched constant:** the program cannot read its own position, so the ROM holds Y0 as two data bytes and the copy loop writes Y0 + 22 into the child's ROM. Child ROM differs from parent ROM in exactly those two bytes. (Alternative: positions relative to the arm, which the spec does not allow, or a generation counter, which RAM cannot keep.)
- **Description stream (data in ROM):** the CPU's 757 nodes as two reference fields per gate and one per DFF. First version: fixed-width fields unpacked by a K2-like loop (about 1.8 KB); a gamma or entropy code is a later optimization.
- **Generator code:** (a) place pass: DFF nodes then NAND nodes along the row; (b) wire pass: for each node, wire producers to its pins; (c) RAM generator: loops over words and bits producing the same cell and mux structure as nandgen's RAM, plus decode, plus connections to the CPU's address, wdata and we lines; (d) ROM and ARM placement and their address, data and EN wires; (e) program the child's ROM with the copy loop (patching Y0); (f) idle, attach EN, idle, wire `run`. All kernels K1-K4 are the building blocks; their code is already written and verified for this ISA.
- **Order constraint (spec section 7):** all PLACEs, then ROM programming (before the ROM is wired), then wires, EN, run last.
- **RAM working set:** the program needs counters, a few 16-bit coordinates and pointers: guess 40-60 bytes, so the smallest machine may be 64 B; I will measure by instrumenting the real program.
- **ROM budget:** CPU description about 1.8 KB + code (K1-K4 total 670 B plus generator and glue, guess 1-1.5 KB) is near 4 KiB. ROM size is a world constant (default 12 address bits).

## 5. Milestones
1. Python reference interpreter of the description format (generates the command stream; checked identical to `script_world`) and the exact layout above.
2. Generator pieces as Hack-vN assembly (Python macro assembler), each checked against the reference command stream by running it in the lockstep harness and comparing the ARM log.
3. RAM generator and glue; whole program assembled; ROM image size and RAM high-water mark measured.
4. Run in RNDW: parent builds child, child builds grandchild; verify both against the reference and that the grandchild runs a marker program.
5. Report data point X: ROM bytes, RAM bytes, NAND/DFF, ticks.

## 6. Open decisions
See the questions asked with this draft: RAM size strategy, ROM size, and whether the one patched constant is an acceptable meaning of "quine".

## 7. Decisions (2026-10-13) and milestone 1 result
Decisions from review: (1) RAM size: find the minimum by building the program and measuring its RAM high-water mark. (2) ROM size: allowed to grow beyond 4 KiB (rom_abits up to 16); report it as part of X. (3) The patched row coordinate is acceptable, but Joshua suggests the arm's coordinates could instead be made relative to the arm itself. That would make the child's ROM byte-identical to the parent's and remove the patch code; it is a small simulator and spec change (PLACE, WIRE and PROGRAM_ROM coordinates become offsets from the issuing arm's origin) and is a pending proposal, not yet made.

Milestone 1 done: the machine is now split into a **core netlist** (CPU, address decode, read-data mux; 766 NAND + 52 DFF for 128 B RAM, 1.27 KB xz as data) and a **RAM generated by loops** (`machine_row.py`: predecode, per-word write enable, 1 DFF + 3 NAND per bit, read mux tree), all nodes in a single row at x = 100 + 3s, y = 2000. `run_row.py` plays the reference sequence through the driver arm; the built child runs K2 (RAM 256 B) and K4 (RAM 64, 128, 256 B) with 0 faults and correct results (K4 places its 1,040 DFFs at the right coordinates). Reference counts for the single-row layout:

| RAM | nodes | arm commands | register writes |
|---|---|---|---|
| 64 B | 4,567 | 13,324 | 44,857 |
| 128 B | 8,309 | 24,038 | 81,571 |
| 256 B | 15,763 | 45,376 | 154,813 |

Next (milestone 2): the builder program itself in Hack-vN assembly, piece by piece, each checked against this reference stream.
