# S2 report: memory-map change (256 KiB RAM)   (2026-10-21)
**Status: DONE (CPU, Rust emulator, regenerated seed/g1 netlists, placement+routing check). Remaining: clang lockstep (`lockstep_rtl.py`) not re-run in the new map.**

## Decision
You chose 256 KiB RAM. New map (parameters `ROM_BITS=16 AB=18 RAM_BITS=18`):
- RAM at 0x00000-0x3FFFF (18 address bits); the 16-byte arm window sits at the top of the RAM space (0x3FFF0-0x3FFFF): writes go to the arm, reads give 0, so RAM there is lost.
- ROM at 0x40000 (address-bus bit 18 selects ROM), 64 KiB (16 address bits), mirrored above.
- The architectural PC keeps 2 stored bytes at RAM 0x40; byte 2 is a hard-wired constant (the ROM-select bit), so the stored PC format is unchanged. AR is 19 bits.
- Old maps still work: width is a parameter (R1-R3 unchanged).

## Changes (all local, not yet filed)
`ucode.py` (AB/ARB, new flags `arrom`, `ldARX`, cond NK2), `rvemu.py`, `cpu_rtl.py`, `cpu_gen.py`, `netsim.py` (RAM width), tests copied/adjusted (`lockstep_rtl`, `gate_vs_rtl`, `randprog`, `xcheck_clang`), new `tests/directed_map.py`.

## Tests (measured, all PASS)
| test | map | result |
|---|---|---|
| randprog RTL vs rvemu | 14/15-bit old maps | PASS |
| randprog RTL vs rvemu | 16/18/18 | PASS, 10 programs x 150 instr |
| gate_vs_rtl, tick-by-tick | 15-bit old | PASS (2 x 8000 ticks) |
| gate_vs_rtl, tick-by-tick | 16/18/18 | PASS (2 x 8000 ticks) |
| directed_map (high RAM, address just below arm window, arm window write/read, ROM and its mirror, auipc/jal/jalr wrap) | 16/18/18 | PASS, 36 instr, arm log as expected |

## Cost of the wider bus (measured, textbook generator before the improver, NOT the g1 HD)
| map | NAND | DFF |
|---|---|---|
| ROM 14 / RAM 8 | 2921 | 77 |
| ROM 16 / AB 18 / RAM 18 | 2993 | 81 |
So +7## Rust emulator (measured)
`rvemu_rs` has `--ab N` (ROM-select bit; default = rom-bits), ROM mirroring (offset masked with the ROM size), arm window reads 0. `diff_rvemu.py` (now uses the r4 tools; earlier it silently imported the older r3c ones) passes: old map 50 programs, new map (ROM_BITS=16 AB=18 RAM_BITS=18) 100 programs x 300 instr; `directed_map.py` also agrees with the Rust emulator (RAM, arm log, instruction count).

## Regenerated netlists for the new map (measured; counts include the one tie node, as the old files do)
| netlist | ROM addr bits | RAM addr bits | NAND | DFF |
|---|---|---|---|---|
| old g0 (hd/cpu_g0.nl) | 15 | 8 | 4613 | 78 |
| old g1 (hd/cpu_g1.nl) | 15 | 8 | 3691 | 78 |
| new seed (hd/m18/cpu_g0.nl) | 16 | 18 | 4719 | 81 |
| new g1 (hd/m18/cpu_g1.nl) | 16 | 18 | 3770 | 81 |
The improver saves 949 NAND (20.1%) in the new map (922 in the old); fixed point holds (`test_improve.py` PASS); the improved HD passes `gate_vs_rtl.py` (2 x 8000 ticks). Fixes needed to get here: `hdmod_export.py` params and `hdexport.py` PORT_ORDER were hard-wired to 8 RAM address bits.

## Placement + routing on the new g1 (measured, normative placement, row-and-channel, R=22, Z=14)
Board 884 x 809 = 715,156 cells, 44,742 commands, 3869 pins/nets, 0 problems in rndp for permutation seed 12. Three other permutation seeds gave 688k, 665k, 691k cells (area only; validation output of those was not shown). The old netlist under the same test: 598k (seed 12). So the 256 KiB map costs roughly 10-20% more area (extra gates, a taller RAM part, 10 more RAM address pins). A comparable old-vs-new average over many seeds has not been run.

## Caveats
- Gate-level test covers 8000 ticks per program only; windows from checkpoints come in S7.
- clang lockstep not re-run in the new map.
