# RNDP world specification: v0.4 DRAFT (simulator exists: `nandgen/rndp`; Replicators 1 and 2 built and verified)

RNDP = Robot + NAND + DFF + PCB (+ optional ROM, optional RAM). A variant of RNDW (`RNDW_SPEC.md` v0.5) in which a wire is no longer an abstract point-to-point edge but copper laid on a grid, so crossings, area and routing effort cost something. Sections marked **[decision]** are choices you made; **[proposal]** are mine and need your yes or no. Section 16 lists what is still open.

Changes in v0.4: Replicator 1 is built, passes the quine check in the simulator, and its measurements are in section 18; the ROM and RAM gate-equivalents are measured at **replicator 5** (the one whose program store and RAM are made of NAND and DFF), confirmed by you after the renumbering (sections 10 and 16); rotation rule and arm-register facts that the builder depends on are now written down (sections 4 and 7); the start-up protocol and its one known tick-0 fault are stated (section 8); the simulator's `--build` option is documented (section 11); section 18 added. Replicator 2 (RAM part) is built and passes the same quine check (section 19). No rule of the world changed.

Changes in v0.3: SOURCE stays 1x1 and the driver harness lays 13 tracks (section 4); default maximum RAM and ROM address width is 16 bits, with 32 allowed by command line (section 9); the ROM gate-equivalent is to be measured when replicator 5 is built (section 10); **all replicators use exactly 2 layers** (sections 5 and 15). Router experiment results are in `nandgen/rndp/analysis/` (section 17).

Changes in v0.2: replicators renumbered 1 to 5 (section 15); RAM footprint has DIN and DOUT on opposite sides (section 4); command code 2 stays reserved, TRACK is 4 and VIA is 5 (section 7); the world imposes no track-laying order (section 8); PLACE onto existing copper kept (section 7); two drivers on one net confirmed as the only detectable short (section 6). Corrections: KIND code 4 was used for both RAM and SOURCE (SOURCE is now state-file code 5 and not placeable); the RAM gate-equivalent in section 10 was recomputed from the actual RAM tile in `nandgen/y/hd/core.hd`.

## 1. Purpose and non-goals

The point of RNDP is to price routing. RNDW gives away routing for free (wires cross freely, have no length, area or delay). RNDP keeps the RNDW rule that **the world may check a layout but never find one**: the arm says which cells carry copper, the simulator accepts or refuses. Any routing intelligence must therefore live in the replicator's circuit or program, and shows up honestly in its ROM image and hardware.

Non-goals: power and ground distribution, clock distribution (the clock is the tick), wire delay, thermal limits, diagonal copper, arm travel time. **[decision]**

## 2. What carries over from RNDW

Ticks and the tick procedure (section 3), NAND/DFF/ARM/SOURCE semantics, arm registers and relative signed 16-bit coordinates (v0.5), the ROM lock idea, fault counting (faults are ignored, counted and invisible to circuits), the tie-high NAND (both inputs unconnected), SVG and batch/interactive CLI. Combinational cycles remain allowed with the same event limit.

What changes: WIRE is replaced by TRACK and VIA (section 7); connectivity is derived from copper (section 5); RAM and ROM become optional, sized parts (section 4).

## 3. Time and evaluation

0. The network is settled (a no-op except in a world just built or loaded).
1. Every ARM whose EN reads 1 performs one register write; all arms sample first, then apply in part order. A CMD write executes (topology or copper change).
1b. Connectivity changes from step 1 are applied (section 6) and the network re-settles.
2. Every DFF latches D; every RAM with WE = 1 writes DIN to its addressed byte. All latch simultaneously from the values settled after 1b (so a RAM read in the same tick sees the pre-write value).
3. The combinational network settles.

Settling is event-driven over nets (a net's value changes when its driver's output changes; sinks are re-evaluated).

## 4. Parts

| Part | Footprint (w x h) | Pins (default orientation) |
|---|---|---|
| NAND | 2x2 | A (0,0), B (0,1), Y (1,0) |
| DFF | 2x2 | D (0,0), Q (1,0) |
| ROM [optional] | 2 x max(a,8) | ADDR[i] (0,i), DATA[j] (1,j) |
| RAM [optional] | 2 x (a+9) | ADDR[i] (0,i), WE (0,a), DIN[j] (0,a+1+j), DOUT[j] (1,j) |
| ARM | 2x9 | ADDR[i] (0,i) i=0..3, EN (0,4), DATA[j] (1,j) j=0..7 |
| SOURCE (harness only) | 1x1 | out (0,0) |

