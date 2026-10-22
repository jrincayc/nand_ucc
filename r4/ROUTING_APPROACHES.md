# R4 routing: approaches tried, difficulties, compute and RAM

Subject: `cpu_g1` (3,769 NAND + 78 DFF after module improvement), rules: same-cell copper connects, 2 layers + vias, board must be built by the in-world RV32EC program (about 1.4e9 instructions per week of simulator time at 60k ticks/s, 26 ticks/instruction).
**Measured** = produced by a run in this session.  **Estimate** = my arithmetic or assumption, not measured.

## 1. One gate per row/column (R1, R2, R3)
Gate-per-row layout, wires are straight runs.  Trivial router (a few hundred bytes of code), RAM ~0, compute ~ O(nets).  Board is huge and thin (area ~ gates x nets).  Rejected by the user: not compact.

## 2. Compact fixed-pitch grid, implicit sites (R2c pitch 5, R3c pitch 6)
Offline generic router (Rust, annealer + PathFinder) writes the paths; the ROM stores them (segment bytes).  Measured: R2c board 262x274, ROM 13,050 B; R3c board 362x374, ROM 21,470 B.  The in-world program only replays stored paths, so no router runs in the world.  Cost: ROM grows with the netlist, and an improver cannot use it (it must compute paths itself).

## 3. Strip / channel router in the world (R4 M3, `tools/strip.py`)
Gates in a single row in body order (order optimized offline by annealing), single-sided channel, left-edge track assignment, no grid memory.
Measured (reference Python): g0 4,691 nodes -> 14,150x137 = 1.94M cells; g1 3,769 nodes -> 11,384x137 = 1.56M cells; 0 problems, validates in rndp.
Estimate: RAM ~23 KB (net endpoint table + track array), compute a few million RV32EC instructions (sort + first-fit).
Difficulty: board is 83:1 elongated.  Cheap in RAM and compute, poor in shape and area (1.56M cells vs 0.41M).

## 4. General maze router in the world, squarish board (option 3)
Offline reference = the Rust PathFinder (A*, 2 layers x 5 direction states, negotiated congestion), annealed placement.  Measured on cpu_g1, effort 3:

| pitch | board | cells | cells/node | heap pops pass 1 | pops total | passes | route time (host) |
|---|---|---|---|---|---|---|---|
| 10 | 632x654 | 413k | 110 | 34 M | 178 M | 11 | 29 s |
| 12 | 756x776 | 587k | 156 | 51 M | 267 M | 14 | 44 s |
| 14 | 880x898 | 790k | 210 | 69 M | 346 M | 12 | 55 s |
(Earlier runs: pitch 20 -> 1272x1264 = 1.6M cells; the router needs effort=3 at pitch 10.)

Finding: a larger pitch does NOT reduce routing work; pops grow roughly with board area (more room to search, wires get longer, congestion is not much lower).  Pitch 10 is the cheapest of those measured, and a tighter pitch is limited only by the router's ability to resolve congestion.

Estimates (assume ~40 RV32EC instructions per pop with a bucket queue; real assembly could be 2x either way):
- one pass at pitch 10: 34M x 40 = ~1.4e9 instructions = one week of simulator time, and it leaves ~6,000 overused cells (invalid).
- full negotiation at pitch 10: 178M x 40 = ~7e9 instructions = ~5 weeks.  Pitch 14: ~1.4e10 = ~10 weeks.
- RAM: occupancy 2 layers x 413k cells at 1 bit ~ 107 KB; with 2-bit wavefront labels ~320 KB; netlist/pins ~30 KB; total ~350 KB (estimate).  Needs a wider address bus (CPU address register is 16 bits now; 32 KiB RAM fits today, 64 KiB needs a third address byte, 512 KiB needs a 20-bit bus plus microcode change).
- PathFinder rip-up also needs per-cell history cost (extra ~1 byte/cell, ~+0.4 MB): estimate.

Difficulties: (a) congestion negotiation multiplies the work 5x; (b) memory is proportional to board area, not to gate count, so compactness (small area) and small RAM pull in the same direction only if the router is cheap; (c) the squarish board forces a real 2-D search.

## 5. Block-enable simulator command (measured, not adopted)
With arm-placed parts inert until enabled: 328 s vs 364 s over 22M ticks (about 10% fewer events).  Does not change the router conclusion.

