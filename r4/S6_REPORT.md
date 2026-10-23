# S6 report: replay in rndp   (2026-10-22)
**Status: PASS for the structural replay (measured). NOT done: replay with the real CPU-driven arm timing, and a golden cell-by-cell comparison (see below).**

## What was done (all measured)
1. `rvemu --armlog` (551,835 arm-register writes) -> `tools/armlog2build.py` -> command file (69,683 commands = the command log; same text format as rndp `--build/--script`, board offset 32).
2. `rndp --build` (direct) and `rndp --script` (driven arm, one register write per tick) both build the world with 0 faults: 3770 NAND, 81 DFF, 1 ROM, 1 RAM (18 address bits), 1 ARM, 3869 nets, 24,174 segments, 16,708 vias, bounding box 871x785.
3. `tests/validate_world.py`: every NAND/DFF pin of the world is on the net the improved netlist requires: 11,472 node pins, 3869 nets, **0 shorts, 0 opens**. Mutation check of the checker: deleting any one track/via command from the build is detected (4 of 4 tried; deleting ROM-byte lines is correctly not a connectivity change).
4. The driven-arm world has exactly the same part pad cells as the direct build (only the 13 harness SOURCEs and the driver's arm are extra). The driven run took 216,649 ticks (the driver skips repeated register values, so this is fewer ticks than the 551,835 writes the real program does).
5. ROM contents in the finished world (24,947 programmed bytes) equal the nonzero bytes of the program image that has the improved HD in it: the child carries the improved HD and the same program (fixed point seen in the physical world).

## Honest limits
- The golden file `golden/cpu_g1_m18.cmds` is a different layout (different node numbering/order, from the earlier pipeline), so a cell-by-cell comparison against it is meaningless; the golden for this pipeline is the Python reference (route_ref), which the S5 command stream equals command for command. Cell-by-cell therefore reduces to S5 identity + the checks above. If you want a frozen golden for the new pipeline, regenerate it from route_ref.
- validate_world does not map ROM/RAM/ARM pins (the arm's EN/RUN late sinks and ROM/RAM bus nets are not checked for shorts to other buses); `lay.expected_keys` needs a Layout object that route_ref does not produce.
- Part-to-node mapping assumes place k = node k (true in route_ref; the in-world program matched it command for command).
- Real arm timing (CPU executing, 26 ticks/instruction) is the S7/S8 run; not done here. The rndp SVG typed ids from earlier are still uncommitted/unfiled.
