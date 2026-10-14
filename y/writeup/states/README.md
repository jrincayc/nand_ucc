# Saved RNDW states (rndw-state 1) -- restart points for the quine (X) and the self-improver (Y)

Every `*.txt` file is a complete world state written by the simulator (`rndw --save`): grid, tick, parts, wires, ROM contents, DFF values, arm registers.
The `cfg` line carries the grid size and the ROM address bits, so a state is restarted with just `--world`:

    rndw --world states/improver_gen2_start_tick0.2M.txt --steps 1000000 --save out.txt

`rndw` is the dependency-free Rust simulator in `nandgen/rndw/` (`cargo build --release --offline`).  A restart continues exactly where the
state stopped (checked: resuming `improver_gen2_built_tick110M.txt` for 90 M ticks built generation 3, identical to the reference).
Add `--svg-at-end --svg-window X0,Y0,X1,Y1 --svg-scale S --out-dir DIR` to draw a window of any state.

Generation g sits in the stripe whose arm origin is (0, 140 g) for Y (stripe 140 for X's 22): generation 1 is built by the harness driver
from the reference command script, generation n+1 is built by generation n through its own arm.

## X: the quine (Hack-vN, 4 KiB ROM, 32 B RAM; 12 ROM address bits)
| file | tick | contents |
|---|---|---|
| quine_gen1_start.txt | 36,652 | generation 1 just built by the driver (2,550 NAND + 308 DFF + ROM + arm), starts running |
| quine_gen2_built_tick8.0M.txt | 8,036,652 | generation 1 has built generation 2 (the first complete copy) |
| quine_gen2_running_tick9.0M.txt | 9,036,652 | generation 2 running, building generation 3 |
| quine_gen3_built_tick16.4M.txt | 16,436,652 | generation 3 complete (3 generations, 0 faults) |
| quine_gen4_started_tick17.2M.txt | 17,236,652 | generation 3 has started generation 4 |
| quine_gen1_seed.script | | the driver's script (place / program ROM / wire) that builds generation 1 |

## Y: the self-improving CPU (Hack-vN-AB, 16 KiB ROM, 256 B RAM; 14 ROM address bits)
| file | tick | contents |
|---|---|---|
| improver_gen1_start_tick0.2M.txt | 196,267 | generation 1 = textbook seed (15,495 NAND + 2,104 DFF), just built by the driver, starts running |
| improver_gen2_start_tick0.2M.txt | 188,506 | generation 2 = the improved machine (14,549 NAND + 2,104 DFF) built by the driver, starts running: use it to watch the fixed point |
| improver_gen2_built_tick110M.txt | 110,196,267 | generation 1 has built generation 2 (verified equal to the reference); generation 2 is running and has placed generation 3 |
| improver_gen3_built_tick200M.txt | 200,196,267 | generations 1, 2, 3 complete and verified; generation 3 has placed all of generation 4 and wired about two thirds of it |
| improver_gen1_rom.bin, improver_gen2_rom.bin | | the two 16,350-byte ROM images (they differ only in the module records) |
| improver_gen1_seed.script | | the driver script that builds generation 1 |

`SHA256SUMS` lists the hashes of all of these files.
