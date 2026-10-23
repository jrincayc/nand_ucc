# S3 report: assembly kernels   (2026-10-22)
**Status: DONE except the HD reader/packer.** The whole placement order and the whole row-and-channel router (fold, nets, zones, lanes, intervals, tracks, command emission through the arm window) run as hand-written RV32EC assembly, bit-exact with the Python references; the arm-register log of the router, decoded into commands, equals the golden command list (44,763 commands for the new-map g1).

## Done (all measured, on the Rust emulator in the new map: ROM 16 bits, AB 18, 256 KiB RAM)
| kernel (kernels/) | does | test | result |
|---|---|---|---|
| `build_graph.s` | packed netlist -> weighted CSR graph (nets in id order, pins deduplicated, anchor vertex, nets of 2..12 pins, weight 60//(p-1)) | `test_build_graph.py` | 25 random netlists + real old/new g1 identical (all of OFF, NBR, WT); 2.29M / 2.36M instructions |
| `lpa_level.s` | one size-capped label-propagation level: xorshift32, mask-and-reject draw, Fisher-Yates shuffle each sweep, first-maximum rule, vertex sizes, u32 votes, up to 15 sweeps | `test_lpa_level.py` | 30 random graphs + real level-0 graph at 4 caps: labels and final RNG state identical; 6.89M instructions for the real level 0 (all 15 sweeps run) |
| `chain.s` | greedy chaining (score 6/3/2 of the last three, first maximum, fallback lowest unvisited) | `test_chain.py` | 60 random cases + real graph up to 3000 items identical; about 420-630 instructions per item |
| `place_order.s` | contraction (groups by first appearance, member lists, in-place leaf-list joins, coarse graph with clamped weights), cap loop 8/32/128/512, top chain, flatten, anchor reversal and removal | `test_place_order.py` | 20 random netlists + real old and new g1 with 2 seeds each: the order of every gate identical to `place_ref.order`. **17.2-17.9M instructions (old map g1) and 18.3-19.3M (new map g1)** for build_graph + all four levels |
| `route1.s` | serpentine fold, sink lists (counting sort), zone choice (half-column integer cost), lane nets sorted by (zone, cmin, cmax), first-fit lanes, zone widths, gate-column x, part x | `test_route1.py` | ROW, COL, NOFF, NSNK, ZONE, LIDX, ZW, GXT, part x and board width identical to `route_ref.py`; **1.73M instructions** |
| `route2.s` | channel intervals per net and row, three LSD counting sorts, left-edge tracks, row baselines Y, height H | `test_route1.py` | IVS, NI, TRK, T, Y, H identical; **4.1M instructions** |
| `route3.s` | place commands (gates, ROM, arm, RAM), per-net wiring with the sink-order insertion sort, trunk/via path rules, late sinks queued and emitted last, board offset RV_OX/RV_OY | `test_route3.py` | decoded arm-register log == `route_ref` commands == `golden/cpu_g1_m18.cmds` (44,763 commands, 352,239 arm byte writes); same with a board offset (1000,77); **4.9M instructions** |

Router total (measured, emulator): **10.70M instructions** (route1+2+3 for the new-map g1 with the golden numbering); placement 18.3-19.3M; so **placement + routing = about 29-30M instructions** (the earlier estimate was 16-17M; about 2.1% of the 1.4e9-instruction week budget). In-world ticks are still the estimate 26 per instruction.
`trace_check.py`: every one of the 3,674 ROM bytes of the placement kernels, and every one of the 5,718 bytes of the router (route1+2+3 with a stub), (with a 3-instruction test stub) is produced by exactly one listing line that names a source line (0 uncovered, 0 multiply covered).

## Reference changes made to get a bit-exact, division-free version (place_ref.py)
- `Rng.below(n)`: mask of the next power of two minus one, bits 8.. of the draw, reject if >= n (the old multiply overflowed 32 bits and RV32EC has no multiply).
- Nets in the order of their id (gate outputs, ROM bits, RAM-out bits) instead of dict insertion order; vote sums asserted to fit u32.
- Because the draws and the net order changed, placement results changed, so the board areas were re-measured: old-map g1 mean 633k cells (598k-650k over 9 permutation/seed pairs), new-map g1 mean 714k (683k-747k): the 256 KiB map costs about 13% more area. Earlier numbers (596k, 636k) were from the previous random sequence. The goldens in `golden/` were regenerated.

## Tool bugs found on the way
- rvasm silently let a later duplicate label override an earlier one (two kernels both had `p1n`); it now reports "label defined twice".
- rvasm's listing cut long encodings (8-byte `li`) with "..", so `trace_check` could not cover them; the listing now shows instructions in full.
- A graph kernel bug (a self-reference was only skipped through the "last sink" trick) and a wrong weight-table entry (60//10 is 6, not 5) were caught by the random tests.
- `IDX` (vertex -> position) first lived inside the temporary-list area and was overwritten by the contraction; now it is a scratch array initialised before each chaining.

## Capacity limits of the kernels (explicit)
At most 4080 vertices, 20480 directed edges, 512 port reads (V_ERR = 1 / 2 on overflow). The real netlists need 3852 vertices, 17932 edges, about 56 port reads. RAM map in `kernels/memmap.s`.

## Not done yet
1. netlist/HD reader or packer in assembly (the packed SRC/PSRC/PTAB arrays are produced by the Python test harness today; in the real pipeline the improver's tables (S4) feed them). PROGRAM_ROM is not part of the router: it goes between `route3_place` and `route3_wire`.
2. Router capacity limits (explicit): sink records <= 8192, intervals <= 6144, board width W <= 2046, zones <= 15, lanes per zone <= 128, tracks per row <= 255, fan-out <= 1024 per net, 1000 late commands per queue (V_ERR=3 on queue overflow). The 4800-gate seed `cpu_g0.nl` exceeds the sink-record limit; real netlists (3851 gates) fit.
3. `build_graph.s` now masks the late bits (14-15) of SRC; the placement tests were re-run with late bits set and still pass.
