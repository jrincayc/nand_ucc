# S4 report: improver in assembly   (2026-10-22)
**Status: IMPROVER CORE DONE; HD record reader/writer and flatten NOT done.**
The module improver (`kernels/improve.s`, hand-written RV32EC, 4,286 ROM bytes) reproduces `ref_improve.improve_record()` byte for byte. What is still missing for the whole in-world pipeline is the code that reads the module records from the HD, calls the improver on each, writes the improved records to the child, and flattens the HD body (instances of the improved modules plus fixed tiles) into the packed netlist that `build_graph.s` / `route1.s` read. That is listed under "Not done" below.

## What was built (measured, Rust emulator, new map)
| item | result |
|---|---|
| `kernels/improve.s` + `memmap_imp.s` | compaction (merge identical gates, drop dead, renumber), fan-out counts, chain cuts of up to 3 leaves sorted by (size, leaves), cone + saved count, truth tables over the leaves, iterative-deepening exhaustive NAND search (GMAX 6), rewrite, partition (outputs last), slot-form layout with the 40-byte record limit, strict-gain rule |
| `tests/test_improve_asm.py` | output compared with the reference: **all 7 library modules of `hd/m18/cpu_mod.hd`** (not, and, or unchanged; xor 9->4, mux 8->4, ha 11->5, fa 25->9 NAND), the improved records again (fixed point), 5 extra modules (xnor, and3, maj, duplicates, two outputs), 297 random modules (duplicates, dead gates, holes), 35 random sum-of-products modules (up to 60 signals) and 3 modules found by differential testing: **351 cases, 0 mismatches** |
| trace_check | all 4,286 ROM bytes (with a 3-instruction stub) covered by exactly one commented listing line |
| cost (MEASURED) | **about 1.4M instructions for the seven library modules** (fa about 1.0M of that, xor 0.17M, ha 0.16M, mux 0.07M); the exhaustive search visits about 5,900 nodes in total (reference count). Random sum-of-products modules cost about 2M each. |

So the improver is cheap: roughly 5% of the placement+routing cost (29-30M instructions), not the "unknown, maybe hundreds of millions" feared in the test plan. The week-long run (S8) is therefore dominated by placement and routing, not by the improver.

## Mutation test (Y's V8) -- `tests/mutate_improve.py`
Single-rule mutations of a copy of `improve.s`; each must make the comparison fail. **9 of 9 listed mutants killed** after strengthening the tests (first version: 7 of 12 killed; the survivors led to the sum-of-products modules and to 3 modules found by running a mutated reference against the real one): saved = gmax without the -1, cut order not sorted, identical gates not merged, strict-gain test off, record limit 40->60, layout topology check off, outputs not moved last by partition, users of the root not rewired, fan-out test ignored.
Not in the list, and why (stated so nobody over-reads the 9/9):
- "outputs not protected in `saved`": redundant guard, because the fan-out count already counts each output once, so the mutant is equivalent.
- "GMAX 6 -> 5": no module was found where the result differs (all 255 three-variable sum-of-products modules and 6,000 random modules tried, with a Python mutant of the reference). Either it is equivalent for modules of this size or the discriminating module is larger than anything tried. **This rule is not covered by the mutation test.**
- the search's "skip a table already present" rule only changes the search cost, never the result.

## Not done
1. Reading the library records out of the HD image in ROM (slot form, format of `hd2asm.py` / Y's records) and writing improved records into the child: the test harness packs the slots directly into RAM.
2. In-world flatten: HD body (837 module instances + fixed PLA/expander tiles + DFFs) -> packed netlist (SRC, KINDA, PTAB with late bits) used by the placer and router. The Python `hdflat.py` / `ref_flatten.py` are the references.
3. Order inside the program: improve library -> write improved HD -> flatten -> place -> route (S5).

## Limits of the kernel (explicit)
Signals < 64 (n_in <= 3, at most 60 gates including the 6 transient new ones); n_out <= 2; slots <= 64; record limit 40 bytes (as in the reference). RAM map `kernels/memmap_imp.s` (0x200-0x2FF variables, 0x1000-0x2100 arrays).
