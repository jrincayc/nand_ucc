# Hack-vN machine in the RNDW world

Status (2026-10-13): built and running in the Rust RNDW simulator. All four kernels run to completion on the gate-level machine with **0 faults** and the results match the behavioral model.

## What it is
One nandgen netlist (`nl_machine.py`) holds the CPU (`hackvn_core` in `nl_hackvn.py`, 705 NAND + 52 DFF), a RAM built from NAND + DFF, and the address decode. The ROM and the ARM are native RNDW parts outside the netlist. `export_world.py` writes the whole thing as an `rndw-state 1` seed world: every part placed on a pitch-3 grid at origin (300,300), every wire listed, the kernel image written into the ROM, the CPU in its post-reset state (state F0 and PC 0x1000 set).

| Block | NAND | DFF |
|---|---|---|
| CPU | 705 | 52 |
| RAM, 1 KiB (8192 cells, read mux, write decode) | ~51,000 | 8,192 |
| Machine total (with tie-high NAND, decode) | 52,177 | 8,244 |
| ROM | one part, 4 KiB (12 address bits) | |
| ARM | one part | |

Memory map: RAM 0x0000-0x03FF (reads of 0x0400-0x0FEF give 0, writes there are ignored), ARM window 0x0FF0-0x0FFF (write-only), ROM 0x1000-0x1FFF. The RAM is 1 KiB, not the 4080 bytes of the earlier map, because the kernels only need addresses below 0x0400; `build_machine(ram_abits=...)` takes other sizes. `run` is wired to a tie-high NAND (an unwired NAND); `reset = NAND(run, run)`. An arm-built child would wire `run` last (spec section 7), which is not exercised here.

## Results (`verify_world.py`, seed 1)
| Kernel | ticks run | Result in the RNDW world |
|---|---|---|
| K1 ROM to arm copy | 25,700 | 0 faults; RAM equal; the second (unwired) ROM at (0,0) holds the first 300 bytes of the parent ROM, written by PROGRAM_ROM commands from the program |
| K2 unpack 9-bit fields | 28,300 | 0 faults; RAM equal to reference (output at 0x0200) |
| K3 bit-parallel NAND sim | 7,800 | 0 faults; RAM equal (60 gates computed at 0x0300) |
| K4 PLACE emitter | 87,100 | 0 faults; 1,040 DFFs placed at exactly the expected coordinates |

Run time in the Rust simulator: 2 s (K3) to 18 s (K4), 52k NAND and 8k DFF.

## Honest limits
- The CPU starts in its post-reset state by seed-world configuration; a reset pulse (run unwired) was not simulated in the world.
- K3's eight input bytes are preloaded into RAM cells in the seed world (the kernel spec assumes them present).
- The ROM image is the kernel only; nothing yet builds the child's CPU and RAM, only fragments (K1 copies bytes, K4 places parts).
- Comparison checked is end state (RAM, child ROM, placed parts), not a per-tick trace against the Python machine; the CPU netlist itself was checked per instruction earlier (NETLISTS.md).
- Placement is a plain grid in netlist order, not an optimized layout.

## Reproduce
In `nandgen/isa/` with `nandgen.py` on the path and the Rust simulator built: `python3 verify_world.py` (all kernels) or `python3 verify_world.py K4`. Seed and final states land in `world_out/` (about 3.8 MB each, not filed).
