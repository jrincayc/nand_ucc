# M3 report -- Python side of Y (HD export, reference flattener, reference improver, mechanical encoder)

Status: done, all tests pass (`python3 tests/test_m3.py`, 25 checks). No ROM code exists yet. Stop for your review before M4.

## What exists
| file | role |
|---|---|
| tools/hd.py | HD data model, reader, writer (round trip exact) |
| tools/hd_export.py | textbook (level-0, unoptimised) machine -> `hd/core.hd` (621 lines, 413 body instances) |
| tools/ref_flatten.py | reference flattener: HD -> flat nodes, build commands (place / ROM / wire order of RNDW v0.5), nandgen netlist for simulation |
| tools/ref_improve.py | NORMATIVE improver (the ROM program in M5 must give identical gate lists) |
| tools/hd2asm.py | mechanical encoder HD -> commented `.byte/.word` assembly, plus an independent decoder (image -> flat graph) |
| tests/machine_lockstep.py, tests/test_m3.py | lockstep vs behavioural model; M3 test suite |
| hd/core.hd, core_improved.hd, core_data.asm, core_improved_data.asm | generated artefacts |

## Results
* Library (NAND per module, textbook -> improved): not 1->1, and 2->2, or 3->3, xor 9->4, mux 8->4, ha 11->5, fa 25->9.
* Unlisted modules (audit B): xnor 10->5, maj 12->6, and3 4->4 (nothing to gain). 54 random 2/3-input modules: same function, fixed point, and identical gate counts to the cutv2 prototype.
* Whole machine (5-bit RAM address, 32 B): seed 3,685 NAND + 310 DFF -> improved 2,773 NAND + 310 DFF (weighted 5,545 -> 4,633, -16%). The RAM tiles (256 DFF + their gates) are not touched by the improver, which is why the whole-machine ratio is smaller than the core ratio (1,958 -> ~1,053 NAND).
* Improved machine runs `demo.asm` (131 instr, 336 ticks, identical to seed) and 25 random programs with random RAM contents in lockstep with the behavioural model.
* Improving the improved description changes nothing (fixed point).
* Build commands: 5,880 wires, no overlapping parts, every sink driven once.
* Data ROM image: 5,051 B (seed) / 4,909 B (improved), `trace_check` passes (every byte explained, every line commented).

## Things you should know (including one correction)
1. The first version of ref_improve.py gave fa = 11 instead of 9. Cause: the improver is greedy and path dependent, and my first renumbering (Kahn, old-index order) led it down a different path than the prototype. Fixed by specifying the renumbering as DFS post-order from the outputs, and cut order as smaller cuts first. Both are now part of the normative text. Greedy path dependence is a real property: other orders could give 9, 10 or 11, so M5 must reproduce the order exactly.
2. Encoding deviates from spec v1.2 in two small ways: module header is 4 plain bytes (flags, n_in, n_out, n_gates) instead of nibbles (tile has 19 inputs, and readability beats 1 byte), and the module area is fixed-size so the body address is the same in every generation. I will fold both into the spec as v1.3 if you agree.
3. HD data begins at ROM offset 0x800, leaving 2 KiB below for the builder and improver code. That is a guess; M4/M5 may need more, and it is one constant (`HD_OFF`). Data ends near 0x13BB offset, so about 3 KiB remain above if code must grow past 2 KiB.
4. Predecode lists must be consecutive `and` instances (stride 2 nodes); the encoder asserts this. A hand edit that breaks it is rejected rather than silently mis-encoded.
5. Speed was not measured on the ROM side; there is no ROM program yet.

## Next (M4, after your review)
Assembly flattener/builder reading this data format and building a child in the RNDW world, differentially tested against ref_flatten.commands().
