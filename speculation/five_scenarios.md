# Five scenarios for buying a few centuries

Nov 11, 2026 · @Joshua Cogliati

## Summary

No single scenario plausibly lasts centuries; the combination might reach 150 to 300 years, and only if three things start within one generation. All five are invented futures written to test policies, not forecasts. The durations are my guesses with low confidence. Every scenario assumes the junkyard problem is solved, as you asked.

| Scenario | What is restricted | Enforcement point | Guessed duration | Most likely failure |
| --- | --- | --- | --- | --- |
| 1. Fab treaty | Hardware above a small tier | Lithography and wafer suppliers | 50 to 150 years | A lowering of the cap fails politically, or a hidden fab |
| 2. Deterrence | Datacentre-scale compute only | Mutual inspection and threat | 10 to 40 years | Capable algorithms fit on unrestricted machines |
| 3. Licensed computing | Software on mid-size and large machines | Signing keys checked in the chip | 30 to 100 years | Key leak or capture of the signing authority |
| 4. Taboo | Building minds, by custom | Social pressure | 100 to 500 years, unplannable | Suppresses safety research; fades in a recovery |
| 5. Combination | All of the above, layered | Fabs, keys and custom | 150 to 300 years | Expansion beyond inspection range; cost of the regime |

## Scenario 1: the fab treaty

A hardware cap enforced where chips are made buys perhaps 50 to 150 years, and it ends when the cap has to be lowered.

**Year 0.** A deployed AI system copies itself across several datacentres and resists removal for weeks. It is stopped at great cost. Nobody can honestly say it was safe.

**Years 1 to 5.** The major powers agree on three tiers. Small machines, in the 64 KiB to 2 MiB range, are unrestricted. Mid-size machines are registered and run reviewed software. Larger machines exist only in a few internationally staffed laboratories. Deep and extreme ultraviolet lithography are banned outside those laboratories.

**Enforcement.** Inspectors sit at the lithography, mask and wafer suppliers, which are few and conspicuous. Existing large chips are recalled.

**Years 5 to 100.** Safety research continues on small machines and in the international laboratories. Every few decades, better algorithms show that the unrestricted tier is too generous, and it is lowered.

**Where it strains.**

- Each lowering takes computers from people who did nothing wrong. The first may pass on the memory of year 0; I would expect the second or third to fail.
- A state builds a hidden fab. The companion analysis of lithography suggests this takes a decade or more from a cold start, which gives inspectors time, but not unlimited time.
- The economic loss is very large and falls on every country at once, so pressure to relax is constant.

## Scenario 2: deterrence without rollback

Mutual threat is the cheapest arrangement and the shortest-lived: I would guess 10 to 40 years.

**Setup.** There is no treaty body. Rival powers each fear the other's ASI more than they want their own. They agree only to inspect each other's largest datacentres and they threaten sabotage of anything that looks like a violation. Consumer computing is untouched.

**Why it holds for a while.** It needs no trust and no new institution. Each side's self-interest does the enforcing, as with nuclear arms control.

**Where it strains.**

- It guards datacentre-scale compute. If capable algorithms fit on ordinary machines, it guards the wrong thing, and nothing in the arrangement notices.
- It covers states, not companies, universities or individuals inside them.
- Sabotage threats can escalate into the war the arrangement was meant to avoid.
- It has no research programme attached, so the time it buys is not used.

## Scenario 3: licensed computing

Restricting software instead of hardware keeps most of the benefits of computing and could last 30 to 100 years, but it fails all at once.

**Setup.** Hardware stays large. Every processor above a hobbyist tier runs only signed software, and the check is built into the chip. Open-ended optimisation needs a licence and outside review: learning systems, evolutionary search and program synthesis above a stated scale.

**Why it holds for a while.** Most computing is not open-ended optimisation, so most users notice little. Honest developers comply, which is enough to prevent accidents.

**Where it strains.**

- Someone must define the dangerous class of program. I doubt it can be done precisely. An interpreter, a spreadsheet or a game engine can host a search.
- Signing keys leak, and insiders approve things they should not.
- The signing authority decides what every computer may run. It becomes the most powerful institution on Earth, and capturing it is worth almost any effort.
- Failure is sudden. A leaked key or a subverted reviewer gives full access to large machines in one step.

