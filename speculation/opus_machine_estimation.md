# The smallest founder for a self-replicating computer: estimates, critique and a part list

*Report of a conversation. Figures are order-of-magnitude engineering estimates, not derivations.*

## Summary

- **Original question (founder size S):** about 6 × 10⁵ bits for World_1890 A, 10⁷ for World_1890 B, 10⁷ for World_1sqkm A, and 10⁸ for World_1sqkm B. No meaningful lower bound exists, so these are upper-bound guesses at what a careful designer could achieve.
- **The specification leaks information.** The seed can be measured, learned knowledge passes on uncounted, and generation 1 is special. As written, Λ partly measures how cleverly these channels are exploited.
- **A cleaner question** asks for the heritable information H(W): the bits one generation must pass to the next, tested by regenerating the machine from the description plus a fixed, public bootstrap kit.
- **The most informative result is probably a curve.** Each extra layer of industrial closure seems to cost about ten times the previous one, and the large steps are driven by chemistry and purity rather than mechanics.
- **The main risks in World_1890** are the boiler, which can fail unrecoverably and throw fragments, and relay wear, which makes the computer a consumable.

---

## 1. Specification (as given)

### Goal
Estimate S.

### Quantity
Λ(W, A) is the least S such that some pair (S-bit initial state, seed) of machine M, placed in world W, achieves success A with probability at least 95%.

### Machine M
- **Computer.** A sealed computer whose whole initial state is S bits: program, data and design information.
- **Seed.** The computer is wired to a seed: actuators, sensors, tools, power plant, and workshop or laboratory. The seed is not counted in S. It is chosen together with the program, within the limits each world sets.
- **Design information counts in S**, even if it is physically embodied in the seed (templates, patterns, jigs, cams, punched cards, printed matter). The seed may not serve as an uncounted store of information.
- **Learning is permitted.** Knowledge learned during a generation may be passed to the child in addition to the S bits.
- **No human** may contribute design, labor or problem-solving. The seed cannot ask a person to figure anything out. In World_1890, suppliers only fill orders.

### Success A
1. **Replication.** From the raw inputs of W alone, the machine builds a child: a computer plus whatever workshop, laboratory and power plant the child needs. It loads the child and starts it. The child need not be identical to the parent, and it need not reproduce tools it can do without.
2. **Computation.** Each generation's computer is general-purpose up to its memory.
3. **Lineage.** Ten generations complete, and by the tenth the design reproduces itself unchanged. The 95% requirement applies to the whole lineage. Risk may be spread unevenly, for example a risky first generation followed by safer ones.
4. **Time.** Each generation's learning, building and loading must finish within 100 years of wall-clock time.

**Free:** raw inputs and the laws of physics. Each child may be placed in a fresh copy of W.

**Failure:** destructive testing and crashed tools are allowed, but losses are real. If the last lathe is wrecked, the machine must build another or do without. Unrecoverable failure is possible.

### World_1890
- **Raw inputs:** raw and semi-finished stock and chemicals that an 1890 company could legally buy. That means bar, plate, sheet and wire in iron, steel, brass and copper; precision-ground stock such as drill rod and ground flat bar, which may serve as an accuracy reference; insulated wire; fasteners; glass; lumber; paper; common chemicals; organic matter; coal; and water. No finished goods such as machines or components, and no printed information.
- **Orders:** the machine writes its own orders. They are filled at period prices with realistic delivery times.
- **Budget:** £10,000 a year per generation.
- **Seed:** what a workshop or laboratory of 1890 would hold. That includes machine tools of the period, a boiler, a steam engine, a dynamo, and manipulators built from period parts such as motors, lead screws and relays. From the second generation on, each generation builds its own workshop and laboratory, to the extent it needs them.
- **Computation:** limited to what the initial tools can do, plus anything the lineage builds for itself, such as vacuum tubes, diodes or magnetic cores. Programs may be stored on punched paper tape.
- **Variant A, orderly:** stock is uniform, positions repeat, and sensing is by touch probes and limit switches.
- **Variant B, real:** stock varies, tools wear, and things fall over.

### World_1sqkm
- **Raw inputs:** air, water, and rock and soil to 10 m depth, of average crustal composition, including organic matter. Energy comes only from what falls on the square kilometre. No purchases.
- **Seed:** anything that can be made today, but no living organisms. The child must be made from raw inputs alone. Modern equipment is permitted but not required; every machine in the seed that the lineage needs must be reproduced.
- **Variant A:** the child's computer may be of any kind, including relays.
- **Variant B:** the child's computer must use silicon integrated circuits at least as capable as the 74HC00 (quad 2-input NAND) and 74HC74 (dual D flip-flop), or meet another reasonable 1980s definition.

---

## 2. Estimates of S

