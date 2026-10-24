# R5 design note: pruned-architecture quine, program in constant NAND gates   (draft 2, 2026-10-24)
Status: **E1-E4, E6-E7 done; E4 built a complete decoder-based token-ring quine at model and structural level (see the E4 section at the end and e4/E4_RESULT.md); not yet run tick by tick in rndp.** Labels: **[M]** measured (R4 or earlier studies), **[E]** estimate to be replaced by an experiment below, **[J]** judgement.
Table row: `| 5 | pruned-architecture quine, program in constant NAND gates | neither |` (neither = no improver, no Turing-completeness requirement).

## 1. Decisions taken (from the discussion)
1. **Metric: NAND + 6 x DFF**, reported together with the raw NAND and DFF counts and the board area. The arm is a free primitive; ROM and RAM parts are not used (`rndp --rom off --ram off`); `PROGRAM_ROM` is not used.
2. **Turing completeness is not required** for R5. If it is wanted it is **R6: a Hack-vN-style (AB) quine that builds its own RAM and ROM from gates**, using the same ROM-as-logic and RAM-from-gates generators developed for R5.
3. **Precomputed layout is fine** (this is a quine, not an improver). The CPU/ISA is free: any word width, any ISA, a pure sequencer, whatever minimizes the metric in a compact layout.
4. Compactness: board area is reported and kept compact (R3c reached 362 x 374 at pitch 6 for 3,019 parts [M]); not part of the minimized metric unless decided otherwise.

## 2. What the quine has to do
The machine must (a) place every NAND and DFF of itself, (b) draw every wire (arm: `PLACE`, `TRACK`, `VIA` only), (c) place its ROM-as-logic and RAM-as-gates (if any), (d) start the child last (RUN wire). All state it keeps is for generating coordinates and reading its own description.
Rough state need [J]: x and y of the current position (~9-11 bits each for a board of a few hundred cells), loop counters, a ROM address, a few temporaries: **~60-120 bits**. That is registers, not an addressable memory; this is why dropping the Turing-complete requirement removes most of the RAM cost.

## 3. Price list (new world: everything is gates)
| thing | cost | status |
|---|---|---|
| DFF | 6 units (metric) | decision 1 |
| RAM bit, addressable (decode + mux), per bit | ~6.3 NAND + 1 DFF = ~12.3 units | [M] calibration from the ISA study (nandgen anchors) |
| RAM bit, recirculating shift register ("delay line"), per bit | **6.1-7.1 units** including position counter and match; access time N/2 ticks; not worth it below ~64 bits | [M], E2 |
| ROM as logic: per stored 1-bit (self-derivable plane) | **~2.2-2.3 NAND** incl. decoder (4-6 per byte of real code); 0-bits are free; a data-shared DAG form is 2.5x cheaper but cannot be regenerated cheaply | [M], E1 |
| describing one irregular gate to itself | 26 bits (R4 module HD) / 55 bits (R3c routed layout) per gate [M] => **~18 / ~38 extra units** at 5.5 units per ROM byte; E3: description is 56-94 % of the total for every ISA | [M] sizes, [E] model |
Consequences [J]: (i) ROM bits are cheap per bit but never negligible: 1 KB of real code is ~5.5k NAND; (ii) every **irregular** gate is expensive because it must be described, every **regular** structure (ROM plane, RAM array, bit slices) is nearly free because a loop generates it; (iii) low-Hamming-weight encodings pay (a 0-bit costs nothing); (iv) R4's in-world placer/router (28 KB, ~2x10^5 NAND as ROM-logic [E]) is out of the question.

## 4. The fixed-point view (why this is a limits experiment)
Total = irregular gates G_irr (CPU/sequencer control, decode, arm driver) + ROM-logic(code + description of G_irr) + registers/RAM. The description of G_irr is itself ROM-logic, but the ROM plane's layout is derived from its own contents (the builder reads a word through the normal read path and emits a wire per 1-bit), so **the ROM needs no separate description**; only the irregular logic around it does. Minimizing the total therefore means: minimize irregular logic, maximize regularity, choose encodings with few ones. The resulting number is a concrete upper bound on a self-reproducing machine in this world; the structure of the optimum (what dominates) is the interesting result.

