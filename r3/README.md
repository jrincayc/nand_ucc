# nandgen RNDP Replicator 3 -- RV32EC quine (ROM and RAM)

A byte-serial, microcoded RV32EC CPU (2922 NAND + 77 DFF) whose 7,982-byte ROM holds a hand-written RV32EC builder
(806 bytes of code, 7,176 bytes of netlist data). It places and wires an exact copy of itself, shifted by CHILD_DX=6200, then starts it.
Every ROM byte maps to a source line (`tests/trace_check.py`, from `out/rom.lst`).

Result (rndp, 2 layers, ROM+RAM): QUINE PASS (parts, segments, vias, ROM contents identical), 0 faults;
about 11.05M ticks per generation; seed 3002 parts / 14959 segs / 5971 vias; 6040x9046 cells; the child restarts the chain (5 copies after 40M ticks).

Pipeline: `./run_all.sh [sim]`. See DESIGN.md.
