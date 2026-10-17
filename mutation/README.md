# Mutation tools for the RNDW von Neumann threshold study (2026-10-16)

Results: `nandgen/RNDW_VON_NEUMANN_THRESHOLD.md` (sections 11 and 12). Simulator used for stage 2: `nandgen/rndw_mut/`.
Scripts are the working copies from the session; paths such as the states directory in `load.py` (`SD`) must be edited. The ROM images come from `rndw_states_M7.tar.gz`.

## ISA level (fast C emulator of Hack-vN-AB plus the arm command log)
- `hack.c`: emulator. Build: `gcc -O2 -shared -fPIC -o libhack.so hack.c`. Records fetched/read bytes, the arm command stream, collects PROGRAM_ROM bytes as the child image, and can compare against a reference stream.
- `emu.py`: ctypes wrapper (`emu.run(...)`). `pymodel.py`: Python port of `isahack.CPU` + machine for differential tests; `difftest.py` (400 random images, 0 mismatches); `cmp_real.py` (real X/Y images).
- `load.py`: reads X/Y ROM images from the states directory. `validate_states.py`: checks emulator output against the saved worlds (placements, wires, child ROM).

## Experiments
- `audit.py` (E1): byte audit, classes FIX / TOREF / SAMEHW / HWDIFF / CRASH; usage `audit.py X|Y stage1|stage2 N|joint N`.
- `e2.py` (E2 / E6): `e2.py X bits all|N` single-bit mutants with chain following; `e2.py X|Y dead` for all-zero and halt-only images.
- `e3x.py`, `e3y.py` (E3, X): relabel RAM variable addresses in the ROM image and verify by emulation.
- `mutprep.py`, `mutbatch.py` (section 12): sample HWDIFF mutants (`mutprep.py sample 100`), write their command streams and child ROMs, run `mutrun child` (from `rndw_mut`) on each.
- `diffs.py`: what the replicating mutants rewired (maps wires to node numbers using `quine_gen1_start.txt`).
- Data: `mut_sample.json`, `mut_rows.json` (per-mutant results of the 100-mutant run).
