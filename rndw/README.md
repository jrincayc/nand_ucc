# rndw: RNDW world simulator

Robot + NAND + DFF + Wires (+ ROM). Rust, standard library only, no cargo dependencies.
Implements `nandgen/RNDW_SPEC.md` (v0.3).

    cargo build --release
    cargo test
    ./target/release/rndw --help

## Differential test against the Python reference

    ./diff_test.sh 3000 1        # needs nandgen.py on PYTHONPATH (default: the parent directory)

Generates netlists and random-input traces from `nandgen.Sim` for the ALU, the parallel and serial
Hack CPUs (levels 0, 1, 2), a RAM, and a CPU+RAM machine, then replays each trace here and compares
every output and DFF wire every tick. Last result: 0 mismatches over about 2.9 million comparisons
(3000 ticks, seed 1); a corrupted-gate control produced thousands of mismatches and exit code 1.

## Quick start

Build a small circuit through a driven arm (one register write per tick), with an SVG when a wire
attaches to an ARM's EN pin:

    ./target/release/rndw --script demo.script --out-dir out --svg-on-en --save out/state.txt

Load a nandgen netlist (inputs become harness Sources) and run it:

    ./target/release/rndw --netlist hack_cpu_serial_w8_aw12_k4_level2.netlist.txt --steps 1000

Interactive mode (press Enter to pause; then `s [file]` save state, `v [file]` SVG, `t`, `c`, `q`):

    ./target/release/rndw --world out/state.txt --interactive

## Modules

| file | role |
|---|---|
| `src/world.rs` | parts, pins, grid, wires, event-driven settle, DFF latch, arm interpreter |
| `src/netlist.rs` | nandgen text netlist import (placed on a pitch-3 grid) and export |
| `src/state.rs` | whole-world save / load; also the seed-world config format |
| `src/svg.rs` | SVG snapshots: detail, coarse merged blocks, window, trigger policy |
| `src/driver.rs` | harness that drives an arm through its pins using Source parts |
| `src/vectors.rs` | replays a `rndw-vectors` trace and compares against the Python reference |
| `tools/gen_vectors.py` | netlists + random traces from `nandgen.Sim` (needs `nandgen.py`) |
| `diff_test.sh` | one-command differential test over 7 designs |
| `src/main.rs` | CLI: batch and interactive modes |
| `tests/world.rs` | 16 integration tests |

## Not done yet

- RAM-bit identification in the report (only raw DFF count).
- Tile-type recognition in SVG (coarse mode merges by spatial block, not by repeated tile).
- True Ctrl-C handling (needs libc or a crate; Enter-to-pause is the dependency-free substitute).
