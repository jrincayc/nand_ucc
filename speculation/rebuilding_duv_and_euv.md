# Rebuilding DUV and EUV lithography after a ban

Nov 11, 2026 · @Joshua Cogliati

## Answer

A ban that holds chipmaking at the i-line limit of 0.35 micrometre makes a frontier-scale training run cost about 50,000 times more energy than it does today, which puts it out of any state's reach. Rebuilding DUV or EUV from destroyed tools takes a state 5 to 20 years, depending on the level. Neither result protects a shutdown unless the existing chips are bought back and the ban covers routes other than DUV and EUV.

Four findings carry the analysis.

1. **Rebuilding is slow.** With tools destroyed and suppliers dissolved, I estimate 5 to 10 years for basic DUV, 8 to 15 for 7 nm-capable immersion DUV and 12 to 20 for EUV. With tools only mothballed, 1 to 4 years. China's catch-up effort is the main evidence \[1\].
2. **The ban is worth about a decade of algorithmic progress.** The 50,000-fold penalty equals about 15 halvings of compute. Language-model algorithms have halved the compute needed for fixed performance about every 8 months \[8\]. If that research continued, the penalty would be consumed in roughly 10 years, with a range of 6 to 18.
3. **The wording matters more than the rebuild time.** Nanoimprint tools already ship with 14 nm line widths at 80 wafers an hour \[13\]. Multi-patterning reaches 7 nm with no EUV \[20\], and nothing in its method depends on the wavelength used. A ban by wavelength leaves both open.
4. **The buyback decides the first decade.** The world held over 15 million H100-equivalents of AI chips at the start of 2026 \[29\], and such chips last five years or more \[30\]. A hidden 1% of that stock is a frontier-scale cluster by 2025 standards. The lithography ban only stops the stock being rebuilt.

| Starting condition | Basic DUV (dry, 250 to 90 nm) | Immersion DUV (7 nm-capable) | EUV (5 nm and below) |
| --- | --- | --- | --- |
| Tools mothballed, staff and suppliers intact | 1 to 2 years | 1 to 3 years | 2 to 4 years |
| Tools destroyed, suppliers dissolved, staff and documents available | 5 to 10 years | 8 to 15 years | 12 to 20 years |
| A generation later: documents survive, practised staff do not | 8 to 15 years | 12 to 25 years | 15 to 30 years |

The times in the table are my estimates, anchored on the evidence section. The three columns correspond to the dry DUV, immersion DUV and EUV rows of the energy table in the next section. Numbers in square brackets refer to the reference list at the end.

## What the ban has to deny

The target is the compute to train a new large language model, so the useful measure is the energy one training run costs at each level of chipmaking.

**How big a run.** GPT-3 took 3.1 x 10^23 floating-point operations to train in 2020 \[7\]. Grok-3, released in February 2025, was the first model estimated to exceed 10^26, and frontier training compute has grown about 4.6 times a year \[6\].

**What each level of lithography delivers.** The table uses a leading supercomputer of each era as a measured anchor. All figures are for the same benchmark, double-precision Linpack.

| Lithography level | Anchor machine | Operations per joule | Energy for a GPT-3 run | Energy for a 10^26 run |
| --- | --- | --- | --- | --- |
| g-line, 0.8 micrometre | none; scaled from the row below \[12\] | 1.3 x 10^5 | 78 GW-years | 25,000 GW-years |
| i-line limit, 0.35 micrometre | ASCI Red, 1997 \[9\] | 1.5 x 10^6 | 6.5 GW-years | 2,100 GW-years |
| Dry DUV, 90 nm | Blue Gene/P, 2007 \[10\] | 3.6 x 10^8 | 10 GW-days | 8.9 GW-years |
| Immersion DUV, 28 nm | Shoubu, 2015 \[10\] | 7.0 x 10^9 | 12 GW-hours | 0.45 GW-years |
| EUV, 4 nm | JEDI, 2024 \[34\] | 7.3 x 10^10 | 1.2 GW-hours | 16 GW-days |

World electricity generation averages roughly 3,400 GW, which is my round figure. Reading the table against that:

