# Opponent pressure at 15% and 30%: pot-pressure never improves, and at 30% it collapses

[#428](https://github.com/dberweger2017/CFR-NLHE-6max/pull/428) follows the [dose amendment](../../nplayer-opponent-pressure-doses.md), committed before either run. Each dose retrains the six-player recipe with `--opponent-pot-raise` at 0.15 or 0.30. Each is compared with #417's 10B on [#427](../nplayer-opponent-pressure/results.md)'s four banks, so every dose plays identical deals. These are one-lineage screens: nothing is promoted, and no default changes.

**The frozen rule's verdicts:**
- **15%:** primary **not shown** (pot-pressure +3.7 [−6.2, +13.6]); no harm flags.
- **30%:** primary **not shown**, and pot-pressure is **much worse: −71.0 [−83.8, −58.3]**. Tight-aggressive is **flagged as harmed: −44.7 [−58.7, −30.7]**.

## The dose-response

Paired change against #417's 10B, all-in adjusted, BB/100. The pot-pressure intervals are 95%; the others are Bonferroni over seven tests ([d15/fields.csv](d15/fields.csv), [d30/fields.csv](d30/fields.csv)).

| Field | 5% (#427) | 15% | 30% |
|---|---|---|---|
| **Pot-pressure (primary)** | +5.9 [−2.3, +14.1] | +3.7 [−6.2, +13.6] | **−71.0 [−83.8, −58.3]** |
| Tight-aggressive | −3.2 | −0.1 | **−44.7 [−58.7, −30.7], harm** |
| Check-call | **−57.4, harm** | −36.1 | +0.5 |
| Call-pressure | +16.4 | +30.5 | +72.0 |
| Trained/call/pressure | +13.7 | +33.9 | +79.1 |
| Trained (#417 3B ×5) | +32.8 | +59.9 | +77.5 |
| Random | +63.4 | +187.5 | +293.6 |
| Random-tight | +39.0 | +142.1 | +217.0 |

Each 30% field change has the same sign in all four banks, except check-call.

**Absolute adjusted result against pot-pressure:** control −31.0; at 5% −25.1, at 15% −27.4, at 30% −102.1.

**Untrained decisions against pot-pressure:**

| Street | Control | 5% | 15% | 30% |
|---|---|---|---|---|
| Preflop | 0.95% | 0.63% | 0.38% | 0.21% |
| Flop | 3.47% | 2.77% | 1.93% | 1.51% |
| Turn | 9.43% | 7.53% | 5.32% | 5.54% |
| River | 21.1% | 16.2% | 11.7% | 12.4% |

**Training telemetry:**

| | Control | 5% | 15% | 30% |
|---|---|---|---|---|
| Iterations to 10B nodes | 390,401 | 448,818 | 664,866 | 1,306,649 |
| Key table froze at iteration | 23,678 | 31,021 | 54,323 | 144,409 |

## What it means

- **Coverage was never the binding problem against pot-pressure.** Pressure removes 40–80% of the untrained raise-heavy spots, depending on street, but the pot-pressure result doesn't improve at any dose. This agrees with #426's replay.
- **The forced raises teach the wrong lesson about raises.** The training opponents' extra pot raises are *card-independent*: they fire at random, whatever the hand. So the more pressure, the more the bot learns that a pot raise is often weak, and the more it calls them down.
  - **Against fields that bet or raise without regard to cards** (random and the mixes), that is exactly right, and the gains grow with the dose.
  - **Against pot-pressure and tight-aggressive**, whose raises are mostly strong hands, it is exploited. At 30% this turns into large losses.
- **The trained-field gains look real, but they don't help the gap.** The bot beats its own 3B copies by more at every dose (+33, +60, +78). The likely reason: it learns to punish the 3B's raises, which are less well-founded. That is a better bot against self-play opponents, not against value-heavy aggression.
- **Implication:** better answers to pot-pressure need training opponents whose pressure is *hand-dependent*, like real aggressive players. For example, the deviation could raise more often with stronger hands. Uniform random pressure won't get there at any strength. The 5–15% models are interesting side candidates (large gains against weak and self-play fields, no flags at 15%), but they don't address the six-player gap.
- **Limits:** one training lineage per dose; the dose-response is descriptive and was not tested for trend.

## Run and cost

- **The runs:** 15% then 30% on bb128 (11:44–17:24 UTC), after the 15% run waited 15 minutes for disk space (plumbing).
  - **Qualification:** for each dose the checkpoint records `opponent_pressure` with the declared probability (462M and 966M forced raises), and export, audit, conversion and binary verification passed.
  - **Pins:** in [d15/model-pins.json](d15/model-pins.json) and [d30/model-pins.json](d30/model-pins.json).
- **Disk:**
  - the arena ran one bank at a time, and traces and model binaries were gzip-compressed after use;
  - to make room, #426's and #427's raw traces and #427's binary were compressed losslessly too: SHA256 first, `gzip -t` verified;
  - nothing was deleted, and 49 GB of working files remain on the HDD for the vacuum cleaner.
- **Temperatures:** CPU peak 75 °C, VRM peak 77 °C, no stop.

Details in [costs.json](costs.json).
