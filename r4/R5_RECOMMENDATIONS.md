# R5: recommendations and experiments   (2026-10-22, written at the end of R4)
Labels: **[M]** measured in R4 (command or file given), **[E]** estimate/extrapolation, **[J]** my judgement. Companion: `nandgen/ISA_COMPARISON.md` (ISA numbers quoted from there are its estimates/netlists, not new measurements).

## 1. What R4 is (all [M], see S1-S7 reports and `sh run_all.sh full`)
| item | value |
|---|---|
| Machine | 3770 NAND (incl. 1 tie) + 81 DFF; RAM part 18 address bits (256 KiB); ROM part 16 address bits (64 KiB window, 28,167 B used) |
| Seed -> child | seed HD 4719 NAND/81 DFF improved to 3770 NAND (-20.1 %); the improved HD is a fixed point of the in-world improver |
| ROM contents | 15,556 B code and constants (hand-written RV32EC, every byte traced to a source line) + 12,611 B hardware description (7 modules, 2389 body entries, 56 ports) |
| Child | 3854 parts, 69.7 k arm commands (24,982 ROM-byte programs, 40,882 track/via), board 872 x 786 cells, child placed 8 cells right of the parent by the program itself |
| Work | 33.4 M instructions; on the NAND/DFF CPU ~0.99 G ticks (29.6 ticks/instruction), 64 min in the Rust gate simulator, ~4.5 h in rndp (S8) |
| Checks | Python reference == assembly, command for command; arm log and final RAM == gate-level CPU; rndp-built world has the netlist's connectivity (0 shorts/opens) |

Where the instructions go (`rvemu --profile`, `tools/profile_report.py`): placement 58 % (lpa_level 34.0, place_order 10.5, build_graph 7.2, chain 6.2), routing 31.7 % (route2 13.9, route3 12.6, route1 5.2), improver 4.1 %, HD flatten 2.4 %, driver/main 3.9 %. Code bytes are inversely related: lpa_level is 588 B of code but a third of the time; improve.s is 4.3 KB (the biggest) but 4 % of the time.

Where the RAM goes (same profile, per phase, bytes touched / bytes whose value changed): build_graph 154 k / 115 k; **place_order 227 k / 184 k (highest address 0x3FE17)**; route1 93 k / 62 k; route2 97 k / 53 k; improver 1 k; flatten 23 k. So the 18th RAM address bit exists because of placement and graph construction; routing alone would fit in 17 bits and the improver in 12. ("Touched" includes reads of never-written zeros, so "changed" is the safer lower bound. Neither is a proof of the minimum: a live-range analysis was not done.)

## 2. What the numbers say
1. **RAM, not the CPU, is the biggest thing R4 carries.** With the ISA_COMPARISON calibration (about 12.3 NAND-equivalents per RAM bit) [E], 256 KiB RAM is ~2.6e7 units against ~4.3e3 for the CPU (3770 + 6 x 81) and ~2.8e6 for the used ROM at f = 1. Whatever the metric, one address bit of RAM (2x) is worth far more than any ISA change, unless RAM and ROM parts are treated as free and only NAND/DFF count. R4's report lists both, which is why they can disagree. **Decide the scoreboard first (section 3, item 0).**
2. **R4's CPU is large next to the candidates.** The byte-serial microcoded RV32EC CPU is 3770 NAND [M]; the ISA study measured Hack-vN 705 NAND/52 DFF and ACC8 1203/62 (CPU only, no memory decode) [M in that study]. A 3-5x smaller CPU is plausible [E], but only the NAND/DFF scoreboard rewards it, and R4's own kernels would get bigger and slower on those ISAs (ISA_COMPARISON: Hack-vN code 670 B vs ACC8 288 B on its four kernels; no RV32EC number exists for those kernels).
3. **The module-level improver reached a fixed point.** -20.1 % on the seed, and a second pass changes nothing [M]. Further gate savings need either new transformations (cross-module, larger cuts, sharing) or a different seed; the improver's own cost is small (4 % of instructions, 4.3 KB ROM) [M], so a stronger one is cheap to afford.
4. **ROM has slack.** 28,167 B used of 65,536 [M]; an image under 32 KB should need only 15 address bits [E, not tried: the CPU generator has to be re-run with ROM_BITS=15 and the whole chain re-verified].
5. **The description is 12.6 KB for 3851 nodes, about 26 bits per node** [M]. ISA_COMPARISON measured 1.5-1.66 B/gate for xz of flat netlists; the module form is already in that range or better, so large gains there need new ideas, not better packing [J].
6. **Time is not the constraint it looked like.** The Rust gate-level simulator does 255 k ticks/s on one core and rndp ~65 k ticks/s [M], so a complete start-to-finish check costs hours, not a week. This changes what is worth testing: whole-program runs at gate level are now routine.
7. **A real defect survived S1-S7 and showed up only when setting up the in-world run (S8):** the child's coordinates are arm-relative, so without an origin offset the child lands on top of the parent (R4 now sets the offset in `main.s`; until then the S5/S6/S7 checks all passed, because the Python reference had the same blind spot and none of them checked parent-versus-child geometry) [M]. Lesson: each layer needs a check that does not share assumptions with the reference.

