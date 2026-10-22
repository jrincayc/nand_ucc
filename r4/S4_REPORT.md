# S4 report: improver in assembly   (2026-10-21)
**Status: NOT STARTED.**

Reference: `tools/ref_improve.py` takes g0 to g1: 4,612 -> 3,690 NAND (measured earlier, the old 8-bit-RAM / 14-bit-ROM map; must be redone on the new map, S2).
Planned: port cut enumeration (up to 3 leaves) and NAND search (GMAX=6), slot-form records; byte-for-byte comparison of output HD with the reference; mutation test (a corrupted rewrite must be reported).
Biggest unknown: instruction count of the improver. It decides whether the week-long run (S8) is feasible. Unmeasured; no estimate is claimed.
