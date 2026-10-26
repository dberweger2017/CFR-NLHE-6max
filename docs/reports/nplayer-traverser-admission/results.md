# Six-player traverser admission: less wasted training, no strength gain, check-call harmed

[#430](https://github.com/dberweger2017/CFR-NLHE-6max/pull/430) follows the [protocol](../../nplayer-traverser-admission.md) committed before training. The six-player recipe was retrained with one change: a new key enters the table only from a traverser update (`--traverser-admission`). The result is compared with #417's 10B on [#427](../nplayer-opponent-pressure/results.md)'s four banks. It is a one-lineage screen: nothing is promoted, and no default changes.

**The frozen rule's verdict:**
- **Primary, not shown.** Against the trained field (five copies of #417's 3B), the paired change is **+1.5 BB/100 [−9.9, +12.9]**, all-in adjusted, over 16,384 blocks.
- **Harm flag: check-call.** The change there is **−53.5 [−99.8, −7.1]** (Bonferroni over seven fields), negative in all four banks.
- **Pot-pressure, named secondary:** +6.2 [−1.8, +14.1]. Both models still lose clearly to that field: control −31.0, admission −24.9.

The mechanism worked in training: the table froze 3.3× later and discarded far fewer updates. But the freed capacity went mostly to rows that opponents never reach, and the share of played decisions on learned rows barely changed outside the river.

## Results

Paired change (admission minus control), all-in adjusted, four fresh banks × 4,096 blocks. Intervals are 95% Student-t for the primary and pot-pressure, and Bonferroni 95% over seven tests for the harm flags ([fields.csv](fields.csv), [summary.json](summary.json)).

| Field | Change, BB/100 | Interval | Per bank | Control → admission, absolute |
|---|---|---|---|---|
| **Trained (#417 3B ×5, primary)** | **+1.5** | [−9.9, +12.9] | +4.8, −10.4, +9.7, +1.8 | +86.8 → +88.3 |
| Pot-pressure (secondary) | +6.2 | 95% [−1.8, +14.1]; family [−4.8, +17.1] | +1.8, +10.9, +12.4, −0.4 | −31.0 → −24.9 |
| Tight-aggressive | −7.8 | [−15.9, +0.3] | −5.3, −12.0, −14.1, +0.1 | +21.1 → +13.3 |
| **Check-call (harm)** | **−53.5** | [−99.8, −7.1] | −22.6, −63.8, −51.2, −76.2 | +290.9 → +237.5 |
| Call-pressure | −1.7 | [−27.4, +24.0] | +10.2, −10.1, −6.3, −0.6 | +84.0 → +82.3 |
| Trained/call/pressure | −7.0 | [−30.3, +16.2] | −37.1, +7.7, +16.9, −15.5 | +53.2 → +46.2 |
| Random | −3.4 | [−22.8, +16.0] | −11.6, +11.4, −17.7, +4.3 | +359.1 → +355.7 |
| Random-tight | +12.2 | [+0.7, +23.8] | +9.5, +0.7, +28.7, +10.1 | +114.9 → +127.1 |

- **Tight-aggressive:** its ordinary 95% interval, [−13.7, −1.9], is below zero, but the family interval reaches +0.3, so it is not flagged.
- **Random-tight:** its family interval is above zero. That is a side effect, not the hypothesis.
- **Replay check:** the control's absolute results match #427's exactly on every field. It replayed the same deals byte for byte.

## Mechanism

**Table and training** ([training.json](training.json)):

| | Control (#417) | Admission |
|---|---|---|
| Key table froze at iteration | 23,678 of 390,401 | **78,568** of 392,449 |
| Opponent-only rows (uniform, positive mass) | 149,758,755 | **0** |
| Zero-mass rows (traverser-only, uniform fallback) | 58,854,501 | **203,543,271** |
| Learned rows (regrets and mass) | 41,388,298 | **46,458,245** (+12%) |
| Traverser updates discarded after the freeze | 68.1% | **50.6%** |
| Training decisions without a row | 66.7% | 66.7% |
| Opponent-only updates declined | — | 669,283,836 key-iterations |
| Rows by street (preflop / flop / turn / river) | 35.1M / 44.2M / 63.6M / 107.1M | 19.0M / 32.3M / 64.8M / 133.9M |
| Regret updates per row (preflop / flop / turn / river) | 2.0 / 2.7 / 2.8 / 2.0 | 4.4 / 4.5 / 4.0 / 3.1 |

**Played decisions:** the share of focal decisions on each kind of row ([rows.csv](rows.csv)):

| Against | Arm | Learned, all streets | Opponent-only | Missing | Learned, river |
|---|---|---|---|---|---|
| Trained | control → admission | 88.8% → 88.3% | 1.7% → 0% | 9.4% → 11.6% | **69.3% → 78.3%** |
| Pot-pressure | control → admission | 97.1% → 97.2% | 0.4% → 0% | 2.5% → 2.8% | **78.4% → 85.9%** |
| Tight-aggressive | control → admission | 99.0% → 99.1% | 0.1% → 0% | 0.9% → 0.9% | 86.5% → 91.1% |
| Check-call | control → admission | 42.9% → 38.6% | 4.5% → 0% | 52.6% → 61.3% | 0% → 0% |

The two arms play different hands, so the all-street shares are not strictly comparable. They are dominated by preflop.

## What it means

- **The opponent-only rows were real waste for training, but not for play.**
  - In the control they held 60% of the table, but only 1.7% of decisions against the trained field (0.4% against pot-pressure) landed on one.
  - Untrained play was never mainly these rows. It is missing keys, and against check-call that means most decisions.
- **Removing them made training denser, not wider where play goes.**
  - Rows get 1.5–2× more regret updates, and a quarter fewer traverser updates are discarded.
  - But 81% of the table now holds traverser-only rows. These are histories reached only under actions the traverser explores but the sampled opponents never play into, so they still play the uniform fallback.
  - Learned rows grow just 12%, and the share of training decisions without a row doesn't move.
- **Denser training didn't buy measurable strength.**
  - The trained field and pot-pressure both moved inside their intervals.
  - Rows that already played improved on the river, at least in coverage, but no field shows a resolved gain except random-tight.
- **Check-call is harmed again, as with 5% pressure (−57.4).**
  - Two different one-change retrainings from the same seed both lose about 55 BB/100 there. Against check-call, 53–61% of decisions have no row and play uniform.
  - That field's result may depend strongly on which lineage reaches which untrained histories. Separating a cause from seed-to-seed variation needs more seeds; this screen cannot.
- **What this says about capacity:** with first-come admission, the 250M table isn't mainly wasted on opponent-only rows in play. The table is too small for the key space six-player self-play explores. It fills with traverser exploration, and rows average 2–4 regret updates over the whole run. Making admission smarter within the same key space moves the margin, not the gap.
- **Limits:** one training lineage per model. The difference mixes the change with seed-to-seed variation, which is unknown here. Treat the side effects as hypotheses, not findings.

## Qualification and cost

- **Legacy parity:** without the option, the branch trainer's 100M-node checkpoint is byte-identical to a `main` build (`69fad647…`). That's the same hash #427 recorded.
- **Determinism:** with the option, 16 and 8 threads give identical 100M-node checkpoints (`f628860f…`).
  - It differs from the legacy run, declines 46.6M key-iterations and stores no row with `visits` 0.
  - At iteration 5,630 it holds 15.8M rows against the legacy run's 58.7M.
- **Pipeline:** export, average-mass audit, conversion and binary verification all passed.
- **Pins:** checkpoint `491110d9…`, binary `84692560…` ([costs.json](costs.json)).
- **Training:** 10,000,003,557 nodes, 392,449 iterations, 2,004 s active.
- **Run:** 21:15–00:08 UTC (2h52m) on bb128, alone. CPU and VRM peaks 76 °C, no stop.
- **Disk:** work files are on the NVMe: 33 GB after compressing traces and the binary, 41 GB free at the end. Nothing was deleted.
- **Failures:** none; no research step was repeated.