## 3. Recommendations for R5 (ordered by value over effort; [J] unless noted)
0. **Fix the scoreboard before designing.** Write down what R5 minimizes: (a) NAND + DFF only; (b) a weighted sum with explicit RAM/ROM bit prices (ISA_COMPARISON uses RAM bit = 12.3 units, ROM bit = f x RAM bit); or (c) a vector reported as in R4. Every item below is judged differently under (a) and (b).
1. **Cut placement/graph memory (target 17, then 16 RAM bits).** Evidence in section 1. Candidate changes, each cheap to try with the existing Python reference as oracle: store each net list once instead of NBR/WT/TNBR/TWT (symmetric copies) and recompute from SRC on demand; 8-bit weights; process LPA per level from the flattened leaf order instead of keeping all levels; overlay graph-building scratch with the LPA arrays. Expected: each removed 20-30 KB array lowers the peak only if it is on the peak path, so first draw the per-array live-range chart (experiment E1). Cost: more instructions (placement is already 58 %).
2. **Try ROM_BITS = 15** (free if it works, see section 2, item 4) and re-measure CPU gates (one PC bit fewer).
3. **Port the hottest kernel before choosing an ISA.** Hand-write `lpa_level` (588 B, 34 % of time) for Hack-vN-style and ACC8-style machines and compare bytes/instructions/memory accesses with RV32EC (E3). Only then decide whether a 3-5x smaller CPU pays for the code growth, under the chosen scoreboard.
4. **Strengthen the improver only if the scoreboard counts NAND.** Offline first (E4): larger cut size, GMAX 7-8, cross-module (flatten, improve, re-modularize), shared-subterm extraction; measure gates saved against instructions and ROM bytes.
5. **Keep the verification ladder and add one more rung:** the R4 ladder (Python reference -> Rust emulator -> gate-level CPU -> rndp) found every defect except the overlap above; add an independent geometric check on the command stream (child region disjoint from parent; no part/track in the arm-relative frame outside the board) to `run_all.sh`.
6. **Do not spend effort on faster ticks per instruction (29.6) or a wider datapath** unless the scoreboard has a time term; it costs gates and changes nothing measured above [J].

## 4. Experiments (what to run to get the data; none requires new infrastructure beyond what is in the kit unless noted)
| id | question | method | output | est. effort |
|---|---|---|---|---|
| E1 | True live RAM per phase | extend `rvemu --profile` with first/last-access timestamps per byte (liveness), per array from memmap; chart the peak | minimum RAM of the current algorithms, array-by-array savings table | 0.5 day |
| E2 | Does a compacted memory map reach 17 / 16 bits? | rewrite the memmap of build_graph + place_order with overlays and 8-bit weights; `test_build_graph`, `test_place_order`, `test_pipeline` as oracle | RAM bits, instruction delta | 2-4 days |
| E3 | ISA cost on R4's own hottest code | hand-assemble `lpa_level` and `chain` for ACC8 and Hack-vN (models in nandgen/isa); run against the same inputs; count bytes, instructions, memory accesses | table next to ISA_COMPARISON section 2 | 3-5 days |
| E4 | Improver headroom | Python `ref_improve` with GMAX/cut-size sweep on `cpu_mod.hd` (and on the two ISA netlists for comparison); record gates vs runtime | curve: NAND saved vs search cost; decide on in-world port | 1 day |
| E5 | Quality/effort of placement | vary LPA sweeps and multilevel (`mlpa_order.py`) against board area, total wire length, tracks, arm commands, instructions | Pareto table; may free 10-30 % of the 58 % | 1-2 days |
| E6 | ROM_BITS = 15 | regenerate HD at ROM_BITS=15 (`cpu_gen`, `hdexport`), rerun `run_all.sh full` | gates, ROM image size, pass/fail | 0.5 day |
| E7 | Description size floor | xz/zstd/own coder on the improved HD and on flat netlists; try parameterized modules (repeat counts) and shared-subterm references | bits/node vs structure; is a decompressor in ROM a net win | 1 day |
| E8 | Second-generation closure under the new layout | run child -> grandchild in rndp (child needs RUN, i.e. the S8 world run past the first EN) and compare shifted copies (compare_gen.py logic) | full quine proof at R4 scale; also checks the arm-offset arithmetic once more | 4.5 h wall |
| E9 | Independent geometry check | add to `validate_world.py`: bounding boxes of parent and child disjoint, all coordinates inside the 16-bit arm range | catches the overlap class of error | 2 h |
| E10 | Sensitivity to the netlist | run the whole pipeline on a second, different CPU (e.g. ACC8 netlist) as the seed HD; does the pipeline need changes, how do RAM/ROM/time scale with N | scaling law RAM vs N (measured at N = 3851 only today) | 1-2 days |

## 5. Caveats
- One netlist (the R4 CPU), one placement seed (1) for all counts; no variance is measured.
- ISA numbers are from a separate study with hand-assembled kernels and its own caveats; R4 provides no RV32EC data for those kernels.
- Instruction-to-tick conversion is measured for this program only (29.6); other code mixes may differ.
- "Lower limit" claims: nothing in R4 is a lower bound. R4 shows an upper bound on what a self-improving, self-placing replicator needs in this world (numbers in section 1) and points to which terms dominate it (RAM, then placement code time, then CPU gates).
