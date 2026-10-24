# E4 result: decoder-based token-ring quine (R5, pruned architecture)

Status 2026-10-23. **Superseded for the final numbers by E5_REPORT.md (column inversion, metric 198,526).** Everything below is MEASURED unless marked otherwise.

## Design (as built)
- Plane: one DFF per row (token ring), 24 columns, tile = INV+NAND per 1-bit. W = 11,350 rows (16 interpreter, 899 pattern, 9,833 compressed layout words, 231 zero pad, 370 explicit C rows, 1 A row).
- Engine2: 981 NAND + 77 DFF. Two passes: pass 1 decodes the compressed layout stream (fmt3: 9-bit mirror coordinates, hi byte = Cx/Cy constant | bit 8), pass 2 dumps the plane with D=0 pattern rows, then C rows (explicit commands: ARM part, ring-start wire, 13 ARM long wires, late ties/EN).
- Geometry: the ARM part is at the origin of the arm-relative frame, in the middle of the plane (plane rows y = -13144..32255, engine block above the plane top at y >= 32256). The ARM's 13 pins and the ring-start (D0) are wired to pads on the block's left edge with long vertical wires written as explicit C rows (fmt3 cannot encode runs > 63).
- Child = parent shifted by DX = 900 (BX+DX = 1024, so Cx = 4, Cy = 0x7E).

## Verification
| check | result |
|---|---|
| rndp --build of the parent world | 833,215 commands, 0 refused, 0 faults |
| rndp pad dump vs logical design (engine netlist + plane + ARM pins) | 520,768 pins, 0 missing, 0 undeclared, 0 opens, 0 shorts |
| Rust model eng2sim (== Python model on a 1,119-row ring, 420,283 writes) at W=11,350 | 515,312,701 cycles, 4,201,838 arm writes, 0 faults |
| arm writes replayed through the arm model vs parent shifted by DX | parts 177,395, vias 1,492, merged wire runs 458,370: all identical |
| gate-level engsim of the real routed netlist (981 NAND + 77 DFF), full size, abstract plane | all 4,201,838 arm writes identical to the model |
NOT done: a full rndp tick-level run of the whole world (about 5.2e8 ticks on 178k parts); the plane is modelled abstractly in the gate-level run, its physical connectivity is checked by the pad dump instead.

## Counts (parent world)
NAND 165,967; DFF 11,427; metric NAND + 6 DFF = 234,529 (the arm is free). Ones in the plane 76,818 (2 NAND each = 153,636 NAND, 65% of the metric). DFF 68,562 (29%). Row inverters 11,350 (5%). Engine 981 NAND + 462 (77 DFF x 6) = 1,443 (0.6%).
Commands to build one child 833,215 (place 177,395, track 654,328, via 1,492). Ticks about 5.15e8 engine cycles (= 4 W^2 + overhead) + one tick per register write is already included. Area: bounding box 429 x 45,760 = 19.6 M cells (plane is 4 W tall). Copper cells 1.37 M (L0) + 1.59 M (L1).
Layout: engine routed at pitch 9, 36 rows, PathFinder (Rust mrouter), seed 2 of 5 (seed 4 left 1 overused cell); 9,007 body commands -> 9,833 data words.

## Lessons
- The ARM's coordinates are relative to the ARM part, so a 4W-tall plane needs the ARM at mid-plane (|y| < 32768) and the engine far from it; cost = about 100 explicit commands (370 rows, 3%).
- Routing the long ring-start wire outside the router's view produced a short; its start must be a reserved pad.
- A sign-extended 9-bit window (an idea tried and reverted) loses the Cx/Cy constants; the model test only passed because it used Cy = 0.
