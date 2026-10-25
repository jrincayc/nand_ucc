# Replicators R1-R5 in one metric (2026-10-24)
Metric = NAND + 6 x DFF ("units"). ROM and RAM parts are converted to gates with the R5 prices: ROM = the E1 self-derivable plane, **built on the actual ROM image where the image exists on disk** [M]; RAM = addressable RAM at 12.3 units per bit (E2) [price M, bit counts M]. R1/R2 ROM images are not on disk: their plane cost is scaled from R3 loose (5.46 NAND per nonzero byte) [E]. R4 is an improver (a different task); R5 is a quine only (no improver, not Turing complete).

| replicator | logic NAND + 6 DFF | ROM as plane | RAM as gates | **total units** | board (cells) | ticks / generation |
|---|---|---|---|---|---|---|
| R1 Hack-vN-AB quine, loose lanes, RAM tiles | 8,809 + 6x1,080 = 15,289 (RAM tiles included) | ~40.7k [E] (7,459 B) | in logic | **~56k** | 136.0 M | 49.5 M |
| R2 same, RAM part, loose | 2,034 + 6x56 = 2,370 | ~33.4k [E] (6,119 B) | 1,024 b = 12.6k | **~48k** | 26.7 M | 13.2 M |
| R2c compact pitch 5 | 2,370 | 84,531 [M] (13,050 B, 39,374 ones) | 12.6k | **~99.5k** | 262 x 274 = 72k | ~8.9 M |
| R3 RV32EC quine, loose | 2,921 + 6x77 = 3,383 | 42,432 [M] (7,982 B, 18,532 ones) | 2,048 b = 25.2k | **~71k** | ~55 M | ~11 M |
| R3c compact pitch 6 | 2,938 + 6x78 = 3,406 | 141,577 [M] (21,470 B, 65,159 ones) | 25.2k | **~170k** | 362 x 374 = 135k | ~19.9 M |
| R4 RV32EC improver | 3,770 + 6x81 = 4,256 | 155,786 [M] (28,167 B, 71,287 ones) | 2,097,152 b = 25.8 M | **~26.0 M** | 872 x 786 = 685k | ~0.99 G |
| R5 (E4) pruned quine, token-ring plane | 165,967 + 6x11,427 total (plane, engine and rows are all gates) | -- | -- | **234,529** | 429 x 45,760 = 19.6 M | 515 M |
| R5 (E4 + E5 column inversion) | 132,214 + 6x11,052 | -- | -- | **198,526** | 429 x 44,260 = 19.0 M | 482 M |
| R6 Hack-vN-AB quine, ROM plane + RAM tiles built from gates | 2,034 + 6x56 core + RAM block 7,952 NAND + 6x1,024 DFF | ~124.8k NAND [M] (16,006 B image, 53.5k ones; Huffman raised ones ~7 %) | R1-style tiles, in the logic column | **141,277** (134,797 NAND + 1,080 DFF) | 1,696 x 7,840 = 13.3 M | not measured (builder ~754 M Hack instr., ~764k arm commands; tick level infeasible, ~318 ticks/cmd) |

## Reading (labels as in the table)
1. **R5 does not beat the earlier quines in this metric.** It is 3-4x above the loose R1-R3 (48-71k), 2x above R2c (99.5k) and 16 % above R3c (170k). Its win is over R4: 131x smaller, but R4 is dominated by its 256 KiB RAM (99.4 % of its units) and does a harder job (improver).
2. **Where the units go** (R5/E5): plane ones 60.1k x 2 = 120k NAND (60 %), DFF (rows + engine) 66k (33 %), row inverters 11k (5.5 %), engine 1.4k (0.7 %). The control logic has been pruned to 1.4k units (R2: 2.4k, R3: 3.4k), but the cost moved into describing the layout: R5 stores 9,570 layout words = **218 bits per described gate** (48,951 stored ones = 46 ones/gate) against **R2c's 41.6 bits per gate** (10,872 B of layout data for 2,090 gates; about 12-16 ones/gate [E]). R5's one-word-per-wire-command stream is about 5x less dense than a path-coded layout at pitch 5-6, and 3x more ones.
3. **Loose lanes are the cheapest in this metric** because their layout needs no data (tier 1, computed from the node index): R2 at ~48k has a ROM of only code + netlist description. The price is area: 26.7 M cells for 2,090 gates (12.8k cells/gate). R5's board is also large (19 M cells, mostly the 96-cell-wide plane stretched 44k tall plus empty space) because the plane is 4 W rows tall: it is not "compact" either.
4. **E3's warning is confirmed by measurement:** description of the machine to itself dominates; the pruned engine (1,058 gates) costs more to describe than R2's whole 2,090-gate CPU, because the stream format and the router (pitch 9, 1.1 words/command, 9 words/gate) are less dense than R2c's.
5. **What would change the ranking [E, not built]:** (a) a path-coded layout stream as dense as R2c's (41.6 bits/gate): layout words 9,570 -> ~1,900, saving ~7.7k rows x (6 + 1) + ~40k ones x 2 NAND = ~130k units, i.e. R5 ~ 70k, but the engine needs a path decoder; (b) rule-generated (lane) layout for the engine: no layout data, only a netlist description (E6: 9-14 bits/gate) -> R5 ~ 45-55k units with a 10 M+ cell board, in the R2 range, not below it. Neither is built; both are estimates.
6. Caveats: R1/R2 ROM planes scaled from R3 [E]; the ROM-as-gates conversion for R2-R4 is hypothetical (they use ROM parts); R5's tick count is the engine cycle count (one arm write per tick, includes waiting); areas of R3/R1 from their reports; single seeds/netlists throughout.

