# Y: self-improving CPU in RNDW -- formal spec v1.5 DRAFT (M1-M6 done)

## 0e. Changes in v1.5 (M5)
The improver is in ROM and integrated (M5_REPORT.md). RAM is 256 B (ram_abits 8; measured need 197 B). Records have a fixed extent; the HD starts at ROM_BASE+0x32E0; the chain record stores W-1; the builder runs two phases (place, wire) of 16 per-type groups, running the improver at the start of each group. PROGRAM_ROM of the records happens in phase 0 before any wire. Skip entries (kind 2) encode holes in improved records.

Companion docs: RNDW_SPEC.md (v0.5), HACK_VN.md, BUILDER_NOTES.md (X: the quine), HANDOFF.md. Experiments: nandgen/y/ (enumnand.py, cutrw.py, e2.py, e3.py).

## 0d. Changes in v1.4 (M4)
- **M4 done**: builder.asm (hand-written assembly, 4.0 KB of code) reproduces ref_flatten.commands() exactly; see section 5 and M4_REPORT.md.
- Data format changes made while writing the builder: every record gate is a (kind, a, b) triple; NAND and DFF have records of their own (types 0, 1); chain rules are fixed 5-byte records (PICKHI carries a divisor, not a shift); ports carry their sink pin coordinates; EN is the last port; HD_OFF = 0x1000.
- Open point for the user: the builder takes 4.0 KB, the data 3.1 KB; the improver will not fit into the remaining 1 KB of an 8 KiB ROM. Options at the M4 review: AB = 15 (16 KiB ROM, +72 NAND +2 DFF), or compact the code first (estimated -400 B), or both.

## 0c. Changes in v1.3 (M3)
- Improver renumbering is DFS post-order from the outputs (a-input first); cuts tried smaller first. ref_improve.py is normative; fa 25->9.
- Module record header is 4 plain bytes (flags, n_in, n_out, n_gates); tile gates are 3 bytes (kind,a,b). Module area fixed size (0x200) so the body address is generation independent. Data starts at ROM offset 0x800 (HD_OFF). See hd2asm.py header for the exact layout.
- Added RAM-read ref bytes 0x8A+j; chain/port refs are relative to the tie node.

## 0b. Changes in v1.2
- **M2 done** (tools/asm.py 300 lines, tools/trace_check.py 181 lines; M2_REPORT.md). Source syntax is Hack's: comments start with `//` (so `;` keeps its Hack meaning in `D;JNE`), `.org .equ .byte .word .space .macro/.endm`, expressions with + - * lo() hi(). Listing format `ADDR BYTES | file:line | [macro NAME @call-site] | source text`; long data wraps onto continuation lines. Macro expansions list the *definition* line plus the call site, and the call line itself appears as a zero-byte entry.
- trace_check C1-C6 (section 3, T2) are implemented as stated, with one addition: C5 decodes every instruction with its own tables and compares it to the source text.

## 0a. Changes in v1.1
- **M1 done** (isa/ in nandgen/y/isa/, report docs M1_REPORT.md): Hack-vN-AB at AB=14: CPU 730 NAND + 54 DFF (X, AB=13: 705 + 52); core with RAM interface 802 NAND (ram_abits 5). Seed (level 0) core = **1,958 NAND + 54 DFF**; module-level improvement alone gives 1,053 (generator library swap, as E2). Section 7 updated.
- **RAM placement is one column per byte** (user suggestion): section 4.5 rewritten. The single-row reach limit is gone, so RAM size is no longer capped at 128 B by layout.

