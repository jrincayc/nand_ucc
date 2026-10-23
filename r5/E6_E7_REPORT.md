# R5 experiments E6 (description bits per gate) and E7 (regularity)

Code: `exp/e6_e7.py` (netlist encodings, LZ, WL classes), `exp/e6_layout.py` (layout encoding of the R4 router output). Outputs: `exp/e6_e7.txt`, `exp/e6_layout.txt`.
Labels: **MEASURED** = exact size of an encoding I implemented (decoder code not counted); **BOUND** = zero-order entropy, a lower bound, no coder built; **ESTIMATE** = model arithmetic.

## Test beds and a caveat
| netlist | NAND | DFF | what it is |
|---|---|---|---|
| `r4/hd/m18/cpu_g1.nl` | 3770 | 81 | RV32EC CPU of R4 |
| `c3/work_r2.nl` | 2034 | 56 | Hack-vN-AB core of R2 (the R2/R2c machine) |
| `c3/work_r3c.nl` | 2938 | 78 | R3c core |

The Project holds the measured Hack-vN (705/52) and ACC8 (1203/62) level-2 netlists, but I could not get them onto the workspace disk (the tool returned them inline only), so they are **not** analysed here. Hack-vN-AB (work_r2) is the nearest family member. Memory parts (ROM/RAM planes) are external to these netlists.

## E6a: netlist description, bits per NAND (MEASURED unless marked)
Encoding: per gate a NOT flag (both inputs equal), then each input as a source/gate flag plus Elias-gamma of the backward distance (gate) or a fixed-width index (DFF/external input). Gates are in topological order, so distances are always positive. DFF D inputs (about 1 bit/gate extra when DFFs are ~2% of nodes) are not included.

| netlist | absolute 2 log2 N | relative + gamma, original order | same, DFS-cone order | BOUND, DFS order | LZ over distance pairs, DFS order |
|---|---|---|---|---|---|
| RV32 cpu_g1 | 24.0 | 13.1 | 12.6 | 12.6 | 13.0 |
| Hack-vN-AB work_r2 | 24.0 | 9.9 | 8.9 | 9.7 | **7.7** |
| R3c core | 24.0 | 14.4 | 14.4 | 14.0 | 14.9 |

- A plain relative-distance code with a one-line decoder gives **9–14 bits/gate** and needs no decompressor beyond a gamma reader. For reference, xz on the text of the same netlists is 26 bits/gate (cpu_g1), 26 (work_r2) and 29 (r3c) per gate, so the earlier "13 bits/gate (xz)" number in E3 was the optimistic one; the simple code roughly halves xz-on-text.
- Reordering into DFS-cone order helps only the regular netlist (-10%). LZ helps only the regular netlist (-14% vs gamma); on the irregular ones it is neutral or slightly worse.
- NOT-form gates (a==b) are 32-62% of NANDs. The flag saves one reference each.

## E6b: layout description (MEASURED, R4 router output for cpu_g1)
Commands 3,854 place + 24,174 track + 16,708 via. Every track is axis-aligned, zero-length ones do not occur, layers alternate across vias.
| encoding | bits/gate |
|---|---|
| naive 16-bit fields | 559 |
| chains of connected segments, layer implied by via parity, zigzag-gamma lengths, placement as deltas | **127.5** (routing 113.7 + placement 13.8) |
| BOUND: zero-order entropy of segment symbols only | 52.6 + chain starts |

So a *general* router's output costs 127 bits/gate to store, twice the 55 bits/gate measured earlier for the R3c compact layout (a layout produced by a compaction tool and encoded for its builder), and 10x the netlist. An explicit layout is therefore only worth it if the layout is compact and highly regular.

## E7: regularity (MEASURED counts)
- Gates covered by LZ copies (DFS order): Hack-vN-AB **64%** (1296/2034; "gates that must be described" = 1001, 49%), RV32 22%, R3c 16%.
- WL structural classes among gates at cone depth 0..6: Hack-vN-AB 1, 3, 8, 21, 47, 87, 136 (6.7% of gates at depth 6); RV32 1, 3, 9, 36, 155, 424, 782 (21%); R3c 1, 3, 10, 40, 177, 473, 829 (28%).
- Reading: the Hack-class datapath is genuinely regular (bit slices), the RV32 and R3c netlists much less. Regularity shrinks the description at best 14% with a generic LZ coder; to get more, the regular parts would have to be emitted by parametrised loops (a generator), which I did not build. The class counts say a generator would need only ~140 distinct local shapes for the Hack core, so a 2-3x reduction of the irregular part is plausible but is an **ESTIMATE**, not a result.

