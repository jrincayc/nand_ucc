# S3 report: assembly kernels   (2026-10-21)
**Status: ONE of about ten kernels exists (LPA sweep); the rest are NOT started.**

## Done (measured)
`kernels/lpa_sweep.s` + `run_lpa.py`: 4 sweeps = 3,651,391 instructions, 320 ROM bytes, labels match the Python model. Hand-written assembly, traceable.

## Gap
The kernel uses a fixed sweep order, not the xorshift shuffle and first-max tie rule of `place_ref.py`; a bit-exact match is required before it counts.

## Remaining kernels (order)
netlist/HD reader, CSR graph build, LPA level (shuffle, sweep, contraction), chain, tree flatten, serpentine fold, lane assignment, trunk intervals, sort + left-edge, path emission to arm commands. Each needs a differential test (Python model vs emulator, real data and random graphs) and a recorded instruction count. Totals so far are estimates: about 16-17M instructions for placer+router, about 200 KB RAM (estimates, INWORLD_COST.md). Blocked on S1 (normative router) for the router kernels.