- **At the i-line limit,** a 10^26 run needs about 60% of the world's electricity for a year. A GPT-3-scale run needs 6.5 GW for a year and about 71 million processors of 1997 type. That is of the order of the whole world's yearly processor output in the late 1990s, a comparison I make from memory. A large state could do the second and not the first.
- **At dry DUV,** a 10^26 run costs about 9 GW-years. That is a national project, not an impossibility. This is why DUV has to be inside the ban, and why any other route to 90 nm matters as much as DUV itself.
- **At immersion DUV,** a 10^26 run is routine for a state.

**Three things that weaken the penalty.**

- Chips built only for neural-network arithmetic use low-precision numbers and gain perhaps ten times over these general-purpose anchors. That is my estimate, and it applies at every level.
- Algorithms improve. At the measured rate \[8\], each year of continued research is worth about a factor of 2.8.
- The efficiency gain per generation was fastest in the era the ban returns to. Computations per joule doubled about every 1.6 years through 2009 \[11\], so small slippage in the permitted feature size is costly.

Memory is not a constraint at any of these levels. i-line tools made 64 megabit memory chips \[4\].

**Against Plan S's own terms.** [Plan S](https://ai-2040.com/?choices=plan-s-root) sets no compute threshold. Its working assumption is that a few thousand GPUs cannot build superintelligence. Three points follow.

- A few thousand present-day GPUs draw about 2 MW, taking 3,000 at 700 watts each as my round figures. Matching them with chips at the i-line limit takes about 100 GW. Matching them with dry-DUV chips takes about 0.4 GW. So a pre-DUV world keeps every covert project that uses new chips below the plan's own harmless line, and a dry-DUV world does not.
- Plan S as written keeps existing datacentres running and lets advanced fabs go on expanding slowly. The proposal examined here replaces both: it bans the lithography and buys back the chips.
- The two halves cover each other's gap. Without the buyback, a breakout uses the installed stock on its first day. Without the ban, the stock is rebuilt. The buyback section sets out how complete it has to be.

## Routes to mass production at DUV level

Six routes besides DUV and EUV can pattern chips, and three of them could plausibly reach DUV-level features in volume.

**Terms.** Half-pitch is half the spacing of the finest repeating lines, and it is the physical measure used here. Node names such as 7 nm are labels, not dimensions. A 7 nm process has a finest half-pitch near 18 to 20 nm and a 5 nm process near 14 nm; both figures are from memory. Multi-patterning splits one layer's pattern across several exposures or deposition steps, to print lines closer together than one exposure allows.

For scale, a current immersion DUV scanner exposes roughly 275 to 300 wafers an hour. That figure is also from memory.

| Route | Finest features shown | Throughput | Status | Caught by a DUV and EUV ban? |
| --- | --- | --- | --- | --- |
| g-line as used, 436 nm | 0.5 to 0.8 micrometre \[4\] | High | Mature, 1980s | No, by assumption |
| i-line as used, 365 nm | 0.35 micrometre \[4\] | High | Mature, 1990s | No, unless named |
| i-line or visible light with modern optics and multi-patterning | None built. Calculated: about 80 nm in one exposure, about 20 nm with quadruple patterning | Same class as DUV | Would need a new scanner | No |
| Nanoimprint | 14 nm lines \[13\] | 80 wafers an hour, which I read as the four-station cluster \[13\] | First commercial tool shipped 2024; no volume chip production confirmed in what I read \[13, 15\] | No |
| Electron-beam direct write | About 30 nm \[17\] | 1 to 2 wafers an hour per chamber \[17\] | Niche. The 10 wafers an hour goal was never met; the leading developer went bankrupt in 2018 \[16\] | No |
| X-ray proximity printing | Sub-micrometre devices in IBM's 1980 to 1992 programme \[18\] | Never reached production | Abandoned. A 2025 startup's revival claims are disputed \[19\] | No |

**g-line as it was used.** The mercury g-line is visible light. It was the production standard to about 0.8 micrometre. This is the baseline the proposal assumes stays legal and easy.

