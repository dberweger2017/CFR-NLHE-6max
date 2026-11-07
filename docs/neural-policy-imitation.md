# Can a network imitate the blueprint where it never trained? Protocol

Committed before any export, training or evaluation. Step 2 of the [neural-policy track](../ROADMAP.md), on [step 1's data](neural-policy-data.md).

## Question

A small network learns the live `widemix`'s strategy (#458 run 1) from the spots where it has a trained row. On spots where `widemix` run 1 has no row but another teacher does, does the network predict that teacher's strategy better than uniform random, the fallback the client plays today?

## Why this test

A table answers only the spots it trained, so the network has to generalize. [Step 1](reports/neural-policy-data/results.md) found that away from six-player short tables, other teachers trained on a third to two thirds of `widemix` run 1's postflop gaps: `widemix` runs 2 and 3, and `widecap` run 1, the 400M-entry model. Their strategies there are real labels for spots the network never saw labeled.

This only tests imitation. Whether the network's choices win chips is step 3's question.

## Data

Exported with `nplayer_features` from step 1, with the same four teachers and the same pins. `widemix` run 1 plays every model seat.

| Split | Jobs | Hands | Roots |
|---|---|---|---|
| train | wide grid at 3, 4, 5 and 6 players; fields: self-play, mixed, and each of the four scripts | 2.4M | `20261108400000 + 1000·job` |
| test-wide | the same jobs, fresh deals | 120,000 | `20261108500000 + 1000·job` |
| test-short | #461's seven short tables, each with its fields | 3,000 per job | `20261108600000 + 1000·job` |

- **Hand counts by player count:** 6 players have twice the hands of 3, 4 or 5, as in step 1.
- **Training data:** only samples where `widemix` run 1 has a positive-mass row, with its strategy as the target.
- **Never used for training:** the test splits, the other teachers' strategies, and every spot where `widemix` run 1 has no trained row.
- **Unseen tables:** the short tables never appear in training. Their stack configurations are fixed tables the wide grid deals only rarely.

## Model and training, fixed now (no tuning)

- **Network:** an MLP with layers 612 → 1024 → 1024 → 512 → 6 and ReLU activations. Illegal labels are masked to −∞ before the softmax.
- **Loss:** cross-entropy against the teacher's distribution.
- **Optimizer:** AdamW, learning rate 1e-3 with cosine decay to 0, weight decay 1e-4.
- **Schedule:** batch 8,192, 4 epochs, float16 mixed precision on bb128's RTX 2070 SUPER.
- **Three training seeds** (`1`, `2`, `3`) on the same data. Each is reported separately; the data seed is fixed by the roots.

## Measure

Total variation is TV(p, q) = ½ Σ |p − q| over the legal labels. Uniform means 1 / (number of legal labels) on each legal label.

- **Rescue set (primary):** test samples where `widemix` run 1 is untrained (zero mass or no row) and at least one other teacher has a positive-mass row. The target is the mean of those teachers' strategies.
- **Primary contrast:** TV(network, target) − TV(uniform, target), averaged over the rescue samples of test-wide and the 3- and 4-player test-short tables, pooled.
  - Intervals cluster by hand: each hand's mean difference is one observation, and a Student-t 95% interval is taken over hands.
  - The six-player short tables are reported, not pooled. Step 1 found only 5–15% of their gaps covered by any teacher, too few for a fair pool.

## Decision rule

**Passes** if, for **every** training seed, the primary contrast's 95% upper bound is below **−0.05**: the network is at least 5 points of TV closer to the other teachers than uniform is. Then step 3 (the network as the missing-row fallback, in play) gets a protocol. **Otherwise it fails,** and the result is reported as is, with no retraining or tuning.

## Also reported

- **Fidelity on trained spots:** TV(network, `widemix` run 1) where run 1 has a positive row, on test-wide and test-short.
- **Seed noise:** TV(teacher k, `widemix` run 1) where both are trained, on the same samples. This is how much the tables themselves disagree, a floor no imitation should be expected to beat.
- **The rescue contrast by street, split and player count**, including the six-player short tables.
- **Top-label agreement**, and training loss per epoch.
- **Costs:** export time, training time, sizes and pins of the weights and data files.

## Rules

- **Host:** bb128, all 16 threads for the export and the 2070 SUPER for training. Stop below 4 GB of available memory or at a CPU of 90 °C. One job at a time.
- **Disk:** about 18 GB of samples on the NVMe, which had 81 GB free at commit time.
- **Failures:** a research failure is reported as is. Plumbing failures go in the PR.
