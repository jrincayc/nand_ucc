# S7 report: gate-level windows from checkpoints   (2026-10-21)
**Status: NOT STARTED beyond the base tools.**

Exists: `netsim.py` (C simulator, compiled by gcc, Python-driven) and the tick-for-tick gate-vs-RTL test, passing in old and new map for 8000 ticks. Needs: checkpoint writer in the emulator, a dependency-free Rust port of netsim, window selection by coverage (each instruction type, kernel entry/exit, longest loops, first/last).
