# S6 report: replay in rndp   (2026-10-21)
**Status: PARTLY PREPARED.**

Done today (rndp, builds clean):
- SVG output now gives every element a typed id: `nand12`, `dff7`, `ram3`, `rom0`, `arm0`, `track<n>`, `via<n>` (number = part index / copper-log index), instead of Inkscape's `rect3771`. Change in `rndp/src/svg.rs` only; not yet exercised on a state file or filed.
Still missing: a command log (all robot commands) and checkpoint writer in rndp; a replay driver using real arm timing; cell-by-cell comparison with the golden world. Existing: `validate_layout.py` checks pin nets against the netlist.
