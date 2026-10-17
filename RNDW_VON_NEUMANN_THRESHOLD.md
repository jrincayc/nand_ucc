# The von Neumann threshold of the RNDW world: τ_r, τ_i, τ_c

Written 2026-10-16 for Joshua. Framework: Kabamba, Owens & Ulsoy (2011), "The von Neumann threshold of self-reproducing systems: theory and application", Robotica 29, 123–135 (the attached paper). RNDW data: `nandgen/HANDOFF.md`, `HANDOFF_QUINE_AND_IMPROVER.md`, `HANDOFF_3_TAU_FROM_X_AND_Y.md`, `QUINE_DESIGN.md`, `y/M7_WRITEUP.md`.

**What I did and did not do.** I read those documents and the paper and worked out the mapping and the bounds. I did **not** re-run the simulator or the ISA model. After the first version of this document you supplied `rndw_states_M7.tar.gz`; from it I measured only the ROM images' sizes, hashes, trailing zero bytes and order-0 entropy (§6). All other RNDW numbers are copied from the documents above. Anything labelled "not measured" is exactly that.

---

## 1. Short answer

None of the three can be computed *exactly* for the full RNDW world, because M0 (all possible ROM images) has 2^32768 members (X) or 2^131072 members (Y) and cannot be enumerated. What can be given are **rigorous upper bounds on τ_i and τ_c**, a **structural description of τ_r with weak bounds**, and a **list of measurements that would tighten them**.

| quantity | X (quine) | Y (self-improver) | status |
|---|---|---|---|
| M∞ non-empty? | yes: X is a fixed point, G(X) = X | yes: g1 → g2 → g2 (g3 = g2) | from the verified runs, under the model of §2 |
| **τ_i** (bits) | **≤ 31,376** (= 8 × (4,096 − 174 audited free bytes)); ≤ 26,084 if model-level don't-care bits count (§11) | **≈ ≤ 91,600 (sampled estimate, improver code counted as necessary; §11)**; rigorous: ≤ 131,072 | upper bound only (X audited, §11; Y sampled). Lower bound: only 0, or an uncomputable Kolmogorov term (§5.3) |
| **τ_c** (symbols) | ≤ 3,962 (uniform bytes, H = 8) or ≤ 1,981 (uniform words); **≤ 4,789 with measured H** | ≤ 16,350 or ≤ 8,175; **≤ 23,692 with measured H** | upper bound; with the measured byte entropy (X 6.62, Y 5.52 bits) it is ≈ 8L/H = 4,789 (X) and 23,692 (Y) |
| **τ_r** (generations) | 1 ≤ τ_r < 2^32768 | same shape, 1 ≤ τ_r < 2^131072 | no useful exact value; τ_r here measures the longest "delay line" of cells that die late, not a size (§4) |

Three corrections to how these were framed earlier, since you asked me to flag mistakes:

1. **"Self-improving forever" can never be in M∞.** If a cell must strictly improve (e.g. fewer NAND) every generation, an infinite chain would need infinitely many strict decreases of a non-negative integer. So for that criterion M∞ = ∅ and τ_i = ∞ by Eq. 3.2. Y has to be analysed with a *non-strict* criterion ("replicate; never get worse; improve while possible"), or with a finite "improvement rank". See §4.4. The phrase "improvement-rank" in HANDOFF_3 §2.3 should be read that way.
2. **τ_r is not a size threshold.** It is a property of the whole space M0 (the longest chain of cells before a descendant stops being a cell). A single counter byte in the ROM image already makes it ≥ 256, and the 134 spare bytes of X would allow vastly more (§4.3). The quantities that carry "how big must a replicator be" are τ_i and τ_c.
3. **The free-byte bound is safe even if the parent's spare bytes are not copied.** M∞ is the set of cells that have an *infinite forward chain of cells*, which includes transient cells that only become a fixed point after a step. A parent with arbitrary spare bytes whose child has them zeroed is still in M∞. So |M∞| ≥ 2^1072 (X) and ≥ 2^272 (Y) holds whichever way the bulk copy treats those bytes, provided they are never interpreted.

---

## 2. Mapping RNDW onto a generation system Γ = (U, M, R, G)

The paper (Definition 1): U is a universal set containing cells, resources and outcomes; M ⊆ U the cells; R ⊆ U the resources; G: M × R → U the generation function. Then M_0 = M, M_i = cells that can produce a cell of M_{i-1}; M∞ = ∩ M_i; the rank ρ(Γ) is the smallest ρ with M_ρ = M_{ρ+1}; and

- τ_r = ρ(Γ) (Eq. 3.1), and M∞ is exactly the set of cells meeting it,
- τ_i = log2(|M0| / |M∞|) bits if M∞ ≠ ∅, else ∞ (Eq. 3.2),
- τ_c = τ_i / H symbols, H = −Σ p_i log2 p_i bits per symbol of the representation language (Eqs. 3.3, 3.4).

