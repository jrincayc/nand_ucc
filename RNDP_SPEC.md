# RNDP world specification: v0.3 DRAFT (for review; no simulator code exists yet)

RNDP = Robot + NAND + DFF + PCB (+ optional ROM, optional RAM). A variant of RNDW (`RNDW_SPEC.md` v0.5) in which a wire is no longer an abstract point-to-point edge but copper laid on a grid, so crossings, area and routing effort cost something. Sections marked **[decision]** are choices you made; **[proposal]** are mine and need your yes or no. Section 16 lists what is still open.

Changes in v0.3: SOURCE stays 1x1 and the driver harness lays 13 tracks (section 4, former open item 1); default maximum RAM and ROM address width is 16 bits, with 32 allowed by command line (section 9); the ROM gate-equivalent is to be measured when replicator 5 is built (section 10); the simulator's layer range stays a placeholder, and **all replicators use exactly 2 layers** (sections 5 and 15). Router experiment results are in `nandgen/rndp/analysis/` (section 17).

Changes in v0.2: replicators renumbered 1 to 5 (section 15); RAM footprint now has DIN and DOUT on opposite sides (section 4); command code 2 stays reserved, TRACK is 4 and VIA is 5 (section 7); the world imposes no track-laying order (section 8); PLACE onto existing copper kept (section 7); two drivers on one net confirmed as the only detectable short (section 6). Corrections found while revising: KIND code 4 was used for both RAM and SOURCE (SOURCE is now state-file code 5 and not placeable); the RAM gate-equivalent in section 10 was wrong and is recomputed from the actual RAM tile in `nandgen/y/hd/core.hd`.

## 1. Purpose and non-goals

The point of RNDP is to price routing. RNDW gives away routing for free (wires cross freely, have no length, area or delay). RNDP keeps the RNDW rule that **the world may check a layout but never find one**: the arm says which cells carry copper, the simulator accepts or refuses. Any routing intelligence must therefore live in the replicator's circuit or program, and shows up honestly in its ROM image and hardware.

Non-goals: power and ground distribution, clock distribution (the clock is the tick), wire delay, thermal limits, diagonal copper, arm travel time. **[decision]**

## 2. What carries over from RNDW

Ticks and the tick procedure (section 3), NAND/DFF/ARM/SOURCE semantics, arm registers and relative signed 16-bit coordinates (v0.5), the ROM lock idea, fault counting (faults are ignored, counted and invisible to circuits), the tie-high NAND (both inputs unconnected), SVG and batch/interactive CLI. Combinational cycles remain allowed with the same event limit.

What changes: WIRE is replaced by TRACK and VIA (section 7); connectivity is derived from copper (section 5); RAM and ROM become optional, sized parts (section 4).

## 3. Time and evaluation

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
- Rotation by k x 90 degrees as in RNDW section 5.
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

