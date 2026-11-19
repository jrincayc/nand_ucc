# Provable hardware lower limits: what can and cannot be proved (2026-11-10)

Status labels: [P] proved or standard, [C] conditional, [E] my estimate, not computed.
Reads on top of `hardware_limits_for_agi.tex`, `DESIGNER_BOUND_NOTES.md`, `RNDW_VON_NEUMANN_THRESHOLD.md`, `HANDOFF_RNDP_R1_R6.md`.
I ran no code for this note. It is argument only.

## 1. Result in one paragraph
A proved limit at the 4 KiB to 64 KiB scale is not reachable with known mathematics, and for the paper's time-free definition it is probably not provable at all. What is provable: (a) an accounting inequality that turns the paper's claim into one conjecture about one number, (b) black-box search bounds, (c) exact thresholds in worlds small enough to enumerate (a few bytes), (d) structural bounds of order log n (a handful of gates). Everything the project has measured is an upper bound and stays one.

## 2. The formal question (my choice)
Fix five things: the sealed machine M (CPU and its I/O), the world W (rules and initial contents), the success set A (action sequences or world histories that count as independence), a step budget T, and a success probability p (take p = 1 first).

**Lambda_T(M, W, A) = the least S such that some S-bit initial state of M (program and data together, as in the paper's R/W-only model) produces a member of A within T steps.**

A "hardware lower limit" is a proved lower bound on Lambda_T. The paper's 64 KiB claim is the conjecture Lambda_T > 524,288 bits for the real world.

Why this form:
- The program lives in the S bits, so S bounds initial information, which is the quantity that survives when the machine starts using the world as memory. A memory cap alone does not survive that: the first thing an escaping machine builds can be more memory (a loop builds RAM tiles; R6 does this).
- T must be in the definition. Without it the question meets section 4, barrier 1.
- W and A must be in the definition. No bound is independent of the environment: a world that contains a "build an AGI" button has Lambda of a few bits. A helpful human or a reachable larger computer is such a button. [P], trivially.

## 3. What is provable
1. [P] **Accounting.** If an S-bit state reaches a in A within T steps, then a is computed from (state, T) by simulating M and W, so S + log2 T >= Kt(A | M, W) - O(1), where Kt is Levin's complexity (program length plus log of run time) minimised over A. For a randomised machine replace Kt by -log2 of the T-bounded algorithmic probability of A; then S + log2(1/p) is at least that. These are definitions unpacked, but they fix the exchange rates: time buys at most log2 T bits, luck buys log2(1/p) bits.
2. [P, physics-conditional] log2 T <= 100 for the adopted budget; about 400 for the Lloyd estimate of 10^120 operations in the observable universe. So search and time together are worth 12.5 to 50 bytes. The limit is therefore Kt(A | M, W) minus at most 50 bytes: the whole question is the size of Kt.
3. [P] **Invariance.** Changing the CPU moves Lambda_T by at most the size of an interpreter of one CPU on the other, with a constant-factor change in T. "64 KiB" means "64 KiB give or take an interpreter" (hundreds of bytes for the CPUs in this project [E]).
4. [P] **Trivial ceiling.** Lambda_T <= |a| + c for the shortest stored a in A. In RNDP this is R6's image: 16,006 B. So in RNDP a Turing-complete replicating constructor is below 64 KiB already.
5. [P] **Black-box search** (already in DESIGNER_BOUND_NOTES section 2). A designer whose only access to A is testing candidates drawn without knowledge of A needs about 1/rho tests. This is unconditional but applies only to designers with no knowledge.
6. [P] **Exhaustive small worlds.** Lambda_T is computable for fixed finite T, so in a world with 2^40 to 2^50 images it can be computed exactly. That is a real lower bound, for 5 to 6 bytes.
7. [P] **State counting.** A closed machine that emits L distinct commands and stops needs at least log2 L state bits and at least log2 n distinct driven coordinate nets to place n parts. This gives n >= about log2 n, which excludes only machines of a handful of gates. I did not work out the exact constant against RNDP_SPEC because the number is uninteresting.

## 4. Why nothing stronger is available
1. **Time-free version: logic.** [P] For decidable non-empty A, some member of A has K(a | W) <= |checker for A| + c (enumerate and test), so the time-free information threshold never exceeds the size of the specification. [P] By Chaitin's theorem ZFC proves no statement K(x) > L for L above a constant c_ZFC of about the size of a ZFC proof enumerator. A lower bound on the time-free threshold for a set with a known member implies such a statement. The published 7,910-state machine whose halting is independent of ZFC (Yedidia and Aaronson 2016) is about 30 KB as a transition table, and smaller machines have been reported since; c_ZFC for Hack or RV32 is unmeasured but I expect it to be below 64 KiB [E]. If so, a time-free 64 KiB information bound is unprovable in ZFC whether or not it is true.
2. **Time-bounded version: the circuit lower bound wall.** Lambda_T is finite and computable, so true bounds have proofs, but the only known general proof is enumeration of 2^S states. A short proof that no small fast program outputs a member of a natural, easily checked set is the same kind of statement as an explicit circuit lower bound. The record there for a function in P is 3.1n - o(n) gates (Li and Yang 2022); no superlinear bound is known. Known techniques (gate elimination, restrictions, communication bottlenecks) do not apply to "design a replicator". This is not a formal reduction; it is a statement about which techniques exist.
3. **Information-flow bounds leak.** Unconditional space bounds exist where input is read once (streaming, one-way finite transducers, INDEX: answering questions about n bits read earlier needs about n bits). The paper's manual W1 xor R1 I/O is such a model. But independence means writing state into the world and reading it back, so the bottleneck is gone exactly when it matters. These bounds can limit a sealed machine's conversation (it cannot recall more than S bits of what it was told), not its escape.
4. **The real world is not a formal object.** W includes humans, documents and other computers, so Kt(A | M, W) for reality has no definition to prove things about. Toy worlds have theorems; reality has estimates.

## 5. Consequences for the paper
1. "We show that a 64 KiB ... limit can be used to make an independence gaining AGI practically impossible" overstates. Both supporting arguments price particular methods (word vectors; 36 bytes per atom). The cost of a method is an upper bound on cost, never a lower bound. Suggested: state it as a conjecture with supporting estimates.
2. P. ubique is used in the wrong direction. A genome of 1,308,759 base pairs is about 2.6 Mbit, about 320 KiB: an existence proof that this much heritable information suffices for independent replication given a cell and an ocean. That is an upper-bound witness, and it lies below the paper's 2 MiB "likely lower" row. The 3 MiB figure is the cost of one design method (atom coordinates held in RAM); evolution never held the design in a memory. Caveat: replicating is not gaining independence by design, which is the designer-versus-replicator point of DESIGNER_BOUND_NOTES.
3. The AGI definition excludes time. With time excluded the claim rests entirely on the sealed workspace and on the world being unforgiving, and barrier 1 applies. Adding the budget (2^100 operations) to the definition costs 12.5 bytes of bound and makes the statement well-posed.
4. Rice's theorem remark is fine. The Devore remark is fine as written (no minimum is proved there either).
5. The project's own data cut against a naive reading: R6 (Turing complete, builds its own ROM and RAM from gates) is a 16 KB image, Y is 16 KiB. In RNDP the replication threshold is under 64 KiB. The paper's claim therefore lives in the gap between RNDP and reality (free arm, free parts, no energy, no physics, no opposition) and in design versus copying. Say so explicitly.

## 6. What could still be done
1. Rewrite section "Limiting Estimates" around Lambda_T: definition, the accounting inequality, the conjecture, then the estimates as evidence. Add a short "barriers" subsection (section 4 here).
2. Exact Lambda_T in an enumerable toy world (E7 of the threshold document). Gives a true lower bound and the interpreter constant, at a few bytes. Needs a world design agreed first.
3. Record of failed attempts below a size, as in circuit minimisation: weak evidence, but the only kind that accumulates.
4. Compute c_ZFC-style constant for Hack-vN-AB or RV32EC. Would turn barrier 1 from an estimate into a number. Large effort, modest value.

## 7. Caveats
- Section 4 item 1's size estimate for c_ZFC is not computed for this project's CPUs.
- Section 4 item 2 is an analogy to circuit complexity, not a reduction.
- I did not read RNDP_SPEC.md for this note; item 3.7 is stated only up to its order of magnitude.
