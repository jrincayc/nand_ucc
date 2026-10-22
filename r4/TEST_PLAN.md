# R4 test plan: from the reference to a fully tested in-world improver + placer + router  (2026-10-21)

Principle: one normative reference per step, a differential test per step, and nothing in the ROM that is not traceable to hand-written assembly.  "Done" = exists and passes now.

## Where we are
| layer | status |
|---|---|
| Hardware description (HD) with textbook modules, improver reference (`ref_improve.py`) | done: 4,612 -> 3,690 NAND, g1 HD filed |
| Placement order: integer-only normative reference `tools/place_ref.py` (multilevel LPA + chain, xorshift shuffle, u8 weights) | **done now**: deterministic; over 3 numberings x 3 seeds 598k-669k cells, mean 636k (`tests/test_place_ref.py` builds one in rndp, 0 problems) |
| Row-and-channel router `tools/rowchan.py` | reference exists and validates in rndp, but is NOT yet normative: uses Python floats in the lane-zone choice, Python `sorted` with string tie-breaks, dict iteration order |
| RV32EC emulator in Rust, differential vs `rvemu.py` | done (100 random programs agree) |
| One assembly kernel (LPA sweeps) | done, matches a Python model; 3.65 M instructions for 4 sweeps (measured) |
| Gate-level CPU, microcode model, lockstep tests (from R3) | exist; need re-run after any address-bus change |
| rndp simulator | validates a built world against the netlist (pins/nets); cannot yet log arm commands or write checkpoints |

## Steps, in order
**S1  Make the router reference normative (Python, 1-2 days of work).**  Integer lane-zone choice, canonical sort keys (no strings), fixed iteration order, fixed lane/track assignment rules; write the exact list of arm commands (`place/track/via/rom`) as the golden output.  Test: golden command list for g1; validates in rndp (pins = netlist) and its geometry is stable across Python versions.

**S2  Decide the machine changes that the program needs.**  (a) RAM about 200 KB (estimate) -> address register wider than 15 bits; the microcode, `cpu_rtl`, `rvemu` (both) and the memory map change; re-run `lockstep_rtl`, `randprog`, `gate_vs_rtl`.  (b) ROM size for the improver + placer + router program (unknown; the LPA kernel alone is 320 bytes).  Decide before writing assembly, because the memory map is baked into every address constant.

**S3  Assembly kernels, one per step of the reference, each with a differential test (Python model vs emulator on the real data and on random graphs).**  Order: netlist/HD reader -> CSR graph build -> LPA level (shuffle, shuffled sweep, contraction) -> chain -> tree flatten -> serpentine fold -> lane assignment -> trunk intervals -> sort + left-edge -> path emission to arm commands.  Existing: LPA sweep kernel (needs the xorshift shuffle and the first-max rule of `place_ref.py` to be a bit-exact match; today it uses a fixed order).  Each kernel: instruction count recorded (replaces my estimates).  All ROM bytes traceable (`trace_check`).

**S4  The improver in assembly (M5 of the original plan).**  Port `ref_improve.py` (cut enumeration up to 3 leaves, NAND search GMAX=6, slot-form records); byte-for-byte compare of the output HD with the reference on g0 -> g1; add the mutation test (Y's V8) that the improver reports a corrupted rewrite.

**S5  Whole program on the Rust emulator.**  Run seed ROM with the parent's HD, record the full arm-command log (emulator already logs it), compare with the golden list from S1 command by command.  Check the child's ROM image equals the parent's, the child's HD equals the reference g1.  Fixed-point test: run the child's program on the child's HD: g1 -> g1 (nothing more to improve, same layout).

**S6  Replay in rndp.**  Feed the arm log to rndp (a replay driver or `--script`) with the real arm timing; `validate_layout` on the resulting world: no shorts/opens, pin nets = netlist; compare the built world to the golden one cell by cell.  Needs: nothing new in rndp for correctness; a command log in rndp (you asked for it) for debugging.

**S7  Gate-level CPU checks (windows from checkpoints, as you chose).**  Emulator checkpoints -> state-file writer -> compiled gate-level CPU (`netsim`, to be ported to dependency-free Rust) runs windows of N instructions and compares RAM/registers/arm writes with the emulator.  Pick windows by coverage: every distinct instruction type, every kernel entry/exit, the longest loops, first and last instructions.  Plus rndp with the CPU running the first and the last few million ticks of the whole run.

**S8  One long start-to-finish run (about a week on your i3, single-threaded).**  After S1-S7 pass, run the complete rndp simulation of seed -> child with checkpoints every N ticks (so an interruption costs at most a checkpoint) and the arm-command log on; compare child with golden.  The estimate: improver instructions + about 16 M for placement/routing; at 26 ticks per instruction and about 21k ticks/s with two CPUs running the budget stays within a week only if the improver itself is a few hundred million instructions (not yet measured; the improver port, S4, gives the number).

## What can go wrong (known risks)
1. The improver port may be much larger than the placer/router: unmeasured.  If it exceeds the budget the week-long run is the wrong test and windows are the only full-coverage test.
2. Bit-exact PRNG/tie rules between Python and assembly: the first thing S3 tests.
3. Memory map change (S2) touches the CPU and every earlier replicator test; keep the old 15-bit map for R1-R3 by making the width a parameter (the R3c builder uses ROM_BITS=15 already).
4. Inherited vs computed information: the seed HD must not carry placement (the current numbering is the annealed one, so use randomly permuted or generator-order numbering in the seed, or the result is partly inherited).
5. Quality claims are for one netlist (cpu_g1) and Python-float versions of the router; re-measure after S1.

## Suggested immediate next step
S1 (normative router) and S2 (memory map decision) are the blockers for everything else; S2 needs your decision on RAM size (see INWORLD_COST.md: about 200 KB estimate).
