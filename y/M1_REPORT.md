# M1 report: Hack-vN-AB (address width parameter), AB=14 chosen for Y

Files: nandgen/y/isa/ (copies of the X files, edited; X's own files are untouched). `HACK_AB` env var (default 14; 13 reproduces X exactly; 15 is the maximum because the A-instruction carries 15 value bits).

## Changes
- common.py: AB, ROM_BASE = 2^(AB-1), ARM_BASE = ROM_BASE-16, AMASK, ROM_BYTES derived (AB=13: 0x0FF0 / 0x1000 as before; AB=14: ARM window 0x1FF0-0x1FFF, ROM 0x2000-0x3FFF).
- nl_hackvn.py: PC and A are AB bits, reset PC = ROM_BASE, the A-immediate and AP take rdata[:AB-8]. IR-high stays 5 bits (only C-instruction fields).
- nl_core.py: RAM select = no address bit >= ram_abits; ARM window = addr[AB-2:4] all ones and addr[AB-1]=0; ROM select = addr[AB-1]; rom_abits = AB-1.
- isahack.py: A-value assertion uses AMASK; docs.
- fuzz_hack.py: A-instructions now use the full 15-bit field.

## Size (nandgen level 2 unless noted)
| | AB=13 | AB=14 | AB=15 |
|---|---|---|---|
| bare CPU | 705 NAND + 52 DFF | 730 + 54 | 755 + 56 |
| core, ram_abits 5 | 772 | 802 | |
| core, ram_abits 5, level 0 (Y seed) | 1,886 | 1,958 | |
| level 0 with improved module library (E2) | 1,015 | 1,053 | |

## Verification
1. test_hackvn.py: K1-K4 lockstep, bare CPU, AB=13/14/15 (AB=15 only K1-K4 and fuzz): all ok, tick and access counts identical to X (K1 25,572 ticks, K2 28,156, K3 7,618, K4 86,905).
2. fuzz_hack.py: 30 random 800-instruction images, AB=13 22,921 and AB=14 22,935 instructions compared, 0 mismatches; AB=15 7,654.
3. coretest.py (new): the *core* with decode and an external RAM of 2^10 bytes in lockstep with the behavioural model, AB=13 and 14: boundary-address program (212 instructions), K1-K4, 20 fuzz images (73k instructions), and an **exhaustive decode check of every address** in four CPU states (X, F0, F1, AP0) with random other registers (AB=14: 65,536 checks), covering wdata (the value the CPU reads), ram_we, arm_en and the three address outputs.
4. Rust RNDW simulator vs nandgen.Sim, 4,000 random-input ticks: hackvn AB=14, core AB=14 level 2 and level 0: 0 mismatches (xcheck_y.py).
5. Mutation check of the core decode (rewire one input of a random 'decode'-scope gate): 59 of 60 killed. The survivor (seed 58, gate 137) differs from the core only in states that are not one-hot (checked on 100,000 random valid one-hot states: 0 differences, 200,000 random states: 9,284 differences). Consistent with X's mutation results (survivors only in unreachable states). 40 random-gate mutants over the whole core: 40 of 40 killed.
Notes: an earlier version of coretest.py without the exhaustive decode check let two decode mutants survive (a decode gate only observable for one address pattern); the exhaustive check closed that gap. The kernels alone do not test the high half of the AB=14 space.

## Not done in M1
- HACK_VN.md itself (X's document) is unchanged; this report plus Y_SPEC.md section 2 describe the AB=14 differences. Merge into a HACK_VN_AB.md at M7.
- The mutation sample for the bare CPU (X: 200 mutants) was not repeated; the core mutation sample above covers the changed logic.