## 0. What changed since v0.2
1. **One improver algorithm** replaces "enumerate + composite peephole": 2/3-leaf *cut rewriting* whose replacements are found by *exhaustive synthesis on the spot* (no database), plus duplicate-gate merge and dead-gate removal. Experiment E8 (cutrw.py, Python reference): textbook module -> result (NAND): xor 9->4, mux 8->4, half adder 11->5, **full adder 25->9**, unlisted xnor 10->5, unlisted majority 12->6, and3 4->4 (already optimal), not/and/or unchanged. Every result equals the E1 exhaustive optimum, all functions verified equal. Total search work per module: 0 to 4,535 candidate circuits (FA 4,535, 100 searches).
2. The full adder no longer needs sub-module composition, so **modules stay NAND-only and flat (depth 1)**.
3. Address width is a parameter AB (section 2). 16 is not free (A-instruction has 15 value bits); see section 2.
4. Refs in the body are **node distances** (as in the X stream), not signal numbers, so the flattener needs no signal->node table.
5. The 60-NAND phantom tile of X is not needed: word 0's "previous" input is the tie-high node.
6. Improved modules must be **cached in RAM during a generation** (the child ROM is write-only, and the child's hardware must use the improved modules). This makes Y's RAM larger than X's 32 B; it is the main new cost (section 6.4).

## 1. Goal and success criteria
Generation g0 is the seed: a world built from readable sources (section 3) containing CPU + RAM + arm + ROM. Success:
- S1 (replicate) g0 builds g1: a complete machine (same ISA) with a working arm and a ROM that is a valid next-generation image.
- S2 (improve) g1's hardware has fewer NAND than g0 (weighted cost NAND + 6 DFF), with the same ISA and identical behaviour (equal on K1-K4 and random-program lockstep; module-level equality is exhaustive by construction).
- S3 (continue) g1 builds g2 the same way; g2's description equals g1's (fixed point: no further improvement found) and g2's hardware equals g1's.
- S4 (traceable) every ROM byte of g0 is covered by the listing (section 3), and the audit tests pass.
Reported data: Y_RAM = RAM high-water mark of a generation (bytes), ROM bytes, ticks per generation, weighted cost g0/g1, per module before/after.
M_inf (HANDOFF): the seed design class that both replicates and non-trivially improves; "non-trivial" here = reaches the exhaustive optima on the module ladder AND on two modules not in the library (xnor, and3) without those answers being in ROM.
Scope limit: only combinational library modules are improved. DFFs, the RAM tile/array, the arm, ROM size and the improver's own code are not touched. The claim is "improves its gate-level logic", not "improves itself" in general.

## 2. ISA: Hack-vN-AB
- HACK_VN.md with address width AB parameter (seed X uses AB=13). A, PC and the AP pointer widen to AB bits: AP loads A = {mem[A+1][AB-9:0], mem[A]}; IR-high keeps AB-8 bits. The A-instruction has 15 value bits, so **AB <= 15**. AB=16 would need a new instruction format (a different ISA); if 15 bits is not enough, we stop and discuss RV32EC, as agreed.
- Choose the smallest AB that fits RAM + ARM window + ROM. Expected AB=14 (ROM 8 KiB at 0x2000-0x3FFF, rom_abits=13, reset PC 0x2000). Memory map generalises X: ROM selected by addr[AB-1]; ARM window = top 16 bytes of the lower half (0x1FF0-0x1FFF for AB=14); RAM from 0.
- Cost (measured): AB=14 vs 13: CPU 730 vs 705 NAND, 54 vs 52 DFF (+25 NAND, +2 DFF; AB=15: 755 NAND, 56 DFF). Part of g0 and counted.
- Verification before anything else (milestone M1): regenerate the netlist at AB; rerun test_hackvn.py, fuzz_hack.py, lockstep K1-K4, mutation sample; update HACK_VN.md.
- X (the quine, AB=13) stays as published; Y gets its own ISA instance.
- **Final state (M7, 2026-10-14):** Y runs at **AB = 15** (ROM 16 KiB at 0x4000-0x7FFF, ARM window 0x3FF0-0x3FFF, RAM 256 B at 0-0xFF, rom_abits = 14, reset PC 0x4000); the AB = 14 figures in this section are the original plan and the M1 measurements. The ISA as used is documented in **HACK_VN_AB.md** (delta on isa/HACK_VN.md). Measured at AB = 15: bare CPU 755 NAND + 56 DFF; seed core (level 0, ram_abits 8) 2,021 NAND + 56 DFF. coretest.py was rerun at AB = 15 on 2026-10-14: exhaustive decode check of all 131,072 (state, address) cases ok, K1-K4, boundary program and 20 fuzz images (73,443 instructions) all ok.

## 3. Source tree and traceability
```
y/
  asm/        *.asm  hand-written, every line commented (builder, flattener, improver, libs)
  hd/         core.hd, ram.hd   readable hardware description (symbolic names, comments)
  tools/      asm.py (assembler), hd2asm.py (HD -> commented .byte lines), trace_check.py, make_seed.py
  gen/        generated, committed, diffable: *_data.asm, rom.bin, rom.lst, seed.script
  ref/        ref_flatten.py, ref_improve.py (Python reference implementations of sections 5, 6)
  tests/
```
Rules:
- T1 The ROM image is exactly asm.py's output on asm/*.asm + gen/*_data.asm. No Python emits instructions; macros are fixed expansions printed in the listing.
- T2 asm.py writes rom.lst: address, bytes, source file:line, source text. trace_check.py fails if any ROM byte is not covered by exactly one listing line, if a listing line has no comment, or if a data line has no tag naming what it is (module, instance, port, table).
- T3 hd2asm.py is a mechanical encoder (symbolic HD -> .byte lines with the HD text as the comment). It contains no design knowledge. core.hd is produced by export_hd.py from the nandgen level-0 generator (the textbook design, section 7) and committed; reviewers read core.hd, not the generator.
- T4 Trusted base (small, listed with line counts in the final report): asm.py, hd2asm.py, trace_check.py, make_seed.py (builds the seed world script/state from the same files), the Rust simulator, export_hd.py.
- T5 Audit A (hiding): the seed library must contain only the unoptimised textbook modules; trace_check.py verifies each module's gate count equals the textbook count (not 1, and 2, or 3, xor 9, mux 8, ha 11, fa 25). No lower-cost circuit for any function may appear in ROM.
- T6 Audit B (generality): the improver is also run on modules not in the library: **xnor (textbook 10 -> 5) and and3 (4 -> 4, must be left alone)**, plus 100 random 2-3-input modules checked against the Python reference. Optional stress modules: majority (12 -> 6), 3-input OR (6 expected).
- T7 Hash chain: the log records sha256 of rom.bin, seed.script and each generation's ROM image.

## 4. Description format (HD) -- as implemented by tools/hd2asm.py (M3/M4; the file header of hd2asm.py is the exact byte-level definition)
ROM data starts at HD_BASE = ROM_BASE + HD_OFF (HD_OFF = 0x1000 at AB=14; code is below it).
- `HD_BASE`: `ab` (1 byte). `+0x20`: **directory** of 16 slots x 2 bytes (ROM address of the record of type t, 0 = empty). `+0x40`: **record area** (0x200 bytes, records packed from the start; a child with smaller records leaves the tail unprogrammed). `+0x240`: **body**, then the **chain** record (tile type, count, then the 5-byte rules), then the **ports** record.
- **Records** (types: 0 primitive NAND, 1 primitive DFF, 2+m library module m; the tile module is also a record): `flags` (0 primitive, 1 combinational/improvable, 2 tile), `n_in`, `n_out`, `n_gates`, then `n_gates` gate triples `(kind, a, b)` (kind 0 NAND, 1 DFF with b = a), then `n_out` output signals. Signals 0..n_in-1 are inputs, n_in+g is gate g; a gate refers to earlier signals only. Limits for the improver: comb, n_in <= 3, n_out <= 2, n_gates <= 32.
- **Body**: instance = type byte, then one ref per module input; END = 0xFF. Node numbering: an instance consumes `n_gates` consecutive node numbers. A ref byte is relative to the first node of the instance ("current"): 0x01..0x7F backward distance, 0x80+j ROM data bit j, 0x88 tie-high, 0x89 RUN (only as a direct input of a primitive NAND), 0x8A+j RAM read bit j (output 8+j of the last tile), 0xFD lo hi backward and 0xFE lo hi forward 16-bit distance.
- **Chain**: tile type, count W (<= 255), then one fixed 5-byte rule per tile input: `op, ref(3, padded), param`; op 0 BCAST ref, 1 PREV (param = output j of tile k-1; tile 0 uses the tie-high node), 2 PICKLO (source = node of ref + 2*(k AND param) nodes), 3 PICKHI (source = node of ref + 2*(k / param)). Refs in chain and ports are relative to the tie-high node.
- **Ports**: count, then per port a ref and the sink pin (x, y) bytes relative to the issuing arm. Order: rom_addr0.., arm_addr0..3, wdata0..7, arm_en (EN last so that its wire is the last before RUN).
- Improver (M5) rewrites only the record area; body, chain and ports never change (refs are node distances, independent of ROM addresses).
### 4.5 Placement (not data)
Core nodes: a row as in X: arm at (0,STRIDE); ROM at arm+(0,9); core node i at arm+(6+2i, 9); the tie-high node follows the last core node.
**RAM: one column per byte.** Tile k (RAM byte k) occupies a vertical column: its node j is at arm + (6+2k, 13+2j). All 8 bit slices of one byte are in that column. STRIDE = 140 (a ROM constant of the builder); children are placed at arm+(0, STRIDE). Reach: x up to ~6+2*max(N_core, 2W), y up to 13+2*60; the single-row limit is gone.

## 5. Flattener / builder (ROM program) -- implemented in M4: src/builder.asm (+ src/macros.asm)
Hand-written, commented Hack-vN-AB assembly, a direct transcription of tools/ref_flatten.py: `commands()`. Two passes over the same description (MODE 0 places, MODE 1 wires); between them the ROM is copied (non-zero bytes only, PROGRAM_ROM, before any wire). Shape:
1. `start`: read the chain record (tile type, W); derive the tile gate count, the pointer to the tile's output list, and the x of the last tile column.
2. `pass`: walk the body. Per instance: `lookup` (directory -> record, n_in, n_gates), `decref` the input refs into three 5-byte *sources* (x, y of the driving output pin, RUN flag), then `gates`: per gate read (kind, a, b), `emit` (PLACE, or in MODE 1 `resolve` each input signal and WIRE it; RUN sources are recorded and wired last). The tie-high NAND follows the body. Then the tiles: per tile the same `gates` loop with `WALK` = 1; module inputs come from the chain rules (`resolve` -> tile rules), internal signals from the column.
3. After pass 0: PLACE ROM and ARM, copy the ROM. After pass 1: wire the ports (EN last), then the recorded RUN sinks, then halt.
Positions are 16-bit values kept in RAM; `add16` adds with an unsigned carry test (the ISA has no carry). Variables use 126 bytes of RAM (high-water mark measured on the behavioural model with random RAM preload), so the machine needs ram_abits >= 7 (128 B) until the variables are compacted. Differential test V5: tests/test_m4.py compares the decoded arm writes with ref_flatten.commands() (as a set, plus order constraints); V6 (partial, M4): tests/run_y_world.py + verify_y_world.py run the seed machine in the Rust RNDW simulator (generation 1 builds generation 2).
Cost model: ticks ~ proportional to nodes (about 3,200 ticks per node: 31.1M ticks for the 9,815-node ram_abits 7 machine).

## 6. Improver
### 6.1 Algorithm (ref_improve.py is normative; cutrw.py is its prototype)
Input: module (n_in, gates, outs) with flag improvable. Truth tables are bytes over n_in <= 3 variables (input v = 0xAA, 0xCC, 0xF0 masked to 2^n_in rows); NAND = ~(x & y) masked.
```
repeat until no change:
  merge: gates with identical (a,b) (order-insensitive) are merged; dead gates (not reaching an output) are deleted; gates renumbered topologically
  for each gate root r in order:
    for each cut of r with <= 3 leaves (leaf sets obtained by repeatedly replacing a leaf gate by its two inputs):
      cone  = gates between the leaves and r
      saved = number of cone gates whose every fanout lies inside the cone and that are not module outputs (r counts)
      f     = truth table of r over the leaves (by evaluating the cone)
      if f equals a leaf's table: rewire r's users to that leaf; restart
      for g = 1 .. min(saved-1, GMAX=6): exhaustive search for a g-NAND circuit over the leaves computing f
            (candidates add gate (i<=j) over leaves + earlier new gates, skip a gate whose table already exists,
             prune when targets missing > gates left); first hit wins
      if found: replace r by the new circuit; restart
```
Deterministic: no random numbers, no database, no knowledge of any function. Equality of the result with the input is exact (truth tables), so improved modules are equivalent by construction.
### 6.2 Budget numbers (Python reference)
Searches 0-100 and candidate circuits 0-4,535 per module (table in section 0). On Hack-vN at roughly 100-300 instructions per candidate this is ~1M ticks for the whole library; unmeasured until M5.
### 6.3 Data structures (RAM, per module being improved)
signals table: n_in + up to 32 gate tables (bytes); gates list (a,b) up to 32 x 2 B; fanout counts 32 B; cone/cut scratch ~16 B; search state per level (i, j) up to GMAX=6 levels = 12 B + 6 table bytes. Order of 130 B if done naively; the plan is to share buffers (cone flags as a bit mask in a 32-bit/4-byte set). Must be measured, not assumed.
### 6.4 Improved-library cache
During a generation each library module's current version lives in RAM (or points into the parent ROM if unchanged): improved sizes sum to ~28 gates = ~60 B plus headers ~20 B. Y_RAM is therefore roughly (builder variables ~35 B) + (library cache ~80 B) + (improver scratch ~100 B, aliased with the builder's until the build starts) = **~130-190 B, so RAM 128 B or 256 B**. This is a prediction. Variant B (no cache; re-improve a module at each use, ~315 x 2 improvements per generation) would trade RAM for tens of millions of ticks; only measured if A overflows.
### 6.5 Writing the child ROM
Child ROM = parent ROM bytes up to the module directory (code, body, ports unchanged: refs are node distances, independent of ROM addresses), then the directory slots and module records written from the RAM cache. The directory sits at a fixed ROM address so a size change inside the module area never moves code. Written before any wire touches the child ROM (spec section 7). Unprogrammed cells read 0.
### 6.6 Order within a generation
1. improve all improvable modules -> cache. 2. flatten pass 1 using the cache (child hardware uses improved modules). 3. program child ROM (copy + module area). 4. pass 2 wires, ports, EN, RUN last.
### 6.7 Fixed point
The child's improver runs on its own (already improved) library and finds nothing; g2's description and hardware equal g1's. This is test S3.

