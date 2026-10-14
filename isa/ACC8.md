# ACC8: custom byte accumulator ISA (von Neumann)

Status: behavioral model `isaacc.py` and gate-level netlist `nl_acc8.py` (1203 NAND + 62 DFF, measured), both pass K1-K4 in lockstep.

## 1. Design goal
Smallest control and datapath that still runs the replicator kernels with computed 13-bit addresses and code in ROM. One ALU operand source (accumulator), one 13-bit data pointer with post-increment, zero page as the operand space. The design was written after seeing the kernels (K1 ROM-to-arm copy, K2 bit unpack, K3 bit-parallel NAND sim, K4 PLACE emitter), so it is somewhat fitted to them.

## 2. Machine state
| Register | Width | Notes |
|---|---|---|
| ACC | 8 | accumulator |
| P | 13 | data pointer; LDXP/STXP post-increment it |
| PC | 13 | reset value 0x1000 |
| Z, C | 1 each | Z set by loads, ALU ops, INCZ/DECZ, shifts, CPL; C set by ADD/SUB/shifts (SUB: C = borrow) |
| IR + operand temp | 8 + 16 | fetch state |

No stack, no CALL/RET, no interrupts. 62 DFF in the netlist (PC 13, P 13, ACC 8, IR 8, operand 13, Z, C, 5 state bits).

## 3. Memory map (shared with all candidates)
One memory port, 13-bit address, 8-bit data. RAM 0x0000-0x0FEF, ARM window 0x0FF0-0x0FFF (write-only, reads give 0, ADDR = A[3:0], EN = write strobe & window), ROM 0x1000-0x1FFF. "Zero page" = addresses 0x00-0xFF, always RAM.

## 4. Instructions (41 opcodes). Encoding changed when the netlist was built, so decode is cheap
Class by opcode bits 7:6: `00` one byte, `01` two bytes (operand zp/imm/branch), `10` three bytes (13-bit address), `11` unassigned (treated as NOP, 1 byte).

| Opcode | Mnemonic | Operand |
|---|---|---|
| 0x00-0x0B | NOP CLC SEC CPL SHL SHR ROL ROR LDX STX LDXP STXP | none |
| 0x40-0x47 | LDI ADDI ADCI SUBI SBCI ANDI ORI XORI | imm8 |
| 0x48-0x4F | LDZ ADDZ ADCZ SUBZ SBCZ ANDZ ORZ XORZ | zero-page address |
| 0x50-0x54 | STZ INCZ DECZ LPZ SPZ | zero-page address |
| 0x58-0x5B | JZ JNZ JC JNC | low byte of target |
| 0x80-0x83 | LDA STA LPA JMP | 13-bit address, little endian |

Semantics (a = ACC, M[x] = memory byte):
- ALU group (imm and zp forms, same 8 functions): LD, ADD, ADC, SUB, SBC, AND, OR, XOR. ACC = ACC op operand; ADC/SBC use C. INCZ/DECZ z: M[z] = M[z] +- 1 in memory, sets Z only.
- STZ z: M[z] = ACC. LDA/STA a: absolute 13-bit load/store (ARM window, fixed buffers). LPA a: P = a. JMP a: PC = a.
- LDX/STX: ACC = M[P] / M[P] = ACC. LDXP/STXP: same, then P = P + 1 (13-bit, wraps).
- LPZ z: P = {M[z+1][4:0], M[z]} (two data reads). SPZ z: M[z] = P[7:0], M[z+1] = P[12:8] (two writes).
- SHL, SHR, ROL, ROR (carry through C), CPL, CLC, SEC, NOP.
- **JZ JNZ JC JNC are page-relative:** if taken, PC = {PC[12:8], operand}, where PC is the address of the *next* instruction. A branch can only reach its own 256-byte page; the assembler rejects others. This replaced the signed relative branch (it saves a 13-bit adder, about 100 NAND).
- JMP to itself halts the behavioral model. Z is set by loads, ALU ops, INCZ/DECZ, shifts, CPL; C by ADD/ADC/SUB/SBC (SUB: C = borrow) and shifts.

## 5. Instruction lengths and timing proxy
1 byte: pointer ops, shifts, flag ops. 2 bytes: zp, imm, branch. 3 bytes: LDA, STA, LPA, JMP. Time proxy = memory accesses (fetch bytes + data reads + data writes); real cycle count depends on the sequencer.

## 6. Measured on the four kernels
| Kernel | code bytes | instructions | memory accesses |
|---|---|---|---|
| K1 ROM->arm copy (N=300) | 49 | 3,911 | 11,732 |
| K2 unpack 40 x 9-bit | 78 | 2,017 | 5,363 |
| K3 60-gate NAND sim | 55 | 1,445 | 4,158 |
| K4 emit 1040 PLACE cells | 106 | 17,724 | 53,954 |
| sum | 288 | | 75,207 |

## 7. Gate-level netlist (measured)
`nandgen/isa/nl_acc8.py` builds it with nandgen (level 2). Interface: rdata[8], reset in; addr[13], wdata[8], we out. One memory address per tick, combinational read, clocked write. States (one-hot): F0 opcode, F1 operand 1, F2 operand 2, X execute, X2 second access of LPZ/SPZ. Every instruction has an X tick, so ticks per instruction = 1 + operand bytes + 1 (+1 for LPZ/SPZ).

**1203 NAND + 62 DFF.** By block: decode 106, control 50, address mux + incrementer 139, ALU 394 (8-bit adder with logic-op taps, operand mux, 6-way result select), flags 42, ACC 31, IR/operand registers 112, P 125, PC 121, write-data mux 82. This is 34 % above my earlier estimate of 900. nandgen xz of the netlist: 1,952 bytes.

Verified: lockstep with `isaacc.py` on K1-K4 (per-instruction compare of PC, ACC, P, Z, C; final RAM and ARM log equal), plus 30 random-instruction programs (every opcode, 16k instructions), plus the Rust RNDW simulator replaying 4000 random-input ticks against nandgen.Sim with 0 mismatches. Mutation check: 150 random single-wire rewires, 17 survived; 9 of those are equivalent circuits (redundant logic), 8 differ only where my tests do not reach (mainly upper PC bits, because test code sits in one page).

## 8. Known weaknesses
- One pointer: K2 and K3 spend many accesses swapping pointers through zero page.
- No indirect-through-P load (P = M[P]); table-of-pointers code needs LPZ and a zero-page copy.
- 16-bit counters cost two INCZ plus a branch each.
- Encoding and opcode list are provisional; branch range is ±127 bytes.
