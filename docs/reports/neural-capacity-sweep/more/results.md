# More rows: do bigger advantage networks pay off?

This is the third exploration on the [capacity sweep](../results.md)'s question: one seed and a quick read, not a gate.
- **Data:** a new seeded subsample of 13.5M rows from the 19M-row HDD copy of the pilot's advantage reservoir after iteration 122:
  - 13,000,467 training rows (5.65M warm);
  - 499,533 held-out rows.
- **Fits:** on the M4 (base M4 MacBook Pro, 16 GB, MPS) on November 10, 2026, from 04:53 to 11:00 UTC. Each fit got 20,000 steps at the pilot's settings.

The 4.5M-row fits use a seeded, nested part of the same training rows. Every fit is scored on the same new held-out rows, so these numbers compare with each other, not with the earlier sweep's.

## Answer

**With more rows, the bigger network starts to win, but rows matter much more than size.**

Errors are on held-out rows; lower is better.

| Network | Training rows | Error | Best during the fit | Deep CFR rows | Warm rows | River | TV | Minutes on the M4 |
|---|---|---|---|---|---|---|---|---|
| `mlp-2m` | 4.5M | 827 | 817 (step 12,000) | 1365 | 127 | 1285 | 0.386 | 14 |
| `mlp-13m` | 4.5M | 859 | 830 (step 12,000) | 1419 | 130 | 1332 | 0.368 | 94 |
| `mlp-2m` | 13M | 681 | 681 (step 20,000) | 1122 | 106 | 1041 | 0.382 | 17 |
| `mlp-13m` | 13M | **660** | **660** (step 20,000) | **1084** | 108 | **1012** | **0.360** | 97 |
| `cards-15m` | 13M | 697 | 697 (step 20,000) | 1153 | **103** | 1046 | 0.373 | 141 |

- **Going from 4.5M to 13M rows** cuts held-out error by 18% for `mlp-2m` and by 23% for `mlp-13m`.
- **The order flips with more rows:**
  - at 4.5M rows, `mlp-13m` is 3.8% worse than `mlp-2m` (1.6% worse at their best points), and it overfits after step 12,000;
  - at 13M rows, it's 3.0% better overall, 3.4% better on the Deep CFR rows and 2.8% better at the river, with a 6% lower TV.
- **Card embeddings lose their edge.** `cards-15m` is worse than `mlp-2m` at 13M rows (697 against 681). It was 5–7% better at 1.5M rows and 1.4% better at 4.5M. It helps when data is scarce, not at scale.
- **The fits at 13M rows were still improving slightly at step 20,000,** so more steps would help all of them a little.

Overfitting at 13M rows, on Deep CFR rows (training error against held-out error):

| Network | Training | Held out |
|---|---|---|
| `mlp-2m` | 843 | 1122 |
| `mlp-13m` | 682 | 1084 |
| `cards-15m` | 963 | 1153 |

At 4.5M rows, `mlp-13m` reached 344 on its training rows against 1,419 held out.

## By street and player count (held out, 13M rows)

| Network | Preflop | Flop | Turn | River | 3p | 4p | 5p | 6p |
|---|---|---|---|---|---|---|---|---|
| `mlp-2m` | 173 | 674 | 1064 | 1041 | 724 | 665 | 721 | 637 |
| `mlp-13m` | 161 | 646 | 1046 | 1012 | 699 | 634 | 707 | 620 |
| `cards-15m` | 189 | 701 | 1091 | 1046 | 727 | 675 | 753 | 655 |

`mlp-13m`'s gain over `mlp-2m` is spread over every street and player count, 2–7%.

## What this means for the next Deep CFR run

1. **Rows first.** The pilot's advantage reservoir held 30M rows. Keep it at least that large, and fit on all of it: this is the 18–23% lever.
2. **A bigger network is a second-order gain** of about 3% at 13M rows, likely more at 30M. But Deep CFR evaluates the advantage network inside every traversal, so a 6× larger network costs traversal speed as well as fit time. Before choosing `mlp-13m`, measure the Rust traversal throughput with it. Until then, `mlp-2m` is the default.
3. **Drop card embeddings for now.** They don't help at this scale, and Rust can't play them.

## Limitations

- **One seed.** The 3% difference between `mlp-13m` and `mlp-2m` at 13M rows is small. #478's two plain networks agreed within 0.2% at 4.5M rows, which suggests the noise between runs is smaller than 3%, but that wasn't measured.
- **Rows from early in the pilot only** (up to iteration 122). There was no tuning per network, and the step count was fixed.
- **Offline only:** a better fit isn't better play.
- **Plumbing:**
  - the 8.4 GB copy from bb128 to the M4 was relayed through a third Mac at about 0.5 MB/s, and took 4¼ hours;
  - every file's hash matched bb128's.

## Files

- [`report.json`](report.json): the table above.
- [`subsample.json`](subsample.json): the source and the hashes.
- `<run>/result.json`: every split, the curve, and the weight hash.
- `<run>/run.log`: the run's progress lines.

| | SHA-256 |
|---|---|
| Training rows | `00dc0d49…7c8` |
| Held-out rows | `50c830d4…9a818` |

The weights stay on the M4 under `~/neural-capacity-sweep-20261109/runs-more/`:

| Run | Weights SHA-256 |
|---|---|
| `mlp-2m-r4.5m` | `f3659605…0ebf` |
| `mlp-2m-r13m` | `3869cafe…339c` |
| `mlp-13m-r4.5m` | `2a4408c6…18a6` |
| `mlp-13m-r13m` | `355c5620…5da6` |
| `cards-15m-r13m` | `bd18fb1d…d39d` |
