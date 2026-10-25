# RNDP replicators: tutorial / introduction

How a human or a future LLM can build, run and check each replicator (R1-R6) in this project. Spec of the world: `nandgen/RNDP_SPEC.md`. Numbers and comparison: `nandgen/rndp_r5/REPLICATOR_COMPARISON.md`.

## 1. The world in one paragraph
RNDP is a 2-copper-layer PCB grid with NAND gates (pads A(x,y) B(x,y+1) Y(x+1,y)), D flip-flops (D(x,y) Q(x+1,y)), vias, and one "arm" that a CPU drives through memory-mapped registers (PLACE, PROGRAM_ROM, TRACK, VIA). A replicator is a machine whose program makes the arm build a copy of the machine (shifted by a constant DX) and then start it (the RUN wire is always wired last). Unit cost metric: NAND + 6 x DFF. Floating NAND inputs read 0.

## 2. Prerequisites and building the simulator
- python3 (stdlib only for all tools), Rust/cargo.
- `cd nandgen/rndp && cargo build --release` gives the `rndp` binary (tests: `cargo test --release`; see `rndp/README.md`).
- The layout tool (R2c, R3c, R6): `cd nandgen/rndp_layout/layout && cargo build --release`.
- Assemblers: `nandgen/y` (Hack-vN-AB ISA, `asm.py`, `HACK_VN_AB.md`). Always set `HACK_AB=15` for Hack builds.

## 3. rndp CLI essentials
`rndp [--rom on|off] [--ram on|off] [--layers 2] [--width W --height H] --build FILE [--world STATE] [--steps N] [--save STATE] [--cmd-log F] [--dump-pads F] [--dump-on-en F] [--checkpoint ...] [--svg-*]`
Standard run procedure (every replicator):
1. Build the seed (everything except RUN wires): `rndp --rom on --ram on --layers 2 --build WORK/seed.build --steps 40 --save WORK/s1.state` (use `--rom off --ram off` where the tree has no ROM/RAM part: R1 is `--ram off`, R5/R6 both off).
2. The 40 warm-up steps matter: the CPU is held in reset; without them it never starts.
3. Add RUN: `rndp --world WORK/s1.state --build WORK/run.build --steps N --dump-on-en WORK/en --save WORK/gen1.state`.
4. Quine check: `python3 tests/compare_gen.py WORK/gen1.state [DX]` (child == parent shifted by DX; parts, segments, vias).
Speed: roughly 450-60,000 ticks/s depending on board size, so large boards (R4-R6) are checked on the instruction model and by structural checks, plus short tick windows, not a full tick run.

## 4. Verification ladder (same in all trees)
(a) builder program on the behavioural model (`tests/run_builder*.py`) emits exactly the reference arm commands; (b) the reference commands built in rndp give pin nets equal to the netlist (`validate_geometry.py` / `validate_layout.py`, no opens/shorts); (c) tick-level seed/run and `compare_gen.py` where affordable.

## 5. The replicators
Each tree is `nandgen/rndp_rN/` with its own README.

**R1** (`rndp_r1`): Hack-vN-AB CPU, 16 KB ROM part, RAM built from 128 gate tiles, hand-lane layout, no improver. 8,809 NAND + 1,080 DFF. Files: `hd/core_r7.hd`, `tools/{hd2asm,ref_flatten,make_seed}.py`, `src/{macros,ram,builder}.asm`, `tests/{run_builder,validate_geometry,compare_gen}.py`.
```
python3 tools/hd2asm.py hd/core_r7.hd hd/core_r7_data.asm
HACK_AB=15 python3 tools/asm.py -o out src/macros.asm src/ram.asm src/builder.asm hd/core_r7_data.asm
HACK_AB=15 python3 tests/run_builder.py out hd/core_r7.hd
python3 tests/validate_geometry.py hd/core_r7.hd
python3 tools/make_seed.py hd/core_r7.hd out/rom.bin WORK
rndp --rom on --ram off --layers 2 --build WORK/seed.build --steps 40 --save WORK/s1.state
rndp --world WORK/s1.state --build WORK/run.build --steps N --dump-on-en WORK/en --save WORK/gen1.state
python3 tests/compare_gen.py WORK/gen1.state
```
**R2** (`rndp_r2`): same, but RAM is a RAM part (2,034 NAND + 56 DFF). Identical commands with `hd/core_r7_ram.hd` and `--ram on`.

