# rndp: RNDP world simulator

Robot + NAND + DFF + PCB (+ optional ROM, RAM). Rust, standard library only. Implements `nandgen/RNDP_SPEC.md` v0.3.

    cargo build --release
    cargo test --release          # 16 integration tests
    ./target/release/rndp --help

## Status (first milestone)

Done: parts NAND, DFF, ROM, RAM, ARM, SOURCE with the section 4 footprints and rotation; copper on L layers
(TRACK, VIA); pads through every layer; cached union-find nets; the one detectable short (two drivers) refused
atomically for TRACK, VIA and PLACE; PLACE onto existing copper; ROM lock; arm interpreter with commands 0, 1, 3, 4, 5
(2 faults); event-driven settle; DFF and RAM latch (RAM reads see pre-write values); `rndp-state 1` save / load;
`--dump-on-en`, `--checkpoint`, `--snapshot-prefix`; SVG per layer; scripted driver arm; capability flags
(`--layers`, `--rom`, `--ram`, `--max-rom-addr-bits`, `--max-ram-addr-bits`, default 16 bits, up to 32 with sparse memory).

Not done: netlist import/export, differential test against the Python reference `nandgen.Sim` (needs routed
netlists), RAM-bit identification in the report, interactive mode, coarse SVG for huge worlds, any replicator.

## Cross-check against the router experiment

    python3 tests/crosscheck_routes.py nandgen/rndp/analysis/core_body.hd routes.json target/release/rndp /tmp/xc

Converts a `routes.json` from `slice_router.py` / `glue_router.py` to a state file, loads it here and checks that
two pads share a simulator net exactly when they share a netlist net. Result: 0 shorts and 0 opens on all six
layouts (slice at L=2,3,4; glue at L=2,3,4). This is a second, independent connectivity implementation
(Rust union-find over placed copper) agreeing with the Python checker.

## Notes and known limits

* Driver harness: ARM at (10,2), 13 one-cell SOURCEs at x=8 and x=13, laid by ordinary TRACK commands. Reserved block
  x 8..13, y 2..10. Script coordinates are absolute; the driver converts to arm-relative.
* PROGRAM_ROM takes its address from B.x as an unsigned 16-bit value, so ROM addresses above 65535 cannot be
  programmed by an arm (a 32-bit-address ROM needs an extension; spec open question).
* Memory above 20 address bits is sparse; below, dense.
* Tie-high NANDs start at 1; ROM / RAM outputs start at 0 (their contents start at 0).
* A pad net's driver is its single output pin; the fan-out list of a signal may hold duplicate consumers (harmless).