### 2.1 The choices

| element | RNDW meaning (proposed) |
|---|---|
| U | all arm-buildable world fragments (parts, wires, programmed ROM contents), plus the bin |
| R | the bin of parts, treated as inexhaustible: **R is a singleton** (a closed machine; the 4th von Neumann requirement, an external input that can vary the offspring, is not modelled) |
| G(x, r) | run x until its arm halts; the fragment the arm built, with ROM programmed. Faults are counted, never visible (spec v0.5), so G is deterministic |
| M (the "cell" space) | the choice below; this is the decision that changes the numbers |

### 2.2 Two definitions of a cell

- **Definition A, fixed hardware.** A cell is a ROM image P of the world's ROM size S bytes, in a machine with fixed hardware H0. A built fragment is a cell iff its hardware equals H0 (up to translation; arm-relative coordinates make the child ROM byte-identical). |M0| = 2^(8S). This is the simplest, and it is what the X figures use.
- **Definition B, self-instantiated (recommended).** A cell is a ROM image P; its machine is the one P's own hardware description instantiates. A built fragment is a cell iff its hardware equals the instantiation of the ROM contents it carries (the self-consistency your `verify_*` scripts already check). |M0| = 2^(8S), with unparseable images as null machines that build nothing.

**Y forces Definition B.** Under A, g1's child g2 has different hardware (14,549 vs 15,495 NAND), so G(g1) ∉ M and g1 would be a non-replicator; only g2 (with H0 := g2's hardware) would qualify. That is not what we mean. Under B both g1 and g2 are cells, and the bounds below are unchanged in form.

### 2.3 Assumptions to keep in view

1. **Infinite space.** The real world has a finite grid, so literally only finitely many generations fit (Y uses stripes 140·n apart). The idealisation is an unbounded plane; finite space is a resource limit that would turn every M∞ cell into a finite-rank cell.
2. **Determinism and halting.** G(x) is the state when the arm stops commanding; a machine that never halts or faults is a non-cell.
3. **Membership is structural.** "Cell" means the built fragment *is* a machine of the family, not that it has been shown to run. That is what makes "child is a cell" decidable by comparing the build with the reference.
4. **Fixed-point proof is by determinism.** X: child ROM byte-identical and hardware identical to the parent, tested over three generations with 0 faults, hence G(X) = X and every descendant is X. Y: g2 and g3 identical, so g3 builds a g4 identical to g3 (the 200 M tick run completed g3 and started g4; the fixed point rests on equality plus determinism, not on a finished g4).

---

## 3. What is established about X and Y

- **X** is a generation cycle of order 1 (Prop. 5 / Cor. 3: any self-reproducing cell lies in M∞). ROM image 3,962 B in a 4 KiB ROM; RAM 32 B (30 used); 2,550 NAND + 308 DFF.
- **Y**: g1 → g2 → g2. A transient of length 1 into a fixed point; both in M∞. ROM image 16,350 B in 16 KiB (34 B free); RAM 256 B (196 high-water); 15,495 → 14,549 NAND, 2,104 DFF.
- Because the machines are closed (no inputs), one execution trace per generation covers all dependencies.

---

## 4. τ_r: the rank threshold

### 4.1 Structure (R a singleton)

With R a singleton G is a function, so the paper's sets have a simple reading: x ∈ M_i iff x's forward orbit stays inside M for at least i steps. A cell x ∈ M_i \ M_{i+1} ("deficient rank i") is one whose descendants are cells for exactly i generations and then something that is not a cell. Then:

