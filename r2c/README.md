# RNDP Replicator 2c -- compact Hack-vN-AB quine (ROM and RAM)

Same machine as `rndp_r2` (2,090-node Hack-vN-AB core, 128 B RAM part, no improver) but the child is laid out **compactly**:
NAND/DFF sites on a 5x5 pitch grid, routed by the generic router in `rndp_layout`, instead of the loose dedicated-lane layout.
The builder program no longer carries a per-node netlist; it carries the placed-and-routed result as ROM data.

| | R2 (loose) | R2c pitch 6 | R2c pitch 5 (final) |
|---|---|---|---|
| board | loose (see rndp_r2) | 308 x 320 | **262 x 274** |
| ROM bytes | see rndp_r2 | 12,937 | **13,050** (code 2,178 + data 10,872) |
| builder RAM high-water | | 54 B | 54 B |
| builder instructions | | 3.4M | 3.47M |

Verification (all pass): builder on the instruction model == independent ROM decoder == layout copper (`tests/run_builder_c.py`);
layout built in rndp, pin nets == netlist, 2,108 nets, 0 problems (`validate_layout.py`); full quine in rndp, 15M+ ticks, 0 faults, **QUINE PASS**
(2093 parts, 9867 segments, 2120 vias, 12,435 ROM bytes identical), first EN around tick 8.87M.
Pitch 4 does not route.

## Files
`hd/core_r7_ram.hd` (netlist source), `hd/lay_data.asm` (GENERATED from `rndp_layout/data/r2c_p5.lay`), `src/builder_c.asm` + `ram_c.asm` + `macros.asm`
(builder), `outc/` (rom.bin, rom.lst, symbols), `tests/run_builder_c.py`, `tests/compare_gen.py`, tools as in `rndp_r2`. Loose-layout files are kept for reference.

## Pipeline
```
python3 ../rndp_layout/tools/nl_export.py tools hd/core_r7_ram.hd work.nl
../rndp_layout/layout/target/release/layout work.nl r2c_p5.lay px=5 py=5 ml=16 mr=16     (or use ../rndp_layout/data/r2c_p5.lay)
python3 ../rndp_layout/tools/lay2asm.py r2c_p5.lay work.nl hd/lay_data.asm --hack
HACK_AB=15 python3 tools/asm.py -o outc src/macros.asm src/ram_c.asm src/builder_c.asm hd/lay_data.asm
HACK_AB=15 python3 tests/run_builder_c.py outc work.nl r2c_p5.lay
python3 ../rndp_layout/tests/validate_layout.py work.nl r2c_p5.lay outc/rom.bin
python3 ../rndp_layout/tools/make_seed.py work.nl r2c_p5.lay outc/rom.bin WORK
rndp --rom on --ram on --layers 2 --build WORK/seed.build --steps 40 --save WORK/s1.state
rndp --world WORK/s1.state --build WORK/run.build --steps 15000000 --dump-on-en WORK/en --save WORK/gen1.state
python3 ../rndp_layout/tests/compare_gen.py WORK/gen1.state 262         (run ~10M more ticks first so the child is complete)
```
Note: run past the first EN; the child's last wires finish after ~10M further ticks.
