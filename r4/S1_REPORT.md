# S1 report: make the router reference normative   (2026-10-22)
**Status: DONE for the Python reference.** (The assembly port is S3.)

## Changes to `tools/rowchan.py` (measured results below)
| was | now |
|---|---|
| lane-zone choice in floats (`xz = ... - 1.5`) | integers in half-columns (`xz2 = 2*P*(u+1)*Z - 3`); ties -> lowest zone |
| optional `ZMODE='mean'` using `round()` and a float mean | removed |
| sort keys `str(key)` (so `n10` < `n2`) | canonical integer key `nk(key)` = (0, gate no.) / (1, ROM bit) / (2, RAM-out bit) |
| nets visited in dict insertion order | nets visited in `nk` order (lane choice, emission) |
| sink order relied on sort stability | explicit tie-break by pin-list index |
Rules are written into the module docstring.

## Golden output
`tests/golden_route.py [--write] NL`: permuted numbering (seed 12) -> `place_ref.order` (seed 1) -> serpentine fold -> `rowchan` (R=22, Z=14) -> arm command list (`lay.commands`, i.e. place/track/via lines as the rndp build file but without the board offset). Stored in `golden/`: `cpu_g1_m18.cmds` (new 256 KiB map; 44,763 commands, sha256 811fbfe7...) and `cpu_g1_hd.cmds` (old map; 43,702 commands, sha256 befbd1d1...), each with the `.sha256` of the commands and of the `.lay` text.
Measured: the output is identical under PYTHONHASHSEED = 1, 77, 123456 (new map) and 5 (old map).

## Results (measured; the figures in this section were taken before S3 changed the placement reference - see the update below)
- new-map g1: 884 x 808 = 714,272 cells (was 715,156 before the change), rndp 0 problems.
- old-map g1: 775 x 770 = 596,750 (was 598,300), 0 problems.
- refined placement (`test_rowchan.py`, 6M-move annealing): 489,678 cells, 0 problems (was 490k) - quality unchanged by the integer rules.

## Caveats
- The permutation that starts the test uses Python's `random.Random(12).shuffle`, which is the test input, not part of the in-world algorithm; its sequence is not guaranteed across Python versions. If it ever changes, rewrite the goldens (or store the permuted netlist).
- The golden cmds list is the geometry for a ROM-less build (`lay.commands(L, nl, [])`); ROM programming commands come with the real ROM (S5).
- The assembly version must reproduce these command lists byte for byte (S3/S5).

## Update 2026-10-22 (after S3)
S3 changed `place_ref.py` (mask-and-reject random draw, nets in id order), so the placement, and with it the goldens, changed. Regenerated goldens (same test, permutation seed 12, order seed 1): new map 887 x 842 cells, 44,763 commands; old map 800 x 771, 43,702 commands. Both validate in rndp with 0 problems (new map) and are identical across PYTHONHASHSEED = 3 and 99. Over 9 permutation/seed pairs the area is 598k-650k (mean 633k) for the old map and 683k-747k (mean 714k) for the new map; the single golden draws are at the high end of the spread.