## 6. Further options tried (2026-10-21)
### 6a. Sequential hard-obstacle maze router, no rip-up (MEASURED, `tools/router_counters_obst.patch` on the c3 router)
Same A*, but cells used by other nets are impassable, one pass, big nets first.  cpu_g1:
| pitch | failed sinks | pops (one pass, includes failed floods) |
|---|---|---|
| 10 | 129 of 7,503 | 246 M |
| 14 | 83 of 7,503 | 296 M |
Result: about 1-2% of sinks cannot be routed, and the pass costs MORE than a negotiated first pass (34 M at pitch 10) because each failed search floods the board.  At 40 instr/pop (estimate) that is ~1e10 instructions (~7 weeks), so it is worse on both counts.  Needs rip-up or a bounded search box, i.e. back to negotiation.

### 6b. Row-and-channel router on a squarish board (MODEL ONLY, `tests/rowchan_model.py`, ESTIMATE of area; no layout built or validated)
The strip order is folded serpentine into R rows (gate pitch 3); one trunk per net in the channel at its median row; pins in other rows cross through feedthrough columns; tracks by left-edge, so channel height = trunk density.
| R rows | width x height | area (cells) | aspect |
|---|---|---|---|
| 16 | 1647 x 461 | 759k | 3.6 |
| 24 | 1197 x 565 | 676k | 2.1 |
| 32 | 975 x 648 | 632k | 1.5 |
| 40 | 842 x 708 | 596k | 1.2 |
| 48 | 755 x 802 | 606k | 1.1 |
Estimated area ~600k cells at R about 40, squarish: about 1.45x the pitch-10 maze board (413k) but 2.6x smaller than the strip (1.56M).  The feedthrough count is a crude upper-style bound (worst gap crossings, no sharing), so the real figure could be better or worse; unvalidated.
Estimated compute: sort + left-edge + drawing wire cells (~2e5 cells x ~20 instr) = ~1e7 to 5e7 RV32EC instructions, i.e. 1-3% of the one-week budget (estimate).  Estimated RAM: per-net records (~4k x 16 B) + per-row/column bookkeeping, ~64-100 KB (estimate), far below the maze router's ~350 KB, and independent of board area.
Difficulties not yet solved: dogleg-free assignment when two pins in one column conflict vertically, feedthrough column allocation per row, and placement quality (the strip order was optimised for 1-D, so a 2-D-aware ordering could cut the feedthroughs).

### 6c. Still open (estimates)
- Longer verification run (a month) makes full negotiated maze routing at pitch 10 feasible (~5 weeks estimate).
- Bounded-box maze router with rip-up on top of the row-and-channel result for the few nets the channels cannot take.

### 6b-result. Row-and-channel BUILT and validated (MEASURED, `tools/rowchan.py`, `tests/test_rowchan.py`)
Real layout (rows of gates, one single-sided channel below each row, layer-1 feedthrough lanes in zones every Z gate columns, parts to the right), built in rndp with 0 shorts / 0 opens on cpu_g1:
| R rows | Z | board | cells | aspect | lane columns | track rows |
|---|---|---|---|---|---|---|
| 16 | 14 | 967 x 668 | 646k | 1.45 | 182 | 605 |
| 20 | 14 | 821 x 743 | 610k | 1.10 | 177 | 668 |
| 24 | 14 | 724 x 829 | 600k | 1.15 | 173 | 742 |
| 32 | 14 | 598 x 936 | 560k | 1.57 | 167 | 825 |
(R=20, Z=14 and R=24, Z=14 were built in rndp and validated; the other rows are generator output only.)  The model in 6b was right on area (about 600k cells) but the tracks are the dominant height: about 670 track rows against 40 gate rows.  About 1.5x the area of the pitch-10 maze board (413k), 2.6x smaller than the strip.
Saved state for inspection: `cpu_g1_rowchan_R20.state` (no ROM data programmed, offset (32,32)).

