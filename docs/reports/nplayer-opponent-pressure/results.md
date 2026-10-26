# Six-player opponent-pressure screen: pot-pressure not shown, check-call harmed

[#427](https://github.com/dberweger2017/CFR-NLHE-6max/pull/427) follows the [protocol](../../nplayer-opponent-pressure.md) committed before training. The six-player recipe was retrained with one change: opponents of the learning seat take the pot-size raise 5% of the time (`--opponent-pot-raise 0.05`). The result is compared with #417's 10B on fresh deals. It is a one-lineage screen: nothing is promoted, and no default changes.

**The frozen rule's verdict:**
- **Primary, not shown.** Against pot-pressure, the paired change is **+5.9 BB/100 [−2.3, +14.1]**, all-in adjusted, over 16,384 blocks. Both models still lose clearly to that field on these banks: control −31.0, pressure −25.1.
- **Harm flag: check-call.** The change there is **−57.4 [−108.1, −6.6]** (Bonferroni over seven fields), negative in all four banks.
- **Large gains elsewhere:**
  - trained +32.8 [+16.2, +49.3];
  - random +63.4 [+42.4, +84.5];
  - random-tight +39.0 [+27.1, +50.9].

  These are side effects, not the hypothesis.

## Results

Paired change (pressure minus control), all-in adjusted, four fresh banks × 4,096 blocks. Intervals are 95% Student-t for the primary and Bonferroni 95% over seven tests for the others ([fields.csv](fields.csv), [summary.json](summary.json)).

| Field | Change, BB/100 | Interval | Per bank | Control → pressure, absolute |
|---|---|---|---|---|
| **Pot-pressure (primary)** | **+5.9** | [−2.3, +14.1] | +0.8, +1.0, +27.6, −5.8 | −31.0 → −25.1 |
| Tight-aggressive | −3.2 | [−11.6, +5.1] | −4.9, −2.8, −2.1, −3.1 | +21.1 → +17.9 |
| **Check-call (harm)** | **−57.4** | [−108.1, −6.6] | −68.9, −39.9, −50.3, −70.4 | +290.9 → +233.5 |
| Call-pressure | +16.4 | [−10.6, +43.4] | +7.7, +12.3, +51.2, −5.7 | +84.0 → +100.4 |
| Trained/call/pressure | +13.7 | [−10.5, +37.9] | −6.8, +11.4, +22.5, +27.9 | +53.2 → +67.0 |
| Trained (#417 3B ×5) | +32.8 | [+16.2, +49.3] | +29.6, +24.1, +43.6, +33.7 | +86.8 → +119.6 |
| Random | +63.4 | [+42.4, +84.5] | +43.7, +85.3, +53.5, +71.2 | +359.1 → +422.6 |
| Random-tight | +39.0 | [+27.1, +50.9] | +30.2, +36.1, +39.5, +50.0 | +114.9 → +153.8 |

**Mechanism: untrained spots shrink a little.** Share of focal decisions with no trained row:

| Against | Preflop | Flop | Turn | River | All |
|---|---|---|---|---|---|
| Pot-pressure, control → pressure | 0.95% → 0.63% | 3.47% → 2.77% | 9.43% → 7.53% | 21.1% → 16.2% | 2.48% → 2.13% |
| Tight-aggressive | 0.25% → 0.16% | 0.82% → 0.61% | 3.83% → 3.19% | 13.3% → 8.9% | 0.91% → 0.82% |
| Check-call | 0.25% → 0.27% | 69.6% → 72.0% | 99.8% → 99.9% | 100% → 100% | 52.6% → 53.8% |

## What it means

- **The pressure reached the raise-heavy spots, but only partly.** Untrained river decisions against pot-pressure fell by a quarter (21% → 16%), and preflop by a third. The improvement against pot-pressure is positive but not resolved, and the field is still a large loss. 5% pressure isn't enough to close the six-player gap on its own.
- **The bot got stronger against balanced and random play.** It gained against its own 3B field and the random fields. It now does better when opponents put money in.
- **It gave up value against calling stations.** That is consistent with expecting more raises, so value-betting less against players who never raise. Check-call histories after the flop remain almost entirely untrained in both models: that gap is unchanged.
- **The key table freezes early in both runs.** The 250M-entry table filled at iteration 31,021 of 448,818 (control: 23,678 of 390,401). After that, new histories can't get rows. So whichever spots are visited in roughly the first 7% of training decide which spots the bot can ever learn. Pressure changes visitation for the whole run, but it can change the key set only during that early window.
- **Limits:** one training lineage for each model. The difference mixes the change with seed-to-seed variation, which is unknown here. Treat the side effects as hypotheses, not findings.

## Qualification and cost

- **Legacy parity:** without the option, the branch trainer's 100M-node checkpoint is byte-identical to a `main` build (`69fad647…`).
- **Determinism:** with the option, 16 and 8 threads give identical checkpoints (`a38fe135…`, 1,634,891 forced raises). It differs from the run without pressure.
- **Pipeline:** export, average-mass audit, conversion and binary verification all passed.
- **Pins:** checkpoint `8fdd7911…`, binary `91c70fdc…` ([costs.json](costs.json)).
- **Training:** 10,000,025,057 nodes, 448,818 iterations, 2,020 s active, and 152,961,237 forced opponent pot raises.
- **Run:** 00:09–02:30 UTC on bb128 alongside #425. CPU peak 75 °C and VRM peak 76 °C; no stop triggered. The work files take 57 GB on the HDD.
- **The one interruption was plumbing.** The first launch stopped after the parity checks passed, on a shell `pipefail` in the header check. It was fixed and resumed, reusing the four verified parity checkpoints. No research step was repeated.
