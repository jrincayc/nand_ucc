# RNDP Replicator 4 (improver) -- RV32EC CPU: module-level HD (M1) and reference improver (M2)

Status: M1, M2, M3 done. Nothing runs in the world yet. RAM decision: 32 KiB (fits the existing address map).

The R3c CPU generator (`tools/cpu_gen.py`) builds an already-optimised flat netlist (constant folding, structural hashing, shared inverters):
2,937 NAND + 78 DFF. That leaves nothing for a module-level improver, so R4's *seed* is regenerated from the textbook module library of Y
(not, and, or, xor, mux, ha, fa; `tools/modnet.py`). Same generator, different `Net`: `ModNet` emits one module instance per datapath operation
(constants folded at generation time, nothing shared). The microcode PLA and the instruction expander stay **fixed flat tiles** (built with hashed NANDs,
marked `# pla` / `# expander` in the HD); the improver will not touch them.

| | NAND | DFF |
|---|---|---|
| R3c flat optimised netlist (reference) | 2,937 | 78 |
| R4 textbook seed (837 module instances + fixed tiles) | 4,612 | 78 |
| of which fixed tiles (PLA + expander) + 3 constant gates | 1,430 | |
| module instances: and 346, or 226, mux 141, not 70, xor 46, fa 8 | 3,182 | |
| seed with Y's library savings (and 2, or 3, not 1, xor 4, mux 4, ha 5, fa 9) | about 3,690 | 78 |

The remaining gap to 2,937 is cross-instance sharing, which the module improver (by decision) does not do.

## Files
| path | role |
|---|---|
| tools/modnet.py | ModNet (module-instance Net), textbook library `LIB`, `flatten()` (expand instances with the library) |
| tools/cpu_gen.py | the R3c generator; `build(net=...)` accepts a ModNet; PLA and expander run inside `net.flat(label)` |
| tools/hdmod_export.py | writes `hd/cpu_mod.hd` (library, body of dff / nand / module instances, ports) |
| tools/hdflat.py | independent HD -> NAND/DFF flattener |
| tools/seed_stats.py | the table above |
| tools/netsim.py | `CPU_SEED=mod` simulates the flattened module seed |
| tests/test_hd_seed.py | HD write(read(x)) == x; hdflat(HD) == ModNet.flatten gate for gate |
| hd/cpu_mod.hd | the generated seed HD (2,345 body lines) |

## Checks
```
ROM_BITS=15 python3 tests/test_hd_seed.py                  # round trip, PASS
ROM_BITS=15 CPU_SEED=mod python3 tests/gate_vs_rtl.py 6 20000   # module seed vs microcode model, tick for tick on random programs, PASS
```
Open: RAM size (32 KiB fits the existing address map; 64 KiB needs a third address-register byte and microcode changes).

## M2: the reference improver
`tools/ref_improve.py` is Y's normative improver, unchanged (cut enumeration up to 3 leaves, exhaustive iterative-deepening NAND search, GMAX 6).
`tests/test_improve.py` runs it over `hd/cpu_mod.hd` and writes `hd/cpu_mod_improved.hd`.

| module | seed | improved |
|---|---|---|
| not / and / or | 1 / 2 / 3 | unchanged |
| xor | 9 | 4 |
| mux | 8 | 4 |
| ha | 11 | 5 |
| fa | 25 | 9 |
| **CPU** | **4,612 NAND + 78 DFF** | **3,690 NAND + 78 DFF (-20.0%)** |

Checks: each improved module has the same truth tables (asserted); improving the improved HD is a no-op; `write(read(x)) == x`;
the improved CPU matches the microcode model tick for tick (`CPU_HD=hd/cpu_mod_improved.hd ROM_BITS=15 python3 tests/gate_vs_rtl.py 6 20000`: PASS).
Not done: Y's mutation test of the improver rules (V8); it is the same code, but the R4 assembly port will need it.

## M3: reference place and route ("strip")
`tools/strip.py` is the normative P&R the in-world program must reproduce. Placement = body order of the HD (offline-optimised, see below);
routing = one single-sided channel, left-edge track assignment, no grid memory (it needs only per-net left/right ends and a per-track right end).
* Gate k at base column 3k (gap column for the NAND's B stub, then two gate columns), row Y0. ROM, ARM, RAM are upright blocks at the right end
  with a staircase of layer-0 stubs (one column per pin). Every pin goes up a layer-1 stub in its own column to its net's track (layer 0); a via joins them.
  Because no two stubs share a column there are no vertical constraints, so left-edge is density-optimal.
* `tools/order_hd.py` reorders the HD body (annealing on total net span over instances; deterministic). The improver keeps body order, so g1 inherits it.
  The order is data in the HD (like Y's node order), not computed in the world.
* `tools/hd2nl.py` HD -> netlist (nodes in body order, holes absent, tie node before its user); `tools/lay.py`, `tests/validate_layout.py` as in rndp_layout.

| | nodes | board | cells | tracks |
|---|---|---|---|---|
| g0 seed (4,612 NAND + 78 DFF) | 4,691 | 14,150 x 137 | 1.94 M | 119 |
| g1 improved (3,690 NAND + 78 DFF) | 3,769 | 11,384 x 137 | 1.56 M | 119 |
Reference points: R3c compact (annealed, PathFinder) about 135k cells; R3 loose 55 M. Unordered body order gave 11,384 x 315 (3.6 M).
Both layouts build in rndp with 0 shorts/opens (`ROM_BITS=15 python3 tests/test_strip.py`); the ordered improved HD matches the microcode model tick for tick.
Files: hd/cpu_seed.hd (ordered seed), hd/cpu_g1.hd (improver output), hd/cpu_g{0,1}.{nl,lay}.
Next (M4): the RV32EC builder that computes this layout in the world from the HD in ROM (pass 1 positions, pass 2 stubs, left-edge, emit commands).
Memory estimate for M4: per net left/right/track about 6 B x 3,800 = 23 KB, so 32 KiB RAM is tight but plausible; to be measured.
