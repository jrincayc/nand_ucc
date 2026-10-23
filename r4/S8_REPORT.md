# S8 report: start-to-finish run in rndp   (2026-10-23)
**Status: PASS (measured).** The parent machine (the R4 CPU as 3770 NAND + 81 DFF, RAM part 18 bits, ROM part 16 bits holding the 28,167-byte R4 program with the improved HD) ran in rndp from reset, improved/placed/routed its own description and built a child that equals itself.

## Setup
- Parent = the layout the R4 program produces for the improved HD, built from the arm-command log of the emulator run (`tools/make_seed.py`; undoes the child-frame offset, places it at (40,1200)): 69,713 commands, then the 5 RUN-wire commands applied after 40 reset ticks. Board 871 x 785 cells. This makes the parent a fixed point: its ROM carries the improved HD, and the improver leaves it unchanged.
- Child frame offset (set by the program, `kernels/main.s`): OX = W + 8 - xa = 58, OY = -y_lastrow = -759, i.e. child 880 cells right of the parent (DX = 880), same rows.
- `rndp --world s1.state --build run.build --steps 1.1e9 --checkpoint ck.state --checkpoint-every 25e6 --cmd-log ... --dump-on-en en`, 1 core. The container restarted once at tick 475M; the run was resumed from its checkpoint (tick 475,000,000) with the remaining steps; nothing else was lost (the arm had not written anything before that tick).

## Results (measured)
- Robot-command log (`cmd2.log`, new `rndp --cmd-log`, one line per executed arm command with tick, absolute A/B, registers, ok/FAULT): **69,718 commands = 3854 place + 24,982 rom + 24,174 track + 16,708 via, 0 FAULT lines**; first command at tick 774,326,003, last at tick 958,654,234.
- `tests/compare_gen.py` on the checkpoint at tick 975M: parent 3854 parts / 24,174 segments / 16,708 vias; child 3854 / 24,174 / 16,708; **parts, segments (collinear pieces merged), vias identical to the parent shifted by 880; ROM 24,982 bytes in both, 0 differing addresses: QUINE PASS.** World fault counter 0.
- The 5 RUN wires were the last commands; after them the child CPU started (16M further ticks simulated, no faults); a grandchild was not waited for (it would need another ~960M ticks, E8 in R5_RECOMMENDATIONS.md).
- Wall time: ~55-60k ticks/s in rndp, about 4.8 h for the 960M ticks to the last command (plus a few minutes lost to the restart).
- Ticks: improved-HD program = 32,288,147 instructions; at the gate-level average of 29.55 ticks/instruction (S7, seed-HD image) that predicts 954.1M ticks; the log's last command is at 958.65M (+0.5 %). The gate-level run of S7 used the seed-HD image (33.4M instructions, 987M ticks), so the two tick totals differ by design, not by a simulator discrepancy [consistent; the improved-HD image was not itself run in gatesim].

## Limits
- One generation: parent -> child. The grandchild was not built.
- The parent is built from the same command stream the child is compared with (the stream is the emulator's, which S5/S7 tie to the Python reference and to the gate-level CPU), so the quine check shows the in-rndp CPU reproduces that stream and the arm applies it as the emulator predicts; it does not independently validate the layout algorithm (S6 does that by netlist connectivity).
- Only parts, copper segments, vias and ROM contents are compared (the compare_gen set); DFF/RAM contents of the child are initial (zero) and not compared.
- Single seed (placement RNG seed 1), single netlist.