- M∞ = cells whose forward orbit never leaves M (in a finite M0 these are the cells that reach a cycle: X, and Y's g1, g2);
- τ_r = ρ(Γ) = 1 + (the longest finite chain length over all deficient cells), or 0 if every cell is in M∞.

(Paper, Cor. 5 and Prop. 7: with R a singleton and every cell generable the rank is 0 or ∞. Here not every cell is generated by anyone, so the rank is finite but large.)

### 4.2 Bounds

| bound | argument | status |
|---|---|---|
| ρ ≥ 1 | some cell has a non-cell child (a ROM that builds nothing, or a corrupted description), so M0 ≠ M1 | follows from the definition; one cheap run to confirm |
| ρ ≥ 2 | a deficient-rank-1 cell: a cell whose child is a cell but whose grandchild is not. Under Definition B this is easy: a one-bit change in the description gives a child with one altered gate that still counts as a machine of the family but fails when it runs. Under Definition A it needs a delayed failure (§4.3) | not exhibited yet; the mutation experiment E2 (§8) produces such cells directly |
| ρ ≥ 256 | **counter construction:** x_c = X plus a counter byte c in the ROM that the copy loop decrements; at c = 0 the child is built without its RUN wire (a non-cell). Then G(x_c) = x_{c-1}, so x_c ∈ M_c \ M_{c+1} and ρ ≥ c + 1 | **not built.** Needs the decrement and test to fit in the 134 spare bytes; I would expect it to, but have not checked. A k-byte counter gives ρ ≥ 256^k |
| ρ ≤ \|M0\| − \|M∞\| | paper Prop. 4 and its proof (every layer is non-empty) | rigorous: ρ < 2^32768 (X), < 2^131072 (Y) |

### 4.3 Why this is not an informative number

The counter construction shows that ρ(Γ) for the space of *all* ROM images is bounded below by roughly 2^(spare bits not needed by the quine skeleton): hundreds to ~1000 bits for X. The value is set by how long a *contrived delay line* can be hidden in the spare capacity, not by anything about replication. What does carry information is the dichotomy of Principle of Degeneracy: **a cell can produce non-degenerate offspring iff it is in M∞**, and the sizes of M∞ and M0 (τ_i, τ_c). I would report τ_r only as "M∞ ≠ ∅; ρ finite but huge and dominated by delay lines", plus the observed structure: X has cycle length 1 and transient 0; Y has transient 1 and cycle length 1.

### 4.4 The Y criterion matters

| criterion for "G(x) is a cell" | M∞ | τ_i | τ_r |
|---|---|---|---|
| replication only (Definition B) | contains g1, g2 and X-like cells | finite, ≤ 130,800 bits | huge (delay lines), as in §4.3 |
| replication and cost never increases (Γ_mono) | contains g1, g2 | finite, ≤ 130,800 bits | huge |
| replication and cost *strictly* decreases (Γ_imp) | **empty** (no infinite strictly decreasing chain of a non-negative integer) | **∞** | finite: g2 has deficient rank 0, g1 deficient rank 1, so ρ ≥ 2; an upper limit is the largest possible NAND-count span |

So the von Neumann information threshold for "self-replicating *and* self-improving" is only meaningful as Γ_mono (improve until a fixed point), which is the Y you built.

**Adopted criterion for Y (decision D2/D4, confirmed by Joshua).** Y is analysed with **Γ_mono**: a Y cell is an image that (i) replicates, (ii) never builds a worse child (NAND count never increases), and (iii) **contains a working improver**, meaning that it would build a strictly better child whenever its description contains an improvable circuit. Clause (iii) is why the improver code is counted as necessary and not as free dead code. Y is evaluated at the **fixed point g2**, where the improver finds nothing further; g1 → g2 → g2 puts both g1 and g2 in M∞.

- τ_i and τ_c for Y are the Γ_mono values (estimate ≲ 91,600 bits, §11).
- **Improvement rank** is reported *separately* from τ_r: the number of strict improvements still available before the fixed point (g1 = 1: 15,495 → 14,549 NAND; g2 = 0). It is finite because the NAND count is a non-negative integer. It is **not** the paper's τ_r (that is the delay-line quantity of §4.3, the same kind as X's) and **not** a size threshold: it depends on how much improvable circuit the starting description holds and on the search the improver runs. The g1 = 1 figure comes from this one start and is not an intrinsic property of Y.
- Under the strict criterion Γ_imp, M∞ = ∅ and τ_i = ∞; that is not used.

---

## 5. τ_i: the information threshold

### 5.1 Upper bound, from what exists

Take M0 = all ROM images of S bytes with world constants fixed (Definition A or B). Let L = bytes of the working image. If the other S − L bytes are never interpreted (never feed control flow, addresses or arm coordinates; at most copied), any values there still give a cell in M∞, so |M∞| ≥ 2^(8(S−L)) and

τ_i = log2(2^(8S) / |M∞|) ≤ 8L.

| | S (ROM) | L (image) | free | |M∞| ≥ | τ_i ≤ |
|---|---|---|---|---|
| X | 4,096 B (32,768 b) | 3,962 B | 134 B (1,072 b) | 2^1072 | **31,696 bits** |
| Y | 16,384 B (131,072 b) | 16,350 B | 34 B (272 b) | 2^272 | **130,800 bits** |

This bound is independent of S as long as the program does not depend on it (a larger ROM adds equally to numerator and denominator). The ~99 kbit gap Y − X is an *indicative* price of self-improvement in this world only: the two differ in ISA width (AB 13 vs 15), RAM (32 vs 256 B) and description format.

### 5.2 Refinements, all of which can only lower the upper bound

