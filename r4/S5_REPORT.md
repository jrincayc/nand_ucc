# S5 report: whole program on the Rust emulator   (2026-10-21)
**Status: NOT STARTED (needs S1, S3, S4).**

Exists: dependency-free Rust RV32EC emulator `rvemu_rs` with arm-command logging; agrees with `rvemu.py` on 100 random programs (old map). It still lacks the new memory map (`--ab`, ROM mirror, arm window reads 0), so the differential test must be re-run after that update (S2 leftover).
Planned checks: arm-command log vs golden list from S1; child ROM equals parent ROM; child HD equals reference g1; fixed point g1 -> g1.
