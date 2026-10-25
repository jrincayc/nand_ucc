# Hand-off: RNDP replicators R1-R6 (state at 2026-10-25)

Supersedes the replicator parts of `HANDOFF.md`, `HANDOFF_QUINE_AND_IMPROVER.md` and `HANDOFF_3_TAU_FROM_X_AND_Y.md` for the RNDP world. Start with `RNDP_REPLICATORS_TUTORIAL.md` (how to run and rebuild each replicator) and `rndp_r5/REPLICATOR_COMPARISON.md` (all numbers).

## 1. Question and metric
Lower limits on self-replicating machines (von Neumann threshold) in the RNDP world: a robot arm, NAND gates, DFFs, a 2-layer copper grid with vias (`RNDP_SPEC.md`). Metric: units = NAND + 6 x DFF; the arm is a free primitive. Every replicator rebuilds a copy of itself (shifted by a constant DX), then starts it with the RUN wire last. Quine check: child == parent shifted by DX (`compare_gen.py`).

## 2. Results (units; details in REPLICATOR_COMPARISON.md)
| R | what | units |
|---|---|---|
| R1 | Hack-vN-AB, ROM part, RAM from 128 gate tiles, hand-lane layout | ~56k |
| R2 | R1 with a RAM part | ~48k |
| R2c | R2, compact placed/routed layout | ~99.5k |
| R3 / R3c | RV32EC core, lane / compact | ~71k / ~170k |
| R4 | RV32EC improver (in-world placer/router, 256 KiB RAM part) | ~26.0 M |
| R5 | pruned quine, program as constant NAND plane, no ROM/RAM parts, not Turing complete | 234,529 (E4), **198,526 (E5)** |
| R6 | Hack-vN-AB quine (Turing complete) that builds its own ROM plane + RAM tiles from gates, no ROM/RAM parts | **141,277** (134,797 NAND + 1,080 DFF) |
R1-R4 numbers are not comparable with R5/R6: they use a ROM and/or RAM part, which is free in the metric. Among the all-gates designs (no parts), R6 (141k, Turing complete) is smaller than R5 (198k, not Turing complete), because R5's token-ring plane and 11k DFFs cost more than R6's compact Hack core plus a 16 KiB image.

## 3. R6 (done this session)
Design: `rndp_r6/R6_DESIGN.md` (Measurement 9 is final). Stored compact R2c core layout with edge pins, ROM plane (plane3) and RAM block (128 R1-style tiles) emitted by the Hack builder through a glue VM, templates, parametric interface-wire bytecode, Huffman-coded core path stream (Huffman added ~5k NAND of plane ones but was needed to fit 16 KiB). Image 16,006 B (cap 16,384; Hack ROM at 16384..32767, `HACK_AB=15`).
Verification: model run 754 M Hack instructions -> 763,734 arm commands equal to the reference except RAM-block track segmentation (identical copper); whole board in rndp: 0 opens/shorts over 406,564 pins; tick-level quick test 452 commands, 1 M ticks, 0 mismatches. Board 1,696 x 7,840 cells.
Not done: full tick-level quine (about 764k commands x ~318 ticks at ~470 ticks/s: infeasible), so ticks/generation is unmeasured.

## 4. Where things are
- Tree per replicator: `rndp_r1 ... rndp_r6`; simulator `rndp`; layout tools `rndp_layout`; Hack ISA/assembler `y`; spec `RNDP_SPEC.md`.
- R6 test helpers: `rndp_r6/tests/` (cmp3/cmp4/cmpd/cmplog compare command streams, dumpcmds, shiftb, run_emit, reg_plane.sh). Untested after being moved there.
- Removed from the Project to save space (regenerable): hand-lane `*_data.asm` (`tools/hd2asm.py`), R4 `hd/m18/cpu_g1.{hd,nl}`, `cpu_seed.hd`. `golden/cpu_g1_m18.sha256` is now orphaned. The Project is near its 2.0 MB cap; remaining removal candidates: old `y/hd/core*.hd` variants, `rndp/analysis` outputs.
- Archive of this session's files: `r6_session_files.tar.gz` (given to Joshua, not in the Project).

## 5. Caveats and lessons
- 40-tick warm-up in rndp before adding RUN wires, or the CPU never starts.
- Assembler has no `&`; model supports AB <= 15 only; pip needs `--break-system-packages`.
- `compare_gen` needs a 24-cell margin (child wires extend ~16 cells left of the child).
- Set the arm-relative origin explicitly (R4 lesson).
- Layout annealing flags for the `.lay` files were not recorded; keep `r2c_vp_p5.lay`.
- Unverified: the tutorial commands for R2c-R5 were taken from READMEs, not re-run; `--rom/--ram off` flags for R5/R6 inferred.

## 6. Suggested next steps
1. R6 variants: smaller ROM image (drop Huffman if a better layout shrinks the stream), or an 8 KiB bank fallback (noted earlier).
2. Measure ticks/generation for R6 with a checkpointed or windowed tick run, or a faster simulator.
3. Add an improver on top of R6 (R4 is the only improver, at 26 M units, using ROM/RAM parts); that is the open gap for the "replicator + self-improvement" threshold.
4. Feed R5/R6 numbers into the tau_i / tau_c discussion of `HANDOFF_3_TAU_FROM_X_AND_Y.md` (R6 is a stronger upper bound than R1-R4).
5. Re-run the tutorial end to end from a clean checkout to catch stale paths.