## 7. Seed design (textbook, honest)
- Core = nandgen build_core at level 0 for the Hack-vN-AB ISA with the *assembly additions* needed for the Y builder (any added instruction or state is part of the ISA change and listed in HACK_VN.md). Library = the seven textbook modules; constants are explicit instances (ONE = nand(in0, nand(in0,in0)) as nandgen level 0 does).
- Current numbers (**AB=14**, ram_abits 5, Python, M1): core 1,958 NAND + 54 DFF at level 0; module-level improvement alone gives 1,053 (E2, library swapped in the generator; AB=13 gave 1,886 -> 1,015). Expected from the real flattener with the cut-rewrite library: 1,053. nandgen level 1/2 reach 833/802 by cross-instance sharing, which is out of scope (R3 deferred), and should not appear in Y's result.
- The seed is *not* nandgen level 1 or 2.

## 8. Verification plan
V1 ISA widen (M1): section 2 list. V2 asm.py + trace_check.py unit tests (known programs, a deliberate uncovered byte must fail). V3 ref_improve.py vs cutrw.py agree on every library module and 100 random modules; every result checked equal by truth table. V4 asm improver vs ref_improve.py on the same set (gate list identical). V5 asm flattener vs ref_flatten.py (command sequence, as set). V6 RNDW end to end: seed -> g1 -> g2, 0 faults; g1 part counts equal the predicted flattened improved description; g2 == g1; ROM images per section 6.5. V7 behaviour: the child netlist extracted from the RNDW state passes K1-K4 and 30 random programs in lockstep with isahack.py. V8 mutation check on the improver: 50 single changes to ref_improve.py's rules (e.g. wrong saved count, skip dedupe) must be caught by V3-V6.

