# ISA comparison for the RNDW replicator CPU (von Neumann candidates)

Scripts: `nandgen/isa/` (`common.py` harness, `isa6502.py`, `isaz80.py`, `isahack.py`, `isaacc.py`, `isasubleq.py`, `compare.py`). Run `python3 compare.py` inside that folder.

## 1. Setup
One 13-bit address space, one memory port: RAM 0x0000-0x0FEF, ARM register window 0x0FF0-0x0FFF (write-only), ROM 0x1000-0x1FFF, reset PC 0x1000. Each ISA is an executable behavioral model; every kernel was assembled by hand, run on three seeds and checked against an independent Python expectation (all PASS). Kernels: K1 ROM->arm copy (N=300), K2 unpack 40 nine-bit fields, K3 bit-parallel NAND sim (60 gates), K4 emit 130 words x 8 PLACE commands (1040 cells). Time proxy = memory accesses.

Models: 6502-lite (97 real opcodes), Z80-lite (real opcodes, no stack/IX/IY), Hack-vN (Hack ALU/encoding, 2-byte instructions from unified memory, plus ONE added instruction AP: A = 13-bit pointer read from mem[A], mem[A+1]; without it Hack cannot reach a computed address from code in ROM), ACC8 (my custom 38-opcode accumulator + 13-bit pointer P with post-increment), SUBLEQ (code in RAM via boot loader, 8-bit cells).

## 2. Measured (all kernels pass)
| ISA | code bytes K1/K2/K3/K4 | sum | memory accesses (sum K1-K4) |
|---|---|---|---|
| 6502-lite | 51/115/89/146 | 401 | 77,914 |
| Z80-lite | 37/66/39/75 | 217 | 50,728 |
| Hack-vN | 112/206/160/192 | 670 | 143,689 |
| ACC8 | 49/78/55/106 | 288 | 75,207 |
| SUBLEQ | K1 only: 236 | - | K1: 59,697 (others 10-24k) |

SUBLEQ: only K1 implemented. Plain SUBLEQ has no bitwise ops and 8-bit signed compares make carry and unsigned tests very awkward (I hit the 0x80 wrap hazard repeatedly), so K2-K4 were not written. K1 alone is 4.8x ACC8 in code and 5.1x in accesses, and its code lives in RAM (236 B of RAM, ~23k NAND-equivalents at 12.3 per bit). Treat "SUBLEQ is worse" as supported for K1, and likely but unmeasured for K2-K4.

## 3. Hardware (ESTIMATES, +-25 %, not netlists)
Component sums calibrated on nandgen anchors (Hack ALU 238 NAND, parallel Hack datapath 489 NAND/32 DFF, serial k=4 389/39, RAM bit ~6.27 NAND + 1 DFF): registers 4 NAND/bit + DFF, pointer incrementers, address mux, decode ~3 NAND/opcode, sequencer. Result NAND/DFF: 6502-lite 1190/76, Z80-lite 1540/100, Hack-vN 800/54, ACC8 900/64, SUBLEQ ~750/80 (incl. loader). Serial datapaths would cut these further for any ISA. These must be replaced by real netlists for the finalists.

## 4. Cost model and what it says
Weighted cost = NAND + 6*DFF, RAM bit = 12.3 units, ROM bit = f x RAM bit.
(a) Program bytes only: at f=0 hardware decides (Hack-vN 1124 < ACC8 1284 < 6502 1646 < Z80 2140). At f=0.5: Z80 12.8k, ACC8 15.4k, 6502 21.3k, Hack 34.0k. At f=1: Z80 23.4k, ACC8 29.6k.
(b) Adding the CPU description in ROM (the child's netlist; 1.65 B per gate from xz of nandgen netlists, which assumes a decompressor kernel costing extra code not counted): the description dominates. f=0.5: ACC8 93k, Hack 103k, 6502 124k, Z80 146k; f=0.1 and f=1 give the same order.
Takeaway: once the machine has to carry its own hardware description, gate count matters ~5-10x more than program size, so Z80-lite (best code density) loses and ACC8 / Hack-vN lead. Their gap (~10 %) is inside the +-25 % hardware uncertainty, so no winner is justified yet.

## 5. Caveats
- Kernel programs are my hand assembly; part of the differences is algorithm choice (e.g. Hack K2 uses a bit loop, others shift).
- Hardware numbers are estimates; the f sweep is a modeling choice, not a measurement.
- The description-size term assumes xz-like compression and ignores the decompressor.
- Time = accesses ignores multi-cycle microarchitectures.
- ACC8 was designed by me after seeing the kernels (some fitting); the others use fixed existing opcodes.

## 6. Recommendation
Build real gate-level netlists (nandgen + RNDW differential test) for ACC8 and Hack-vN next, then rerun section 4 with measured counts. Drop 6502-lite, Z80-lite (hardware too large for the code savings) and SUBLEQ (K1 already 5x worse) unless the ROM-cost assumption changes.

## 7. Update: measured gate-level netlists for ACC8 and Hack-vN (2026-10-13)
Both were built with nandgen (level 2), one memory address per tick, and verified in lockstep against the behavioral models (see `ACC8.md`, `HACK_VN.md`, `NETLISTS.md`). CPU only; memory decode and the ARM window are common to all candidates and not included.

| | NAND | DFF | NAND+6 DFF | xz of netlist | code bytes K1-K4 | accesses K1-K4 |
|---|---|---|---|---|---|---|
| Hack-vN | 705 | 52 | 1017 | 1,256 B | 670 | 143,689 |
| ACC8 | 1203 | 62 | 1575 | 1,952 B | 288 | 75,207 |

My estimates were 800/54 and 900/64: Hack-vN came in 12 % under, ACC8 34 % over (outside my stated +-25 %). ACC8's ALU (six-way result select and operand muxes, 394 NAND), pointer register P and the PC/P/OP load muxes cost more than the component sum assumed.

Cost with the measured description (xz bytes of the netlist) in ROM, RAM bit = 12.3 units, ROM bit = f x RAM bit:

| f | Hack-vN | ACC8 |
|---|---|---|
| 0 (ROM free) | 1,017 | 1,575 |
| 0.1 | 19.9k | 23.6k |
| 0.5 | 95.5k | 111.5k |
| 1 | 190k | 221k |

So with measured numbers Hack-vN is ahead at every f, by 15 % at f=0.5 and 14 % at f=1. The earlier ordering (ACC8 slightly ahead) came from the underestimated ACC8 hardware. Caveats: ACC8 was written once and not optimized (the nandgen cut-rewriting optimizer has not been run on either); Hack-vN reuses the already-optimized Hack ALU. The 1.65-byte-per-gate description size is now measured (1.66 and 1.54). Hack-vN's code size (670 B) and access count (1.9x ACC8) are still the weak side; they matter if ROM is cheap and time matters.