## 5. Candidate architectures (to compare by experiment, not by argument)
- **S: hardwired sequencer quine.** Nested-loop counters + a small ROM plane of per-object parameters + the arm register driver. Smallest control, no stored-program overhead, not Turing complete. Likely the lowest metric [J]; the ROM plane holds the only irregular data.
- **M8: minimal 8-bit accumulator machine** (ACC8/Hack-vN-like, 705-1,203 NAND [M, ISA study, CPU only]) + program in ROM-logic. Bridges to R6.
- **B1: bit-serial machine** (nandgen serial anchor 389 NAND/39 DFF at k=4 [M]) with delay-line registers. Fewest gates, most ticks.
For each: gates, DFF, ROM ones, words, ticks to complete the quine, arm commands, board area. Ticks matter for verification: gatesim ~255k ticks/s, rndp ~55-60k ticks/s [M], so a design needing more than ~1-2 G ticks cannot be verified end-to-end and would need checkpoint windows.

## 6. Layout and quine mechanics
- **Layout:** precomputed (offline router/placer from R3c/R4 tools, pitch ~6) for the irregular logic; **generated by loops** for ROM plane and RAM/shift-register arrays. Data for the irregular part is stored in the ROM plane in a compact form (R3c needed 20.9 KB of layout data [M]; that must drop by an order of magnitude, so the irregular logic has to be small and gridded).
- **ROM plane:** words x bits grid; a 1-bit = a via/stub joining word line and bit line; builder emits `TRACK`/`VIA` per 1 while scanning its own address space.
- **Start:** RUN wire last (as R3c/R4); child shifted by a constant DX, with the arm-relative origin offset set explicitly (the R4 lesson [M]: without it the child overlaps the parent).
- **Check:** `compare_gen.py` (parts, segments, vias identical to the parent shifted by DX); the ROM comparison goes away (no ROM part), instead compare the gate-level ROM wires as ordinary copper.

