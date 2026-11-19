# Hand-off: provable limits, world estimates, lithography ban, designer ladder (state at 2026-11-16)

Written at the end of the session of 2026-11-10 to 2026-11-16. It continues `HANDOFF_RNDP_R1_R6.md`. Read `designer_bound/PROVABLE_LIMITS_NOTES.md` first; it is the summary of the argument.

## 1. Where things stand
- **Provable limits.** No proved hardware limit at the 4 KiB to 64 KiB scale is reachable. Three quantities are kept apart: Lambda (least state for one world, stored design counts), H (heritable information of a replicator), Delta (designer: one state that succeeds across a class of worlds). Any true worst-case limit is at most H plus a constant. Details and barriers: `designer_bound/PROVABLE_LIMITS_NOTES.md`.
- **World estimates.** H is about 2 x 10^6 bits for an orderly 1890 workshop, 10^7 for a real one, 5 x 10^7 for raw land with a relay computer, 2 x 10^8 with 1980s-class chips. All estimates; only R6 (1.3 x 10^5 bits, RNDP) is measured. A 64 KiB or 2 MiB limit cannot rest on replicator description size.
- **Designer.** No general designer has been measured. First figure: R4 as a rung-1 designer (any netlist, fixed geometry) is S = 1.99 x 10^6 bits, 89% of it working RAM, about 11 times the stored design R3c. Plan and measurement: `designer_bound/DESIGNER_LADDER_SPEC.md` v0.1 draft.
- **Lithography ban and chip buyback** (Joshua's proposed addition to Plan S of AI 2040, question from Thomas Larsen). Rebuild takes 5 to 20 years with tools destroyed; holding chipmaking at the i-line limit costs about 50,000 times more energy per training run; the ban must be defined by capability, and the buyback decides the first decade.

## 2. Where the documents are
Project files:
- `designer_bound/PROVABLE_LIMITS_NOTES.md` (expanded 2026-11-15)
- `designer_bound/DESIGNER_BOUND_NOTES.md` (section 4.1 amended 2026-11-15)
- `designer_bound/DESIGNER_LADDER_SPEC.md`, `r4_designer_measure.py`, `r4_designer_measure_output.txt`

Claude Docs artifacts (NOT in the Project; export them if they should be kept here):
- Rebuilding DUV and EUV lithography after a ban: https://claude.ai/artifact/J6WPiLuUGBvdz6UzWwMwWS
- Five scenarios for buying a few centuries: https://claude.ai/artifact/6D9Zu78eX2vBhGen9dbkRL
- Least S for a universal computer constructor in World_1890 and World_1sqkm: https://claude.ai/artifact/49s77KYTnGbfJnT59XJV7x

Not in the Project: the second-opinion report `opus_machine_estimation.md` (Joshua has it); the text of Plan S (https://ai-2040.com/?choices=plan-s-root).

## 3. Decisions made by Joshua
- Time budget 2^100 operations (earlier). Worlds: World_1890 and World_1sqkm as defined in the estimates document.
- Designer ladder: the designer may design a machine other than itself; rung 3 uses register-transfer expressions; order is step 0 (done), toy world, rung 2; visible faults are parked (may need undo; would be a separate world variant).
- Documents not yet distributed should carry no version-history remarks. Working notes in the Project may keep a corrections section.

## 4. Open questions waiting for Joshua
1. Metric for the ladder: S = ROM + RAM written, design input reported separately. Yes or no.
2. May rndp be generalised to read part footprints from a configuration file (Rust, no dependencies) for rung 2?
3. Minimise R4's RAM before quoting 2 x 10^6 bits, or quote it unminimised?
4. Toy-world design: word size and memory cap; who chooses the instruction sets; fixed point or infinite chain of descendants; how the k worlds differ. Needs a design note before any code.
5. Lithography paper: is i-line (365 nm) inside the ban? A comment thread in that document asks this.

## 5. Suggested next steps, in the agreed order
1. Toy-world design note (exact Lambda and Delta in an enumerable world; the only route to a lower bound).
2. Rung 2 of the ladder (world geometry on the tape). The reference router hard-codes pitch, footprints, port kinds and two layers, so this is mostly new work.
3. A stored layout of R4's own CPU, for a like-for-like rung-0 comparison.
4. Rewrite the paper's "Limiting Estimates" section around Lambda, H and Delta (PROVABLE_LIMITS_NOTES section 6).

## 6. Things to be careful about
- Do not quote 309/128 = 2.4 as a designer-to-design ratio. Those sources are a layout toolchain plus the design.
- The two world-estimate passes are not independent (both Claude models; the specification came from a chat that had seen earlier figures).
- The second-opinion report's part rows sum to 548 against a stated 650, and its control-code and per-part figures are low against this project's measurements.
- In the lithography paper, about ten journal citations are from memory and marked so; check volume and page numbers before citing. The lithography node attached to each supercomputer anchor is also from memory.
- The 1% buyback accuracy is a judgment with no study behind it.
- Items marked [mem] in PROVABLE_LIMITS_NOTES need checking before they go into the paper.
- R4 measurement was run on a clone of https://github.com/jrincayc/nand_ucc (directory `r4/`), not on Project copies.
