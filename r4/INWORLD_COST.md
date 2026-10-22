# R4: in-world cost of "LPA + parts anchor + row-and-channel" (cpu_g1)  -- 2026-10-21

Pipeline (no order passed in, node numbers random): netlist -> graph -> label propagation (4 sweeps) -> greedy chain of clusters -> breadth-first order inside clusters -> serpentine fold into R=22 rows -> row-and-channel router (lane zones, left-edge tracks) -> arm commands.
Layout produced by the Python reference: 990 x 821 = 813k cells, built in rndp, 0 problems (`cpu_g1_lpa_anchor.state/.svg`).
Legend: MEASURED = run on the RV32EC emulator; COUNTED = operation count from the Python reference; ESTIMATED = counted operations x my per-operation instruction guess.

| step | work (COUNTED) | instructions |
|---|---|---|
| build CSR graph from the netlist | 9,679 pin entries, 17,760 pair entries | ~1.0 M (ESTIMATED, ~35/entry + net reading) |
| label propagation, 4 sweeps | 15,080 vertex visits, 69,768 neighbour visits | **3.65 M (MEASURED**, assembly kernel `kernels/lpa_sweep.s`, 320 ROM bytes, labels equal the Python model of the kernel) + ~0.3 M shuffle (ESTIMATED) |
| greedy chain of clusters | 1,264 steps, 798k candidate scans, 17k cluster-edge visits | ~6 M (ESTIMATED, ~7/scan; a heap would cut this to under 1 M) |
| breadth-first order in leaves | 17k edge visits | ~1 M (ESTIMATED) |
| fold into rows | 3,769 gates | ~0.1 M (ESTIMATED) |
| lane assignment, trunk intervals | 505 multi-row nets, 4,882 (net, channel) trunks | ~0.3 M (ESTIMATED) |
| sort trunks / left-edge | ~38k n log n compare-swaps, 57k first-fit compares | ~1.5 M (ESTIMATED) |
| emission: path points and arm commands | 7,503 paths, 48k points, 44.3k commands (23.9k track, 16.6k via, 3.8k place) | ~3 M (ESTIMATED: 44.3k x 27.4 measured instr/command of the R3c builder = 1.2 M, plus ~40/point to compute the points = 1.9 M) |
| **total** | | **about 17 M** (ESTIMATED; even 3x higher is about 50 M) |

Against the budget (about 1.4e9 instructions per week of simulator time) this is about 1.2% (3.6% at 3x), against about 7e9 for the negotiated maze router (ROUTER_ESTIMATE.md).

RAM (ESTIMATED): CSR offsets 7.5 KB + neighbours 35 KB + weights 17 KB + labels/votes/sizes 22 KB + cluster graph ~50 KB + trunk intervals ~40 KB + positions ~15 KB + netlist copy and misc ~20 KB = about 200 KB.  This does not fit 32 KiB RAM; it needs an 18-bit address bus (256 KiB) and the microcode change for a wider address register.  (The maze router was ~350 KB.)

Caveats:
- The assembly kernel uses a fixed vertex order and a first-maximum tie rule; the Python reference shuffles and breaks ties at random (901 vs 1,264 clusters).  The layout quality of the kernel's rule has not been tested, and a fixed order in the world would follow the netlist numbering (inherited order), so the in-world version needs the shuffle (counted above).
- The hierarchical caps (480 / 120 / 30) of lpa_order.py in practice only ran at the top level: the first LPA converged after 4 sweeps into about 1,264 small clusters, each at most 30 gates, so there was no recursion.  A real multilevel version (coarsen, repeat) is untested and could give a better order.
- Not counted: the improver itself, reading the hardware description, and the module flattening.

## Update: multilevel version (`tools/mlpa_order.py`, caps 8/32/128/512, seed 1)
Layout 810 x 751 = 608k cells, built in rndp, 0 problems (`cpu_g1_mlpa.state/.svg`).  Operation counts (COUNTED): 21 LPA sweeps over all levels, 28,403 vertex visits, 182,972 neighbour visits; chaining: 70k cluster-edge visits, 9k candidate scans.
Instructions (ESTIMATED from the measured kernel: about 25 per neighbour visit + 127 per vertex visit): LPA about 8.2 M; chaining about 2.2 M (7 per scan, 30 per edge visit); the rest of the pipeline as in the table above without the breadth-first step (CSR 1.0 M, fold 0.1 M, router about 1.8 M, emission about 3 M).  Total about 16 M, again about 1.2% of the week budget.  RAM about 200 KB (estimate; the contracted graphs are smaller than the gate graph).
The caveats above (fixed vs shuffled order, no recursion in the first version) apply; this version does recurse: 4 levels.
