> **Superseded 2026-10-24 by E4_RESULT.md** (the stream-cost problem below was solved with a decoder; final numbers there).

# E4 interim (2026-10-22/23): engine verified at gate level; explicit-layout stream is ~4x larger than estimated

## Done and verified
- Plane tile (rndp connectivity: faults/opens/shorts 0), pattern compiler (899 words), cycle model, gate-level engine netlist
  (`engine_net.py`: 638 NAND incl. tie, 58 DFF, metric NAND+6*DFF = 986).
- `engsim` (Rust, gate-level) vs `engine_model.py` on the 932-row test program: identical 373,537 arm writes, then halts (`verify_engine.py`).

## New measurement: cost of describing the engine's own layout (the A/C stream)
Router = R4 `route_ref` generalised (`eplace.py`, `eroute.py`, `elay.py`: 26 external nets x0..x24 + D0 instead of ROM/RAM pseudo-parts, arm real).
Engine .nl (696 gates) -> 8,327 build commands (4,463 tracks, 3,167 vias, 697 places), board ~275 x 313 (R=14).
Stream words (register writes with persistence + 1 CMD write per command; commands sorted to minimise register changes), `streamcost.py`:
| R (rows) | words |
|---|---|
| 6 | 23.2k |
| 14 | 23.3k |
| 22 | 24.1k |
| 45 | 26.2k |
Breakdown at R=14: place 1.4k (2.05/cmd), horizontal L0 tracks 6.8k (3.25), vertical L1 tracks 8.6k (3.72), vias 6.5k (2.09). Wiring = 21.8k words = ~31 words/gate, ~22 per sink pin.
MEASURED (words); the earlier "~10 words/gate => W 5-7k rows" was an ESTIMATE and is wrong by ~3.5x for a generic router.

## Consequence
- W ~ 24k rows -> plane height 4W ~ 96k cells > 16-bit arm coordinates (and > 13-bit counters). Not buildable as is.
- Need W <= ~7k rows. Options (not yet built):
  1. Hand/template layout of the engine with local wiring by 1-cell links (est. ~12k words even with 60% local refs; still too many).
  2. Shrink the engine itself (move counters/muxes into plane data or bit-serial): 637 NAND -> ~200 NAND would put ~7k words in range.
  3. Data-driven gate cells (pattern = interpreter, each plane row = one gate record), needs coordinate arithmetic in the engine; likely cheaper in words but adds adders.

## Update: option 2 (shrink engine) and a command-minimising maze router (2026-10-23)
- Engine floor: counters t/rr (14-bit incrementers, reload), the t==rr comparator, the 24-bit capture register and the 24:1 condition mux are ~400 of the 637 NAND. Cheap rewrites (drop rr hold mux, zero-reset counters) save maybe 60-100 NAND (~15%); I did not apply them because the stream cost is not sensitive enough (below). ESTIMATE.
- `maze.py`: two-layer A* router, cost = runs + vias (+0.02/cell), pads block both layers, pin-escape reservations, plane column tops as L0 terminals at y=0, D0 as one explicit long wire to the ring input. 24 rows, pitch 5-6, LPA order.
- MEASURED, partial routing (not all sinks routed): pitch 6: 114 nets / 408 sink connections failed, routed part = 2,460 tracks + 209 vias + 697 places = 11.6k words; pitch 5: 79 nets / 336 sinks failed, 12.6k words. About a third of the sink connections are missing, so a complete layout would be ~17-19k words (ESTIMATE by scaling), versus 23-24k for the channel router. Gain ~25%, not the 3x needed.
- Conclusion so far: automatic wiring costs ~25-35 words per gate. 700 gates -> 17-24k plane rows, above the ~7-8k that 13-bit counters allow and, at 4 cells per row, above the 16-bit arm coordinate range once rows > 16k. Shrinking the engine by 20% does not close this. What would: (a) a hand/template datapath layout with bit-slice regularity and 1-cell links (needs design work, est. 8-12k words), or (b) an engine of ~150-200 gates, which means a different architecture (not counters + comparator).

## Update 2: command-level decoder study (2026-10-23)  [fmt2.py, engine2_net.py, enc_measure.py]
Question: can a small decoder in front of the arm cut the ROM, given that every engine gate costs ~12 build commands to describe and the stream is itself ROM gates (2 NAND per stored 1)?
- MEASURED (channel-routed layout, 696 gates, 8,165 commands): sorted delta coding, Elias-gamma deltas = 11.4 bits/command (11.7 KB) vs ~70 bits/command (72 KB) now.
- MEASURED (round trip verified): format F2, ONE 22-bit data word per command: dx[7:0] (mod-256 add to a mirrored A.x), len[13:8] (<=63, longer tracks split), orient, dy[16:15] (0..3), c[18:17]; escape words Hy (Ay += delta8) and Hk (kind/val). Decoding by the reference semantics reproduces all non-track commands and the covered track cells exactly (arm model, 0 faults). Result: 8,916 words, 57,023 ones = 6.4 ones/word. Old explicit stream: ~24.7k words, ~211k ones. So 2.8x fewer rows and 3.7x fewer ones.
- MEASURED (netlist builder, not yet simulated): engine2 with interpreter datapath (8-bit adder, A.x/A.y 8-bit mirrors, operand/addend muxes, WF data sources, pass flag p2, D-flag rows, isdata gate): 973 NAND + 75 DFF (metric 1423) vs 678 NAND + 59 DFF (1032) for the same build without it. Decoder cost: +295 NAND, +16 DFF.
- Requirements found: (1) engine layout must lie in one 256x256 aligned block (mirrors are 8 bits, hi bytes constant) - the channel router needs ~87k cells, so this needs the denser maze layout; (2) two passes (decode pass with D=1 rows over data words, then the plane-dump pass) because the pattern rows overwrite arm registers; (3) 14-bit counters suffice with last = (rr == M) constant compare and M=16319, engine block at y = 0x7F00..0x7FFF.
- ESTIMATE (fixed point): the decoder's own 1048 gates also need describing: ~12.4 words/gate -> ~13k data words + 899 pattern rows -> W ~ 14k rows, ~91k ones => ~196k NAND + 14k DFF => ~280k units vs ~590k now (2.1x). With a completed maze router (~0.6x commands): W ~ 8.8k, ~180k units.
- Not done: interpreter micro-rows, extended pattern, engine2 vs model lockstep, layout in 256x256, full rndp quine run.