**i-line.** The i-line, 365 nm, is near-ultraviolet: neither visible nor deep ultraviolet. A ban on DUV and EUV leaves it legal. It reached 0.35 micrometres by 1996 and made 16 and 64 megabit memory chips \[4\]. Whether i-line is banned is the first thing to settle.

**Longer wavelengths with modern optics.** This is the route I rate most dangerous, because every part of its supply chain stays legal.

- Resolution is k1 times wavelength divided by numerical aperture \[2, 3\]. The 1990 i-line tool had an aperture of 0.5 \[4\]. Immersion DUV scanners reach 1.35 and run k1 near its floor of 0.25 \[3\].
- Applying those values to 365 or 405 nm light gives a half-pitch of 76 to 85 nm in one exposure. That is the dry-DUV row of the energy table.
- Self-aligned multi-patterning then halves the pitch with deposition and etching, not with optics \[28\]. It is how 7 nm chips are made on DUV tools without EUV \[20\]. Two rounds would bring 80 nm to about 20 nm.
- Nobody has built such a scanner, because DUV was the easier path. Resists and lenses for it would need development. I estimate 5 to 10 years for a state starting from a healthy i-line industry.

**Nanoimprint.** This is the only non-optical route with a production tool today.

- A patterned template is pressed into liquid resist, a method shown at 25 nm in 1996 \[14\]. Canon's tool prints 14 nm lines and targets 100 wafers an hour \[13\].
- Canon puts its energy use at about a tenth of an EUV tool's \[13\]. The whole cluster with its mask replicator is smaller than one EUV scanner \[13\].
- The weaknesses are defects and template life. Canon claims alignment near 1 nm and publishes no defect rates \[13\]. Each replica template lasts about 2,000 wafers \[13\]. Adoption has so far been in memory trials, photonics and gene sequencing, not logic \[15\].
- The master template is written by electron beam \[13\], which is the inspection point.

**Electron-beam direct write.** It draws each wafer without a mask. It is too slow for mass production and fast enough to matter.

- At 1 to 2 wafers an hour, one chamber patterns roughly 12,000 wafer layers a year. If only the ten finest layers of a chip are written this way, that is about 1,200 wafers a year per chamber. The arithmetic is mine and assumes the quoted throughput holds for dense patterns, which the vendor does not claim \[17\].
- A state with a hundred chambers could supply a serious cluster. A market could not.

**X-ray proximity printing.** It needs a synchrotron and masks at final size, which is why it lost to optics \[18, 23\]. A rebuild would take longer than DUV and would be conspicuous. I rate it a low risk.

**Masks without electron beams.** Laser writers resolve about 200 nm and above \[16\], which is ample for masks at g-line and i-line feature sizes. Fine electron-beam writers could therefore be banned outright.

A ban that names wavelengths will be worked around. A ban that names capability, meaning resolution, alignment accuracy and aperture, covers all six routes.

## What a DUV chain needs

A DUV scanner adds three things to a good i-line tool, and the rest of the chain is shared with permitted chipmaking.

| Item | Needed beyond i-line tools | How hard to rebuild |
| --- | --- | --- |
| Light source | Line-narrowed excimer laser, KrF at 248 nm or ArF at 193 nm \[2, 3\] | Moderate. Excimer lasers have other uses; the lithography grade is specialised |
| Optics | Fused silica and calcium fluoride lenses for DUV \[3\] | Hard. Very few firms have made lithography-grade lenses \[27\] |
| Resist | Chemically amplified resists, a different chemistry from i-line resists \[3\] | Hard. Chinese producers hold under 1% of the KrF and ArF resist market despite years of effort \[1\] |
| Stage and alignment | Nanometre-scale positioning for immersion and multi-patterning | Hard, but the same skill as any precise scanner |
| Immersion | Ultra-pure water between lens and wafer \[3\] | Moderate once the dry tool works |
| Masks, etch, deposition, metrology, design software | Finer versions of what a permitted fab already has | Moderate; the skills stay in practice under the ban |

