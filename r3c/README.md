# RNDP Replicator 3c -- compact RV32EC quine (ROM and RAM)

The byte-serial microcoded RV32EC CPU of `rndp_r3` (3,016 nodes with a 15-bit ROM address: 32 KB ROM window), but the child is laid out
compactly: NAND/DFF sites on a 6x6 pitch grid, routed by the generic router in `rndp_layout`. The hand-written RV32EC builder (`src/builder_c.s`,
598 bytes of code) walks ROM data: a 2-bit kind bitmap for the sites, then one routed path per sink, ports (EN last), RUN sinks.

| | R3 loose | R3c pitch 7 | R3c pitch 6 (final) |
|---|---|---|---|
| board | 6200 wide, ~55M cells (ROM_BITS=14 netlist) | 417 wide | **362 x 374** (135k cells) |
| ROM bytes | 7,982 (code 806 + data 7,176) | | **21,470** (code 598 + data 20,872) |
| parts / tracks / vias | 3002 parts / 14,959 segs / 5,971 vias | | 3019 parts / 18,273 builder tracks / 5,293 vias |
| first EN (ticks) | ~11M per generation | ~18.6M | ~19.9M |
| builder instructions | | | 727,585 |

Trade: compactness costs ROM bytes (about 2.7x) for about 400x less area. Pitch 6 vs 7: +1.3 KB of data for -24% area. Pitch 5 does not route.
ROM_BITS=15 was needed (data does not fit 16 KB); the CPU is parameterised (`ROM_BITS` env var in the tools and tests).

Verification (all pass): builder on rvemu == independent ROM decoder == layout copper, ROM before wires (`tests/run_builder_c.py`);
layout built in rndp, 3,034 nets, 0 problems; full quine in rndp (45M ticks, 0 faults) at pitch 6 and pitch 7: parts, segments (collinear
chunks merged), vias, 20,468 ROM bytes identical, **QUINE PASS**. Existing CPU tests (lockstep, gate-vs-RTL, clang cross-check) pass at ROM_BITS=15.
Registers 11-14 of the arm fault on write; the builder never touches them.

## Pipeline (ROM_BITS=15 in the environment)
```
python3 ../rndp_layout/tools/nl_export.py tools hd/cpu15.hd work.nl
../rndp_layout/layout/target/release/layout work.nl r3c_p6.lay px=6 py=6 ml=16 mr=16      (or ../rndp_layout/data/r3c_p6.lay)
python3 ../rndp_layout/tools/lay2asm.py r3c_p6.lay work.nl hd/lay_data.asm
python3 tools/rvasm.py -o outc src/builder_c.s hd/lay_data.asm
python3 tests/run_builder_c.py outc work.nl r3c_p6.lay
python3 ../rndp_layout/tests/validate_layout.py work.nl r3c_p6.lay outc/rom.bin
python3 ../rndp_layout/tools/make_seed.py work.nl r3c_p6.lay outc/rom.bin WORK
rndp --rom on --ram on --layers 2 --build WORK/seed.build --steps 40 --save WORK/s1.state
rndp --world WORK/s1.state --build WORK/run.build --steps 45000000 --dump-on-en WORK/en --save WORK/gen1.state
python3 ../rndp_layout/tests/compare_gen.py WORK/gen1.state 362
```