## Hardware inventory per replicator (added 2026-10-23) [M]
Counted from the actual seed builds (all parts and wires except the 7 RUN-wire commands): R1 and R2 generated with `make_seed.py`, R2c/R3/R3c from `c3/work_*` and `r3/work`, R4 from `r4/golden/cpu_g1_m18.cmds`, R5 from the parent worlds in `rndp_r5_worlds.tar`. Script: `nandgen/rndp_r6/stats_build.py`.
Track length = sum of |dx|+|dy| over TRACK commands (grid steps, both layers; wires that share copper are counted per command, so it is a slight overcount of distinct copper).

| replicator | NAND | DFF | ROM part (capacity / image bytes / nonzero bytes / ones) | RAM | track length, grid steps (L0 + L1) | per gate | TRACK cmds | vias | board bbox (cells) |
|---|---|---|---|---|---|---|---|---|---|
| R1 loose, RAM tiles | 8,809 | 1,080 | 16 KiB / 16,288 / 7,459 / 25,087 | 128 B as 128 tiles (7,680 gates + 1,024 DFF, in NAND/DFF) | 28.95 M (4.42 M + 24.54 M) | 2,928 | 47,364 | 18,729 | 4,581 x 29,698 |
| R2 loose, RAM part | 2,034 | 56 | 16 KiB / 16,041 / 6,119 / 20,979 | 128 B part | 4.27 M (1.71 M + 2.56 M) | 2,041 | 10,449 | 4,171 | 4,222 x 6,318 |
| R2c compact p5 | 2,034 | 56 | 16 KiB / 13,050 / 12,435 / 39,374 | 128 B part | 49,735 (25,353 + 24,382) | 23.8 | 9,864 | 2,120 | 240 x 259 |
| R3 loose | 2,922 | 77 | 16 KiB / 7,982 / 7,765 / 18,532 | 256 B part | 9.97 M (3.99 M + 5.98 M) | 3,323 | 14,956 | 5,970 | 6,040 x 9,046 |
| R3c compact p6 | 2,938 | 78 | 32 KiB / 21,470 / 20,468 / 65,159 | 256 B part | 110,868 (54,497 + 56,371) | 36.8 | 18,272 | 5,293 | 342 x 355 |
| R4 improver | 3,770 | 81 | 64 KiB / 28,167 / -- / 71,287 | 256 KiB part (18 address bits) | 653,728 (374,456 + 279,272) | 169.8 | 24,143 | 16,766 | 886 x 841 |
| R5 (E4) | 165,967 | 11,427 | none (plane is gates) | none | 3.21 M (1.62 M + 1.59 M) | 18.1 | 654,328 | 1,492 | 429 x 45,760 |
| R5 (E5) | 132,214 | 11,052 | none | none | 3.05 M (1.50 M + 1.55 M) | 21.3 | 576,133 | 1,406 | 429 x 44,260 |
| R6 | 134,797 | 1,080 | none (plane is gates; image 16,006 B of 16,384 cap) | none (tiles are gates) | 5.37 M (3,063,049 + 2,304,236) | 39.5 | 529,447 segments | 99,177 | 1,696 x 7,840 |

Reading:
- Loose-lane track length is 4-29 M steps, 2,000-3,300 per gate, because each wire runs on its own lane across a board that is 26-136 M cells. Compact layouts use 24-37 steps per gate (R2c, R3c), and R4's placed-and-routed CPU about 170 per gate.
- R5 has more copper than R2c/R3c/R4 in total (3.0 M steps) only because it has 70-80x more gates; per gate it is the shortest (18-21 steps), since plane wires are local. Almost all of R5's TRACK commands are single-cell plane links (576k commands).
- Via counts: R5 uses almost none (1.4k), R4 the most per gate (4.4 per gate), R2c 1.0 per gate.
- R4 RAM and ROM are parts, not gates; the units in the main table convert them with the E1/E2 prices. R1's DFF count includes its RAM tiles (1,024 of the 1,080).
- R4's cmds file has no ROM contents; its ROM image size and ones are from the main table.


R6 note [M]: Turing-complete (Hack-vN-AB) and fully self-built (no ROM/RAM parts). Builder equals reference on the model (764k commands, identical copper); rndp whole board 0 opens/shorts over 406,564 pins; quick tick-level test 452 commands, 0 mismatches over 1M ticks. Huffman-coded core path data was needed to fit the 16 KiB ROM cap, at ~+5k NAND. Details: rndp_r6/R6_DESIGN.md.