The market is concentrated. ASML held 98.7% of immersion DUV sales in 2024 and Nikon the rest \[1\]. Dissolving two firms and their optics and laser suppliers removes the capability.

The consequence is uncomfortable for the proposal. A permitted, thriving g-line and i-line industry keeps most DUV skills in practice: precision optics, stages, resist chemistry, etch and mask-making. The ban removes the laser, the lens materials and the resist, and leaves the rest warm. That is why the middle row of the answer table is 5 to 10 years and not 20.

## What an EUV chain needs

EUV shares almost nothing with longer-wavelength tools, so a ban on it is far more durable than a ban on DUV.

- **One integrator.** ASML is the only maker. Each machine has more than 100,000 components from about 5,100 suppliers \[1\].
- **Light source.** Tin droplets are hit by a high-power laser to make 13.5 nm light \[25\]. Production tools use sources of about 250 watts \[13, 25\]. A Chinese prototype source shown in October 2026 was reported at 15 watts \[22\].
- **Optics.** EUV is absorbed by lenses and by air, so the machine uses multilayer mirrors in vacuum \[24\]. Each reflects about 70%, so a train of ten passes under 3% of the light. Zeiss makes them in a subsidiary that works only with ASML, which owns 24.9% of it \[1\].
- **Resist, masks and inspection.** Each is a separate specialised industry with very few firms \[27\].
- **Customers.** ASML needed more than a decade of joint work with TSMC, Intel and Samsung, who also invested in it, to turn a working tool into a production tool \[1, 26\].

Several of these have a single qualified supplier. A ban that dissolves those few firms and scatters their staff removes knowledge that is not written down in one place.

## Evidence on rebuild time

Two bodies of evidence set the estimates: how long the technology took the first time, and how long China is taking to repeat it with every advantage a rebuilder would have.

**The first time.**

| Milestone | Year | Elapsed |
| --- | --- | --- |
| First DUV tool delivered for research, Nikon KrF \[1\] | 1988 | start |
| KrF scanner at 0.25 micrometre delivered to IBM \[5\] | 1995 | 7 years |
| First immersion tool shipped \[1\] | 2004 | 16 years |
| Commercial 7 nm production on immersion DUV, TSMC \[1\] | 2018 | 30 years |
| EUV industry consortium formed \[1, 26\] | 1997 | start |
| First EUV demonstration tools shipped, ASML \[1\] | 2006 | 9 years |
| Commercial 5 nm production on EUV, TSMC \[1\] | 2020 | 23 years |

**China's repeat.** This is the closest thing to an experiment on the question. China has a state chip fund deploying $48 billion in its third phase, published science, former ASML engineers, imported components and a fleet of imported DUV machines to take apart \[1\].

- SMEE was founded in 2002 to build DUV tools. It has had sustained sales only of i-line tools \[1\].
- Domestic immersion DUV reached about five machines in 2026, with critical parts still imported from Japan \[21\].
- An EUV prototype built in 2025 makes EUV light and no chips. It relies on parts salvaged from ASML machines, and project sources said it would have been nearly impossible without former ASML staff \[1\].
- The forecast in \[1\] puts commercial 7 nm-capable immersion DUV in China at 2032 to 2038 and commercial EUV at 2037 to 2044. Each range spans the forecast's two estimation methods.
- China already makes 7 nm chips on imported immersion DUV tools with multi-patterning \[20\]. The process knowledge transfers once the tool exists.

**How I read it for a rebuild.** A rebuilder after a ban knows the path, which removes the dead ends that cost the pioneers years \[1\]. A rebuilder also lacks what China has: working machines to dismantle, foreign parts to buy and practising experts to hire. Those roughly cancel in the middle row of the answer table. The bottom row assumes the experts are gone, which pushes the time back toward the original 23 to 30 years.

**What would shorten it.** Capable AI assistance in design, simulation and software. The forecast calls this a large source of uncertainty and does not quantify it \[1\]. Plan S as written keeps today's AI systems running, so a rebuilder would have that help. A buyback removes most of it.

## The buyback

In the first decade the buyback matters more than the rebuild time, because the chips already made are enough for a breakout and do not wear out quickly.