- NAND, DFF, ARM, SOURCE are as in RNDW. ROM and RAM are **byte-wide** [decision]; wider words are made by placing several. `a` is the part's address width, given at PLACE time in VAL (section 7), 1 <= a <= the world's maximum for that part. [decision]
- ROM: DATA = cell[ADDR], combinational; unprogrammed cells read 0; programmable only while unlocked (section 8).
- RAM: DOUT = mem[ADDR], combinational; at the latch step, if WE = 1, mem[ADDR] := DIN. Contents start at 0. No lock; the arm cannot read or write RAM directly. **DIN is on the left side with ADDR and WE, DOUT on the right side.** [decision]
- **Escape rule [proposal]:** every pin lies in the outer column of its footprint, so each pin has a free outward neighbour cell. (A pin in a middle column would have only pads or other pins as neighbours and could never be reached, because pads pierce every layer.) Hence two-column footprints.
- **Rotation (as implemented, v0.4).** Rotation k x 90 degrees as in RNDW section 5. For ANGLE 1 a cell (dx,dy) of a footprint of height h maps to (h-1-dy, dx), anchored at the top-left of the rotated box. Hence the ARM (2x9) rotated once is 9 wide and 2 tall: ADDR[i] at (8-i,0), EN at (4,0), DATA[j] at (8-j,1). A ROM with 14 address bits rotated once is 14 wide and 2 tall: ADDR[i] at (13-i,0), DATA[j] at (13-j,1). Replicator 1 uses exactly these two placements so that all bus pins face the same side.
- Parts occupy rectangles; overlap or out-of-bounds is a fault. **A part blocks nothing else**: copper and vias may pass under any part, except that a pad is copper in its own cell on every layer (section 5). [decision]
- Constant 1 = tie-high NAND (both inputs unconnected). Constant 0 = NAND with both inputs on a tie-high net. A cheap local tie-high NAND beside each consumer is usually cheaper than routing one constant across the board.
- **SOURCE is 1x1 [decision, v0.3]**, harness-only (test drivers, netlist inputs) and not placeable by an arm. In the state file KIND codes are 0 NAND, 1 DFF, 2 ROM, 3 ARM, 4 RAM, 5 SOURCE. (RNDW used 4 for SOURCE; RNDP's state format is new, so no compatibility issue.)
- **Driver harness (non-normative).** In RNDW, `driver.rs` drives an arm by placing 13 one-cell SOURCEs in a 21 x 13 block and wiring one to each ARM pin. In RNDP the harness does the same, with 13 one-cell SOURCEs, and lays the 13 connections as short tracks through the same TRACK path as any arm (no back door).

## 5. Grid, layers, copper and nets

- Integer grid W x H (each at most 65536) and **L layers** (world constant, default 2, range 1..8 as a placeholder; the code must not hard-wire 2). [decision] **Every replicator is built and measured at L = 2** [decision, v0.3]: two-layer boards are historically common and easy to visualize. Other L values are for experiments only.
- Each layer's cell is either empty or holds copper belonging to one net. Copper occupies about half the pitch, so:
  - copper in the **same cell** of the same layer is connected, which makes A-B plus B-C give A-C;
  - copper in **adjacent** cells is not connected (half a pitch of clearance), so parallel runs one cell apart are legal. [decision]
- Copper is **orthogonal only**: a segment runs along one row or one column. A turn is two segments sharing a corner cell. [decision]
- **Pads** are through-hole and pierce every layer. A pad is copper in its own cell on all layers, and a track on any layer reaching the pad cell connects to the pad. [decision]
- A **via** is a plated hole: copper in one cell on all layers, joining them.
- Copper is permanent. There is no remove command, so nets only ever merge, never split.
- Two tracks that cross in one cell on one layer are connected there. To cross without connecting, use different layers.

## 6. Nets, connectivity and the short rule

- At PLACE, every pad starts as its own net. A **net** is a set of pads and copper cells joined by shared cells. The simulator keeps a net id per cell and per pad, a union-find over net ids, and per net its pin list and its (at most one) driver. Merging is near-constant time per cell laid; because copper is never removed, connectivity is **cached and incrementally updated**, never recomputed by flood fill after load. [decision]
- A net's value is its driver's output, or 0 if it has no driver. An unconnected input pin reads 0. A net may have any number of input pins (fan-out).
- **Short rule [decision]:** sharing a cell is how connection works, so there is no geometric "different nets in one cell". The one detectable error is a merge that would give a net **two output pins** (two drivers). That command is **refused atomically** (no copper laid) and counted as a fault. A merge that wrongly joins an output to input-only nets is not detectable and is simply a wrong circuit, as on a real board.
- Merges apply in step 1b; every net whose membership changed is marked dirty and re-evaluated before the DFF latch.

## 7. The arm

Registers are as in RNDW (A.x, A.y, B.x, B.y signed 16-bit offsets from the arm's own origin, world axes; KIND; ANGLE; VAL; CMD), and registers keep values between commands, so only changed registers need rewriting. Reserved registers 11-14 remain faults. Per-command cost in ticks is therefore (number of changed registers) + 1. Register numbers: A.x 0-1, A.y 2-3, B.x 4-5, B.y 6-7, KIND 8, ANGLE 9, VAL 10, CMD 15 (low byte first). **Coordinates are relative to the arm's origin and signed 16 bit, so everything an arm builds must lie within -32768..32767 of it; absolute coordinates must still be >= 0 and inside the grid.** A machine whose lane layout is 4,581 wide and 29,699 tall therefore fits, with its child at x offset 4,700. (v0.4)

| Code | Command | Reads | Effect |
|---|---|---|---|
| 0 | NOP | | nothing |
| 1 | PLACE | A, KIND, ANGLE, VAL | place a part at arm + A. KIND 0 NAND, 1 DFF, 2 ROM, 3 ARM, 4 RAM. For ROM and RAM, VAL is the address width |
| 2 | (reserved: RNDW's WIRE) | | unknown-command fault |
| 3 | PROGRAM_ROM | A, B.x (address, unsigned), VAL | as RNDW: set cell B.x of the ROM whose origin is at arm + A, while unlocked |
| 4 | TRACK | A, B, VAL | lay copper on layer VAL in every cell from arm + A to arm + B inclusive (A and B share x or share y; A = B lays one cell) |
| 5 | VIA | A | drill a via at arm + A |

Codes 0, 1 and 3 keep their RNDW numbers, and 2 stays free so an RNDW program that issues WIRE faults instead of silently doing something else.

Faults (ignored, counted): unknown command (including 2); bad KIND or ANGLE (KIND 5 and above, including SOURCE, is not placeable); part overlap; out of bounds (part, pad, track cell or via); disabled part kind; address width out of range or above the world maximum; layer >= L; TRACK not orthogonal; **two-driver merge** (TRACK, VIA or PLACE); PROGRAM_ROM with no ROM at the target, address out of range, or ROM locked.

**PLACE onto existing copper [decision]:** a pad landing on a cell that already holds copper joins that net (subject to the driver rule). This is what makes fan-out cheap: copper laid first can be picked up by parts placed later.

## 8. ROM lock, EN event and the child start order

- **ROM lock:** a ROM is locked once any of its pads' nets has merged with anything (any copper beyond its own pad cell, or any other pin). Program the ROM before it is routed.
- **EN event:** a merge that joins the net of an ARM's EN pad to anything triggers the SVG/state-dump events of section 11.
- **Atomicity:** one TRACK or VIA command is atomic: all of its cells are laid in one tick, or none (on a fault).
- **No laying order is imposed [decision].** A net built from several commands is live after each one, and the world does not refuse partial nets or require a direction. Replicators choose their own order. The only ordering that matters is the RNDW start protocol: place all parts, program the ROM, lay all other copper, connect the child arm's EN driver, and connect `run` to tie-high **last**. Until then the child arm cannot fire and the CPU is held in reset. `run` must still feed exactly one gate.
- **Seed start-up (v0.4).** The first machine is started the same way: build everything except the `run` wires, tick a few times in reset, then lay the `run` wires. (`tools/make_seed.py` writes `seed.build` and `run.build`.) Started with `run` already connected, the machine does not run. **Tick-0 fault (found and fixed in v0.4).** A freshly built or loaded world has unsettled nets, and the first tick used to let arms sample them (all ones: EN=1, address 15, data 255), giving one "unknown arm command 255" fault per seed. A tick now settles the network before the arms sample (step 0), so a seed reports 0 faults.

## 9. Capability flags and world constants

Command line or restart file (the restart file records them, so replays and differential tests are reproducible): `--layers L`, `--rom on|off`, `--ram on|off`, `--max-rom-addr-bits`, `--max-ram-addr-bits`, plus grid size W x H and the event limit. A disabled part kind makes PLACE of it a fault. **Defaults: 16 address bits for both ROM and RAM [decision, v0.3]; 32 bits is allowed by setting the parameter** (the simulator must store sparse or lazily allocated memory above 16 bits, and a 2^32-byte part has a very tall footprint, so grid height limits apply). The size maxima are the world's resource limits, and a replicator is expected to be optimized against them (as Y's RAM was sized from an emulator run). With both off, a program store must be built from tie-high and tie-low NANDs (replicator 5).

## 10. Reporting

Counts of NAND, DFF, ROM, RAM, ARM, SOURCE; **primitive capacity** of ROM and RAM in bits, with a gate-equivalent so replicators with and without the primitive can be compared. **Gate-equivalent for RAM:** the RAM tile in `nandgen/y/hd/core.hd` (`ram_word`, one byte) is 52 NAND + 8 DFF, i.e. 6.5 NAND + 1 DFF per bit, and that tile already contains the per-bit read-chain gates. Address decode is extra (the select signals `ram.and*` in `core.hd`) and is not included. Replicator 1's own RAM (128 bytes, section 18) is this tile times 128 and confirms the figure at the circuit level. **Gate-equivalent for ROM and RAM [decision, v0.4]:** measured at **replicator 5** (renumbered): its program store is constant NAND gates and its RAM is NAND and DFF, so it is the one build in which the ROM and the RAM are actually done in gates. Also report: ROM bytes programmed; nets; copper cells per layer; segments; vias; total track length; bounding-box area of all parts and copper; faults and the first fault messages; ticks and settle events.

## 11. Dump options and restart files

- `--dump-on-en PREFIX`: write a restart file (and the SVG, if enabled) when an EN event fires; name `PREFIX_t<tick>.state`.
- `--checkpoint FILE --checkpoint-every N`: rewrite FILE every N ticks. Written to a temporary file, then renamed, so a crash cannot destroy the last good checkpoint.
- `--snapshot-prefix P --snapshot-every M`: write a new numbered restart file every M ticks.
- `--build FILE` (v0.4): apply `place KIND X Y ROT ABITS`, `track L X0 Y0 X1 Y1`, `via X Y`, `rom X Y ADDR VAL` lines directly to the world with absolute coordinates, no arm and no ticks; refused commands count as faults. It combines with `--world`, so a saved state can be extended. Used to make seed worlds and to check geometry (`--dump-pads`).
- Existing SVG options (`--svg-on-en`, `--svg-every`, `--svg-at-end`, window, coarse mode) carry over; copper is drawn per layer in distinct colours and vias as circles.

## 12. State file `rndp-state 1`

Header (`cfg`, `tick`, `faults`, `romwritten`), then lines `part ID KIND X Y ROT VAL`, `arm ID ...registers`, `dff ID VALUE`, `mem ROMID ADDR VALUE`, `seg LAYER X0 Y0 X1 Y1` and `via X Y`, in laying order. The loader rebuilds the cell map and the connectivity cache, so neither is saved. **Acceptance test:** run N ticks, dump, reload, run M more, and compare with an uninterrupted N+M run. `tests/compare_gen.py` uses this format for the quine check (section 18).

## 13. Simulator performance (non-normative)

Latch only DFFs whose D changed; evaluate RAM and ROM as native arrays (they are parts, so no tile recognition is needed); levelise the acyclic bulk later if a long run needs it. Gate-level behaviour of NAND/DFF remains the reference, as in the RNDW differential test. Measured (v0.4): the 9,889-node Replicator 1 runs at about 33,000 ticks per second.

## 14. What the world measures: the three tiers

Who knows where the copper goes is the quantity of interest, tracked as bytes of ROM image per tier: (1) **rule-generated** (stamp a module N times, emit bus tracks from chain rules), (2) **computed** (a small maze router inside a module-sized window), (3) **explicit data** (tracks for irregular glue). The hardware description gains geometry: modules with pins on their boundary, placement as data (a floorplan with stamp loops), not the output of an annealer. Replicator 1 sits at the cheap end: its layout is the "dedicated-lane" scheme, tier 1 in full (section 18), and its ROM carries no copper data at all.

## 15. Replicators and comparisons

| id | replicator | parts enabled |
|---|---|---|
| 1 | Hack vN AB quine | ROM only |
| 2 | Hack vN AB quine | ROM and RAM |
| 3 | RV32EC quine | ROM and RAM |
| 4 | RV32EC improver | ROM and RAM |
| 5 | pruned-architecture quine, program in constant NAND gates | neither |

All five are built for **L = 2** [decision, v0.3]. Build order 1, 2, 3, then 4 and 5 in either order. Comparisons: 1 against RNDW's X isolates the routing price; 1 to 2 isolates the free RAM primitive; 2 to 3 isolates the ISA (compare total image, with code and description reported separately; if 3's ROM is smaller than 1's and 2's, RV32EC has features Hack vN AB lacks); 1 to 5 is the pruning effect. The improver (4) starts from an abstract module such as an adder and finds its placement and routing at **module level**; its score is the module's **bounding-box area, with NAND count as the tie-break**. [decision]

Note on 1 versus 2 (v0.4): Replicator 1 has no RAM part, so its 128 bytes of RAM are NAND and DFF tiles *inside the machine*, and the builder has to wire them. Replicator 2 replaces those 128 tiles (7,680 nodes) with one RAM part and its ROM image should shrink by the tile rules and the tile-related builder code.

## 16. Open items

1. Layer range 1..8 for the simulator is a placeholder with no strong preference; change only if a reason appears.
2. Waiting on measurements: ROM and RAM gate-equivalents (replicator 5); whether a 32-bit default is ever needed (decided by emulator runs of the replicators).
3. (closed in v0.4) The tick-0 fault was a simulator bug, fixed by settling before the first sample.
4. A denser layout than the dedicated-lane one (stamped tiles, shared lanes) is the next step for the area figures; Replicator 1 is deliberately the loose baseline.

## 17. Evidence so far (router experiment, 2026-10-20)

Files: `nandgen/rndp/analysis/` (`slice_router.py`, `glue_router.py`, `sweep.py`, `check_routes.py`, logs, `slice_bit3_L2.svg`). One ALU bit slice of `core.hd`, annealed placement plus maze router, validated by an independent geometry-only checker (negative controls rejected). L = 2: smallest routed pitch 3x3, 41x31 = 1271 cells = 3.69x NAND-only area, 346 segments, 21 vias, about 1.8 KB of explicit track data. L = 3 and 4 shrink it to 2.93x. About 2.4 segments and 11-13 explicit bytes per inter-instance link. Irregular glue (decode, control, RAM decode): 3.6x to 10.4x NAND area depending on layers. Caveats: greedy router, flat placement, bus connections beyond the region not counted, 5 B per segment and 2 B per via are assumed encodings.

## 18. Replicator 1 results (v0.4)

Files: `nandgen/rndp_r1/` (README gives the pipeline). Machine: Y's Hack-vN-AB, 15-bit address bus, 8-bit data, ROM 14 address bits (16 KB), RAM 128 bytes as NAND/DFF tiles. L = 2.

**Machine.** 9,889 nodes: 8,809 NAND and 1,080 DFF (2,208 core nodes, one tie-high node, 128 tiles of 60 gates: 52 NAND + 8 DFF).

**Layout ("dedicated lane").** One node per row (core node g at (10+2g, 13+3g), tile gates in stacked columns), one horizontal lane row per input pin. One sink = TRACK L1 driver to lane row; VIA; TRACK L0 lane row to pad column; optional TRACK L0 to the pad. 75,991 build commands plus the ROM: 47,369 tracks, 18,731 vias, 9,891 parts (9,889 nodes + ROM + ARM). About 6.57M copper cells (4.43M on layer 0, 2.14M on layer 1); total track length 29.0M cells; bounding box 4,581 x 29,699 = 136.0M cells for 9,889 nodes (about 13,800 cells per node, versus 4 for the parts alone). This is the loose baseline; nothing is optimised for area.

**Verification.** (a) Reference geometry built in the simulator: 0 refused commands, pad nets equal the hardware-description netlist exactly (9,899 nets), and dropping one command is detected as an open net. (b) The assembly builder, run on the behavioural machine, issues exactly the reference command multiset, with ROM programmed before any wire, EN last of the ports and the `run` wires after it. (c) **Quine in the simulator:** at tick 50,000,000 the child (4,700 cells to the right) has the same 9,891 parts, 47,369 segments, 18,731 vias and 7,459 programmed ROM bytes as the parent, and has already started placing a grandchild.

**Cost.** Builder run: 19.4M instructions, 47.4M memory accesses. In the simulator the child's EN wire is laid at tick 49,529,755, i.e. **about 49.5M ticks per generation**; about 25 minutes of wall time at 33k ticks/s. Builder RAM use: 118 of 128 bytes.

**ROM image (7,459 nonzero bytes; image spans 16,288 bytes up to the end of the data).**

| part | bytes |
|---|---|
| builder code (nonzero bytes below the data; code spans 5,806 bytes) | 4,549 |
| hardware description (3,264 bytes span, 2,910 nonzero) | 2,910 |
| of which module records | 430 |
| of which body (2,208 core nodes as instances) | 2,494 |
| of which chain record and 5-byte tile rules | 97 |
| of which ports (rom/arm/wdata/en: ref + sink pad + lane row) | 161 |

No copper geometry is stored: positions are computed from the node index by the builder (tier 1 entirely). The hardware description is 2.9 KB for 9,889 nodes; the builder is larger than the data.

**Faults.** None. (The first run showed one tick-0 fault, a simulator bug, section 8. The Replicator 1 quine check above was made before the fix; Replicator 2 was re-run after it.)

**Not yet measured.** A full second generation; the ROM and RAM gate-equivalents (replicator 5).

## 19. Replicator 2 results (v0.4)

Files: `nandgen/rndp_r2/`. Same CPU as Replicator 1, but the 128 bytes of RAM are one RAM part (`ram_abits` 7, footprint 2 x 16, KIND 4) instead of 128 NAND/DFF tiles. The 63 RAM-select nodes of the core go too (the part decodes its own address), leaving 2,090 nodes: 2,034 NAND and 56 DFF, plus one tie-high node. L = 2, `--ram on`.

**Wiring of the RAM part.** Origin (RX,RY) = (tie_x + 8, tie_y + 3), unrotated. ADDR[0..6] = addr.mux0..6, WE = decode.and18 (the store strobe), DIN[0..7] = alu.mux48..55 (the same nets as wdata). Sink pads are on the part's left column and the lane row is the pad's own row, so each is TRACK L1, VIA, TRACK L0 with no vertical piece. DOUT[c] at (RX+1, RY+c) is extended on layer 0 to the out column RX+3+c and a via, as Replicator 1 did for the tile outputs. The read value is gated outside the RAM, as before, so the part's always-on DOUT is correct.

**Verification.** Geometry in the simulator: 0 refused commands, 2,108 nets equal to the netlist (RAM pins included). Builder on the behavioural model: exactly the reference commands, ROM first, `run` last; 5.2M instructions, 12.6M memory accesses, 118 B of RAM. Simulator quine: the child's EN wire is laid at tick **13,229,153**, and at tick 14,000,000 the child has the same 2,093 parts, 10,454 segments, 4,173 vias and 6,119 ROM bytes as the parent. Re-run after the tick-0 fix: 0 faults, same EN tick, same result.

**Measurements, Replicator 1 -> 2.**

| | Replicator 1 | Replicator 2 |
|---|---|---|
| nodes (NAND+DFF) | 9,889 (8,809 + 1,080) | 2,090 (2,034 + 56) |
| RAM | 128 tiles | 1 part, 1,024 bits |
| parts | 9,891 | 2,093 |
| segments / vias | 47,369 / 18,731 | 10,454 / 4,173 |
| copper cells (L0 + L1) | 4.43M + 2.14M | 1.71M + 0.91M |
| total track length | 29.0M | 4.30M |
| bounding box | 4,581 x 29,699 = 136.0M | 4,222 x 6,318 = 26.7M |
| ROM bytes programmed | 7,459 | 6,119 |
| code / description (nonzero) | 4,549 / 2,910 | 3,557 / 2,562 |
| builder instructions | 19.4M | 5.2M |
| ticks per generation | 49.5M | 13.2M |

The free RAM primitive removes 7,799 gates (79% of the nodes) and 81% of the area, but only 18% of the ROM image: the builder and the description are dominated by the core, not by the 128 identical tiles that rule-generation already made cheap. The area is still dominated by the dedicated-lane layout: 26.7M cells for 2,090 gates is about 12,800 cells per gate. CHILD_DX is still 4,700 (the Replicator 1 value); the machine now needs only 4,238, so it could shrink. The dense layouts are future work (section 16, item 4).
