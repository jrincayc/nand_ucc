# R5 design note: pruned-architecture quine, program in constant NAND gates   (draft 1, 2026-10-22)
Status: **discussion draft, nothing built.** Labels: **[M]** measured (R4 or earlier studies), **[E]** estimate to be replaced by an experiment below, **[J]** judgement.
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
| E4 | Quine skeleton at small scale | smallest quine of a toy sequencer (e.g. 100-200 NAND) in rndp; count commands, ticks, area; check the DX/offset logic | confirms the mechanics and exposes the dominant term early |
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
