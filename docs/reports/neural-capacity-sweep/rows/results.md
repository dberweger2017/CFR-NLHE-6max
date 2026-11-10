# Rows or noise? Advantage-network fits on fewer rows

This is a follow-up to the [capacity sweep](../results.md): one seed and a quick read, not a gate. It ran on the M4 (base M4 MacBook Pro, 16 GB, MPS) on November 9, 2026, from 19:30 to 21:10 UTC, on the sweep's rows and settings.

## Answer

**The advantage fit is limited by the number of rows. Noise alone isn't the wall.** Each tripling of training rows cuts held-out error by 20–25%, and the curve hasn't flattened at 4.5M rows. With fewer rows, both networks memorize their training rows.

So the sweep's finding that bigger networks don't help applies at 4.5M rows. It may not hold with many more rows.

Errors are on held-out rows; lower is better. "Best during the fit" is the lowest held-out error among the 10 checks, which is what early stopping would keep.

| Network | Training rows | Final error | Best during the fit | Deep CFR rows | Warm rows | River | TV | Training error, Deep CFR rows |
|---|---|---|---|---|---|---|---|---|
| `mlp-2m` | 0.5M | 1538 | 1301 (step 1,000) | 2569 | 200 | 2526 | 0.427 | 60 |
| `mlp-2m` | 1.5M | 1134 | 1043 (step 3,000) | 1894 | 150 | 1819 | 0.405 | 359 |
| `mlp-2m` | 4.5M | 835 | 835 (step 10,000) | 1390 | 115 | 1317 | 0.393 | 816 |
| `cards-15m` | 1.5M | 1052 | 997 (step 4,000) | 1755 | 139 | 1647 | 0.398 | 485 |
| `cards-15m` | 4.5M | 823 | 823 (step 9,000) | 1373 | 110 | 1275 | 0.388 | 967 |

The 4.5M-row fits are the sweep's runs.

**Card embeddings help most when rows are scarce.** At 1.5M rows `cards-15m` is 5–7% better than `mlp-2m` (best 997 against 1043; final 1052 against 1134). At 4.5M rows it's only 1.4% better. The embeddings make the network more sample-efficient, but the advantage shrinks as rows grow.

**Follow-up:** with [13M rows](../more/results.md), `mlp-13m` beats `mlp-2m` by 3.0%, and card embeddings no longer help.

## Huber loss

`mlp-2m` on 4.5M rows, with the loss quadratic up to 20 BB per label and linear beyond.

| Loss | Error | Weighted | Deep CFR rows | Warm rows | River | TV |
|---|---|---|---|---|---|---|
| Squared error (the pilot's) | **835** | **526** | **1390** | 115 | **1317** | 0.393 |
| Huber, 20 BB | 867 | 541 | 1453 | **107** | 1351 | **0.371** |

**The result is mixed.** Huber is 4% worse on squared error. That's expected, since both the metric and the targets favor the plain mean. But it's better on the low-noise warm rows, and its regret-matched strategy is closer to the targets' (TV 0.371, as good as `mlp-13m`). It's not a clear win, so the pilot's loss stays. Huber is worth a play test only if TV turns out to matter more than squared error.

## What this means

1. **More rows per fit is a real lever.** The pilot's advantage reservoir held up to 30M rows, more than this subsample. Before the next Deep CFR run, the open question is whether the bigger networks start to pay off at 15–30M rows.
2. **Use `mlp-2m` for now.** It's the right size at 4.5M rows. A bigger network is worth revisiting only once a fit with many more rows shows a gain.
3. **Card embeddings are the sample-efficient option.** They're worth more for small reservoirs, for example per-player-count or per-street fits.

## Limitations

- **One seed and nested subsets of one subsample.** No tuning per run.
- **Fixed 10,000 steps:** smaller row sets get more passes over the data. The "best during the fit" column shows the trend holds with early stopping too.
- **The held-out error includes a noise floor nobody knows.** The rows trend says it isn't reached at 4.5M rows.
- **Offline only;** nothing was played.
- **Plumbing:** the first `run.sh rows` stopped at the Huber run. macOS bash 3.2 treats an empty argument array as unbound under `set -u`. The runner now passes `--rows 0` (every row), and the restart skipped the two finished fits.

## Files

- [`report.json`](report.json): every fit above.
- `<run>/result.json`: splits by source, street and player count, the training curve, and the weight hash.
- `<run>/run.log`: the run's progress lines.

The weights stay on the M4 under `~/neural-capacity-sweep-20261109/runs-rows/`:

| Run | Weights SHA-256 |
|---|---|
| `mlp-2m-r0.5m` | `0e66c1a5…ba30` |
| `mlp-2m-r1.5m` | `6c8fd160…6cdc` |
| `mlp-2m-huber20` | `72f998bd…cddb` |
| `cards-15m-r1.5m` | `dd85a8fa…fac2` |
