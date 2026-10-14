# Gate-level netlists for the ISA candidates

Files (all under `nandgen/isa/`; they import `nandgen.py` from the parent folder, so run with `PYTHONPATH=..:.`):
- `nl_hackvn.py`, `nl_acc8.py`: nandgen builders (`build_hackvn(level)`, `build_acc8(level)`).
- `hackvn_cpu_level2.netlist.txt`, `acc8_cpu_level2.netlist.txt`: exported netlists (nandgen text format; inputs = rdata[8], reset).
- `fastsim.py`: compiles a netlist to straight-line Python; `lockstep.py`: runs a netlist against a behavioral model (`run_lockstep` on a kernel, `run_image` on any ROM image) comparing architectural state every instruction, RAM and ARM log.
- `test_hackvn.py`, `test_acc8.py`: kernels K1-K4 in lockstep. `fuzz_hack.py`, `fuzz_acc8.py`: random-instruction programs.
- `mutate.py`, `mut_*.py`, `classify_run.py`: rewire random gates and check that the tests notice; survivors are compared on random valid states to separate equivalent gates from untested ones.
- `xcheck_rndw.py`: replays random-input traces in the Rust RNDW simulator and compares with nandgen.Sim.
- `isaacc.py` was changed (opcode numbers, page-relative branches, ADCI/SBCI/ORI); kernels and results are unchanged.

Memory interface used by every netlist: `addr[13]` (function of registers only), `rdata[8]` (combinational read of addr), `wdata[8]`, `we` (clocked write at addr in the same tick).
