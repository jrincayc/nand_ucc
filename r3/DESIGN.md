# Replicator 3 design
- ISA: full RV32EC user level; FENCE no-op; no CSR/trap/ECALL. Halt convention in tests: `jal x0,0`.
- Datapath: byte-serial (8-bit ALU), ~55 ticks per instruction, 128-entry microprogram (83 micro-instructions) as a 7-bit uPC PLA (209 product terms, 56 lines).
- Registers x1..x15 live in RAM at 4*N (x0 gated to 0). RAM 256 B; CPU-private bytes 0x40..0x4F (PC 0x40.., PS copy 0x44..); user data from 0x50.
- Memory map: ROM 0x4000..0x7FFF (PC 14 bits, architectural PC = 0x4000|pc14); ARM window 0x3FF0..0x3FFF write-only, one stored byte = one arm register write (reg = addr&15; registers 11-14 fault in the world); gaps read 0.
- State: 77 DFFs (live, upc, k, IR[32], AR[15], A, R, C, Z, SA, SB). C extension expanded by a 776-gate expander (verified over all 28,822 halfwords).
- Netlist data: hot table, ports, node records (DFFs first, then DFS post-order); reference byte encoding is in tools/hd2asm.py.
- Verification: rvasm vs llvm-mc (4800 cases), rvemu vs clang (native), RTL vs rvemu lockstep, gate level vs RTL tick-for-tick, builder on rvemu vs reference commands, geometry validation, quine in rndp.
- Open: netlist is ~3,000 gates vs 2,090 in R2 (expander and PLA are the targets).
