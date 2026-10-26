# Live-order node ladder: more training makes the bot tighter, not stronger against this panel

[#439](https://github.com/dberweger2017/CFR-NLHE-6max/pull/439) follows the [protocol](../../nplayer-live-order-nodes.md) committed before training. #431's live-order lineage (seed 2026102361001) was resumed from 10B to 30B and 50B nodes. Each step was compared with the previous checkpoint on new shared banks, against #417's 3B and the scripted fields. It is a one-lineage screen: nothing is promoted, and no default changes.

**The frozen rule's verdict:**
- **Primary, not shown.** 10B → 30B against the trained field is **−25.4 BB/100 [−33.8, −16.9]**: 30B is worse.
- **Second contrast, worse.** 30B → 50B is **−10.0 [−16.5, −3.4]**.
- **Harm flags:** random and random-tight on 10B → 30B; random on 30B → 50B.
- **Pot-pressure** doesn't move: +1.9 [−3.6, +7.4], then +3.1 [−1.2, +7.5].

**Decision:** the 200 BB work starts at **10B nodes**.

## Results

Paired change, all-in adjusted, 16,384 blocks (196,608 hands) per field. The trained field has its 95% interval; the others have Bonferroni 95% intervals over seven tests ([ladder.csv](ladder.csv), per-contrast `summary.json`).

| Field | 10B → 30B | 30B → 50B | 10B / 30B / 50B, absolute |
|---|---|---|---|
| **Trained (#417 3B ×5)** | **−25.4** [−33.8, −16.9] | **−10.0** [−16.5, −3.4] | +191.3 / +165.9 / +155.9 |
| Random | **−83.0** [−99.4, −66.6], harm | **−32.8** [−41.7, −24.0], harm | +533.3 / +450.3 / +417.5 |
| Random-tight | **−13.4** [−21.7, −5.1], harm | −4.3 [−9.1, +0.4] | +114.4 / +101.0 / +96.6 |
| Check-call | −8.0 [−45.8, +29.9] | −14.7 [−36.5, +7.1] | +188.0 / +180.0 / +165.3 |
| Pot-pressure | +1.9 [−3.6, +7.4] | +3.1 [−1.2, +7.5] | +28.9 / +30.8 / +34.0 |
| Tight-aggressive | +3.2 [−0.8, +7.2] | +0.2 [−2.7, +3.1] | +33.9 / +37.0 / +37.3 |
| Call-pressure | +13.0 [−10.9, +36.9] | +2.1 [−12.4, +16.5] | +106.8 / +119.8 / +121.9 |
| Trained/call/pressure | +10.0 [−11.2, +31.2] | +5.7 [−6.5, +18.0] | +151.3 / +161.2 / +167.0 |

Per bank, the trained-field changes are −34.4, −24.5, −31.7 and −10.9 (10B → 30B), then −4.9, −15.2, −14.0 and −5.8 (30B → 50B). Every bank points the same way.

**Trajectory against the trained field:** +191 at 10B, +166 at 30B, +156 at 50B. The decline slows, from −1.3 to −0.5 BB/100 per extra billion nodes, but doesn't stop.

## Mechanism

**Table** (per-contrast `training.json`):

| Checkpoint | Entries | Learned rows | Decisions without a row (cumulative) | Regret updates per row (preflop / flop / turn / river) |
|---|---|---|---|---|
| 10B | 38.6M | 18.7M | 0.66% | 66 / 32 / 49 / 51 |
| 30B | 48.3M | 25.8M | 0.27% | 147 / 74 / 119 / 121 |
| 50B | 53.4M | 29.8M | 0.18% | 215 / 111 / 181 / 181 |

The table keeps growing slowly and never nears the cap. Rows get far more updates, so the extra nodes are spent refining existing rows, as expected.

**Where the value goes:** additive per-category contributions ([10b-30b/breakdown.csv](10b-30b/breakdown.csv), [30b-50b/breakdown.csv](30b-50b/breakdown.csv)):

| Field, contrast | Biggest losses | How play changes (share of hands) |
|---|---|---|
| Trained, 10B → 30B | all-ins before the river −17.2; 3-bet pots as raiser −16.1, as caller −13.1 | all-ins before the river 5.4% → 4.2%; 3-bet as raiser 3.5% → 2.7%, as caller 6.1% → 5.1%; preflop folds 76.5% → 77.6% |
| Trained, 30B → 50B | all-ins −8.0; 3-bet as raiser −4.9, as caller −4.0 | all-ins 4.2% → 3.8%; 3-bet as raiser 2.7% → 2.5%, as caller 5.1% → 4.8% |
| Random, 10B → 30B | all-ins before the river −82.0; calling 3-bets −61.6; 3-betting −33.0 | all-ins 14.1% → 11.4%; calling 3-bets 10.7% → 8.7%; preflop folds 81.9% → 85.0% |
| Random, 30B → 50B | all-ins −34.2; calling 3-bets −24.6; 3-betting −14.5 | all-ins 11.4% → 10.5%; calling 3-bets 8.7% → 8.0% |
| Pot-pressure, 10B → 30B | none material; all-ins +5.1 | all-ins 2.0% → 1.6% |

**Reading:** with more training, the bot plays fewer big preflop pots. It 3-bets less, calls fewer 3-bets and gets all-in less often, and the effect shrinks with each step.
- **Against fields that raise and re-raise weakly** (random, and #417's 3B, which plays uniform in about 10% of its spots), getting the money in wide is very profitable, so tightening costs value.
- **Against pot-pressure,** whose re-raises are value-heavy, the same tightening costs nothing, and the point estimates improve slightly.

## Checks

- **Resume:** a live-order run resumed from 100M to 200M nodes is byte-identical to a straight run (`a3b03465…`).
- **Inputs:** #431's 10B checkpoint (`75245fbb…`) and binary (`f894a59f…`) match their pins.
- **Pipeline:** the 30B and 50B checkpoints (binaries `076be058…`, `1b5f8cf1…`) pass export, mass audit, conversion and verification.
- **Opponents unaffected:** #417's 3B found positive-mass rows for 89.6–89.7% of its decisions in every arm.
- **Trace integrity:** all 128 traces pass the replay scan with zero fallback violations, 49,152 hands each.

## What it means

- **There's no plateau from capacity any more, but these fields don't reward more training.**
  - The live-order table doesn't freeze, and rows keep improving their estimates.
  - The average strategy moves toward tighter preflop play in big pots, which gives up value against weak and loose opponents and none against aggressive ones.
- **Why this could happen** (hypotheses for the next work):
  1. **Balance versus exploitation:** the strategy approaches balanced self-play play, which exploits weak fixed strategies less. The panel's weak fields reward exploitation.
  2. **Merged rows drifting toward self-play:** live-order rows merge spots (imperfect recall), and longer training may tune each merged row to the situations self-play visits most.
  3. **The panel itself:** no field measures exploitability, so "worse against this panel" doesn't establish "weaker".
- **Ways to tell them apart:**
  - checkpoints head-to-head (10B against 50B);
  - an exploitability probe such as a local best response on each checkpoint;
  - range comparisons in the big-pot spots identified above.
- **Limits:**
  - One lineage. The direction is consistent across all banks and both steps, but the size could vary by seed.
  - Pot-pressure and tight-aggressive changes are unresolved, so no improvement there is established.

## Cost

- **Run:** 15:56–20:26 UTC (4h30m) on bb128, alone. Peaks 76 °C CPU and VRM.
- **Training:** 10B → 30B and 30B → 50B took about 2,675 s each.
- **Evaluation:** per contrast, about 17 minutes of arena and about 62 minutes of all-in scoring.
- **Disk:** 19 GB on the HDD ([costs.json](costs.json)). Nothing was deleted.