**What exists.**

- Epoch AI put the world's AI computing capacity at over 15 million H100-equivalents, drawing over 10 GW, in a dataset published in January 2026 \[29\]. The unit is one Nvidia H100, an accelerator first sold in 2022.
- At the 2025 price of about $500,000 for 16 H100s \[31\], that stock cost roughly $470 billion. The multiplication is mine. By 2029, when Plan S begins, the stock would be several times larger.
- Datacentre GPUs stay physically usable for five years or more. They are usually retired after two to four years for economic reasons \[30\]. Waiting for the stock to decay therefore takes longer than the decade the Plan S authors give their deal.

**How complete it has to be.** Two lines bracket the answer.

| Line | H100-equivalents | Share of the 2026 stock | Power | Training it can do in a year |
| --- | --- | --- | --- | --- |
| Plan S's harmless level, "a few thousand GPUs" | 3,000 | 0.02% | 2 MW | About 4 x 10^25 operations |
| A frontier cluster of 2024 to 2025 | 100,000 | 0.7% | 70 MW | About 10^27 operations, ten times the largest run of early 2025 \[6\] |

The last column assumes 10^15 low-precision operations a second per H100 and 40% utilisation. Both figures are from memory.

- A buyback can plausibly be accurate to better than 1% of the stock for any one holder. It cannot plausibly reach 0.02%. So it can keep the world below the frontier-cluster line and not below Plan S's harmless line, which Plan S accepts by assumption.
- 70 MW is easy to hide inside a national grid. Energy monitoring will not catch a retained 1%. The count has to.
- Each retained chip is worth about 50,000 times its power draw in chips at the i-line limit. Retained stock therefore outweighs anything permitted fabs can make.

**Three designs.**

| Design | What happens to the chips | What a breakout starts with | Cost |
| --- | --- | --- | --- |
| Consolidate and monitor. This is Plan S as written and the draft treaty of Scher et al. \[31\] | Clusters above 16 H100-equivalents move to declared sites within 120 days and are inspected \[31\] | The whole stock, on the day a state expels the inspectors | Low. AI services continue |
| Buy back and destroy datacentre chips | Accelerators and server processors above a performance line are destroyed under inspection | Hidden caches, plus consumer hardware gathered together | The AI and cloud industries, and compensation of the order of the stock's cost |
| Buy back everything below a feature-size line | All advanced chips are destroyed, phones and PCs included | Hidden caches only | Computing returns to 1990s capability at once, and billions of devices must be collected from private owners |

**My recommendation** is the second design, with the lithography ban doing the work of the third by attrition. This is a judgment.

- With no new advanced chips made, phones and PCs wear out and are replaced by devices on permitted technology. I would guess ten to fifteen years.
- Consumer hardware is a poor substitute in the meantime. A top consumer graphics card is of the order of a third of an H100, from memory. Reaching the 100,000 line would take some 300,000 cards in one place, which is visible commerce. The draft treaty already monitors sales above one H100-equivalent \[31\].

**How to verify it.**

- Count from the production side. Advanced accelerators came from a handful of fabs, packaging lines and memory makers \[27\]. Their shipment records give a ledger to reconcile against chips surrendered.
- Stop production before counting, so the ledger is closed.
- Treat failed chips as working until they are destroyed under inspection, as the draft treaty does \[31\]. Otherwise "failed in service" is the route to a hidden cache.
- Destroy, do not store. A warehouse of bought-back chips is the mothballed-tool problem again.

**Precedents.** A concentrated stock held by few parties can be bought and destroyed almost completely. A dispersed one cannot.

- The Megatons to Megawatts programme bought and diluted 500 tonnes of Russian weapons uranium between 1993 and 2013 \[32\]. That is about 20,000 warheads' worth, a figure I have only from a search summary.
- Australia's 1996 buyback collected over 650,000 firearms. Official estimates in 2014 still put about 260,000 guns in grey and black markets \[33\].

Datacentre chips resemble the first case and consumer devices the second. That is the reason to buy back the concentrated stock and let the dispersed stock age out.

