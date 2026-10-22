# R4: in-world grid router, instruction-count estimate (2026-10-21)

Tools: `rvemu_rs/` (dependency-free Rust RV32EC emulator, same semantics as `tools/rvemu.py`; `tests/diff_rvemu.py` runs random programs on both and compares RAM, arm log and instruction count: 100/100 agree).  Speed: about 30 M instructions/s (the R3c builder, 727,585 instructions, runs in 0.024 s).  A week of simulator time at about 60 k ticks/s and 26 ticks/instruction is about 1.4e9 instructions.

Reference router (the c3 PathFinder, A* on 2 layers x 5 direction states), `cpu_g1.nl` (3,769 gates), pitch 10, effort 3 -> board 632x654 = 413k cells:

| pass | cumulative heap pops | overused cells after |
|---|---|---|
| 1 | 34 M | 5,990 |
| 2 | 70 M | 3,257 |
| 3 | 105 M | 1,584 |
| 4 | 136 M | 510 |
| final (11 passes) | 178 M | 0 |

At about 40 RV32EC instructions per pop (bucket queue, byte-serial memory) one pass costs about 1.4e9 instructions = the whole one-week budget; the negotiated (PathFinder) result costs about 7e9 = about 5 weeks, and the first pass still leaves about 6,000 overused cells.
Memory: occupancy + labels + netlist about 350 KB.
Consequence: a congestion-negotiating router does not fit; the in-world router needs either a cheaper algorithm (hierarchical / channel-based, fewer expansions per net, no rip-up), a coarser pitch (fewer cells), or a longer verification run.  The squarish-board, small-memory, cheap-compute triangle cannot be satisfied at once with a general maze router.