### 6d. Module-level placement + bundles (MEASURED area, ESTIMATED compute; `tools/modplace.py`)
Caveat first: the improved HD has no module hierarchy below the two flat tiles (`pla` 764 gates, `expander` 662) and the register names; the textbook modules (not/and/or/xor/mux/ha/fa) are unnamed instances.  So "modules" here are clusters of S consecutive gates of the (1-D annealed) body order, each a rectangle of h rows x w columns, and the clusters are placed on a 2-D grid by annealing on a trunk-length proxy (row crossings weighted by lane cost), then routed by the same row-and-channel router.
| layout | board | cells | track rows | lane columns |
|---|---|---|---|---|
| serpentine fold (6b) | 821 x 743 | 610k | 668 | 177 |
| clusters 4x15 on 5x13 grid | 1021 x 675 | 689k | 600 | 359 |
| clusters 5x12 | 1068 x 648 | 692k | 573 | 415 |
| clusters 3x20 on 7x10 grid | 943 x 652 | 615k | 574 | 326 |
(3x20 validated in rndp, 0 problems.)  Result: cluster placement lowers the track rows (668 -> 574) but the extra row-crossing wires need more lanes (177 -> 326), so the area does not improve (610k -> 615k).  The 1-D order was already annealed for short nets, and the fold keeps neighbouring rows neighbours.
Bundles (compute side; measured counts, estimated effect): of 7,407 driver-to-sink connections, with clusters of 60 gates 2,613 (35%) cross clusters and form only 610 distinct (source cluster, destination cluster) pairs; 259 pairs carry 4 or more wires (1,981 wires; largest bundle 23).  Routing each pair once as a bundle would cut the number of inter-cluster searches by about 4x (estimate), but it does not reduce area: parallel wires of a bundle still need one track each.  The intra-cluster 65% is unaffected.
Conclusion: module-level grouping saves ROUTER COMPUTE, not BOARD AREA, and only if real module boundaries exist; area comes from the track and lane counts, which depend on total wire length.  For the improver, a hierarchical HD (named modules with ports, as in Y's core.hd) would be needed first.

### 6e. Cheap improvements to row-and-channel (MEASURED, cpu_g1; `tools/rowchan.py` ZMODE, `tools/refine.py`)
1. Lane zone chosen by least total trunk extension instead of the mean pin column: 610k -> 564k (R=20, Z=14).
2. Gate-level 2-D annealing of the placement (`refine.py`, proxy = trunk length per used row to the net's mean column + alpha x row span, with the ROM/ARM/RAM as a fixed pseudo-pin at the right end of the last row).  Two pitfalls found on the way: without the part pins the proxy moved the part nets' drivers away from the parts (real trunk length 289k -> 465k, area 860k); and the proxy is in gate columns while the real layout is in cells (about x4.5), so alpha has to be about 18, not 22 in cell units.
| step | board | cells |
|---|---|---|
| serpentine, lane at mean (6b) | 821 x 743 | 610k |
| + lane by least extension | 814 x 693 | 564k |
| + 2-D refinement (R=20, Z=8) | 871 x 572 | 498k |
| + 2-D refinement (R=22, Z=14) | 786 x 623 | 490k (aspect 1.26, validated in rndp, 0 problems) |
| + 2-D refinement (R=24, Z=8) | 767 x 640 | 491k (aspect 1.20, generated only) |
Now 1.19x the pitch-10 maze board (413k) and 3.2x smaller than the strip.  Saved state: `cpu_g1_rowchan_R22.state`.
Consequence for the improver: the placement is now a (row, column) per gate, not just the body order, so the HD must carry the placement (or the improver must re-run an annealer in the world, which is far too expensive); this is parent-to-child information, like the improved HD itself.  Remaining cheap ideas (not tried): pins leaving through the top of the gate for Y and B, jogged (dogleg) trunks, balancing the channel heights (15 to 58 tracks per channel at R=20).

### 6f. Placement without the inherited order: label propagation (MEASURED, cpu_g1, R=22, Z=14; `tools/lpa_order.py`)
Question: how much of the result is the offline 1-D order from `order_hd.py`?  Test: orderings that do not use it.  LPA = size-capped label propagation, applied hierarchically (caps 480 / 120 / 30), clusters chained greedily, breadth-first order inside the 30-gate leaves; then the same serpentine fold and row-and-channel router (and optionally the same 6M-move 2-D refinement).
| start order | folded only | + 2-D refine (6M moves) |
|---|---|---|
| random | 8.3M cells | 900k |
| LPA (seed 1 / seed 2) | 1.03M / 0.99M | 616k / 632k |
| offline annealed 1-D order (inherited) | 539k | 490k |
LPA recovers most of the gap between random and annealed (8x better than random folded) and is linear time per sweep with memory of a few words per gate and per connection; it is the first placement method here that looks affordable in the world.  It is still 1.9x worse folded and 1.25-1.3x worse after refinement than the inherited order.  Not yet tried: more refinement moves, LPA with the part pins as an anchor, LPA used to seed the in-world local refinement.
Follow-up (MEASURED, R=22, Z=14): LPA with the parts as an anchor (pseudo-node for ROM/ARM/RAM in the graph, order reversed so the parts' cluster is last) and 20M refinement moves at T0=3:
| start | folded | + 20M-move refine |
|---|---|---|
| LPA, no anchor, seed 1 / 3 | 1.03M / 1.05M | 620k / 648k |
| LPA, anchor, seed 1 / 3 | 763k / 770k | 659k / 659k |
| inherited annealed order | 539k | 490k (6M moves) |
The anchor helps the folded layout a lot (1.03M -> 763k) but not after refinement (659k vs 620-648k), and more moves do not help (616k with 6M, 620k with 20M): the refinement is stuck in a local optimum set by the starting order, so the gap to the inherited order (490k) is not a matter of move count.  A single seed set only; the spread between seeds is about 5%.  Not tried: a hotter refinement start (T0 > 3), alpha tuned per start, recursive bisection / spectral ordering instead of LPA.

Leak check (MEASURED): the 763k/770k above used the netlist's own numbering, which is the inherited order, and it still leaks through tie-breaks.  With the node numbers randomly permuted before running (no order information at all), LPA + parts anchor, folded, no refinement, R=22, Z=14, gives 990 x 821 = 813k (seed 1) and 983 x 848 = 834k (seed 2), aspect 1.2; the seed-2 layout was built in rndp with 0 problems.  So the honest no-inherited-order figure is about 0.8M cells, about 1.65x the best refined layout (490k) and 1.9x smaller than the strip (1.56M).

See `INWORLD_COST.md` for the in-world instruction count of this pipeline (about 17 M instructions, ~200 KB RAM, estimates plus one measured kernel) and the correction that the hierarchy only ran at one level.

### 6g. Multilevel label propagation (MEASURED area, cpu_g1, R=22, Z=14, node numbers randomly permuted, no refinement; `tools/mlpa_order.py`)
LPA with a size cap, contract the clusters, repeat on the cluster graph with a larger cap; the cluster tree is flattened by chaining the children of each node; the parts are an anchor.
| order | board | cells |
|---|---|---|
| one-level LPA + chain (6f) | 990 x 821 | 813k |
| multilevel caps 8/32/128/512, seed 1 / 2 | 810 x 751 / 830 x 772 | 608k / 641k |
| caps 4/16/64/256, seed 1 / 2 | 802 x 785 / 839 x 783 | 630k / 657k |
| caps 16/64/256, seed 1 / 2 | 860 x 765 / 871 x 790 | 658k / 688k |
| caps 6/18/54/162/486, seed 1 / 2 | 834 x 779 / 819 x 757 | 650k / 620k |
Best 608k (aspect 1.08, built in rndp, 0 problems): 25% below the one-level version, with no order information, no refinement; 1.24x the best refined inherited layout (490k), 1.5x the pitch-10 maze board, 2.6x smaller than the strip.  Seed spread is about 5-10%.
Cost (see INWORLD_COST.md): about 16 M instructions, similar to the one-level version.

Pitfall: an earlier run used the generator index order inside leaves, which is the inherited order (the first 1.0M numbers); the table uses breadth-first leaves.

## Summary table (cpu_g1)
| approach | board cells | RAM (estimate) | compute (estimate) | status |
|---|---|---|---|---|
| strip | 1.56M | ~23 KB | ~5e6 instr | built, validated |
| row-and-channel (R=22, refined placement) | 490k (measured) | ~64-100 KB (estimate) | ~1e7-5e7 instr (estimate) | reference built, validated in rndp; in-world version not built |
| negotiated maze, pitch 10 | 413k | ~350 KB | ~7e9 instr (~5 weeks) | pops measured, in-world not built |
| hard-obstacle maze, pitch 10 | 413k | ~110-320 KB | ~1e10 instr | measured, fails 129 sinks |

## 7. What this says about a universal constructor
Placement and routing are the expensive part of self-improvement: the netlist is a few KB, but compact routing wants memory ~ board area (hundreds of KB) and ~10^8 expansions.  Cheap routers (strip/channel) trade away compactness.  The hard part is not the logic, it is the geometry.