**What it does to Plan S.** Plan S keeps datacentres running and roughly doubles the AI capacity available to users. A buyback ends that, and with it much of the plan's economic and political appeal. The proposal is a different plan at a higher price, close to the fab-treaty scenario in the companion scenarios document. Its case rests on the Plan S authors' own expectation that their version plausibly collapses within a decade or so.

## Implications for the design of the ban

Eight measures would make the ban and buyback deny training-scale compute and keep denying it.

1. **Define the ban by capability.** Ban any tool that prints below a stated half-pitch or aligns layers better than a stated tolerance, whatever it uses. An alignment limit also blocks multi-patterning, which depends on it \[28\].
2. **Choose the permitted level from the energy table.** At 0.35 micrometre a GPT-3-scale run costs a state 6.5 GW-years. At 0.8 micrometre it costs 78. The choice between permitting i-line and permitting only g-line is a choice about which size of run to deny.
3. **Ban nanoimprint and fine electron-beam writers by name.** Both exist today and neither is DUV or EUV. Laser writers are enough for the masks that permitted tools need \[16\].
4. **Buy back the datacentre stock, and count it from production records.** Aim for accuracy better than 1% per holder. Let consumer devices age out under the lithography ban.
5. **Destroy, do not mothball.** This applies to tools and to bought-back chips. The difference between the first and second rows of the answer table is the whole value of the ban in its first decade.
6. **Dissolve the single-source suppliers and inspect their trades.** Lithography lenses and mirrors, line-narrowed lasers, chemically amplified resists, mask blanks, electron-beam columns and precision stages each come from a handful of firms \[1, 27\].
7. **Use energy and wafer volume as a second check on new chips only.** A covert run on permitted chips needs gigawatts and tens of millions of processors, which is easy to see. A retained cache of modern chips needs tens of megawatts, which is not.
8. **Treat the ban as time-limited unless research also stops.** The penalty equals about a decade of algorithmic progress at the measured rate \[8\]. Plan S bans algorithmic research and expects covert progress to be at least ten times slower. If that holds, the decade becomes roughly a century. The lithography ban depends on it.

**In reply to the question as asked.** Rebuilding the DUV or EUV supply chain is not rapid. With tools destroyed, a state needs most of a decade for dry DUV and well over a decade for EUV, and the effort is large and hard to hide. The weak points are elsewhere: chips that escape the buyback, routes the ban does not name, a permitted industry that keeps the skills alive, and algorithmic progress that lowers the compute a dangerous run needs.

## Caveats

- The rebuild times are my judgments, not calculations. There is one historical case for EUV and about two for DUV.
- The energy table compares supercomputers, which differ in design as well as lithography. ASCI Red was the fastest machine of 1997, not the most efficient, and its power figure excludes cooling \[9\]. Blue Gene/P was built for efficiency. The step between those two rows therefore overstates the lithography effect. The g-line row is an extrapolation by ideal scaling \[12\], with no measured machine behind it.
- The lithography level attached to each anchor machine is from memory: 0.35 micrometre for ASCI Red's processors, 90 nm for Blue Gene/P, 28 nm for Shoubu and 4 nm for JEDI.
- In the buyback section, the H100's throughput, the utilisation figure and the consumer-card comparison are from memory. The 15 million figure is one estimate for early 2026, read from a news report of the dataset. The size of the 2029 stock is not sourced.
- The 1% accuracy I assume for a buyback is a judgment. I found no study of how closely production records can be reconciled with chips in the field.
- The decade-of-algorithmic-progress figure extrapolates a 2012 to 2023 trend \[8\]. It could run faster or stall.
- The long-wavelength resolution figures are a formula applied to a tool nobody has built.
- Plan S sets no numerical compute threshold, so the comparison with it uses its phrase about a few thousand GPUs, with my own round figures for their number and power.
- I am not a lithography engineer. A practitioner should review the routes table and the DUV table.

## References

Entries marked "read" I opened and checked for this document. Entries marked "summary" I used from a search summary. Entries marked "from memory" are standard references whose details I did not re-check; verify volume and page numbers before citing them.

