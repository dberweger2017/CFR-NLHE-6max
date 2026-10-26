# Live-order node ladder: 30B and 50B score worse than 10B against this panel

[#439](https://github.com/dberweger2017/CFR-NLHE-6max/pull/439) follows the [protocol](../../nplayer-live-order-nodes.md) committed before training. #431's live-order lineage (seed 2026102361001) was resumed from 10B to 30B and 50B nodes. Each step was compared with the previous checkpoint on new shared banks, against #417's 3B and the scripted fields. It is a one-lineage screen: nothing is promoted, and no default changes.

**The frozen rule's verdict:**
- **Primary, not shown.** 10B → 30B against the trained field is **−25.4 BB/100 [−33.8, −16.9]**: 30B is worse.
- **Second contrast, worse.** 30B → 50B is **−10.0 [−16.5, −3.4]**.
- **Harm flags:** random and random-tight on 10B → 30B; random on 30B → 50B.
- **Pot-pressure** (named secondary, individual 95%): +1.9 [−3.6, +7.4], then +3.1 [−1.2, +7.5]. No change is established either way.

**Decision:** keep 10B as the working candidate and the starting node budget for the 200 BB work.
- **What the evidence shows:** it argues against simply extending this lineage.
- **What it doesn't show:** it is not a general ranking of the checkpoints, and not evidence that longer training can't help another seed or another field.
- **Kept:** the 10B, 30B and 50B checkpoints and their adverse panels are all preserved.

## Results

Paired change, all-in adjusted, 16,384 blocks (196,608 hands) per field.
- **The trained field** has its individual 95% Student-t interval, the decision interval.
- **Every other field** has its **Bonferroni 95% interval over seven tests**, the interval behind the harm flags.
- **Pot-pressure** also shows its individual 95% interval, because the protocol names it as a secondary.

[ladder.csv](ladder.csv) exports both interval types for every field. Each contrast's `summary.json` has the full detail.

| Field | 10B → 30B | 30B → 50B | 10B / 30B / 50B, absolute |
|---|---|---|---|
| **Trained (#417 3B ×5)**, individual 95% | **−25.4** [−33.8, −16.9] | **−10.0** [−16.5, −3.4] | +191.3 / +165.9 / +155.9 |
| Random | **−83.0** [−99.4, −66.6], harm | **−32.8** [−45.0, −20.6], harm | +533.3 / +450.3 / +417.5 |
| Random-tight | **−13.4** [−21.7, −5.1], harm | −4.3 [−10.8, +2.2] | +114.4 / +101.0 / +96.6 |
| Check-call | −8.0 [−45.8, +29.9] | −14.7 [−44.6, +15.2] | +188.0 / +180.0 / +165.3 |
| Pot-pressure | +1.9 [−5.6, +9.5]; individual [−3.6, +7.4] | +3.1 [−2.9, +9.1]; individual [−1.2, +7.5] | +28.9 / +30.8 / +34.0 |
| Tight-aggressive | +3.2 [−2.3, +8.7] | +0.2 [−3.8, +4.2] | +33.9 / +37.0 / +37.3 |
| Call-pressure | +13.0 [−10.9, +36.9] | +2.1 [−17.8, +21.9] | +106.8 / +119.8 / +121.9 |
| Trained/call/pressure | +10.0 [−11.2, +31.2] | +5.7 [−11.0, +22.5] | +151.3 / +161.2 / +167.0 |

Per bank, the trained-field changes are −34.4, −24.5, −31.7 and −10.9 (10B → 30B), then −4.9, −15.2, −14.0 and −5.8 (30B → 50B). Every bank points the same way.

**Trajectory against the trained field:** +191 at 10B, +166 at 30B, +156 at 50B. The decline slows, from −1.3 to −0.5 BB/100 per extra billion nodes, but doesn't stop.

## Mechanism

**Table** (per-contrast `training.json`):

| Checkpoint | Entries | Learned rows | Decisions without a row (cumulative) | Regret updates per row (preflop / flop / turn / river) |
|---|---|---|---|---|
| 10B | 38.6M | 18.7M | 0.66% | 66 / 32 / 49 / 51 |
| 30B | 48.3M | 25.8M | 0.27% | 147 / 74 / 119 / 121 |
| 50B | 53.4M | 29.8M | 0.18% | 215 / 111 / 181 / 181 |

The table keeps growing slowly and never reaches the configured 250M cap, which therefore isn't binding. Rows receive far more regret updates. This measures how much data each row gets, not how accurate its estimates are. Abstraction and visitation limits remain possible.

**Where the change shows up** ([10b-30b/breakdown.csv](10b-30b/breakdown.csv), [30b-50b/breakdown.csv](30b-50b/breakdown.csv)):
- **What the breakdown is:** hands are grouped by how each arm's hand actually unfolded (ending, preflop line, position). A category's contribution is its summed result over all hands, divided by the hands per arm.
- **Contributions add up only within one grouping.**
  - The endings sum exactly to the field's change, and so do the preflop lines.
  - Groupings overlap, so contributions from different groupings must not be added. All-in contributions and 3-bet contributions count many of the same hands.
- **They describe, they don't explain.** Categories follow each policy's own trajectory, so a contribution doesn't identify the causal value of a changed action in matched states.

| Field, contrast | Largest contributions (by ending; by preflop line) | Category shares (share of hands) |
|---|---|---|
| Trained, 10B → 30B | all-ins before the river −17.2; 3-bet pots as raiser −16.1, as caller −13.1 | all-ins before the river 5.4% → 4.2%; 3-bet as raiser 3.5% → 2.7%, as caller 6.1% → 5.1%; preflop folds 76.5% → 77.6% |
| Trained, 30B → 50B | all-ins −8.0; 3-bet as raiser −4.9, as caller −4.0 | all-ins 4.2% → 3.8%; 3-bet as raiser 2.7% → 2.5%, as caller 5.1% → 4.8% |
| Random, 10B → 30B | all-ins before the river −82.0; calling 3-bets −61.6; 3-betting −33.0 | all-ins 14.1% → 11.4%; calling 3-bets 10.7% → 8.7%; preflop folds 81.9% → 85.0% |
| Random, 30B → 50B | all-ins −34.2; calling 3-bets −24.6; 3-betting −14.5 | all-ins 11.4% → 10.5%; calling 3-bets 8.7% → 8.0% |
| Pot-pressure, 10B → 30B | all-ins before the river +5.1; no other category above ±4 | all-ins 2.0% → 1.6% |

**Reading (descriptive):**
- **What changed in play:** with more training, fewer hands end in 3-bet pots or all-ins before the river, and slightly more end in preflop folds. The shift shrinks with each step.
- **Where returns fell:**
  - Against fields that raise and re-raise weakly (random, and #417's 3B, which plays uniform in about 10% of its spots), the categories that shrink are also where the arm's returns fall.
  - Against pot-pressure, whose re-raises are value-heavy, the same categories shrink while the field's overall change is unresolved: +1.9, then +3.1. That doesn't establish zero cost.
- **What would show causation:** a matched-state probe comparing the arms' actions in identical big-pot decisions. This screen doesn't measure it.

## Checks

- **Resume:** a live-order run resumed from 100M to 200M nodes is byte-identical to a straight run (`a3b03465…`).
- **Inputs:** #431's 10B checkpoint (`75245fbb…`) and binary (`f894a59f…`) match their pins.
- **Pipeline:** the 30B and 50B checkpoints (binaries `076be058…`, `1b5f8cf1…`) pass export, mass audit, conversion and verification.
- **Opponents unaffected:** #417's 3B found positive-mass rows for 89.6–89.7% of its decisions in every arm.
- **Trace integrity:** all 128 traces pass the replay scan with zero fallback violations, 49,152 hands each.

## What it means

- **The configured table cap isn't binding any more, but these fields don't reward more training.**
  - The live-order table doesn't fill, and rows receive more updates. Whether their estimates get more accurate isn't measured, and abstraction or visitation limits may still bind.
  - On this lineage, longer training goes with fewer big preflop pots. Returns fall against weak and loose fields, and changes against aggressive fields are unresolved.
- **Why this could happen** (hypotheses for the next work; neither progress toward equilibrium nor lower exploitability is measured here):
  1. **Balance versus exploitation:** the strategy approaches balanced self-play play, which exploits weak fixed strategies less. The panel's weak fields reward exploitation.
  2. **Merged rows drifting toward self-play:** live-order rows merge spots (imperfect recall), and longer training may tune each merged row to the situations self-play visits most.
  3. **The panel itself:** no field measures exploitability, so "worse against this panel" doesn't establish "weaker".
- **Ways to tell them apart,** each a separate question with its own protocol and budget:
  - checkpoints head-to-head (10B against 50B);
  - an exploitability probe such as a local best response on each checkpoint;
  - a matched-state comparison of the big-pot decisions identified above.
- **Limits:**
  - One lineage. The direction is consistent across all banks and both steps, but the size could vary by seed.
  - Pot-pressure and tight-aggressive changes are unresolved, so no improvement there is established.

## Cost

- **Run:** 15:56–20:26 UTC (4h30m) on bb128, alone. Peaks 76 °C CPU and VRM.
- **Training:** 10B → 30B and 30B → 50B took about 2,675 s each.
- **Evaluation:** per contrast, about 17 minutes of arena and about 62 minutes of all-in scoring.
- **Disk:** 19 GB on the HDD ([costs.json](costs.json)). Nothing was deleted.
