# E5: encoding weight (R5, 2026-10-24).  Labels: [M] measured, [E] estimate.

Question: how many plane ones (2 NAND each) can be saved by choosing the stored encoding, at what engine cost?

## Candidates measured on the real ring (E4 design, W = 11,350, 76,818 ones, 9,833 layout words)
| encoding | result [M] |
|---|---|
| plain | 76,818 ones |
| **per-column inversion** (stored bit = logical ^ inv_j; engine inverts the plane output, 1 NAND per column) | only columns above 50 % ones qualify: col 21 (command flag) 10,153 of 11,350 -> 1,197; col 19 (track code bit) 8,841 -> 2,509. Saves 15,288 ones |
| dx as sign + complemented magnitude | 25,174 vs 24,168 ones in dx: worse (negative dx are only 923 of 9,451 commands) |
| len - 1 / len Gray | 12,801 / 14,451 vs 14,701 ones in len: at most 1.9k, needs a decrement/XOR chain: not taken |
| per-row complement flag | row weights 3-18 (mean 6.7 of 24); only ~230 rows exceed 12: not worth a flag column + 24 XOR |
Column density over the whole ring (ones of 11,350): [5445, 4457, 3833, 5029, 3551, 2578, 1329, 669, 1598, 4787, 4365, 3142, 2473, 1690, 1070, 3601, 2059, 463, 2945, 8841, 1084, 10153, 371, 1285].

## Implemented and verified (final configuration: inv = columns 19, 21)
- Engine: `w[j] = NOT(x[j])` for j in INV (`spec2.INV`, env `E5_INV=19,21`). Pattern compiler: the two cell variants of an inverted column swap their condition polarity (free). Plane stores `row ^ mask`; zero pad rows therefore store ones in those columns (2 each), so W is kept close to the natural size (pad 105 of 10,975 rows).
- Final build (seed 2 of 6 legal seeds, W = 10,975: 1 A + 16 interpreter + 899 pattern + 9,570 layout + 105 pad + 384 explicit rows):
  NAND 132,214; DFF 11,052; **NAND + 6 DFF = 198,526** (E4 baseline 234,529: -15.4 %). Plane ones 60,130 (layout words 48,951 = 81 %); area 429 x 44,260 [bounding box from the build]; engine cycles 481,824,451; arm writes 3,780,092; commands to build a child 720,806.
- Checks: rndp --build 0 refused / 0 faults, pad dump 418,759 pins 0 missing/opens/shorts; Rust model child == parent shifted by DX (143,267 parts, 1,406 vias, 372,518 merged wire runs); gate-level engsim of the routed netlist at full size: all 3,780,092 arm writes identical to the model. Small-ring gate-level and model tests with inversion also pass (425,203 writes).
- Still not done: tick-level rndp run of the whole world; the gate-level run models the plane abstractly.

## Reading
- The saving comes entirely from two columns that are structurally dense (a flag that is set in 96 % of layout words and a code bit set for every track). Everything else is below 50 % density and cannot be helped by a static polarity choice.
- Remaining ones: layout words 81 %; value-level recoding (len, dx) gives <= 2k ones of 60k and needs logic: left as is. Larger levers: fewer commands per gate (router/placer quality) and the 899 pattern rows (7.2k stored ones).
- Variance: 6 router seeds at W = 10,975 gave 9,570-10,326 layout words, all legal; the spread of the final metric over seeds is about +-2 % [M for words, E for metric].
