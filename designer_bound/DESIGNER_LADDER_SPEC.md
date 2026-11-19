# Designer ladder: specification, v0.1 DRAFT (2026-11-15)

A plan for measuring what a designer costs, as opposed to a stored design. Sections marked **[decision]** are choices Joshua made; **[proposal]** are mine and need a yes or no; **[M]** is measured. Nothing in sections 6 to 8 is to be built before the proposals are agreed.

Reads on top of `PROVABLE_LIMITS_NOTES.md` (definitions of Lambda, H and Delta), `DESIGNER_BOUND_NOTES.md`, `nandgen/RNDP_SPEC.md` v0.4, `nandgen/rndp_r4/` (R4).

## 1. Purpose
The project has upper bounds for stored-design replicators (X, R1 to R6) and no figure for a designer. A designer is a machine that reads a specification from a declared class and emits a working design for it. This plan measures how the designer's size grows as the class widens.

It cannot produce a lower bound except in the toy world of section 5. Every other figure is an upper bound for its class.

## 2. Why the specification is on a tape
RNDP has no feedback: the arm is write-only and faults are invisible (`RNDP_SPEC.md` sections 1, 2 and 7). A machine cannot learn about its world by acting, so it must be told. The specification is held on a ROM part that the harness supplies and the machine reads. No rule of RNDP changes.

## 3. Decisions
1. The designer may design a machine other than itself. A fixed point (a designer that designs itself) is not required. **[decision, 2026-11-15]**
2. Rung 3 takes its behavioural description as register-transfer expressions. **[decision, 2026-11-15]**
3. Order of work: step 0 (measure R4), then the toy world, then rung 2. **[decision, 2026-11-15]**
4. Visible faults are parked. Joshua's concern: learning from faults may also need a way to undo things, which would be a significant change. Notes for when it is revisited: a refused command is atomic and lays nothing, so a failed probe leaves no trace; a successful probe leaves permanent parts or copper, which a machine could confine to a scratch region. The cost is the closed-machine property that R1 to R6 and the state-counting bound rely on. If done, it should be a separate world variant, not a change to RNDP. **[parked]**

## 4. The ladder and the metric
| Rung | Specification class | Status |
|---|---|---|
| 0 | One world, one design (stored) | R2c, R3c, R6 |
| 1 | Any netlist within capacity, fixed world geometry | R4, measured in section 5 |
| 2 | Rung 1 plus world geometry on the tape | proposal, section 7 |
| 3 | Rung 2 plus logic from register-transfer expressions | proposal, section 8 |

**Metric [proposal].**
- S = ROM image bytes + RAM bytes written during the run, in bits. This is the initial state plus the working state the run needs.
- The ROM is split into designer code and design input. The design input is on the tape and is reported separately.
- T = instructions executed. Hardware (NAND, DFF, parts) is reported beside S, not inside it.
- Crossover = S of the designer (code plus RAM) divided by S of one stored design for the same task. It is the number of distinct designs a lookup table could hold in the same space.

No rung invents the replication strategy. The builder's method is supplied at every rung.

## 5. Step 0: R4 measured as a designer [M]
Script `r4_designer_measure.py`, output `r4_designer_measure_output.txt` (this directory). It assembles R4's ROM, runs it on R4's own RV32EC emulator with `--profile`, and counts ROM bytes by source file and RAM bytes written. Run on a clone of `nand_ucc` on 2026-11-15.

| Quantity | Improved description | Seed description |
|---|---|---|
| ROM bytes | 28,167 | 28,167 |
| of which designer code | 15,556 | 15,556 |
| of which design input (hardware description) | 12,611 | 12,611 |
| RAM bytes written | 220,132 | 220,137 |
| S = ROM + RAM written | 248,299 B = 1.99 x 10^6 bits | 248,304 B |
| RAM share of S | 88.7% | 88.7% |
| Instructions | 32,288,147 | 33,415,317 |
| Arm register writes | 552,115 | 552,115 |

Designer code by part: improver 4,306 B; router 5,702 B (route1 to route3); placement 3,678 B (build_graph, lpa_level, chain, place_order); description flattening 1,480 B; main and start 390 B.

