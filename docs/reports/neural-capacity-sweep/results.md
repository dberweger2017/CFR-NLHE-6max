# Advantage-network capacity sweep: results

This is an exploration run of [the sweep](../../neural-capacity-sweep.md): one seed and a quick read, not a gate. It ran on November 9, 2026:
- **Subsample:** taken on bb128.
- **Fits:** the M4 MacBook Pro (base M4, 16 GB, MPS, torch 2.15) fitted the networks one after another, from 15:10 to 18:36 UTC.

## Answer

**The advantage network is too small at 0.5M parameters, but it isn't the main limit beyond about 2M parameters.**
- **Going from 0.5M to 2M parameters** cuts held-out error by 9% (by 10% on the Deep CFR rows).
- **Beyond 2M, a bigger network mostly memorizes the noise in the sampled regrets.** Learned card embeddings gain a little more, but adding width or depth gains nothing.

All errors below are on held-out rows, so lower is better. The unit is squared big blinds summed over the legal labels.

| Network | Parameters | Error | Weighted (the loss) | Warm rows | Deep CFR rows | River | TV to target policy | Minutes on the M4 |
|---|---|---|---|---|---|---|---|---|
| `mlp-0.5m` (the pilot's) | 0.48M | 916 | 569 | **109** | 1538 | 1477 | 0.412 | 3.5 |
| `mlp-2m` | 2.2M | 835 | 526 | 115 | 1390 | 1317 | 0.393 | 7.3 |
| `mlp-13m` | 12.8M | 836 | 528 | 118 | 1390 | 1312 | **0.370** | 47 |
| `res-15m` | 15.1M | 857 | 537 | 112 | 1431 | 1346 | 0.399 | 71 |
| `cards-15m` | 15.5M | **823** | **517** | 110 | **1373** | **1275** | 0.388 | 72 |

## Overfitting: training rows against held-out rows

The training error is measured on a seeded uniform sample of 499,900 training rows, as many rows as the held-out set.

| Network | Training: Deep CFR rows | Held out: Deep CFR rows | Training: warm rows | Held out: warm rows |
|---|---|---|---|---|
| `mlp-0.5m` | 1180 | 1538 | 89 | 109 |
| `mlp-2m` | 816 | 1390 | 82 | 115 |
| `mlp-13m` | **572** | 1390 | 74 | 118 |
| `res-15m` | 931 | 1431 | 87 | 112 |
| `cards-15m` | 967 | 1373 | 87 | 110 |

From 2M to 13M parameters, training error on the Deep CFR rows falls by 30%, but held-out error doesn't move. `mlp-13m` reached its best held-out error at step 7,000 (830) and then got slightly worse. On the warm rows every network bigger than the pilot's does worse held out.

So the targets are noisy enough that a bigger plain network fits the noise, not the signal. **For this data, sample noise limits the fit, not network size.**

`cards-15m` overfits least and generalizes best. The structure it adds (cards as cards, not 52 separate input bits) helps a little, most at the river (−3% against `mlp-2m`).

## By street and by player count (held out)

| Network | Preflop | Flop | Turn | River | 3p | 4p | 5p | 6p |
|---|---|---|---|---|---|---|---|---|
| `mlp-0.5m` | 210 | 822 | 1423 | 1477 | 968 | 899 | 968 | 859 |
| `mlp-2m` | 201 | 772 | 1310 | 1317 | 868 | 813 | 886 | 794 |
| `mlp-13m` | 202 | 771 | 1323 | 1312 | 880 | 818 | 883 | 789 |
| `res-15m` | 208 | 804 | 1339 | 1346 | 887 | 839 | 921 | 806 |
| `cards-15m` | 221 | 763 | 1284 | 1275 | 857 | 804 | 881 | 776 |

The 0.5M → 2M gain is spread evenly across streets and player counts. Larger regrets on later streets carry most of the error.

## What this means for the next Deep CFR run

1. **Use the 2M network (1024-1024-512) for the advantage network.** It's the clear, cheap gain. The Rust engine can play it today: it's the strategy network's shape. It costs about 2× the fit time of the pilot's network.
2. **Don't rent a GPU to fit a 15M network.** On this data, it would mostly memorize noise.
3. **The bigger lever is less noisy targets.** Options:
   - more traversals per iteration;
   - a baseline or variance reduction in the sampled regrets;
   - more rows per fit: the pilot's reservoir held 30M rows, and this sweep used 4.5M.
4. **Card embeddings are a possible later step,** not a next one. They gained 1.4% overall and 3% at the river, but Rust inference would need the new architecture.

## Limitations

- **One seed and one subsample,** from early in the pilot (iteration 122 of 309). Later Deep CFR rows, for example from PR477's snapshots, may be noisier, and more rows may favor bigger networks.
- **Each fit got 10,000 steps** at the pilot's learning rate, with no tuning per architecture. The residual networks might do better with tuning.
- **The error has an unknown noise floor.** Differences between networks matter, not the level.
- **A better offline fit isn't better play.** Nothing was played.
- **First version of the overfitting column:** the run script first measured training error on the subsample's first rows, which are all warm rows (the subsample keeps the reservoir's order). That made overfitting look extreme (training error 33–41). The `rescore` command re-scored the saved weights on a uniform training sample. It reproduced every held-out number, so they're unchanged. The first-rows numbers stay in each `result.json` as `train_rows_first_rows`.

## Files

- [`report.json`](report.json): the table above.
- `runs/<network>/result.json`: every split, the training curve, and the weight hash.
- `runs/<network>/run.log`: the run's progress lines.
- [`subsample.json`](subsample.json): the subsample's source and its hashes.

| | |
|---|---|
| Training rows | 4,500,100 (1,953,727 warm), SHA-256 `ca533aa0…a67` |
| Held-out rows | 499,900 (217,600 warm), SHA-256 `914ac40b…4ad4` |

The weights stay on the M4 at `~/neural-capacity-sweep-20261109/runs/`. Their SHA-256s:

| Network | Weights SHA-256 |
|---|---|
| `mlp-0.5m` | `161edf20…ef67` |
| `mlp-2m` | `4e52a095…e7d9` |
| `mlp-13m` | `1be376df…75b4` |
| `res-15m` | `97f9c2b3…6d06` |
| `cards-15m` | `0bfa2f32…4a28` |