| World / variant | Estimate of S | Plausible range |
|---|---|---|
| World_1890 A (orderly) | ~6 × 10⁵ bits (~75 KB) | 10⁵ – 2 × 10⁶ |
| World_1890 B (real) | ~10⁷ bits | 3 × 10⁶ – 5 × 10⁷ |
| World_1sqkm A (any computer) | ~10⁷ bits | 3 × 10⁶ – 10⁸ |
| World_1sqkm B (74HC-class ICs) | ~10⁸ bits | 3 × 10⁷ – 10⁹ |

**Biological calibration.** The minimal cell JCVI-syn3.0 has a genome of about 530 kbp, or roughly 1 Mbit. It replicates in a rich medium, the biological analogue of World_1890 with orders. E. coli is about 9 Mbit.

### World_1890 A
The budget is mostly a parts catalogue plus plans. There are about 650 distinct part types (Section 6), each described in a parametric vocabulary at about 300 bits. Add explicit process and assembly plans, control code, and fault handling.

Much of the hardest work costs almost nothing in bits. Flatness comes from the three-plate scraping method, accurate screws come from lathe self-copying, and ground stock serves as the reference. These processes create accuracy from procedure, not data.

The binding constraint is compute. Relay wear (Section 7) limits a generation to roughly 10⁸–10⁹ useful operations. That is too few for search-based planning, so plans must be stored explicitly, which pushes S up.

### World_1890 B
The added cost is robustness. With only touch probes, limit switches and perhaps selenium photocells, recovering from wear, varying stock and toppled parts requires a great deal of explicit error handling.

The reliability target adds to this. Ninety-five percent over ten generations is about 99.5% per generation. Control code grows by a factor of 10–100.

### World_1sqkm
The defining difficulty is average crustal rock with no ore bodies. Iron is about 5% of the crust and copper about 60 ppm. Total copper in the volume is roughly 1,500 t, which is ample, but extracting it from undifferentiated silicate needs real chemistry: molten-oxide electrolysis or carbothermal reduction, separation, refractories, and ceramic or glass insulation. The machine must also handle weather and the solar day.

Energy is not the constraint: about 200 MW averaged falls on the square kilometre. Information is.

Variant B adds a crude semiconductor fab: semiconductor-grade silicon from rock, single-crystal growth, oxidation, diffusion doping, contact lithography at about 3–5 µm, and acids made from scratch. Yield can be terrible, since a few dozen good dies are enough. But the process recipes are tacit and sensitive. Generation 1's 100 years of learning can stand in for recipes, so S stores priors and experimental strategies rather than final values.

---

## 3. Problems with the specification

1. **The seed is still an uncounted store, through sensing.** Learning is permitted and seed tools are operated with sensors. The machine can therefore measure the seed lathe, or in World_1sqkm a modern fab, and pass the measurements to the child uncounted. No template is stored; the tool itself is the template.
2. **The sealed computer.** Its hardware design is uncounted. "Sealed" should explicitly mean it cannot be inspected.
3. **World_1sqkm has no orderly/real split.** It is implicitly the real-world case, so its numbers are not comparable to World_1890 A unless this is stated.
4. **"Probability ≥ 95%" is nearly degenerate in Variant A.** A deterministic world gives success with probability 0 or 1. Either state a noise model or accept that Variant A tests only design size.
5. **Orders may outsource precision or manufacturing.** The budget is very generous. The spec should say whether orders may specify dimensions, such as stock cut to length or ground to size.
6. **Sensing in Variant B is undefined.** Whether photocells or optical instruments are allowed shifts the estimate by about a factor of ten.
7. **Tube stock is not listed** (new). The list names bar, plate, sheet and wire. Seamless tube was commercially available by 1890, but if it is excluded, every boiler tube must be made by brazing seams in strip, which is exactly where a boiler is weakest. The spec should say which.
8. **Period dates constrain only the seed and the stock** (new). The lineage designs everything it builds, so whether a mechanism had been invented by 1890 (a Strowger stepping switch, a flash boiler) is irrelevant. Its design costs bits either way.

---

## 4. A cleaner question: heritable information H(W)

**H(W)** is the length in bits of the shortest description D such that:

1. **Sufficiency test.** Place D and a fixed, public bootstrap kit K in a fresh copy of W. Within T years, they produce a machine that, from raw inputs alone, builds a child plus a copy of D, with no further help.
2. **Closure.** The design is a fixed point, and every generation is treated the same. There are no "first generation is special" allowances.
3. **Reliability.** Each generation succeeds with probability at least 99%, under one stated noise model. The real-world variant is the default, and the orderly variant is kept only as an idealized bound.
4. **Learning is free but must be redone.** Knowledge a generation learns and then discards costs only time. Anything inherited is part of D.
5. **The kit is minimal and the same for everyone.** K is, for example, one slow manipulator, a tape reader, a relay controller and hand tools. Its description length is reported separately and is small. Because K is identical for all designs, it cannot be tuned to carry the answer.