Reading:
- R4 is a rung-1 designer: it places and routes whatever netlist its description holds, up to 4,080 vertices and 20,480 directed edges, for one hard-coded world geometry.
- Its size is working memory, not program. The code is 15.6 KB; the run writes 220 KB of RAM.
- Against R3c, the nearest stored design (21,470 B image + 256 B RAM = 1.74 x 10^5 bits), R4 is 11.4 times larger. The crossover is about 11 designs.
- This comparison is loose. The two CPUs differ (R4 has an 18-bit address bus and 3,770 NAND against 2,938). R4's layout is about six times the area and uses about 170 track steps per gate against 37. R4's memory map was sized for convenience, not minimised, so 220 KB is the high-water mark of one implementation.
- The instruction counts match `S8_REPORT.md`, so the build is the same program that was verified in rndp.

Checked while measuring: the reference router hard-codes the geometry (pitch 3, the three port kinds, two layers, the part footprints). Rung 2 is therefore mostly new work, not a parameter change.

## 6. The toy world (exact figures) [proposal, outline only]
The enumerable world of `PROVABLE_LIMITS_NOTES.md` section 8, with one addition: a one-word input that tells the machine which of k worlds it is in. The worlds differ in something the replicator must get right, such as the encoding of the port commands.

For each k, exhaustive search gives the least machine that replicates in all k worlds, and the least for each world alone. The ratio is an exact designer-to-design figure. The question it answers: does cost grow like a lookup table (about log2 k bits plus k variants) or level off as one general method takes over?

This is the only part of the plan that yields a lower bound. It needs its own design note before any code. Open decisions carried over: word size and memory cap; who chooses the instruction sets; fixed point or infinite chain of descendants; how the k worlds differ.

## 7. Rung 2: world geometry on the tape [proposal]
**Tape contents.** For each part kind: footprint width and height, and each pin's offset and direction. The number of layers. The arm's register map and command codes.

**Class.** Worlds that obey RNDP's rules with different constants: every pin in an outer column (the escape rule), at least two layers, orthogonal copper, the same short rule.

**Simulator.** rndp fixes the footprints in code. Testing rung 2 needs them read from a configuration file, with RNDP's values as the default. This generalises the simulator and changes no rule. Rust, standard library only. **Needs your yes.**

**Test.** At least five worlds (RNDP plus four variants, for example a 3x2 NAND with pins on other sides, a 2x3 DFF, three layers, permuted command codes) and at least two netlists. Pass means: the emitted commands build in that world's simulator with 0 faults, and the connectivity equals the netlist (`validate_world.py`).

**Method.** Python reference first, with RAM high-water and operation counts reported as measured, counted or estimated, as in `INWORLD_COST.md`. Assembly only if the reference figures justify it.

**Limit of the claim.** The class is infinite and the test set is finite. The result is "works on these worlds", plus an argument for the rest.

## 8. Rung 3: logic from register-transfer expressions [proposal]
**Tape contents.** Registers with widths; one assignment per register per clock; expressions over and, or, xor, not, add, subtract, equality, less-than, multiplexing, bit slices and concatenation, and constants; ports to the ROM, RAM and arm parts.

**What the designer adds.** Bit-level expansion, mapping to NAND and DFF from a small set of rules (for example a ripple adder), then the existing improver, then the rung 1 or 2 layout.

**Test designs.** The R4 CPU, for which an RTL model already exists (`rndp_r4/tools/cpu_rtl.py`, `tests/lockstep_rtl.py`), and the Hack-vN-AB core. Pass means the synthesised netlist matches the RTL in lockstep simulation and then passes the rung 1 or 2 tests.

**To settle before starting.** The exact expression grammar and its binary encoding on the tape; whether the mapping rules count as designer code (I think yes).

## 9. What this will and will not show
- It gives designer figures for three widening classes, and the shape of the growth between them.
- Each figure is an upper bound for its class. Only section 6 can give a lower bound.
- The classes are chosen by us. "General" remains a judgment, and the ladder makes the dependence on the class explicit.
- It says nothing about a designer that learns its world by experiment (decision 4).

## 10. Open items
1. Yes or no on the metric (section 4), the simulator generalisation (section 7) and the rung 3 outline (section 8).
2. The toy-world design note (section 6), which is next in the agreed order.
3. A fairer rung-0 comparison for R4: a stored layout of the same CPU, so the 11.4 ratio compares like with like.
4. Whether to minimise R4's RAM before quoting 2 x 10^6 bits as a rung-1 figure.
