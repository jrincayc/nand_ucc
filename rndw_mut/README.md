# rndw_mut: local variant of nandgen/rndw used for the von Neumann threshold mutant experiments

Differences from `nandgen/rndw` (2026-10-16):
- `src/world.rs`: identical rules and code, plus an optional arm command log (`World::log_cmds`, `World::cmdlog`, type `CmdRec`),
  `arm_exec` made `pub`, and `arm_index_of`. Nothing else changed.
- `src/state.rs`: unchanged. `src/lib.rs` exports only `state` and `world` (no netlist/svg/driver/vectors).
- `src/bin/mutrun.rs`: new harness with subcommands
  - `validate A.txt B.txt`: run A to B's tick; check `save_state()` is byte-identical to B (done: quine_gen1_start -> quine_gen2_built_tick8.0M, equal).
  - `child CMDS ROM [--max-ticks N --stall N --per-cmd N]`: replay a parent's arm command stream into an empty world (child only), program the child ROM, run the child, and compare what it builds with the stream that built it. Verdicts: REPLICATES, DIVERGES, STALLED (with ROM-address diagnostics), ARM_EN_UNWIRED, NO_ARM.
  - `full STATE ROM TICKS`: gate-level run of the parent with a mutant ROM poked in (cross-check of `child`).
  - `watch STATE TICKS pidA pidB ...` and `watch3 STATE TICKS (other new dest)...`: compare gate outputs over a run (used to see how often a rewired gate would differ).
- Command files come from the ISA emulator (`hack.c`/`emu.py`, not in the Project): `P kind x y rot`, `W ax ay bx by` (absolute), `X code kind angle ax ay bx by val` (expected, relative).

Build: `cargo build --release --offline`. Results: `nandgen/RNDW_VON_NEUMANN_THRESHOLD.md` section 12.
