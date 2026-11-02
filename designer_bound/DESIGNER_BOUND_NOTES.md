# Lower bounds on design cost: working notes (2026-11-01)

Status labels: [P] proved or standard result, [C] conditional on a stated assumption, [M] measured here, [E] estimate, [U] not measured.
Companion data: `nandgen/RNDW_VON_NEUMANN_THRESHOLD.md` (tau_i, mutation audit), `nandgen/HANDOFF_RNDP_R1_R6.md`, `nandgen/rndp_r6/R6_DESIGN.md`.
Scripts and raw outputs are in this directory (`nandgen/designer_bound/`).

## 1. The question
Not "how small can a replicator be" but "how much must a designer of the replicator contain, given that the replicator does not yet exist". The replicator may store its own layout; the designer must derive it.

## 2. Framing that gives something provable
Let P be the specification, R the output (the replicator), T the number of candidates the designer can test.
- [P] Search-versus-knowledge: a deterministic designer that finds R by testing candidates against P determines R from P plus the index of the candidate, so K(R|P) <= log2 T + |knowledge| + O(1). Equivalently |knowledge| >= K(R|P) - log2 T - O(1).
- [P] K(R|P) cannot be proved large (Chaitin); this is the von Neumann threshold problem again. Unconditional lower bounds on design cost are out of reach.
- A usable form is the dichotomy: designer size >= min( log2(1/rho) - log2 T , |evaluator| + |candidate generator| ), where rho is the fraction of machines of size <= s that satisfy P.
- Self-reference adds only a constant (Kleene recursion theorem).

## 3. Compute budget (user's number, adopted)
- 5e9 years = 1.6e17 s. Total work about 1e30 = 2^100 operations (about 1e3 parallel units at 1e9/s). Sequential depth at most about 2^89 steps.
- Candidates tested: log2 T between about 55 and 90. Full tests of a replicator candidate cost 2^30-2^45 operations each (about 2^55-2^70 tests); with early rejection of most candidates, up to about 2^85-2^90. Use 90 as the conservative (designer-friendly) value; it weakens the search term by about 1 byte relative to 80.
- Anything above 2^100 is off the buildable Pareto frontier. Exponential recomputation stays out; polynomial algorithms of degree up to about 5-9 in the design size fit.