1. **Unread bytes inside the image** (padding, e.g. the 18 B record-area padding in Y, bytes copied but never interpreted). Needs the dependence ("taint") audit, E1.
2. **Behaviour-preserving transformations that give distinct valid images:** RAM variable addresses (X: 30 variables in 32 B; `y/src/ram.asm` is the single place they are assigned), routine order, node order of the description if the encoded stream still fits. log2 of the number of verified distinct images is a rigorous addition to the exponent of |M∞|. Needs E3.
3. **Other replicators entirely** (a different quine, a different encoding) also lie in M∞. They make τ_i smaller still, and cannot be counted without finding them; a replicator smaller than X would lower the bound to 8 × its size.
4. **Mutation neutrality** (E2): the fraction of single-bit flips whose child equals the reference child gives a conservative, empirical lower bound on neutral mutants. If positions were independent, constrained bits ≈ L × (non-neutral fraction); label it an estimate.

### 5.3 Lower bound: what can and cannot be said

The tempting counting argument is the coding theorem: the number of S-bit programs whose output is a given object y is at most about 2^(8S − K(y)). Applied here it gives

τ_i ≥ K(H | world rules) − O(1),

where K is Kolmogorov complexity of the hardware (or of the whole built fragment) *given* the machine whose behaviour the ROM drives. Two reasons it does not yield a number:

- K is uncomputable. Every computable quantity we hold (xz sizes, the 1,658 B CPU description, the 1.27 KB xz of the core netlist) is an *upper* bound on K.
- The additive constant is the complexity of the machine that interprets the ROM. Because the arm is write-only, the program cannot inspect the hardware, so it must carry the information; but the interpreter (ISA semantics, arm protocol, simulator) already pins down a CPU of similar order of complexity. I therefore expect the bound to be close to vacuous at this scale. This is my reasoning, not a verified result.

Hence: **RNDW gives upper bounds on τ_i and τ_c, never lower bounds.** A real lower bound needs an enumerable M0 (§8, E7), where the paper's algorithm (its Section 5, the descendency matrix) computes ρ, M∞, τ_i exactly by brute force.

### 5.4 Sensitivity to the choice of M0

The earlier flat-netlist bounds (HANDOFF.md §4) answer a different question and are ~100× larger, because random NAND graphs are not like real designs:

| M0 | τ_i bound | source |
|---|---|---|
| flat NAND/DFF netlists, Hack machine with 4 KiB RAM | 3.54 to 4.39 Mbit | HANDOFF.md (needs a replicator in the space) |
| placed netlists | ~3.95 Mbit | same |
| generator program, 5,680 B xz | ~45.4 kbit | same |
| **ROM images, X** | **≤ 31.7 kbit** | this document |
| **ROM images, Y** | **≤ 130.8 kbit** | this document |

If M0 were instead *pairs* (hardware, ROM), τ_i would increase by log2 of the number of hardware designs in the family (the ROM bound plus a hardware term). I recommend the ROM-only M0 above (decision D1, §9).

---

## 6. τ_c: the complexity threshold

τ_c = τ_i / H (Eq. 3.4), H the entropy in bits per symbol of the language used to write a cell down. With τ_i ≤ 8L:

| language (symbol) | H (bits/symbol) | X, τ_c ≤ | Y, τ_c ≤ |
|---|---|---|---|
| bytes, uniform | 8 | 3,962 | 16,350 |
| 16-bit instruction words, uniform | 16 | 1,981 | 8,175 |
| bytes, empirical order-0 entropy of the real image (**measured 2026-10-16**) | X 6.619, Y 5.521 | **≤ 4,789** | **≤ 23,692** |
| 16-bit words, empirical order-0 entropy (**measured**; biased low, only 2,048 / 8,175 words) | X 8.488, Y 7.401 | ≤ 3,734 | ≤ 17,673 |

Measured from the saved states (`rndw_states_M7.tar.gz`): X's image (3,962 B) is byte-identical in generations 1, 2 and 3 (same SHA-256 on all six built copies) and its last 134 bytes are zero; Y's two 16,350 B images differ in only 105 bytes (13,142 to 13,317, the module records) and have H_byte = 5.52 and 5.51. Compressed sizes for scale: X 2,604 B xz, Y 5,520 B xz (gen 1). So with the measured byte entropy τ_c ≤ 8L/H gives about 4.8 k symbols for X and 23.7 k for Y; these are still upper bounds, and the byte-uniform value L is the smaller of the two only because it assumes H = 8.

Caveats: Eq. 3.3 assumes independent symbols, and the entropy of one specific image is only a proxy for the entropy of the language. A fairer H uses a corpus of programs in the same assembly language. The 5,680 B / H = 4.60 figure in HANDOFF.md is for the Python generator source, not for these ROM images.

---

## 7. Status summary

