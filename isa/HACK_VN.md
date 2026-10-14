# Hack-vN: Hack-derived von Neumann ISA

Status: behavioral model `isahack.py` and gate-level netlist `nl_hackvn.py` (705 NAND + 52 DFF, measured), both pass K1-K4 in lockstep. For comparison the nandgen parallel Hack datapath alone is 489 NAND + 32 DFF with no instruction register or fetch control.

## 1. What changed from Hack
1. **Von Neumann.** Code and data share the 13-bit, 8-bit-wide address space. Instructions are 16 bits, fetched as two bytes (low byte first) from consecutive addresses, so every instruction costs two fetch accesses.
2. **8-bit data, 13-bit A.** D is 8 bits; A is 13 bits; the ALU is 8 bits. M = memory[A]. The A-instruction loads A with a 13-bit value (Hack's 15-bit field, upper two bits ignored). Destination A from the ALU writes A[7:0] only; A[12:8] is unchanged.
3. **One new instruction, AP** (`110` prefix): A = {mem[A+1][4:0], mem[A]}, an indirect load of a 13-bit pointer stored as two bytes in memory (two data reads). Without it Hack cannot form a computed address from code in ROM: unmodified Hack can only reach addresses written as constants in A-instructions, and self-modifying code would need the program in RAM.
4. **Memory-mapped ARM.** Stores to 0x0FF0-0x0FFF go to the arm registers.

Everything else is standard Hack: no carry flag, no shifts (left shift is D+D or D+M), signed jump tests on the ALU output, no stack, no call/return.

## 2. Encoding
- A-instruction: `0 vvvvvvvvvvvvvvv`, A = v[12:0].
- C-instruction: `111 a cccccc ddd jjj`. `a`=1 selects M instead of A as ALU y input. `cccccc` is the standard Hack comp table (0, 1, -1, D, A/M, !D, !A/!M, -D, -A/-M, D+1, A+1, D-1, A-1, D+A, D-A, A-D, D&A, D|A, all 8-bit). Dest bits ddd = A, D, M (bit 5, 4, 3). Jump bits jjj = JGT, JEQ, JGE, JLT, JNE, JLE, JMP; the jump target is A as it was before the instruction; test is on the signed 8-bit ALU output.
- AP: `110 xxxxxxxxxxxxx`.
Halt in the model: a jump back to the A-instruction immediately before the jump.

## 3. Typical idioms (in 2-byte instructions)
| Operation | Sequence |
|---|---|
| D = M[var] | `@var ; D=M` (2 instr, 4 B) |
| M[var] = D | `@var ; M=D` |
| const to D | `@k ; D=A` (k < 256) |
| Conditional jump | `@label ; D;JNE` |
| 16-bit increment (little endian pair) | `@lo ; M=M+1 ; D=M ; @skip ; D;JNE ; @hi ; M=M+1 ; skip:` (7 instr, 14 B) |
| Load through pointer var | `@ptr ; AP ; D=M` |
| Store through pointer var | (D holds value) `@ptr ; AP ; M=D` |
| Chained pointer (table of pointers) | `@tptr ; AP ; AP ; D=M` |
| ARM register write | `@0x0FF0+r ; M=D` |

## 4. Measured on the four kernels
| Kernel | code bytes | memory accesses |
|---|---|---|
| K1 ROM->arm copy (N=300) | 112 | 24,668 |
| K2 unpack 40 x 9-bit | 206 | 27,939 |
| K3 60-gate NAND sim | 160 | 7,553 |
| K4 emit 1040 PLACE cells | 192 | 83,529 |
| sum | 670 | 143,689 |

K2 uses a bit-at-a-time loop with doubling masks because there is no right shift. K3 benefits from AP: the gate table entries are absolute pointers, so `@t ; AP ; AP ; D=M` reads val[a] directly. K4 detects the carry of x+3 with a sign test (old low byte negative, new low byte non-negative).

## 5. Gate-level netlist (measured)
`nandgen/isa/nl_hackvn.py` builds it with nandgen (level 2). Interface: rdata[8], reset in; addr[13], wdata[8], we out. One memory address per tick, combinational read, clocked write (a read-modify-write such as `M=M+1` uses one address in one tick). States (one-hot): F0 low byte, F1 high byte (A-instructions finish here), X execute C-instruction, AP0, AP1. Ticks: A-instruction 2, C-instruction 3, AP 4; ticks are 1.03x the access count on the kernels.

**705 NAND + 52 DFF** (earlier estimate 800/54). By block: control 36, address mux + incrementer 100, ALU 263 (nandgen's Hack ALU at 8 bits), PC 114, A register 123, D 26, instruction registers 41. Registers: PC 13, A 13, D 8, IR low 8, IR high 5 (only bits 12..8 are kept), 5 state bits. nandgen xz of the netlist: 1,256 bytes.

Verified: lockstep with `isahack.py` on K1-K4 (per-instruction compare of PC, A, D; final RAM and ARM log equal); 30 random programs of 800 instructions covering all 18 comp codes, all destinations, all jump conditions and AP (22,915 instructions); the Rust RNDW simulator replaying 4000 random-input ticks against nandgen.Sim with 0 mismatches. Mutation check: 200 random single-wire rewires, 4 survived (1 equivalent circuit, 3 differ only in states the tests do not reach).

## 6. Known weaknesses
- Every operation on memory goes through @addr ; X=M, so code is 4 bytes per simple load/store.
- No carry, no shift, no bitwise tricks: K2-style code is slow; multi-byte arithmetic needs sign-test or zero-test carries.
- Variables must sit at addresses reachable by the 13-bit A-instruction (fine here, all below 0x1000 or in ROM).
- The AP choice (A = pointer in memory) is mine; a different minimal fix (for example a second register AH) was considered and rejected because loading D and the pointer both needed a free register.
