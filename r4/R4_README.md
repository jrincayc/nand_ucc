# R4 minimum kit
Unpack `r4_min.tar.gz` (and optionally `rndp_src.tar.gz` next to it), then `sh run_all.sh quick` (minutes) or `sh run_all.sh full` (adds the ~1 h gate-level run).
Needs: python3 (stdlib only), Rust/cargo (no crates). `RNDP=/path/to/rndp` to also build the world in rndp (`cargo build --release` in rndp/).

| file | role |
|---|---|
| kernels/*.s (16 files, hand-written RV32EC) | the in-world program: memmap*.s = RAM map; improve.s (improver), hdflat.s (HD flatten), build_graph/lpa_level/chain/place_order.s (placement), route1-3.s (router + arm commands), main.s, start.s |
| hd/m18/cpu_mod.hd, cpu_mod_improved.hd | seed hardware description (carried in ROM) and its improved form (fixed point) |
| hd/m18/cpu_g1.nl | the CPU as NAND/DFF netlist (used by gatesim and validate) |
| tools/rvasm.py | assembler (listing names a source file:line for every byte) |
| tools/hd.py, hd2bin.py, hd2nl.py, hdflat.py, netlist.py | HD reader, HD -> ROM data, HD -> netlist |
| tools/place_ref.py, route_ref.py, ref_improve.py, lay.py | Python reference placer, router, improver (the normative versions the assembly must equal) |
| tools/build_rom.py, armlog2build.py, cmp_gate.py | assemble everything; arm log -> rndp build file; compare gate-level run with emulator |
| tests/test_pipeline.py | whole program on the emulator vs the Python reference, command for command, + fixed point |
| tests/trace_check.py | every ROM byte comes from exactly one source line |
| tests/validate_world.py | rndp-built world has exactly the netlist's connectivity |
| rvemu_rs/ | dependency-free Rust RV32EC emulator (logs arm writes) |
| gatesim_rs/ | dependency-free Rust gate-level simulator of cpu_g1.nl (tick = RNDP tick) |
Not in the kit (per-kernel unit tests, mutation tests, golden files, older replicators): in the Project under nandgen/rndp_r4/tests.
