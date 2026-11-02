# rndp_layout -- generic placer/router and compact-builder toolchain for RNDP replicators

Turns any flattened NAND/DFF netlist (+ one ROM, optional RAM, one ARM) into a **compact 2-layer PCB layout**
(parts on a pitch grid, each net routed with PathFinder-style negotiated congestion), encodes the layout as ROM data,
and checks it three independent ways. Used by `rndp_r2c` (Hack) and `rndp_r3c` (RV32EC).

## Pipeline
```
tools/nl_export.py TOOLSDIR HD OUT.nl             flatten an HD with that tree's ref_flatten -> netlist (.nl)
layout/target/release/layout NL OUT.lay px=5 py=5 ...      place (annealing on HPWL) + route; exit 2 and a list of overused cells on failure
tools/lay2asm.py LAY NL OUT.asm [--hack]          encode sites/paths/ports/RUN as ROM data (+ .equ constants)
(assemble the tree's builder + OUT.asm)
tests/run_builder_c.py (in the tree)              builder on the instruction model == independent ROM-data decoder == layout copper
tests/validate_layout.py NL LAY rom.bin           build the layout in rndp; pin nets must equal the netlist (no shorts, no opens)
tools/make_seed.py NL LAY rom.bin WORK            seed.build (everything but RUN) + run.build
rndp --world ... ; tests/compare_gen.py STATE DX  quine check
```
`layout` needs `cargo build --release` in `layout/`. The final layouts are kept (`data/*.lay`), so the chain is reproducible from them;
the exact annealing flags for them were not recorded (pitch is `px=py`; other keys at their defaults except `ml=mr=16`, effort and seed raised until routed).

## Netlist format (.nl)
`rom A` / `ram B` header; `n k N|D src [src]` nodes in site order; `p name src` ports. Sources: `n<k>`, `rom<j>`, `ramo<c>`, `open`;
suffix `@1` = EN-late sink, `@2` = RUN-late sink (wired last so the machine starts held in reset; ROM is programmed before any wire).

## ROM data encoding
Sites are on a px*py grid and numbered by site index, so placement is implicit (a 2-bit kind bitmap, or a kind exception list for Hack).
Then one routed path per sink (pin A then B; DFF only D), ports (EN last), RUN sinks. A path starts at the sink pad and ends on any cell
of the net's existing copper, so path order is electrically irrelevant except EN/RUN last.
Segment byte: `[7] last | [6] via | [5:4] dir (+x,-x,+y,-y) | [3:0] length 1..15`; length 0 = next byte holds 1..255; extension byte 0 = "no path".
First-segment via bit = start on layer 1; later via bits = VIA at the current point (layer toggles). Paths never end in a via.
Coordinates are arm-relative; CHILD_DX = board width. Runs longer than 255 are split into collinear chunks (compare_gen merges these).

## Router notes
A* over (layer, x, y, dir); costs: turn, via, history*16, present-sharing (x1.4/iteration, capped); history +2/iteration; shuffled net order;
stagnation widening with 5x5 rip-up. Pads block other nets. `edge` margin (default 14) keeps tracks off the top/bottom board rows;
`ml/mr` side margins 16 are needed or the wrap around the ROM column congests.

## Findings
* Area vs ROM bytes: tighter pitch -> smaller board, more path bytes (more turns). Huffman-coding the segments saves only ~1 bit of 8, not worth it.
* Minimum routable pitch: R2 netlist 5 (4 fails), R3 netlist 6.
* compare_gen: child wires extend up to 16 cells left of the child board, so the parent/child split uses a 24-cell margin (`CUTM`).