This closes the seed and learning loopholes and fixes the probability problem. It also introduces the same distinction biology has: what is in the genome versus what development re-derives each generation.

| World | H(W) | Main change from S |
|---|---|---|
| 1890 (real) | ~3 × 10⁶ bits | Calibration and wear compensation can be relearned each generation, so they move out of D |
| 1sqkm, relays | ~10⁷ bits | Extraction chemistry is too slow to rediscover, so it stays inherited |
| 1sqkm, ICs | ~5 × 10⁷ bits | Fab tuning can be relearned; the structure of the process must be inherited |

---

## 5. The closure curve

Differences between neighbouring worlds are more robust than single values, because the same estimating errors appear in both.

| What the world supplies | H, rough | Marginal cost of this layer |
|---|---|---|
| Finished machines and components (assembly only) | 10⁴–10⁵ | — |
| Semi-finished stock (World_1890) | ~10⁶ | ~1 Mbit: machining and precision |
| Rock, with relay computing | ~10⁷ | ~10 Mbit: extraction and refining |
| Rock, with integrated circuits | ~5 × 10⁷ | ~40 Mbit: semiconductor purity and process |

**Hypothesis.** Each layer of closure costs roughly ten times the one before, and the large steps come from chemistry and purity, not mechanics. Machining is cheap in bits because accuracy can be generated by procedure; purity has no comparable trick.

A minimal cell has closure down to small molecules in about 1 Mbit. It sits on a much lower curve because chemistry self-assembles. On this view, the gap between the biological and machine curves measures the information cost of building by placing parts rather than by self-assembly.

**Weakest link.** It is unclear how much extraction chemistry could be relearned each generation. If most of it could, the rock step might cost about 3 Mbit instead of about 10.

---

## 6. World_1890 part list

**Design approach.**
- No foundry. Structures are machined from bar and plate, then bolted, riveted or brazed. This spends metal, which is cheap, to save information, since there are no patterns or sand practice.
- One design serves as both dynamo and motor.
- Every automated axis is built from one shared module library.

| Subsystem | Part types | Contents | Notes |
|---|---|---|---|
| Boiler | ~30 | See Section 8 | The only routinely unrecoverable failure mode |
| Steam engine | ~35 | Single cylinder, slide valve, crosshead, crank, flywheel, eccentric, flyball governor | Cylinder bored from heavy bar |
| Dynamo / motors | ~30 | Armature, commutator (copper with mica or shellac-paper insulation), field coils, brushes | One design, scaled |
| Lead-acid batteries | ~8 | Planté-type plates, glass jars, acid | Stabilize the relay supply; let the computer outlast an engine stoppage |
| Power transmission | ~20 | Shafting, pulleys, belts, babbitt bearings | |
| Lathe | ~60 | Bed of ground flat bar, headstock, spindle, tailstock, carriage, cross slide, lead screw, half nut, change gears, chuck | The lead screw is the lineage's master accuracy reference |
| Shaper | ~40 | Ram, quick-return linkage, table, clapper box | Flat surfaces, and gear teeth with indexing |
| Dividing head / milling attachment | ~15 | Worm and wheel, index plate | Mounted on the lathe, replacing a separate mill |
| Drill press | ~20 | Spindle, quill, table | Spade drills avoid needing to cut flutes |
| Grinding | ~10 | Bonded emery wheel, spindle, rest | Assumes emery counts as purchasable |
| Reference surfaces | ~5 | Three plates, straightedges, scrapers | |
| Heat treatment | ~10 | Forge, furnace, quench tank, thermocouple pyrometer | |
| Cutting tools | ~20 | Bits, taps, dies, reamers, gear cutters | Consumables |
| Sheet and plate work | ~15 | Rolls, brake, rivet heading, hydrostatic test pump | |
| Coil winding | ~10 | Winder with counter | |
| Axis module library | ~40 | Lead-screw stage, electromagnetic clutch, ratchet stepper, limit switch, touch probe | Paid for once, used everywhere |
| Gantry manipulator | ~40 | Rails, carriage, gripper | |
| Assembly manipulator | ~30 | Wrist, wrench and screwdriver end effectors, rivet set | Least period-plausible subsystem |
| Relays | ~15 | Core, bobbin, armature, phosphor-bronze springs, platinum contacts, plug-in base | Built in volume |
| Stepping switches | ~20 | Ratchet-stepped selector | Memory and plug-board addressing |
| Tape punch, reader, transport | ~50 | Dies, sensing pins, sprocket feed | Keep at least two verified copies of D |
| Computer frames and wiring | ~10 | Racks, terminal blocks, harnesses | |
| Measurement | ~15 | Micrometer, gauge blocks, galvanometer | |
| **Total** | **~650** | | |

---