Registers are as in RNDW (A.x, A.y, B.x, B.y signed 16-bit offsets from the arm's own origin, world axes; KIND; ANGLE; VAL; CMD), and registers keep values between commands, so only changed registers need rewriting. Reserved registers 11-14 remain faults. Per-command cost in ticks is therefore (number of changed registers) + 1.

| Code | Command | Reads | Effect |
|---|---|---|---|
| 0 | NOP | | nothing |
| 1 | PLACE | A, KIND, ANGLE, VAL | place a part at arm + A. KIND 0 NAND, 1 DFF, 2 ROM, 3 ARM, 4 RAM. For ROM and RAM, VAL is the address width |
| 2 | (reserved: RNDW's WIRE) | | unknown-command fault |
| 3 | PROGRAM_ROM | A, B.x (address), VAL | as RNDW: set cell B.x of the ROM whose origin is at arm + A, while unlocked |
| 4 | TRACK | A, B, VAL | lay copper on layer VAL in every cell from arm + A to arm + B inclusive (A and B share x or share y; A = B lays one cell) |
| 5 | VIA | A | drill a via at arm + A |

Codes 0, 1 and 3 keep their RNDW numbers, and 2 stays free so an RNDW program that issues WIRE faults instead of silently doing something else.

Faults (ignored, counted): unknown command (including 2); bad KIND or ANGLE (KIND 5 and above, including SOURCE, is not placeable); part overlap; out of bounds (part, pad, track cell or via); disabled part kind; address width out of range or above the world maximum; layer >= L; TRACK not orthogonal; **two-driver merge** (TRACK, VIA or PLACE); PROGRAM_ROM with no ROM at the target, address out of range, or ROM locked.

**PLACE onto existing copper [decision]:** a pad landing on a cell that already holds copper joins that net (subject to the driver rule). This is what makes fan-out cheap: copper laid first can be picked up by parts placed later.

## 8. ROM lock, EN event and the child start order

- **ROM lock:** a ROM is locked once any of its pads' nets has merged with anything (any copper beyond its own pad cell, or any other pin). Program the ROM before it is routed.
- **EN event:** a merge that joins the net of an ARM's EN pad to anything triggers the SVG/state-dump events of section 11.
- **Atomicity:** one TRACK or VIA command is atomic: all of its cells are laid in one tick, or none (on a fault).
- **No laying order is imposed [decision].** A net built from several commands is live after each one, and the world does not refuse partial nets or require a direction. Replicators choose their own order. The only ordering that matters is the RNDW start protocol: place all parts, program the ROM, lay all other copper, connect the child arm's EN driver, and connect `run` to tie-high **last** ("last wire" now means the last cell of copper that completes the net). Until then the child arm cannot fire and the CPU is held in reset. `run` must still feed exactly one gate.

## 9. Capability flags and world constants

Command line or restart file (the restart file records them, so replays and differential tests are reproducible): `--layers L`, `--rom on|off`, `--ram on|off`, `--max-rom-addr-bits`, `--max-ram-addr-bits`, plus grid size W x H and the event limit. A disabled part kind makes PLACE of it a fault. **Defaults: 16 address bits for both ROM and RAM [decision, v0.3]; 32 bits is allowed by setting the parameter** (the simulator must store sparse or lazily allocated memory above 16 bits, and a 2^32-byte part has a very tall footprint, so grid height limits apply). The size maxima are the world's resource limits, and a replicator is expected to be optimized against them (as Y's RAM was sized from an emulator run). With both off, a program store must be built from tie-high and tie-low NANDs (replicator 5).

## 10. Reporting

Counts of NAND, DFF, ROM, RAM, ARM, SOURCE; **primitive capacity** of ROM and RAM in bits, with a gate-equivalent so replicators with and without the primitive can be compared. **Gate-equivalent for RAM [corrected in v0.2]:** the RAM tile in `nandgen/y/hd/core.hd` (`ram_word`, one byte) is 52 NAND + 8 DFF, i.e. 6.5 NAND + 1 DFF per bit, and that tile already contains the per-bit read-chain gates. Address decode is extra (the select signals `ram.and*` in `core.hd`) and is not included. **Gate-equivalent for ROM [decision, v0.3]:** measured, not predicted, when replicator 5 is built; its tied-NAND program store is the gate-level version of a ROM. Also report: ROM bytes programmed; nets; copper cells per layer; segments; vias; total track length; bounding-box area of all parts and copper; faults and the first fault messages; ticks and settle events.

## 11. Dump options and restart files

- `--dump-on-en PREFIX`: write a restart file (and the SVG, if enabled) when an EN event fires; name `PREFIX_t<tick>.state`.
- `--checkpoint FILE --checkpoint-every N`: rewrite FILE every N ticks. Written to a temporary file, then renamed, so a crash cannot destroy the last good checkpoint.
- `--snapshot-prefix P --snapshot-every M`: write a new numbered restart file every M ticks.
- Existing SVG options (`--svg-on-en`, `--svg-every`, `--svg-at-end`, window, coarse mode) carry over; copper is drawn per layer in distinct colours and vias as circles.

## 12. State file `rndp-state 1` (sketch)

Header with the section 9 constants and the tick; parts with kind, position, rotation, address width; arm registers; DFF values; ROM contents; RAM contents; copper stored as **segments** (layer, x0, y0, x1, y1) and via cells, in laying order. The loader rebuilds the cell map and the connectivity cache, so neither is saved. **Acceptance test:** run N ticks, dump, reload, run M more, and compare with an uninterrupted N+M run.

## 13. Simulator performance (non-normative)

Latch only DFFs whose D changed; evaluate RAM and ROM as native arrays (they are parts, so no tile recognition is needed); levelise the acyclic bulk later if a long run needs it. Gate-level behaviour of NAND/DFF remains the reference, as in the RNDW differential test.

## 14. What the world measures: the three tiers

Who knows where the copper goes is the quantity of interest, tracked as bytes of ROM image per tier: (1) **rule-generated** (stamp a module N times, emit bus tracks from chain rules), (2) **computed** (a small maze router inside a module-sized window), (3) **explicit data** (tracks for irregular glue). The hardware description gains geometry: modules with pins on their boundary, placement as data (a floorplan with stamp loops), not the output of an annealer.

## 15. Replicators and comparisons

| id | replicator | parts enabled |
|---|---|---|
| 1 | Hack vN AB quine | ROM only |
| 2 | Hack vN AB quine | ROM and RAM |
| 3 | RV32EC quine | ROM and RAM |
| 4 | RV32EC improver | ROM and RAM |
| 5 | pruned-architecture quine, program in constant NAND gates | neither |

All five are built for **L = 2** [decision, v0.3]. Build order 1, 2, 3, then 4 and 5 in either order. Comparisons: 1 against RNDW's X isolates the routing price; 1 to 2 isolates the free RAM primitive; 2 to 3 isolates the ISA (compare total image, with code and description reported separately; if 3's ROM is smaller than 1's and 2's, RV32EC has features Hack vN AB lacks); 1 to 5 is the pruning effect. The improver (4) starts from an abstract module such as an adder and finds its placement and routing at **module level**; its score is the module's **bounding-box area, with NAND count as the tie-break**. [decision]

## 16. Open items

1. Layer range 1..8 for the simulator is a placeholder with no strong preference; change only if a reason appears.
2. Nothing else is open at spec level. Items waiting on measurements: ROM gate-equivalent (replicator 5); whether 32-bit default is ever needed (decided by emulator runs of the replicators).

## 17. Evidence so far (router experiment, 2026-10-20)

Files: `nandgen/rndp/analysis/` (`slice_router.py`, `glue_router.py`, `sweep.py`, `check_routes.py`, logs, `slice_bit3_L2.svg`). One ALU bit slice of `core.hd`, annealed placement plus maze router, validated by an independent geometry-only checker (negative controls rejected). L = 2: smallest routed pitch 3x3, 41x31 = 1271 cells = 3.69x NAND-only area, 346 segments, 21 vias, about 1.8 KB of explicit track data. L = 3 and 4 shrink it to 2.93x. About 2.4 segments and 11-13 explicit bytes per inter-instance link. Irregular glue (decode, control, RAM decode): 3.6x to 10.4x NAND area depending on layers. Caveats: greedy router, flat placement, bus connections beyond the region not counted, 5 B per segment and 2 B per via are assumed encodings.
