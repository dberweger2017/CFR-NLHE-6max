# Six-player opponent-pressure training screen (protocol)

This protocol is committed before any training or evaluation. It is a one-lineage development screen: nothing is promoted, no default or release changes, and #417's control stays the six-player model.

## Why

[#426](reports/nplayer-six-player-loss-diagnosis/results.md) found the six-player gap is the pot-pressure field: −22.3 BB/100 [−30.8, −13.7] after all-in adjustment. The same field gives +31.6 at four players.

Two things go wrong against it:
- **Untrained spots:** spots without trained rows grow sharply with table size (against pot-pressure, river 2.3% → 18.3% of decisions).
- **Learned lines that fail:** the bot opens or calls and then folds to a re-raise, and goes all-in below equity.

A passive fallback didn't help (−4.3 [−9.2, +0.6]).

**The hypothesis:** self-play rarely produces repeated pot-sized raises, so the bot neither visits nor learns good answers to them. Training against opponents that sometimes add a pot-size raise should teach those answers.

## The training change

`nplayer_train --opponent-pot-raise 0.05`, a fast-mode-only option recorded in the checkpoint as `opponent_pressure` (`opponent-pot-raise-v1`):
- **When it fires:** at every sampled decision of a seat other than the current traverser where the menu has a raise, with probability 0.05.
- **What it plays:** the opponent takes the menu's pot-size raise (label 4, or label 3 when the pot raise equals the minimum raise) instead of sampling its policy.
- **Draws:** the 0.05 draw is a separate, domain-separated path draw, so the policy draw is unchanged when pressure doesn't fire.
- **What is unchanged:**
  - **the recorded policy:** average strategies still accumulate the table policy at opponent nodes, so the exported model is still the bot's own policy;
  - **the traverser:** it still enumerates every action;
  - **the deals** are the same.

The training game is deliberately changed: each seat learns against slightly more aggressive opponents. Without the option, the trainer's output bytes are unchanged.

## Arms

| Arm | Model |
|---|---|
| Control | #417's six-player 10B, SHA256 `086938a8…c46178` |
| Pressure | The same recipe from scratch: seed 2026102361001, fast mode, 8 roots per seat, 250M entries with whole-iteration freeze, average scope 3, trained to 10B nodes, plus `--opponent-pot-raise 0.05` |

Only the 10B endpoint exists and is evaluated; no checkpoint is chosen.

## Qualification before training (the run stops on any failure)

1. **Legacy parity:** without the option, the branch trainer and a `main` build produce byte-identical 100M-node checkpoints.
2. **Determinism:** with the option at 0.05, 16 and 8 threads produce byte-identical 100M-node checkpoints. They differ from the run without pressure, and they record a positive `pressured_actions`.
3. **Pipeline:** export, average-mass audit, binary conversion and binary verification pass, as for #417.

## Evaluation

- **Fields:** #417's eight fields with its opponents, including #417's 3B in the trained fields.
- **Design:** paired arena, control against pressure as the focal player.
- **Deals:** four fresh banks per field of 4,096 deal blocks × 12 seatings, with new roots `20261025900000 + 100·bank + field index`.
- **Scoring:** results are scored realized and all-in adjusted, as in #426. The adjusted result is the decision quantity.

**Decision rule, fixed now:**
- **Primary:** the pot-pressure paired change (pressure minus control), all-in adjusted, pooled over the four banks (16,384 blocks). **Improved** if its 95% Student-t lower bound is above 0; otherwise **not shown**.
- **Mechanism:** the share of focal decisions with no trained row (missing or zero-mass) against pot-pressure, compared by arm.
- **Harm flags:** for the other seven fields, Bonferroni 95% intervals over seven tests. A field whose upper bound is below 0 is flagged as harmed.
- **Also reported:**
  - **descriptive:** absolute adjusted returns of both arms per field, per-bank estimates, and the training telemetry (iterations, entries, freeze iteration, pressured actions).

A positive result would justify confirmation with more seeds. It doesn't promote anything, and one lineage cannot separate the change from seed-to-seed variation.

## Rules

- **Host:** bb128, 16 threads, alongside #425. Stops: CPU 90 °C, VRM (Thermistor 15) 100 °C.
- **Disk:** about 55 GB of working files on the HDD under `/mnt/data2tb/nplayer-six-player-pressure-20261025/`. Inputs are read only.
- **Failures:**
  - A research failure (for example the primary not shown, or harm flagged) is reported as is, with no retry, retuning or extra hands.
  - A qualification failure stops the run before training.
  - Plumbing problems go in the PR for the owner.
- **Evidence:** compact results go in Git; working files stay on bb128 for the vacuum cleaner.
