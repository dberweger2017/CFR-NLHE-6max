# Six-player live-order keys: large gains, pot-pressure now beaten, check-call harmed

[#431](https://github.com/dberweger2017/CFR-NLHE-6max/pull/431) follows the [screen protocol](../../nplayer-live-order-screen.md) committed before training. The six-player recipe was retrained with one change: [live-order keys](../../nplayer-live-order-keys.md) (`--key-schema live-order`) instead of full-history keys. The result is compared with #417's 10B on [#427](../nplayer-opponent-pressure/results.md)'s four banks. It is a one-lineage screen: nothing is promoted, and no default changes.

**The frozen rule's verdict:**
- **Primary, improved.** Against the trained field (five copies of #417's 3B), the paired change is **+105.4 BB/100 [+92.9, +117.9]**, all-in adjusted, over 16,384 blocks. It is positive in all four banks.
- **Harm flag: check-call.** The change there is **−110.7 [−163.6, −57.8]** (Bonferroni over seven fields), negative in all four banks. Both models still win clearly against that field: control +290.9, live-order +180.2.
- **Pot-pressure, named secondary: +58.4 [+50.2, +66.5].** The six-player gap is closed on these banks: control **−31.0**, live-order **+27.3**.

## Results

Paired change (live-order minus control), all-in adjusted, four fresh banks × 4,096 blocks. Intervals are 95% Student-t for the primary and pot-pressure, and Bonferroni 95% over seven tests for the harm flags ([fields.csv](fields.csv), [summary.json](summary.json)).

| Field | Change, BB/100 | Interval | Per bank | Control → live-order, absolute |
|---|---|---|---|---|
| **Trained (#417 3B ×5, primary)** | **+105.4** | [+92.9, +117.9] | +120.1, +97.4, +94.9, +109.2 | +86.8 → +192.2 |
| **Pot-pressure (secondary)** | **+58.4** | 95% [+50.2, +66.5]; family [+47.2, +69.5] | +67.2, +44.4, +61.8, +60.0 | **−31.0 → +27.3** |
| Tight-aggressive | +15.0 | [+7.4, +22.6] | +20.4, +9.6, +16.0, +13.9 | +21.1 → +36.1 |
| Trained/call/pressure | +81.5 | [+54.8, +108.2] | +51.9, +117.8, +97.4, +58.8 | +53.2 → +134.7 |
| Random | +187.7 | [+160.4, +215.0] | +195.7, +193.9, +142.2, +219.1 | +359.1 → +546.9 |
| Call-pressure | +5.6 | [−23.6, +34.7] | +15.1, −17.4, +30.5, −5.8 | +84.0 → +89.6 |
| Random-tight | −0.2 | [−12.4, +12.0] | −16.6, −0.5, +9.1, +7.1 | +114.9 → +114.6 |
| **Check-call (harm)** | **−110.7** | [−163.6, −57.8] | −105.1, −96.4, −89.6, −151.6 | +290.9 → +180.2 |

Realized (unadjusted) changes agree in sign and size on every field: for example trained +102.5 and pot-pressure +61.1.

## Mechanism

**Table and training** ([training.json](training.json)):

| | Control (#417) | Live-order |
|---|---|---|
| Entries at 10B nodes | 250,001,554, frozen at iteration 23,678 | **38,608,704**, never frozen |
| Training decisions without a row | 66.7% | **0.66%** |
| Traverser updates discarded | 68.1% | **0%** |
| Regret updates per row (preflop / flop / turn / river) | 2.0 / 2.7 / 2.8 / 2.0 | **66 / 32 / 49 / 51** |
| Opponent-only rows | 149.8M | 14.5M (traverser admission off) |
| Iterations to 10B nodes | 390,401 | 363,668 |

**Played decisions:** the share of focal decisions on learned rows (regrets and mass), from [rows.csv](rows.csv):

| Against | All streets, control → live-order | River | Missing, all streets |
|---|---|---|---|
| Trained | 88.8% → **99.7%** | 69.3% → **99.8%** | 9.4% → 0.0% |
| Pot-pressure | 97.1% → **99.9%** | 78.4% → **99.6%** | 2.5% → 0.0% |
| Tight-aggressive | 99.0% → **100%** | 86.5% → **99.8%** | 0.9% → 0.0% |
| Random | 72.8% → **97.9%** | 14.6% → **98.1%** | 20.7% → 0.2% |
| Trained/call/pressure | 66.2% → **90.5%** | 5.6% → **73.8%** | 30.2% → 3.4% |
| Call-pressure | 55.3% → 68.2% | 0% → 2.8% | 40.1% → 17.5% |
| Check-call | 42.9% → 41.0% | **0% → 0%** | 52.6% → 49.1% |

## Checks on the result

- **Control replay:** the control's absolute results match #427 and #430 exactly on every field.
- **Opponents unaffected:** in the trained field, #417's 3B opponents (`6cd50bf1…`, history keys) found positive-mass rows for 89.3% of their decisions against the control and 89.5% against live-order. So they played normally in both arms.
- **Trace integrity:** all 64 traces pass the replay scan with matching hashes and zero fallback violations, 49,152 hands each.
- **Information:** every key feature comes from the acting seat's public observation. The key adds no information a player at the table lacks; it removes detail.

## What it means

- **Capacity was the binding problem, and the key was the way past it.**
  - Three earlier screens changed which histories get rows (#427, #428, #430) and moved strength very little.
  - Making far fewer, much better-trained rows moves it a lot. With nearly every training decision finding a row, and rows getting 30–60 updates instead of 2–3, the bot gains on every field that bets or raises into it.
- **The six-player gap is closed on these deals.** Pot-pressure goes from −31.0 to +27.3. It's not a pressure-specific trick, because tight-aggressive and the mixed trained field improve too.
- **Merging spots didn't cost measurable strength anywhere except check-call.** The risk the protocol named, distinct spots sharing a row, doesn't show up against any field that bets.
- **Check-call is the exception, and its mechanism is visible.**
  - Its multiway rivers remain unvisited by self-play under any key: 0% learned in both arms, 49–53% of all its decisions missing.
  - Against a field that never folds, the uniform fallback in those spots costs value. Better-trained earlier streets seem to steer the bot into more of them, but that is a hypothesis, not a measured cause.
  - The field remains a large win (+180.2).
- **Limits:**
  - One training lineage per model, so the difference mixes the change with seed-to-seed variation. It is unknown here, though no earlier six-player seed difference came close to +105.
  - The trained field is #417's own 3B, and a stronger foreign model may exploit that ancestor more easily than #417's 10B does. The scripted-field gains don't share that caveat.
  - Nothing here is release acceptance.

**Next, per the protocol:** confirmation with more seeds, then the 200 BB six-player work. Neither starts automatically.

## Qualification and cost

- **Legacy parity:** without the option, the branch trainer's 100M-node checkpoint is byte-identical to a `main` build (`69fad647…`).
- **Determinism:** with the option, 16 and 8 threads give identical 100M-node checkpoints (`482a0f8f…`).
- **Pipeline:** export, average-mass audit, conversion and binary verification all passed.
- **Pins:** checkpoint `75245fbb…`, binary `f894a59f…` ([costs.json](costs.json)).
- **Training:** 10,000,005,692 nodes, 363,668 iterations, 1,335 s active, against #417's ~2,000 s. The checkpoint is 2.0 GB and the binary 2.2 GB, against 9.6 GB and 14.2 GB.
- **Run:** 06:27–08:32 UTC (2h05m) on bb128, alone. CPU peak 74 °C, VRM peak 75 °C, no stop.
- **Disk:** 8.0 GB on the HDD and 3.5 GB on the NVMe after compression. Nothing was deleted.
- **Failures:** none; no research step was repeated.