## 4. What was measured
### 4.1 Knowledge to regenerate R6 from sources [M, upper bound only]
xz -9e, comments and blank lines stripped, repo clone of `nand_ucc` (`measure.py`, `measure_output.txt`):
| tier | raw | xz |
|---|---|---|
| A builder source (rndp_r6/hack/*, r2c/src/builder_c.asm) | 67 KB | 8.2 KB |
| B hardware description (r2c core_r7_ram.hd) | 21 KB | 2.1 KB |
| C python image generators + assembler/hd tools | 72 KB | 21.3 KB |
| D layout tool (c3 main.rs + vp patch) | 34 KB | 8.3 KB |
| A+B+C+D jointly | 168 KB | 38.7 KB (309 kbit) |
| + simulator as world model (G) | | +14 KB (53 KB jointly) |
Excluded: the stored layout `r2c_vp_p5.lay` (an annealer output, regenerable from D plus a seed), the spec (the repo copy is v0.3, older than the Project's v0.4).
Interpretation: this measures a *general* designer. R6's own image (16,006 B = 128 kbit) already regenerates R6, so K(R6|P) <= about 128 kbit plus fixed Hack-machine semantics; the extra roughly 180 kbit is a generality premium. The earlier claim "the sources are the measurable upper bound on K(R6|P)" was too loose.

### 4.2 Essential fraction of an image [M, from existing mutation study]
From RNDW_VON_NEUMANN_THRESHOLD.md sections 11-12: X has 174 free bytes of 4,096 (about 4%); tau_i(X) <= 31,376 bits of 32,768; Y (improver counted necessary) about 30% free, tau_i(Y) <= about 91,600 bits. About 4% of X's hardware-changing single-bit mutants still replicate. These are upper bounds on tau_i; lower bounds are unavailable (section 5.3 there).
New here [M]: R2c builder image (13,050 B): all bytes are read at least once (2,178 fetched as code, 10,872 read as layout data), no untouched padding. "Read" includes copy-only bytes, so this is not yet an interpreted-versus-copy-only split. (`romtouch.py`)

### 4.3 Evaluator (the part of a search-based designer that decides whether a candidate replicates)
| term | bound | status |
|---|---|---|
| register file to interpret arm commands | at least about 100 bits | [E] from the spec |
| child-versus-parent comparison | about 100-200 bits via a multiset fingerprint, constant memory | [P] technique, not built |
| tick-level sequential state | at least the state bits the run uses. R2c builder (3.47 M instructions): 51 of 128 RAM bytes written, only 287 bits ever toggle (`ramactivity.py`) | [M] for R2c, [U] for R6 |
| combinational evaluation of arbitrary networks | circuit evaluation is P-complete, so polylog space only if P is in polyL | [C] |
| copper connectivity | O(log n) bits of state with a random walk (expected cover time <= 2m(n-1)); the cost is time, because each step needs a neighbour lookup | [P] |
| simulator rules as code | world.rs = 7.5 KB xz (about 60 kbit); whole simulator 124 kbit; about 72k units as a ROM plane before a CPU | [M] upper-bound proxy |
Net-size measurement (`netsizes.py`, `netsizes_output.txt`) on the R6-style ROM plane built from the real R2c image (plane3_gen.py, 94,269 gates, 556,951 commands):
- 94,291 copper nets = 94,291 logical nets; 0 opens, 0 shorts (reproduces the project's own check, so the parse is valid).
- Every net is a tree (edges = cells - nets exactly). Median 8 cells, p99 1,365, max 61,994; the top 10 nets carry 70% of the walk cost.
- Random-walk cover bound, summed over nets: 8.9e10 = 2^36.4 steps. With 30 repeats and a scan of all 557k commands per step as the neighbour lookup: 2^60.4 (2^55.5 without repeats). Inside the 2^100 budget by about 40 doublings. Plane only (94k of 105k gates); core and RAM block not included.
- Because nets are trees, a deterministic Euler-tour walk needs 2m = about 1e7 steps, but it fails on nets with loops, so it cannot be assumed for arbitrary candidates.
Faults are invisible to circuits in RNDP, so an in-world designer cannot learn about a short from the world; it has to check beforehand or build correct by construction (which is knowledge).

## 5. Things said earlier in the exploration that were wrong or too strong (corrections)
1. A union-find over all pins needing about 7.6 Mbit is the cost of one method, not a lower bound; time can substitute for memory in connectivity.
2. The 2^70 compute budget came from converting at the project simulator's speed; the budget is 2^100 (section 3).
3. A memory lower bound of the form "frontier width x log" holds only for a one-pass sweep designer. With random-access read-only input and write-only output, layout memory can be polylog; memory is not where design cost lives. The density bound (state costs at least 4 cells per bit; a RAM-based router cannot hold a map of the board) concerns RAM-based designers only.
4. Toy-world enumeration cannot reach the crossover where rho falls to 2^-80..-90, because measuring such a fraction needs about 1/rho samples. Only a trend at small sizes can be fitted; extrapolation is an estimate, not a bound.
5. Sources are not the tightest upper bound on K(R6|P); the 16 KB image is (section 4.1).

## 6. Open items, in suggested order
1. Interpreted-versus-copy-only byte audit for R2c/R6 images (extend mutation/audit.py); turns image size into essential bits.
2. Measure R6's real RAM and register activity (needs the R6 builder image; `rndp_r6/hack/lay_data.asm` and `prims.asm` are not in the repo clone).
3. Exact rho(s) in a tiny enumerable world (E7 of the threshold document); expected form log2(1/rho) = s - c, so measure c against the interpreter's complexity.
4. State P explicitly. With hardware fixed, the tau_i figures apply; with hardware free, add about 17 kbit (xz of the core description). The strength of any bound is the strength of P.
5. Pebbling width of R6's network (live nets in a good topological order); gives the combinational-state term for R6 itself.

## 7. Reproduction
Clone https://github.com/jrincayc/nand_ucc. `measure.py` expects `repo/nand_ucc/` next to it; `ramactivity.py` and `romtouch.py` hard-code the clone path in `R=` (edit it); `netsizes.py BUILD PINS.json` takes the output of `rndp_r6/plane3_gen.py r2c/outc/rom.bin 0 plane3.build` and its `.pins.json`. Python needs numpy and scipy for netsizes.py. Run with `python3 -I`.