## 9. Milestones (each ends with a stop for your review)
M1 widen the ISA, verify (DONE, M1_REPORT.md). M2 asm.py + listing + trace_check (DONE, M2_REPORT.md). M3 export_hd + hd2asm + ref_flatten + ref_improve (all Python, no ROM). M4 asm flattener/builder (a quine-style generation with an unimproved library: X-like). M5 asm improver. M6 integration, RNDW runs, audit tests. M7 write-up with data point Y and an updated X comparison.

## 10. Risks / open points
1. RAM size: choose by measured Y_RAM; the column layout (4.5) has no reach limit. A bigger ram_abits costs (RAM bit ~12.3 weighted units) in the metric only.
2. ROM fit: estimate ~5 KB (builder ~2.2 KB code, body ~1.1 KB, ports/tile ~0.3 KB, modules ~0.2 KB, improver ~1.5 KB). AB=14 gives 8 KiB; improver or builder may need to shrink if AB=15 is needed.
3. Instruction count of cut enumeration on a no-shift ISA is the largest unknown (bit sets for leaves/cones, 32-bit masks in 8-bit registers).
4. Equal-cost rewrites and resubstitution are not used; results might be non-minimal for modules where sharing across cones is needed. R2-level only.
5. Sequential modules and the RAM tile are not improved (scope).
6. The textbook module bodies are my construction (nandgen level 0). If you prefer another baseline (for example one from a textbook figure), say so before M3.
7. Weighted-cost metric fixed at NAND + 6 DFF; the ROM cost factor f is reported separately.
