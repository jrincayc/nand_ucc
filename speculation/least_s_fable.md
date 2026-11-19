# Least S for a universal computer constructor in World\_1890 and World\_1sqkm

Nov 15, 2026 · @Joshua Cogliati

## Answer

My estimate for the least S is about 2 x 10^6 bits in an orderly 1890 workshop, 10^7 in a real one, 5 x 10^7 on raw land with a relay computer, and 2 x 10^8 on raw land with simple integrated circuits. Nothing close to these figures can be proved. They cost one style of design, so cleverer designs could come in lower.

| World and variant | Low | Central | High | Central, in bytes |
| --- | --- | --- | --- | --- |
| World\_1890-A: orderly workshop | 5 x 10^5 | 2 x 10^6 | 10^7 | 244 KiB |
| World\_1890-B: real workshop | 3 x 10^6 | 10^7 | 10^8 | 1.2 MiB |
| World\_1sqkm-A: raw land, any computer | 10^7 | 5 x 10^7 | 10^9 | 6 MiB |
| World\_1sqkm-B: raw land, 1980s-class integrated circuits | 3 x 10^7 | 2 x 10^8 | 3 x 10^9 | 24 MiB |
| World\_1sqkm-C: raw land, present-day chips | 10^10 | 10^11 to 10^12 | 10^13 | 12 to 120 GiB |

All figures are bits of heritable information: everything one generation must pass to the next. The provable lower bound in every row is a few hundred bits at most. The only measured point nearby is the R6 replicator in RNDP, at 1.3 x 10^5 bits, in a world where the arm, the parts and exact placement are free.

The figures combine two estimating passes: a top-down bracket from published anchors, and a bottom-up parts census from a second-opinion report, adjusted with this project's own measurements. The Method section describes both.

## Formal setup

The quantity is the heritable information H(W): the length of the shortest description D that, placed in a fresh copy of world W with a fixed starter kit, yields a machine that reproduces itself and D from raw inputs. It is Lambda\_T(M, W, A) with the leaks closed, and the definitions below are my choices.

**M, the machine.** A sealed computer loaded with D, wired to tools, actuators, sensors and a power plant. The first generation gets a small public starter kit K: one slow manipulator, a tape reader, a relay controller and hand tools. K is the same for every design, so it cannot be tuned to carry the answer. Every later generation builds everything it uses.

**A, the success set: a universal computer constructor.** Four conditions.

1. Replication. From the raw inputs of W alone, the machine builds a child computer and the child's workshop and power plant, loads D, and starts it.
2. Fixed point. The child meets these same conditions with the same D. No generation is special.
3. Universal construction. Given an extra description on an input tape, the machine builds the described object, for any object its tools can make. The extra description is not counted.
4. Universal computation. The computer is general-purpose up to its memory.

**What counts in D.** Everything inherited. That includes design information embodied in templates, jigs, cams or printed matter. It also includes anything measured from the parent's tools: the test is run with no parent present, so a parent lathe cannot serve as an uncounted template.

**Learning.** A generation may learn by experiment. What it learns and does not pass on costs only time. What it passes on is part of D.

**Reliability.** In the real variants, each generation succeeds with probability at least 99%. In the orderly variant the world is deterministic, so that variant measures design size only.

**T, the budget.** One generation must finish within 100 years. The 2^100-step budget adopted earlier never binds here: a relay computer manages perhaps 10^8 to 10^9 operations in a generation.

**What is free.** Raw inputs and the laws of physics. Unlike RNDP, there is no free arm and there are no free parts.

**No people.** If W contains skilled people who follow instructions, H falls to the length of a letter, because their knowledge is part of W. Both worlds exclude it. In World\_1890, suppliers only fill orders for stock.

## Method

The estimate comes from three sources: published anchors that bracket it, a parts census that builds it up, and this project's measured replicators, which calibrate the code sizes. It remains a costing of one kind of design, so it yields a plausible range and not a bound.

**What D has to hold.**