| item | exact | bound | not available |
|---|---|---|---|
| X ∈ M∞, cycle length 1 | verified by runs | | |
| Y ∈ M∞, transient 1 | verified by runs | | |
| τ_i (X, Y) | | upper: 31,696 / 130,800 bits (conditional) | lower bound; exact value |
| τ_c (X, Y) | | upper: ≤ 4,789 / 23,692 symbols (byte alphabet, measured order-0 H); ≤ L with H = 8 | a corpus-based H |
| τ_r | | 1 ≤ ρ < 2^S (weak); ρ ≥ 256 conjectured (§4.2, unbuilt) | exact value (needs full enumeration) |
| Γ_imp for Y | τ_i = ∞; ρ ≥ 2 (g1 rank 1, g2 rank 0) | | |

---

## 8. What is still needed (ordered by value per effort)

| id | measurement | gives | needs |
|---|---|---|---|
| **E1** | dependence audit: instrument the ISA model; classify every ROM byte as instruction fetch, interpreted data, copy-only, or unread; perturb copy-only/unread bytes and confirm the child command stream is unchanged | rigorous count of free bytes ⇒ a *checked* upper bound on τ_i (replaces the 134 B / 34 B assumption) | the ROM images (now available from `rndw_states_M7.tar.gz`; X's is read from the `rom` lines of any quine state); the ISA model `isahack.py` / `asmrun.py` is still needed. Pitfall: does the bulk copy cover all S bytes or only L? |
| **E2** | single-bit (and some pair) mutation sampling: classify child as identical (A), different (B), crash (C); for B run the child in the RNDW simulator | empirical neutrality; direct examples of deficient-rank-1 cells (ρ ≥ 2); rank-0 vs rank-1 split | `mutate_m6.py` as a base; simulator time (X ≈ 7.65 M ticks per generation; Y much more, so only a handful) |
| **E3** | verified symmetry count: permute RAM variable addresses, reorder routines/description, re-assemble with `asm.py`, replication-test each variant | a rigorous extra term in log2 \|M∞\| | `ram.asm`, `asm.py`, the builder tests |
| **E4** | order-0 entropy of the images: **done** (§6). Still open: a corpus of programs in the same assembly for a fairer H | τ_c with a measured H | a corpus |
| **E5** | build the counter-limited X variant (a counter byte in the spare ROM, decremented in the copy loop) | demonstrates ρ ≥ 256 concretely, and makes the "τ_r is dominated by delay lines" point with a real cell | ~tens of bytes of Hack-vN code; fits in the 134 B only if the code is small |
| **E6** | confirm M0 \ M1 ≠ ∅: an all-zero ROM and a ROM with a corrupted description both build non-cells | ρ ≥ 1 | one or two short runs |
| **E7** *(optional)* | a miniature world with an enumerable M0 (a toy ISA / tiny ROM) and the §5 algorithm of the paper | an **exact** τ_r and τ_i for a small world, and the only route to a true lower bound | a design for a toy world that has a replicator at an enumerable size (unknown whether one exists); decide whether it is worth it |

---

## 9. Decisions and questions for Joshua

- **D1: M0. DECIDED (Joshua, 2026-10-16): ROM images only** (hardware determined by the ROM description, Definition B). The pairs variant, which adds a term for the number of hardware designs, is not used.
- **D2: Y's criterion.** Replication only, or replication with non-increasing cost (Γ_mono)? Not strict improvement, which forces τ_i = ∞ (§4.4). Is a finite "improvement rank" (g1 = 1, g2 = 0) the number you want to report next to it?
- **D3: Which experiments**, and in what order. I suggest E1, E3, E4, E2, with E5 and E6 as short additions and E7 only if you want exact small-world values.
- **D4: Images.** Received (`rndw_states_M7.tar.gz`); E4 is done. E1 now needs only the ISA model and the builder/improver sources in a working tree.
- **D5: Finite space.** Is the unbounded-plane idealisation acceptable, or should the finite grid enter R?

---

## 10. Caveats

- All RNDW sizes and counts come from the handoffs and M7 write-up; I did not recompute them. In particular the 134 B and 34 B of unused ROM and the 3,962 B / 16,350 B image sizes are taken as given.
- Section 5.1 assumes the unused bytes are never interpreted. E1 is the check; until then, treat 31,696 and 130,800 as conditional upper bounds.
- The counter construction (§4.2) and the expectation that it fits in the spare bytes are reasoning, not a built and tested cell.
- Section 5.3's remarks on the coding theorem and the size of the additive constant are my argument and have not been checked formally.
- Everything is an upper bound from real designs: code showing that L bytes suffice never shows that L bytes are required. The hidden-design list from HANDOFF.md (hand-optimised cells, the HD format and tools, ROM, DFF and arm as primitives, the ISA, the module ladder and cost function that define improvement in Y, the test bench as specification) applies to every number here.


---

## 11. Results of the experiments you asked for (E1, E2, E6; E3 for X only)

Decisions applied: D1 ROM images only (Definition B); D2 Y is analysed as the **fixed point g2** (`improver_gen2_rom.bin`); D5 unbounded plane. Method: a C emulator of the Hack-vN-AB ISA plus ARM command log, validated by 400 random differential tests against the Python model (0 mismatches) and by reproducing the saved gen1→gen2→gen3 worlds for X and Y exactly (placements, wires, ROM bytes). A mutant ROM is run to halt; its command stream is compared with the reference stream and its PROGRAM_ROM output is collected as the child. Classes (a mutant is the reference ROM with one or more bits changed; it is run to a normal halt and its non-ROM arm commands are compared, in order, with those of the unmodified image; PROGRAM_ROM commands are not compared but are collected as the child ROM):
- **FIX**: halts normally, non-ROM command stream identical to the reference, and the child ROM is byte-identical to the mutant (a fixed point).
- **TOREF**: as FIX, except the child ROM equals the *reference* image (the changed byte was never copied, so the child reverts).
- **SAMEHW** (same hardware): halts normally with a non-ROM command stream identical to the reference, i.e. it builds the identical machine, but the child ROM differs from both the mutant and the reference image. It is not yet a fixed point; E2 re-runs the child as a new parent and follows the chain.
- **HWDIFF** (different hardware): the mutant would build a different machine. Any of: *diverged* (a non-ROM command differs from the reference at that position), *short* (halted before issuing all the reference commands), *badrom* (invalid ROM programming, e.g. wrong origin or out-of-range address). The first difference stops the comparison; whether the different machine would itself replicate is not tested, so under Definition B these may be good replicators of another machine.
- **CRASH**: never reaches a normal halt: illegal instruction, malformed arm command, command-log overflow, or timeout. The timeout is 2 × the reference instruction count + 1,000, so a valid but much slower mutant would be classed as CRASH (not observed, not ruled out).

**These tests model Definition A (hardware fixed) exactly; HWDIFF mutants change what is built and so under Definition B are other machines, undecided at ISA level.**

**E1, X byte audit (all 4,096 bytes).** 2,128 bytes are fetched as instructions, 1,834 are read as data, 134 are never touched. Perturbing each non-fetched byte (two values): 134 unread bytes → TOREF; 40 read-but-copy-only bytes → FIX; 1,753+ description bytes → HWDIFF/CRASH (interpreted). Trying all 255 other values on the 174 candidates: **all 174 stay free**. 300 random joint assignments of all 174: 300/300 gave same-hardware children. So X has ≥ 174 free bytes ⇒ **|M∞| ≥ 2^1392 ⇒ τ_i(X) ≤ 32,768 − 1,392 = 31,376 bits** (safe even though the 134 unread bytes are zeroed in the child, because the child is still a cell).

**E2, single-bit mutation.** X exhaustive (32,768 flips): HWDIFF 21,059; FIX 5,612; CRASH 4,825; TOREF 1,072; SAMEHW 200. Of the FIX flips, 5,180 are in *fetched* bytes: bits the ISA model ignores (e.g. AP's 13 low bits, A-instruction bits 14:13). That is a model-level fact, **not hardware-verified**; if counted, first-order τ_i(X) ≤ 32,768 − (1,072 + 432 + 5,180) = 26,084 (single-bit independence assumed, so treat as indicative). Y (g2) random sample of 20,000 of 131,072 flips: FIX 8,674 (43.4%), HWDIFF 6,664, CRASH 4,513, SAMEHW 149. FIX includes ~3,100 bytes of never-executed improver code, which are free for replication but not for a cell that must still improve. **Improver code counted as necessary (your decision, applied).** A replication-only test of the g2 image calls 43.4% of flips free (≈ 56,900 free bits, τ_i ≲ 74,000), but that is the wrong target: the g2 run never executes the improvement path. I ran the g1 image (it executes 11,894 distinct instruction bytes against g2's 9,796; 2,168 bytes are used only when improving) and treated every byte fetched by either run as part of a cell that must still replicate and improve. All 2,660 sampled flips in those g1-only bytes were FIX in the g2 test and so are *not* free for an improvement-capable cell; excluding them leaves 6,014 free of 17,340 sampled flips in the remaining bytes (34.7%), i.e. ≈ 39,400 ± 400 free bits and **τ_i(Y, improvement-capable) ≈ ≤ 91,600 bits** (first-order, single-bit independence, estimate, not a proof). Caveats: code never executed in either run but still part of the improver (paths for other circuits) cannot be told apart from padding this way, so this may still overstate the free bits; and, as with X, a large share of the free bits in fetched bytes are ISA-model don't-care bits that are not hardware-verified. Making this rigorous needs the per-byte all-values audit I did for X, not yet run for Y.

**Rank evidence.** SAMEHW mutants chain: X has 177 mutants whose child crashes and 23 whose child is a different-hardware machine, so chains of cells of length ≥ 2 exist (**τ_r ≥ 2**, i.e. deficient-rank 1 cells exist). In Y a sample showed 22 (SAMEHW→FIX) and 3 (SAMEHW→SAMEHW→FIX): mutants that need up to two replications to reach a fixed point, i.e. transients inside M∞. Depth never exceeded 3 in these samples; larger ranks need counter-like state, which I did not find by random flips.

**E6, non-cells.** For both X and Y, the all-zero ROM halts with an illegal instruction, and a minimal halt-only image emits no arm commands (rejected as short). Neither builds anything, so they are not cells, so M ≠ M0 and **τ_r ≥ 1**.

**E3 (symmetry count), X only, done at binary level.** A re-assembly from the Python builders was judged infeasible in the time allowed (the builder imports about ten source files, e.g. `nandgen.py`, `nl_hackvn.py`, `wirepass.py`, which the Project returns only inline). Instead I relabelled RAM variable addresses *in the ROM image*: the 214 executed A-instructions (30 distinct RAM addresses 0–29) whose next instruction touches memory (M operand/destination or AP) were rewritten under a permutation of the 32 RAM addresses, and each variant was run in the emulator (hardware stream must match, child must equal the variant, i.e. class FIX). Results: 328 of 495 tested transpositions are FIX (98 HWDIFF, 53 SAMEHW, 16 CRASH); uniform shifts of all variables by ±1, ±2 are FIX; a greedy search found a set S of 25 mutually swappable addresses, and **150 of 150 random permutations of S were FIX** (so the success fraction is above ≈ 98% at 95% confidence). That gives about log2(25!) ≈ **83.7 bits of verified-by-sampling symmetry**, i.e. roughly 2^83.7 distinct working X images that are not part of the free-byte count (different bytes). A uniform random permutation of all 32 addresses fails (0 of 150 FIX), because the remaining 7 addresses are constrained (for example 16-bit pointer pairs read through AP). Routine reordering was not tested, so 84 bits is a lower bound on the symmetry term; the true term is larger but not measured but probably modest, and negligible next to 31,376. Applying it: τ_i(X) ≲ 31,376 − 84 ≈ 31,290 bits. This is Definition A (hardware fixed); the same relabelling for Y was not run.

**Net.** (HWDIFF mutants are not all dead cells: see §12.) τ_i(X) ≤ 31,376 (rigorous, modulo the emulator model; ≈ 31,290 with the E3 term), τ_c(X) ≤ 31,376 / 6.619 ≈ 4,740; τ_i(Y) is estimated ≲ 91,600 bits with the improver counted as necessary (≲ 74,000 if dead improver code were allowed to be free). Lower bounds remain unavailable (§5.3). Per your decisions the improver counts as necessary and Y is reported as Γ_mono with a separate finite improvement rank (g1 = 1, g2 = 0), stated in §4.4. E3 was done for X only (≈ 84 bits).


---

## 12. HWDIFF follow-up: do hardware-changing mutants replicate? (X, 100 sampled, RNDW simulator)

**Question.** §11 puts a mutant in class HWDIFF when it makes the parent build a different machine. The ISA-level test cannot tell whether that different machine is itself a replicator (Definition B). This experiment runs a random sample of X's HWDIFF single-bit mutants in the RNDW simulator.

**Sample.** 100 uniformly random bit flips drawn from the 21,059 X flips whose first-step class was HWDIFF (E2). 66 fall in bytes read as data (mostly the description stream) and 34 in fetched code bytes.

**Method.**
1. Simulator: a local copy of `nandgen/rndw` (`world.rs`, `state.rs`, unchanged apart from an optional log of executed arm commands and making `arm_exec` public) plus a new harness binary. **Validation:** from `quine_gen1_start.txt`, 8,000,000 ticks reproduce `quine_gen2_built_tick8.0M.txt` with `save_state()` byte-identical to the file.
2. Stage 1, building the child: the mutant's arm command stream comes from the validated ISA emulator (run to halt, up to 4× the reference instruction count). It is replayed into an empty world with the simulator's own `place`/`connect`/`program_rom` rules, so overlaps, non-pin sites, double-driven inputs and out-of-bounds placements fault exactly as in the world. The child ROM is programmed just before the first wire, as the real builder does, and a few ticks are run between commands (reset keeps the child's DFFs settled).
3. Stage 2, running the child: the child is then run at gate level. Its own arm commands are compared one by one with the command stream that built it, with a 9 M tick cap and a 400 k tick stall limit. **Replicates** means the child builds a grandchild whose 8,171 non-ROM commands and 3,552 ROM bytes equal those that built the child, i.e. G(child) = child, a Definition-B cell. Reference: the unmutated machine passes (8,171 / 3,552 matched, 0 faults).
4. Cross-check: two mutants were also run fully at gate level (gen-1 world, mutant ROM poked into the parent, 8.7 M ticks) and compared with the replay. The replay and the full run agree on the child's parts, wires and ROM (hashes). For `m_2655_4` the full run also reproduces the replay's "unknown arm command 254" at the child's first command.

**Result (100 mutants).**

| outcome | count | what happened |
|---|---|---|
| **REPLICATES** | **4** (95% CI 1.6–9.8%) | each built the same parts as the original, with one wire redirected (1–2 commands differ). The child builds an exact copy of itself, 0 faults. All four are data-stream bytes. |
| child built but never issues a command (STALLED) | 50 | 11 with the ROM address bus frozen (reset never released, or CPU stuck at an address); 10 in a tight loop of ≤ 8 addresses; 29 executing widely but never writing the arm. 33 of the 50 had no stage-1 fault. |
| child's first command is wrong (DIVERGES) | 30 (27 at command 0) | garbage command codes (`unknown arm command 254/255/…`: 12), a PLACE of an invalid kind or rotation (2), out-of-bounds or overlapping placements (6), wrong-but-valid commands (5). Three children copied correctly for 62, 125 or 1,149 commands, then deviated. |
| parent never finishes building | 11 (parent timed out) | parent's code runs away on a corrupted record: 7 leave the child's arm EN unwired, 4 never place an arm at all. The children are unusable. |
| parent programs the child ROM wrongly | 3 (`badrom`) | PROGRAM_ROM aimed at a non-ROM location; not replayed. |
| parent builds fully but arm EN left unwired | 2 | the wire that connects the child's EN was lost. The child can never issue a command. |

**What the four replicating mutants actually change (X).** Each flips one bit in the Exp-Golomb description stream, which changes one backward distance in a "source" reference, i.e. one wire of the CPU core is attached to a different gate. Nodes are numbered in row order (the core's NANDs lie below node ≈ 941 where the RAM tiles start); a wire goes from a source node to an input pin of a destination node.

| mutant (byte, bit) | destination gate / pin | source was → is | backward distance |
|---|---|---|---|
| m_3584_1 (3584, 1) | node 734, pin B | node 631 → 663 | 103 → 71 |
| m_3078_4 (3078, 4) | node 495, pin B | node 476 → 480 | 19 → 15 |
| m_2554_7 (2554, 7) | node 182, pin B; node 183, pin A (two wires) | 77 → 127; 182 → 174 | 105 → 55; 1 → 9 |
| m_2506_4 (2506, 4) | node 147, pin A | node 92 → 94 | 55 → 53 |

Everything else (2,550 NAND, 308 DFF, ROM, arm, the other 5,309–5,310 wires, all other commands) is identical. These are not logically equivalent swaps: the old and new source signals differ on 30–85% of ticks during a normal generation, and in the original run the rewired gate would have produced a different output on 5.3% (m_3584_1), 13.7% (m_3078_4), 0.8% and 85.5% (the two wires of m_2554_7) and a single tick out of 8 M (m_2506_4). (The second m_2554_7 figure is computed in isolation; that wire's source is itself changed by the first.) So these CPUs compute different internal values for a good part of the run and still copy themselves exactly: the changed gates feed logic that is masked (not observable) for the instructions the quine executes. They are replicators for this program, not necessarily full Hack-vN CPUs; other programs could expose the difference. I did not map the nodes to named CPU blocks (state files carry no names).

**What does not happen.** There is no way to destroy or remove a part (the arm has PLACE, WIRE and PROGRAM_ROM only). A bad command is rejected with a fault and the world continues; 35 of the 86 halting parents hit at least one fault. A parent can only fail to build a working child. One caveat: two mutants had their first fault at a site in the parent's own rows (`m_910_1`, `m_998_1`); in the real world such a wire could attach to an unconnected parent pin, which my replay (child only) cannot show. I did not see evidence of damage.

**Consequences for τ.**
- HWDIFF is not "not a cell". About 4% (CI 1.6–9.8%) of X's HWDIFF single flips are exact replicators under Definition B. First order, that is ≈ 840 further neutral bit positions (CI ≈ 340–2,060 of 21,059), on top of the free bits of §11. If flips were independent, τ_i(X) would fall from ≈ 31,290 to ≈ 30,450 bits under Definition B. This is a rough estimate (independence untested, 4 hits), and it counts only exact self-copies; a child that builds a different but working grandchild would add more.
- All hits are 1-wire rewirings in the description. Code flips (34 sampled) never replicated.
- Y was not run: one Y generation is about 110 M ticks and the sample would take days.

**Cost.** About 8 s per mutant on average (most fail within seconds; a replicating mutant costs ~2 min). Running all 21,059 would take about a day on two cores; a 1,000-mutant sample would take about 1–2 hours.