## Consequences for R5 (ESTIMATE, uses E1's 5.5 units per ROM byte)
1. Netlist description is cheaper than E3 assumed for a Hack-class machine: about 9 bits/gate instead of 13 (Hack-vN has 757 gates+DFF: 0.85 KB, about 4.7k units instead of 6.8k).
2. Explicit layout vs "netlist + in-world placer/router". Measured R4 code: placement kernels 3,674 B + router 5,718 B = 9,392 B (RV32EC, so a different ISA could be smaller or larger).

| gates | explicit layout 55 b/gate | netlist 9 b/gate + R4-size placer/router |
|---|---|---|
| 757 (Hack-vN) | **28.6k units** | 56.3k |
| 2,100 | 79.4k | **64.7k** |
| 3,770 (RV32) | 142.6k | **75.0k** |

Break-even about **1,600-1,800 gates** (against 55 bits/gate), about 650 gates if the explicit layout is as bad as the general router output (127 bits/gate).
So for a Hack-vN-sized R5 the right choice is an explicit, compact, regular layout encoded around 55 bits/gate or less, not a router; a general placer/router only pays above roughly 1,700 gates. A router specialised to one regular layout style might break even much lower (not measured).
3. The layout, not the netlist, is the expensive part of the description: at 55 bits/gate it is about 6x the netlist cost. The main open lever is therefore a layout style whose wiring is implied (pitch-grid template per bit slice, E4) and whose description is mostly loop counts.

## Not done / caveats
- Hack-vN and ACC8 level-2 netlists not analysed (see above). Decoder code size is not counted in any row. The 55 bits/gate is R3c's earlier measurement, not re-derived here. The 127.5 figure is for a general router's output; a layout designed to be compact could be lower.
- Next: E4 quine skeleton and a template-layout study for the Hack-class slice (to test whether implied wiring gets below ~20 bits/gate).

## E8: "template layout" = netlist stored in placement order + the deterministic R4 fold/router (follow-up, 2026-10-22)
Code `exp/e8_template.py`, outputs `exp/e8_work_r2.txt`, `exp/e8_cpu_g1.txt`. Idea: layout is precomputed offline, so the child needs no placer; if the netlist is stored in placement order, the router derives all wiring from it and the layout description is just the netlist (sign bit + gamma(|distance|) per reference, DFF outputs by index). Router = R4 `route_ref.route` (R=22 rows, Z=14), executed on the real netlists. MEASURED.

| netlist, order | bits/NAND to store | board (bbox of commands) | wire length |
|---|---|---|---|
| Hack-vN-AB (2034 NAND): identity | 11.6 | 573 x 512 | 241k |
| DFS-cone | 10.6 | 536 x 423 | 195k |
| R4 placer (LPA) | 11.9 | 442 x 451 | 153k |
| random | 26.6 | router fails (lane overflow) | |
| RV32 (3770 NAND): identity | 15.2 | 968 x 912 | 769k |
| DFS-cone | 14.5 | 888 x 920 | 727k |
| R4 placer (LPA) | 15.7 | 871 x 785 | 597k |

Findings:
- The wiring really is free: storing the netlist in the placement order costs 10.6-15.7 bits/NAND in total, versus 55 (compact explicit) or 127 (router output explicit). Order quality barely changes the storage cost (netlists in any sensible order are about 11-12 / 15 bits) but changes the board by up to 1.5x; random order does not route at all.
- The cost is area. For the Hack-vN-AB core the template board is 199k cells (LPA) to 293k (identity) against 71.8k for the compaction-tool layout of R2c (262 x 274), i.e. 2.8x-4.1x. The pitches of the two tools differ, so treat this as roughly 3x, not an exact ratio. R5 asks for a compact layout, so this is a real cost that the NAND+6DFF metric does not show.
- Code: only the router is needed (5,718 B in R4), not the placer, so the break-even against the 55 bits/gate explicit layout drops from 1,600-1,800 gates to about **1,060** (ESTIMATE: 5,718 x 8 / (55 - 11.9)). At 757 gates: explicit 28.6k units vs template 6.2k + 31.4k = 37.6k. Explicit still wins for a Hack-vN-sized machine, by about 9k units, and is also 3x denser.
- What was NOT tested: a hand-designed bit-slice template whose wiring is implied by construction (not a general channel router). The R4 router is general and large; a router for one fixed row/lane style could be much smaller than 5.7 KB, which would move the break-even down. That needs a design, not a measurement, and is the next step if you want it.