## 7. Verification ladder (reuse from R4)
Python generator/reference -> behavioral model of the machine -> `gatesim_rs` (needs a "closed machine" mode: no ROM/RAM ports; trivial) -> rndp quine with `--rom off --ram off` (`--cmd-log` for the robot-command log). Every layer gets one check that does not share assumptions with the reference: the parent-vs-child geometry check, and a connectivity check of the built world against the netlist (R4's `validate_world.py`).

## 8. Experiments before building (each small)
**Done: E1, E2, E3** - see `E1_E3_REPORT.md` (numbers above are updated from them). **Added after E3:** E6 description encoding (bits per described gate with locality order and no decompressor), E7 regularity (bit-sliced/counter designs: gates described vs gates present). The table below keeps the original plan.

| id | question | method | acceptance / output |
|---|---|---|---|
| E1 | ROM-as-logic cost | generate the decoder + OR planes in nandgen for N = 64-4096 words, W = 8-16 bits, ones-density 10-50 %, with and without the nandgen optimizer; count NAND/DFF; verify by gatesim | NAND per word and per 1-bit with ranges; whether optimization helps and whether it breaks self-derivability of the layout |
| E2 | RAM/register cost | build addressable RAM (64-1024 bits), shift-register memory, and register file in nandgen; measure NAND/DFF per bit and access ticks | table in metric units; where delay-line wins |
| E3 | ISA re-ranking under the new price list | redo ISA_COMPARISON section 4 with ROM per-bit ~1-2 NAND, RAM per E2, description cost per irregular gate from section 3, plus S and B1 | ranked table with uncertainty; pick 2 finalists |
| E4 (DONE, see end of file; scale ended up ~178k parts, not a toy) | Quine skeleton at small scale | smallest quine of a toy sequencer (e.g. 100-200 NAND) in rndp; count commands, ticks, area; check the DX/offset logic | confirms the mechanics and exposes the dominant term early |
| E5 | Encoding weight | for the finalists' programs, compare ROM ones with plain, inverted and Hamming-weight-minimizing encodings | ones saved |
Order: E1, E2 in parallel, then E3, then E4/E5. A go/no-go for each finalist follows E3-E4.

## 9. Risks and open points
- The ROM and description costs are estimates until E1; they could move the optimum between S and M8.
- Offline optimization of the irregular logic (the in-world improver is dropped for R5) can still break regularity; judge it by total (gates + description), not by gate count.
- Delay-line memory ties the program's timing to the loop length (a design constraint, not only a cost).
- Compact layout of a sequencer plus ROM plane may need a purpose-made placer; R3c's generic router at pitch 6 is the fallback.
- Inverted logic: the ROM plane naturally produces inverted outputs; polarity handling must be designed in, otherwise it costs inverters (gates).
- Single seeds/netlists as always; no variance is measured.

## Update after E6/E7 (see E6_E7_REPORT.md)
- Netlist description with a plain relative-distance + Elias-gamma code: 9 bits/gate (Hack-vN-AB, MEASURED) to 13-14 (RV32, R3c); xz on text is 26-29, so E3's 13 bits/gate for Hack-class machines is pessimistic (about 9).
- Layout description: general router output 127.5 bits/gate (MEASURED); compact R3c layout 55 bits/gate (earlier measurement). Layout is about 6x the netlist cost.
- In-world placer+router (R4 code, 9,392 B) vs explicit layout: break-even about 1,600-1,800 gates (ESTIMATE). A Hack-vN-sized R5 (757 gates) should use an explicit compact/regular layout, not a router.
- Regularity: Hack-vN-AB core 64% of gates are LZ copies and only 136 distinct depth-6 cone shapes among 2,034 gates; RV32 and R3c are much less regular. A generator for the regular part is plausible but unmeasured.
- Not analysed: the measured Hack-vN/ACC8 netlists (not on the workspace disk).

## Update after E4 (2026-10-24; details and file list in e4/E4_RESULT.md; labels as above)
Built: a token-ring ROM plane (one DFF per row, 24 columns, INV+NAND per 1-bit) plus a 981-NAND + 77-DFF control engine ("engine2") that (pass 1) decodes a compressed description of its own layout and (pass 2) dumps the plane, then (C) runs explicit rows for the ARM part, ring-start wire, 13 long ARM wires and the late EN/run ties. No CPU, no ROM/RAM parts (`rndp --rom off --ram off`).
**Result [M]:** W = 11,350 rows (16 interpreter + 899 pattern + 9,833 layout words + 231 pad + 370 explicit + 1); 76,818 ones; NAND 165,967, DFF 11,427, **metric NAND + 6 DFF = 234,529**; 833,215 commands to build a child; ~5.15e8 engine cycles; bounding box 429 x 45,760.
Checks [M]: rndp builds the parent (0 refused, 0 faults) and its pad connectivity equals the design (520,768 pins; 0 missing/opens/shorts); the Rust model (== Python model) run at full size builds a child equal to the parent shifted by DX = 900 (parts, vias, merged wires identical); the real routed netlist at gate level (engsim, abstract plane) gives the identical 4,201,838 arm writes. **Not done:** a tick-level rndp run of the whole world (~5.2e8 ticks on 178k parts: not feasible with rndp at ~55k ticks/s).
Dominant terms [M]: plane ones 153.6k NAND (65 %), DFF 68.6k (29 %), row inverters 11.4k (5 %), engine 1.4k (0.6 %). Fixed point: the engine's own gates are described in the stream it decodes, so no bootstrap layout is needed.
Findings that change earlier estimates: (i) the explicit layout stream of a generic router is ~3.5x larger than assumed (E4_INTERIM); the decoder (fmt3: relative mirror coordinates, 1 word per command, 1.1 words/command overall) cut it to 9,833 words for 1,052 gates (~9.3 words/gate, 224 bits/gate in the plane); (ii) the plane is 4 W tall, so the ARM (whose coordinates are 16-bit relative to the ARM part) must sit mid-plane with long wires to the engine (~3 % of rows); (iii) pitch-9 PathFinder routing was needed in the Rust router for 0 overused cells (pitch 7: 34 overused cells; pitch 8: 1); (iv) the in-world model is a pure sequencer, so the E3 ISA ranking is not used by this design.
Open items: (a) re-express the earlier replicators' totals (R2C, R3C, R4) in this metric and compare - not done; (b) E5 (encoding weight) and R6; (c) layout variance: in the final configuration 4 of 5 router seeds reached 0 overused cells, with 9,624-10,372 layout words (used: 9,833); one netlist, one placement order per seed, so this is a spread over router/placement seeds only; (d) the compressed layout stream is the bulk of the plane: 66,212 of the 76,818 ones (86 %) and 9,833 of 11,350 rows [M], so a placer/router that needs fewer commands per gate is the main lever left.