**R2c** (`rndp_r2c`): R2 with a compact placed-and-routed layout. Pipeline: `nl_export.py` -> `layout` (px=py=5) -> `lay2asm.py` -> assemble -> `run_builder_c.py` -> `validate_layout.py` -> `make_seed.py` -> rndp. Generic tools live in `nandgen/rndp_layout` (its README documents the .nl and path encodings); commands in `rndp_r2c/README.md`. Final layouts: `r2c*.lay`.

**R3 / R3c** (`rndp_r3`, `rndp_r3c`): RV32EC core version, dedicated-lane (R3: `./run_all.sh [sim]`) and compact layout (R3c, same layout tools, ROM_BITS=15, pitch 6). See their READMEs.

**R4** (`rndp_r4`): minimal-kit RV32EC improver with an in-world placer/router; `R4_README.md`, `run_all.sh quick|full`. Largest (~26 M units, 256 KiB RAM part).

**R5** (`rndp_r5`): pruned-architecture quine; the program is constant NAND gates (token-ring ROM plane), no ROM/RAM parts, not Turing complete. Read `R5_DESIGN.md`, then `e4/E4_RESULT.md` (design and verification) and `E5_REPORT.md` (final numbers, column inversion). Tools in `e4/`: `assemble.py`, `check_world.py`, `cmp_child.py`, `engine2_model.py`, `verify_engine2.py`. Result 198,526 units (E5).

**R6** (`rndp_r6`): Hack-vN-AB quine (Turing complete) that builds its own ROM plane and RAM tiles from gates; no ROM/RAM parts. Read `R6_DESIGN.md` first (Measurement 9 is the final one). Pipeline (run in `rndp_r6`, tools from `rndp_layout`):
1. Layout the core with edge pins: `r2c_vp_p5.lay` (+ `layout_vp.patch` to the layout tool).
2. `lay2asm.py --hack` (CHILD_DX=1730) -> core layout data; `huff_pack.py` -> Huffman path stream.
3. Generators: `plane3_gen.py` (ROM plane), `ramblock_gen.py` + `tile_gen.py`/`tile_paths.py`/`tile_enc.py` (RAM tiles), `iface_gen.py` (interface wires), `hack/gen_tmpl.py` (templates).
4. `hack/mkb.py` composes `builder_r6.asm` from `hack/*.asm` (`gvm2.asm` glue VM, `huff.asm`, `ram_r6.asm` RAM map, `macros.asm`, `emit3.asm`, ...). Options: `--noemit`, `--quick`, `--test=LABEL`.
5. Assemble with `HACK_AB=15`; image must stay <= 16,384 B (now 16,006). ROM is mapped at 16384..32767.
6. Model check: `emit_model.py` / `sim_gen*.py` (~754 M instructions, 763,734 commands equal the reference apart from RAM-block track segmentation, same copper).
7. `assemble.py` (env `OFS`) builds the whole board; `chk_full.py` checks pin connectivity (0 opens/shorts, 406,564 pins).
8. rndp: seed, 40-step warm-up, then run. The quick test (452 commands, 1 M ticks, 0 mismatches) is feasible; the full quine (~764k commands x ~318 ticks) is not (~470 ticks/s).
Result: 141,277 units, board 1,696 x 7,840.

## 6. Pitfalls
- Forgetting `HACK_AB=15` (AB<=15 in the model); ROM cap 16 KiB.
- Skipping the 40-tick warm-up: CPU never starts.
- Child wires extend ~16 cells left of the child board: use the margin in `compare_gen` (CUTM=24).
- Arm-relative origin must be set (R4 lesson) or the child overlaps the parent.
- Some helper test scripts from R6 (cmp4.py, cmpd.py, cmplog.py, dumpcmds.py, shiftb.py) are not filed in the Project.
- The generated `*_data.asm` files of R1, R2 and `y` (hand-lane trees) were removed from the Project to save space; regenerate them with `python3 tools/hd2asm.py HD OUT.asm` (first step of each pipeline).