- A description of every distinct part of the computer, tools and power plant.
- A process plan for making each part from the raw inputs.
- Assembly order, alignment and test procedures.
- Control software: motion, sequencing, measurement and recovery from errors.

**Pass 1: anchors.** These bracket the answer between about 10^5 and 10^11 bits.

| Anchor | Bits | What it tells us |
| --- | --- | --- |
| R6 in RNDP (this project, measured) | 1.3 x 10^5 | Replication with a free arm, free parts and exact placement |
| Von Neumann's universal constructor ([Merkle's table](https://www.zyvex.com/nanotech/selfRep.html)) | about 5 x 10^5 | Cellular-automaton world, also with free primitives |
| Typical replicator descriptions surveyed by [Freitas and Merkle](https://www.molecularassembler.com/KSRM/5.6.htm) | often under 10^6 | Mostly simplified or simulated worlds |
| JCVI-syn3.0 minimal cell genome, about 531,000 base pairs | 1.1 x 10^6 | A replicator fed a rich medium, the biological analogue of World\_1890 |
| Pelagibacter ubique genome (from the paper) | 2.6 x 10^6 | A free-living replicator, using chemistry as its machine tools |
| NASA 1980 lunar factory (Merkle's table) | over 10^11 | A 100-tonne seed closing from raw regolith, as costed by engineers in 1980 |

Biology sits low because molecules assemble themselves; a machine shop gets no such help. The NASA figure sits high because it prices 1980 software practice, not a minimal design.

**Pass 2: parts census.** A second-opinion report, written by another Claude model from the specification alone, lists the part types of a minimal World\_1890 machine by subsystem and prices each kind of information. I adopt its census and adjust two of its prices.

**Calibration from this project.** Three measured sizes check the code figures.

- The X quine's whole image is 3,962 bytes, or 3.2 x 10^4 bits.
- The R6 image is 16,006 bytes, or 1.3 x 10^5 bits.
- The CPU description inside X is 1,658 bytes, or 1.3 x 10^4 bits.

All three are for worlds with a free arm and perfect placement, so they are floors for the control code of a physical machine.

## World\_1890

In an orderly 1890 workshop the adjusted parts census gives about 2 x 10^6 bits, with a range of 5 x 10^5 to 10^7. A real workshop multiplies that by about five.

**Definition.**

- Raw inputs: raw and semi-finished stock that a firm of 1890 could order. Bar, plate, sheet and wire in iron, steel, brass and copper; precision-ground stock such as drill rod; insulated wire; fasteners; glass; lumber; paper; common chemicals; coal and water. No finished machines or components, and no printed information.
- Child computer: relays or mechanical logic, with the program on punched paper tape. No transistors. Vacuum tubes and other devices are allowed if the lineage makes them.
- Dates constrain only the stock. Whether a mechanism had been invented by 1890 does not matter for anything the lineage builds, because its design costs bits either way.
- Variant A, orderly: stock is uniform, positions repeat, and sensing is by touch probes and limit switches. Variant B, real: stock varies, tools wear, things fall over.

**Assumptions where the definition is silent.** Each can be changed.

- Stock may be ordered cut to length. Stock ground to size is limited to catalogue items such as drill rod.
- Seamless tube may be ordered. Without it, boiler tubes must be brazed from strip, which is where a boiler is weakest.
- Sensing in variant B includes simple photocells as well as touch.

**The design the census assumes.**

- No foundry. Structures are machined from bar and plate, then bolted, riveted or brazed. This spends metal to save information, since there are no casting patterns.
- One design serves as both dynamo and motor, and every automated axis uses one shared module.
- Accuracy comes from procedure, not data: three-plate scraping for flatness, self-copying on the lathe for screws, ground stock as the reference.
- Relays are consumables, like cutting tools. Two computers each direct the repair of the other.
- A flash boiler in its own house. A boiler failure is the one routine event that can end the lineage.

**Census.**

| Subsystem group | Part types |
| --- | --- |
| Power: boiler, engine, dynamo and motors, batteries, shafting | 123 |
| Machine tools: lathe, shaper, dividing head, drill press, grinder, reference surfaces | 150 |
| Tooling and processes: heat treatment, cutting tools, sheet work, coil winding | 55 |
| Manipulation: axis module library, gantry, assembly manipulator | 110 |
| Computer: relays, stepping switches, tape punch and reader, frames | 95 |
| Measurement | 15 |
| Total | 548 |

The report states a total of about 650, but its own rows sum to 548. I use 600.

**Bit budget, variant A.**

| Component | Report | Adjusted | Reason for the adjustment |
| --- | --- | --- | --- |
| Part geometry | 2 x 10^5 | 6 x 10^5 | 300 bits a part type covers about five dimensioned features. That fits a pin, not a lathe carriage. I use 1,000 |
| Process plans | 2.5 x 10^5 | 7 x 10^5 | Scaled with part complexity |
| Assembly sequences | 8 x 10^4 | 10^5 | Rounded up |
| Control code | 5 x 10^4 | 5 x 10^5 | The report's figure is 6 KB. R6 needed 16 KB with a free arm and perfect placement |
| Fault detection and repair | 4 x 10^4 | 10^5 | Includes replacing relays by the thousand |
| Boiler safety and test procedures | 5 x 10^3 | 5 x 10^3 | Unchanged |
| Computer netlist | 10^4 | 1.3 x 10^4 | The CPU description measured in this project |
| Total | 6 x 10^5 | 2 x 10^6 |  |

Taking the high end of my range for each row gives 5 x 10^6. I state the overall range as 5 x 10^5 to 10^7. The low end allows for designs that reuse parts more heavily. The high end allows for errors in a census I did not check part by part.

**Checks.**

- The program fits the medium. At 10 characters an inch, 2 x 10^6 bits is 640 m of paper tape and 10^7 bits is 3.2 km. Copying the longer tape at 10 characters a second takes about a day and a half.
- Compute is scarce. The report estimates that relay contacts last 10^6 to 10^7 switches, which limits a generation to 10^8 to 10^9 useful operations. That rules out planning by search, so plans must be stored. In this world time cannot be traded for stored bits.
- I think the relay-life figure is conservative. The lineage designs its own relays, and later telephone relays lasted far longer; that is from memory. Longer life would loosen the compute limit and could lower the stored plans.
- A learned perception model is not an option. A relay computer cannot run one.

**Variant B.** Recovering from wear, varying stock and toppled parts needs explicit handling for each case. The report puts the growth in control code at 10 to 100 times. I apply that to the adjusted control and fault rows, and assume calibration is relearned each generation and not inherited. That gives about 10^7 bits, with a range of 3 x 10^6 to 10^8. The largest unknown is what an assembly manipulator working by touch really needs.

## World\_1sqkm

On a square kilometre of raw land, matter and energy are ample and information is the constraint: about 5 x 10^7 bits with a relay computer and 2 x 10^8 with simple integrated circuits.

**Definition.**

- Raw inputs: air, water, and rock and soil to 10 metres depth, of average crustal composition with no ore bodies. Energy only from what falls on the square kilometre. No purchases.
- Current technology: the first generation may use any equipment that can be made today, but no living organisms. This saves nothing in D, because every later generation must build what it uses from the raw inputs.
- There is no orderly variant. Weather, terrain and rock that varies make this a real-world case, so it compares with World\_1890-B.
- Variant A: the child's computer may be of any kind, including relays.
- Variant B: the child's computer must use silicon integrated circuits at least equal to simple 1980s logic chips, such as a quad NAND gate and a dual flip-flop.
- Variant C: the child's computer must use present-day chips.

**Closure checks.** These use round figures from memory for crustal abundance and sunlight.

| Quantity | Value | Basis |
| --- | --- | --- |
| Rock available | 2.7 x 10^10 kg | 10^7 cubic metres at 2,700 kg per cubic metre |
| Aluminium in it | 2.2 x 10^9 kg | 8.2% by mass |
| Iron in it | 1.5 x 10^9 kg | 5.6% by mass |
| Copper in it | 1.5 x 10^6 kg | 55 parts per million |
| Average electrical power | 40 MW | 200 W per square metre, 20% conversion, full coverage |
| Energy to make a 1,000 tonne machine | 145 days of that power | 500 GJ per tonne, assumed, for low-grade feedstock |

Neither matter nor energy binds. Copper is scarce enough that a sensible design uses aluminium conductors.

**What is added to World\_1890-B.**

- Digging, hauling, crushing and sorting.
- Extraction chemistry for roughly ten elements from undifferentiated silicate rock: molten-oxide electrolysis or carbothermal reduction, then separation.
- Making the materials 1890 could simply order: steel stock, wire, insulation, glass, refractories, lubricants, abrasives and acids.
- Energy collection: mirrors and a heat engine, or solar cells.

**Estimate, variant A.**

- The adjusted World\_1890 budget works out at about 3,400 bits per part type, all costs included.
- I guess that the extraction and materials plants add 2,000 to 6,000 part types. That gives 9 x 10^6 to 2 x 10^7 bits in an orderly setting.
- The real setting multiplies this by 3 to 10, as in World\_1890. The result is 3 x 10^7 to 2 x 10^8 bits, and I take 5 x 10^7 as central.
- The report's own figure is 10^7. The NASA figure of over 10^11 for a comparable lunar factory is the outlier above. I state the range as 10^7 to 10^9.

Chemistry differs from machining in one way that matters here. Machining gets accuracy from procedure. Purity has no comparable trick, so process recipes must be stored or relearned. The largest unknown is how much of the chemistry a generation can relearn within its 100 years. If most of it can, the figure falls by about three times.

**Variant B.** This adds a crude semiconductor line: purified silicon, crystal growth, oxidation, doping, contact printing at a few micrometres, and acids made from scratch. Yield can be poor, since a few dozen good chips are enough. The report puts the addition at about 4 x 10^7 bits. With my adjustments I put the total at 2 x 10^8, with a range of 3 x 10^7 to 3 x 10^9. One effect could pull it lower: an electronic computer has the compute to derive plans by search and to relearn recipes, which a relay computer lacks.

**Variant C.** Present-day chips require the supply chain described in the companion lithography analysis: machines of 100,000 components and thousands of supplier specialities. I put this at 10^10 to 10^13 bits. It has no second estimate and is the least supported number in this document.

## The cost of each layer of closure

Each layer of the supply chain that the machine must provide for itself multiplies the heritable information by about 4 to 15.

| What the world supplies | Bits | Step from the row above |
| --- | --- | --- |
| Finished gates, a free arm, exact placement (R6 in RNDP) | 1.3 x 10^5 |  |
| Semi-finished stock, orderly (World\_1890-A) | 2 x 10^6 | 15 times: making parts and tools |
| Semi-finished stock, real (World\_1890-B) | 10^7 | 5 times: coping with an untidy world |
| Rock, relay computer (World\_1sqkm-A) | 5 x 10^7 | 5 times: extraction and materials |
| Rock, simple integrated circuits (World\_1sqkm-B) | 2 x 10^8 | 4 times: semiconductor purity and process |

Only the first row is measured. The even steps may be an artefact of one estimator's habits. Differences between neighbouring rows are still more robust than single values, because the same estimating errors appear in both.

Biology sits on a much lower curve. A minimal cell reaches closure down to small molecules in about 10^6 bits. On the report's reading, the gap measures the cost of building by placing parts instead of by self-assembly.

## What the numbers mean for the 64 KiB and 2 MiB limits

Neither limit is supported as a bound on the size of a replicator's description. 64 KiB falls at the low end of the range for the orderly workshop, and 2 MiB falls inside the range for both real-world cases.

| Reference | Bits |
| --- | --- |
| 64 KiB | 5.2 x 10^5 |
| World\_1890-A, low to high | 5 x 10^5 to 10^7 |
| 2 MiB | 1.7 x 10^7 |
| World\_1890-B, low to high | 3 x 10^6 to 10^8 |
| World\_1sqkm-A, low to high | 10^7 to 10^9 |

Four cautions.

1. **These figures answer a different question from the paper's.** They say how small a machine could be independent if someone loaded the design into it. The paper asks whether a machine that small could become independent by accident, which requires it to produce the design.
2. **A constructor is not a designer.** This project has not measured a general designer. R4 chooses where parts and traces go, and the Y improver rewrites small logic modules; both start from a design a person supplied. The 309 kilobits of sources that regenerate R6, against 128 for its image, measure a layout toolchain together with the design it lays out. A designer could also be smaller than the stored design if it derives the design by long search. A relay computer cannot search on that scale. An electronic one can.
3. **These are costs of a design style.** Both estimating passes assume a machine shop that places parts. A design built from very few part families, or one that leans on self-assembly, could fall well below the ranges.
4. **People collapse everything.** Both worlds exclude human help. With it, the answer is the length of a persuasive message.

My reading: a memory limit of this size cannot rest on the size of a replicator's description. If such a limit holds, it is because producing a design is far harder than storing one. That difference is the designer bound in this project's notes, and it has neither a measurement in RNDP nor an estimate for either world.

## Caveats and sources

**Caveats.**

- The two estimating passes are not independent. The second-opinion report was written by another Claude model, from a specification drafted in a chat that had seen earlier figures. Agreement between the passes is weak evidence.
- I did not check the parts census part by part. The report's stated total and its rows disagree, 650 against 548.
- My adjustments rest on two judgments: 1,000 bits per part type, and control code several times larger than this project's replicators. No detailed design supports either.
- The relay-life figure, and the compute limit that follows from it, come from the report. I have not sourced them.
- The worlds are physical, not formal. H is well defined only once W is a mathematical object, which these are not.
- Crustal abundances, sunlight, the energy cost per tonne and the minimal-cell genome size are round figures from memory.
- The Merkle table figures were taken from a search summary of a mirrored copy; I could not open the original page. The Freitas and Merkle chapter was read directly. The NASA figure is a single line in that table, and I did not find how it was derived.

**What would tighten the estimate.**

- A detailed design of one subsystem, for example the lathe at about 60 part types. It would measure bits per part type and per process plan, the two figures everything else scales from.
- A definition of what an assembly manipulator working by touch must do. This is the largest unknown in World\_1890-B.
- Extending RNDP one step toward this world by charging for the arm, so that the replicator builds it from simpler primitives. That gives a measured point between R6 and World\_1890-A.
- An estimate of the designer, not the constructor, for World\_1890-A.

**Sources.**

- Second-opinion report, "The smallest founder for a self-replicating computer: estimates, critique and a part list", supplied as `opus_machine_estimation.md`: parts census, bit budget, relay wear, boiler design, the heritable-information definition and the closure-curve hypothesis.
- [Kinematic Self-Replicating Machines, section 5.6](https://www.molecularassembler.com/KSRM/5.6.htm), Freitas and Merkle, 2004: closure theory; replicator descriptions often under 10^6 bits.
- [Self replication](https://www.zyvex.com/nanotech/selfRep.html), Merkle: table of replicator complexity in bits.
- [Advanced Automation for Space Missions, chapter 5](https://NSS.org/wp-content/uploads/2017/07/1982-Self-Replicating-Lunar-Factory.pdf), NASA, 1982: the 100-tonne lunar seed factory.
- Project files: `HANDOFF_RNDP_R1_R6.md` for R6, `RNDW_VON_NEUMANN_THRESHOLD.md` for the X quine, `DESIGNER_BOUND_NOTES.md` for the regeneration measurements, `PROVABLE_LIMITS_NOTES.md` for Lambda\_T, `hardware_limits_for_agi.tex` for the Pelagibacter genome figure.