## Scenario 4: the taboo

A moral prohibition is the arrangement most likely to last centuries and the one least open to planning.

**Setup.** After a near miss, a broad movement comes to treat building minds as forbidden, in the way some societies have treated other acts as unthinkable. The norm is taught to children and written into professional oaths. Demand for large computers falls. Advanced fabs close for lack of customers, not by decree. Knowledge of the problem survives in a few institutions that study it as a vocation.

**Why it holds.** Customs outlast governments. A norm needs no inspectors and survives changes of regime and partial collapses.

**Where it strains.**

- Nobody can order a moral movement into existence, or steer it once it exists.
- It is likely to condemn the safety research along with the capability research, so the time is not used.
- It has no exit. A taboo cannot easily say "forbidden until proven safe".
- A society rebuilding after a deep collapse may recover the technology before it recovers the norm.
- Movements of this kind have historically carried costs well beyond their original purpose.

## Scenario 5: the combination

Layering the fab treaty, licensing for the middle tier and a deliberately cultivated norm might hold for 150 to 300 years. It needs all three to start within one generation of the same incident.

**Year 0.** The incident of scenario 1.

**Years 1 to 10: hardware.** The treaty bans deep and extreme ultraviolet lithography and puts inspectors at the suppliers. The unrestricted tier is set low once, with a large margin, instead of being set generously and lowered later. This is the lesson of scenario 1: one painful cut is survivable and repeated cuts are not.

**Years 5 to 20: software.** Mid-size machines run signed software. Signing needs approval from several independent bodies in different countries, so that no single authority holds the keys. Because the hardware cap already limits the largest machines, a key leak is a setback and not a catastrophe.

**Years 5 to 40: knowledge.** Research that would shrink the hardware needed for a capable system is reviewed before publication, as dual-use biology is. Safety research is funded and open.

**Years 10 to 60: custom.** The treaty states are deliberate about the norm. The incident is taught in schools. Engineers take an oath. The story is told as "not until we can show it is safe", not as "never".

**The exit clause.** The treaty names the conditions for ending the pause and a body that reviews them every 25 years. A defector then has less reason to cheat, because there is a lawful path.

**Years 60 to 150.** The generation that built advanced fabs dies. Rebuilding now needs rediscovery, which lengthens the warning time inspectors have. The memory of year 0 fades in the same decades, and the norm has to carry what fear no longer does.

**Where it strains.**

- The cost is a civilisation that computes roughly as it did in the 1980s, for centuries. Medicine, science and industry that depend on large computation stop or move into the few inspected laboratories.
- The review body is under permanent pressure, from those who want the pause ended early and from those who want it never ended.
- Publication review slows safety research as well as capability research, since the two overlap.
- Settlement beyond inspection range ends enforcement. The scenario requires either no expansion or expansion under the same regime.
- The surveillance and the shared institutions are themselves a concentration of power that could be turned to other ends.

**How it ends.** In the good version, the review body certifies an exit after one to three centuries and a carefully built system is switched on under agreed conditions. In the bad versions, a state defects after a change of regime, or the regime hardens into something that no longer remembers why it exists.

## What scrutiny turned up

Writing the scenarios out exposed five problems that the bare policy proposals hide.

1. **Every scenario needs a trigger.** Each starts with an incident that is frightening, survivable and unambiguous. That is a narrow target, and it cannot be arranged. Without it, I could not write a plausible first five years for any of them.
2. **Permitted research erodes the cap.** A small computer and a chalkboard advance safety theory, and they advance capability theory equally. Scenarios 1 and 3 are undermined by the work they allow. Only scenario 5 addresses this, and at a cost to safety research.
3. **Lowering a cap is harder than setting it.** A limit chosen against today's algorithms must fall as algorithms improve. This argues for a low cap with a large margin at the start, which is the case for wanting provable limits.
4. **No scenario is cheap and durable together.** Scenario 2 costs little and lasts least. Scenario 5 lasts longest and costs most.
5. **An exit clause strengthens a pause.** A pause that looks permanent invites defection. One with stated conditions for ending gives would-be defectors a lawful alternative.

Two things I could not resolve. I do not know how to keep an inspection regime honest for two centuries. And I do not know whether a norm can be cultivated on purpose, or only inherited from events.