1. Low, H., Turner, J. and Dean, R. "A forecast of Chinese DUV and EUV photolithography progress." AI Futures Project, 19 June 2026. [Link](https://blog.aifutures.org/p/a-forecast-of-chinese-duv-and-euv). Read.
2. Harriott, L. R. "Limits of lithography." Proceedings of the IEEE 89(3), 366-374, 2001. [Copy](https://typeset.io/pdf/limits-of-lithography-4yoo50ugph.pdf). Summary; details from memory.
3. Rothschild, M. et al. "Recent trends in optical lithography." Lincoln Laboratory Journal 14(2), 221-236, 2003. [Link](https://archive.ll.mit.edu/publications/journal/pdf/vol14_no2/14_2recenttrendsop.pdf). Summary; details from memory.
4. Semiconductor History Museum of Japan. "i-line reduction-projection exposure system." [Link](https://www.shmj.or.jp/english/pdf/em/exhibi2458E.pdf). Summary.
5. Semiconductor History Museum of Japan. "KrF excimer laser step-and-scan exposure system." [Link](https://www.shmj.or.jp/english/pdf/em/exhibi2461E.pdf). Summary.
6. Cottier, B. and Owen, D. "How many AI models will exceed compute thresholds?" Epoch AI, 30 May 2025. [Link](https://epoch.ai/blog/model-counts-compute-thresholds). Read.
7. Brown, T. et al. "Language models are few-shot learners." Advances in Neural Information Processing Systems 33, 2020. [arXiv:2005.14165](https://arxiv.org/abs/2005.14165). From memory; the compute figure is in its appendix.
8. Ho, A. et al. "Algorithmic progress in language models." 2024. [arXiv:2403.05812](https://arxiv.org/abs/2403.05812); also in the [NeurIPS 2024 proceedings](https://proceedings.neurips.cc/paper_files/paper/2024/hash/6b066da6a23bc55f9b887e7298102884-Abstract.html). Read (abstract).
9. "ASCI Red." [Wikipedia](https://en.wikipedia.org/wiki/ASCI_Red). Read. It gives 1.3 teraflops peak, 9,298 processors and 850 kW excluding air conditioning. Journal-level: Mattson, T. G. and Henry, G. "An overview of the Intel TFLOPS supercomputer." Intel Technology Journal, Q1 1998. From memory.
10. Feng, W. and Scogland, T. "The Green500 List: Year Two." [Link](https://top500.org:443/files/green500/feng-green500list-year2.pdf). Read. Also TOP500, "Energy-efficient supercomputing comes of age." [Link](https://www.top500.org/news/energy-efficient-supercomputing-comes-of-age-with-top500-green500-merge/). Read.
11. Koomey, J. et al. "Implications of historical trends in the electrical efficiency of computing." IEEE Annals of the History of Computing 33(3), 46-54, 2011. [Copy](https://Www.Gwern.net/doc/cs/hardware/2011-koomey.pdf). Summary; details from memory.
12. Dennard, R. H. et al. "Design of ion-implanted MOSFET's with very small physical dimensions." IEEE Journal of Solid-State Circuits 9(5), 256-268, 1974. From memory.
13. Boyd, J. "Canon delivers nanoimprint lithography to compete with EUV." IEEE Spectrum, 2 January 2025. [Link](https://spectrum.ieee.org/nanoimprint-lithography). Read.
14. Chou, S. Y., Krauss, P. R. and Renstrom, P. J. "Imprint lithography with 25-nanometer resolution." Science 272, 85-87, 1996. From memory.
15. Haley, G. "Nanoimprint finally finds its footing." Semiconductor Engineering, 20 April 2023. [Link](https://semiengineering.com/nanoimprint-finds-its-footing-in-photonics/). Read.
16. "Maskless lithography." [Wikipedia](https://en.wikipedia.org/wiki/Maskless_lithography). Read. Journal-level: Wieland, M. J. et al. "MAPPER: high-throughput maskless lithography." Proc. SPIE 7271, 2009. As listed there.
17. "NTHU orders Multibeam MBX." XenoSpectrum. [Link](https://xenospectrum.com/en/nthu-multibeam-mbx-order/). Summary.
18. Wilson, A. D. "X-ray lithography in IBM, 1980-1992, the development years." IBM Journal of Research and Development 37(3), 1993. [IEEE Xplore](https://ieeexplore.ieee.org/document/5389640). Title seen; content from memory.
19. Ferreira, B. "Substrate's claims about revolutionary ASML-beating chipmaking technology scrutinized." Tom's Hardware, 7 November 2025. [Link](https://www.tomshardware.com/tech-industry/semiconductors/substrates-claims-about-revolutionary-asml-beating-chipmaking-technology-scrutinized-analyst-likens-the-venture-to-a-fraud-report-pokes-holes-in-the-startups-technology-messaging-and-leaders). Read.
20. TechInsights. "China's SMIC plays 7 nm card." 2023. [Link](https://www.techinsights.com/blog/chinas-smic-plays-7-nm-card). Read.
21. "Chinese chipmaking tool roadmaps examined." Tom's Hardware, 4 August 2026. [Link](https://www.tomshardware.com/tech-industry/semiconductors/chinese-chipmaking-tool-roadmap-examined). Summary.
22. "China unveils 90%-domestic EUV light source prototype." TrendForce, 15 October 2026. [Link](https://www.trendforce.com/news/2026/10/15/news-china-unveils-90-domestic-euv-light-source-prototype-mass-production-reportedly-3-5-years-away/). Summary.
23. Pease, R. F. and Chou, S. Y. "Lithography and other patterning techniques for future electronics." Proceedings of the IEEE 96(2), 248-270, 2008. From memory.
24. Wagner, C. and Harned, N. "EUV lithography: lithography gets extreme." Nature Photonics 4, 24-26, 2010. From memory.
25. Fomenkov, I. et al. "Light sources for high-volume manufacturing EUV lithography: technology, performance, and power scaling." Advanced Optical Technologies 6(3-4), 173-186, 2017. From memory.
26. Center for Security and Emerging Technology. "Tracing the emergence of extreme ultraviolet lithography." [Link](https://cset.georgetown.edu/publication/tracing-the-emergence-of-extreme-ultraviolet-lithography/). Cited through \[1\]; not opened.
27. Khan, S. M., Mann, A. and Peterson, D. "The semiconductor supply chain: assessing national competitiveness." Center for Security and Emerging Technology, 2021. From memory.
28. Bencher, C. et al. "22nm half-pitch patterning by CVD spacer self alignment double patterning (SADP)." Proc. SPIE 6924, 2008. From memory.
29. "Global AI compute hits 15 million H100 equivalents, Epoch AI finds." The Decoder, 9 January 2026. [Link](https://the-decoder.com/global-ai-compute-hits-15-million-h100-equivalents-epoch-ai-finds/). Read. It reports an Epoch AI dataset published 8 January 2026, which I did not open.
30. Tozzi, C. "GPU lifespan in data centers: physical vs. economic." Data Center Knowledge, 8 September 2026. [Link](https://www.datacenterknowledge.com/data-center-chips/gpu-lifespan-in-data-centers-physical-vs-economic). Read.
31. Scher, A., Abecassis, D., Barnett, P. and Abeyta, B. "An international agreement to prevent the premature creation of artificial superintelligence." 2025. [arXiv:2511.10783](https://arxiv.org/abs/2511.10783v2). Read (abstract). Its [Article V, chip consolidation](https://ifanyonebuildsit.com/treaty/article-v-chip-consolidation). Read.
32. US Energy Information Administration. Today in Energy article on the Megatons to Megawatts programme, 24 September 2013. [Link](https://www.eia.gov/TODAYinENERGY/detail.php?id=13091). Read.
33. "National Firearms Agreement." [Wikipedia](https://en.wikipedia.org/wiki/National_Firearms_Agreement). Read.
34. TOP500. "Green500 list, June 2024." [Link](https://top500.org/lists/green500/2024/06/). Read.