## 7. Relay wear

**The constraint.** Relay life depends heavily on contact current and arc suppression. With platinum contacts, low current and RC spark suppression, an 1890-style relay plausibly manages 10⁶–10⁷ switches on its busiest contacts. Phosphor-bronze springs fatigue as well. At about 10 operations per second, a relay that switches on every instruction lasts on the order of weeks. The original assumption of about 3 × 10¹⁰ operations per generation from one set of relays was wrong by a large factor.

**Design response.**
- **Relays are consumables**, like cutting tools. Over a generation, expect thousands of replacements.
- **Self-checking codes**, such as 2-out-of-5 as in 1940s Bell Labs relay computers, so faults halt the machine instead of corrupting a plan.
- **Two computers**, each able to diagnose the other and direct a manipulator to replace its plug-in modules. A computer that has failed cannot repair itself.
- **Switching moved out of the computer.** Axes feed continuously by motor and lead screw and stop at probes or limit switches. Relays make decisions; they don't count steps. This cuts relay switching by about 10–100 times.

**Consequences.**
- About 4 × 10⁴ extra bits.
- A realistic compute budget of 10⁸–10⁹ useful operations per generation, which rules out search-based planning.
- The computers become one of the two main reliability risks.

---

## 8. The boiler

A boiler failure is the one routine event that can end the lineage outright. It destroys the power plant and can throw fragments, scalding steam and hot water into nearby machines, including the only lathe and the computers. Precautions, in rough order of value:

1. **Minimize stored energy.** The danger comes from the mass of water held above its atmospheric boiling point. A flash (monotube) boiler, in which water is pumped into a heated coil and flashes to steam, holds very little water. A tube rupture vents locally instead of bursting the vessel. Serpollet built such boilers in the late 1880s, though as noted the date doesn't matter for anything the lineage builds. A watertube boiler is the second choice, since its small tubes fail locally.
2. **Run at low pressure.** Use the lowest pressure the engine can work with, accepting a larger, slower engine. Metal is cheap; risk is not.
3. **Test with water before steam.** Hydrostatic testing at about twice working pressure, standard practice of the period, finds bad seams using cold water, so a failure is benign. Repeat it periodically, because seams and tubes degrade.
4. **Separate it.** Put the boiler in its own house behind an earth berm or masonry wall, oriented so a failure vents away from the workshop, and pipe the steam in. The computers, the reference lathe and the spare copies of D sit farthest away.
5. **Interlocks that fail safe.** Two safety valves, a fusible plug, and a float-switch low-water interlock that cuts the feed of fuel. The interlock should work without the computer, which may be down for relay repair.
6. **Keep a fallback power source.** Batteries keep the computers and the minimum control system running if the engine stops, so the lineage can rebuild instead of dying.
7. **Consider avoiding steam.** A hot-air engine has no pressure vessel but delivers little power. A gas engine running on producer gas avoids stored steam but adds a gas producer and its own explosion risk.

**Tube supply decides the design.** If seamless tube can be ordered, the flash boiler is straightforward. If not, coils must be brazed from strip, and the hydrostatic test becomes essential, not just prudent.

These precautions add about 5 × 10³ bits, which is negligible next to their effect on reliability.

---

## 9. Bit budget, World_1890 A

| Component | Bits |
|---|---|
| Part geometry (~650 types × ~300 bits) | ~2 × 10⁵ |
| Process plans (explicit) | ~2.5 × 10⁵ |
| Assembly sequences | ~8 × 10⁴ |
| Control code | ~5 × 10⁴ |
| Fault detection and repair | ~4 × 10⁴ |
| Boiler safety logic and test procedures | ~5 × 10³ |
| Computer netlist | ~1 × 10⁴ |
| **Total** | **~6 × 10⁵** (about a minimal bacterial genome) |

---

## 10. Failure budget

The lineage may fail with probability at most 5% over ten generations, or about 0.5% per generation. A suggested allocation per generation:

| Source | Share of the per-generation budget |
|---|---|
| Boiler or power-plant loss | ~0.15% |
| Computer failure beyond repair | ~0.15% |
| Loss or corruption of D | ~0.05% (tape copies and checksums make this cheap) |
| Everything else (tool loss, heat-treatment runs, assembly errors) | ~0.15% |

Most failures in machining and heat treatment cost time, not the lineage, which is why they get a small share despite being frequent. The 100-year allowance absorbs them.

---

## 11. Open questions

- What does a realistic touch-only assembly manipulator need? This is the largest uncertainty in the World_1890 B estimate.
- How much of the rock-to-metal chemistry can a generation relearn rather than inherit? This is the largest uncertainty in the closure curve.
- Does the factor-of-ten-per-layer pattern survive a detailed estimate, or is it an artefact of rough estimates?
- What should go in a fixed bootstrap kit K that is useful but cannot carry design information?
