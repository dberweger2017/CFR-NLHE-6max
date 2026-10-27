# Heads-up routes: results

This is a run of [the protocol](../../openpoker-heads-up.md), committed before training. It was one lineage per model on bb128, from source `16a877f9`, with [controller](run.sh), [guard](guarded.sh) and [launcher](after-routing.sh). The launcher started the run when the routing study's controller exited. The data files are [`results.json`](results.json) (every field, interval and missing share) and [`fields.csv`](fields.csv).

All values are BB/100, all-in adjusted, over 4 banks × 4,096 blocks. Each contrast is `humix` minus `hu100`, with both models seen through the projected view.

## Primary results

| Table | Primary field | `humix` − `hu100` | Decision interval | Verdict |
|---|---|---|---|---|
| `100bb` | `hu100` | −5.4 | [−17.4, +6.5] | inconclusive |
| `50bb` | `humix` | +152.0 | [+134.8, +169.1] | mixed better |
| `20bb` | `humix` | +107.6 | [+97.5, +117.7] | mixed better |
| `200bb` | `humix` | +155.0 | [+121.7, +188.4] | mixed better |
| `unequal-a` (150 / 40) | `humix` | +122.8 | [+107.7, +137.9] | mixed better |
| `unequal-b` (250 / 100) | `humix` | +111.2 | [+89.2, +133.2] | mixed better |

**Route under the prespecified rule:** `hu100` when both stacks are within the routing study's **[89.4, 136.9] BB** band, and `humix` otherwise.
- **Why not `humix` everywhere:** the first condition, "mixed adequate at 100 BB", isn't shown. The lower bound, −17.4, crosses the 10 BB/100 margin.
- **The band rule applies** because no depth table reads "fixed better".

## What the numbers say

- **Away from 100 BB, `hu100` collapses against `humix`.** It loses 108–156 per 100 hands, while `humix` breaks even against itself (−0.9 to +7.8). `humix` also beats `hu100` on every script field at every off-depth table: +11 to +134.
- **At 100 BB the two are close:**
  - −5.4 against `hu100` copies;
  - +1.9 against `humix` copies;
  - between −7.4 and +22.6 against the scripts.

  No other field's interval excludes zero, and there are no harm flags. `humix` may be adequate at 100 BB, but this run can't show it at the protocol's margin.
- **Missing shares** (all streets):

  | Table | `hu100` | `humix` |
  |---|---|---|
  | `100bb` | 0.0% | 0.0% |
  | `50bb` | 35.7% | 0.0% |
  | `20bb` | 58.9% | 0.0% |
  | `200bb` | 12.6% | 0.0% |
  | `unequal-a` | 40.3% | 0.0% |
  | `unequal-b` | 14.6% | 0.0% |

- **Size:** heads-up mixing costs far less than six-handed.
  - `humix` used 39.1M entries, with no freeze, and its binary is 2.16 GB.
  - `hu100` used 4.18M entries, and its binary is 0.24 GB.

## Checks and costs

- **Qualification:**
  - the library and paired-arena host tests passed on bb128;
  - six-player fixed training at 100M is still `482a0f8f…`;
  - the heads-up mixture at 100M is byte-identical at 16 and 8 threads (`f7e3f205…`);
  - the smoke run passed.
- **Models:**

  | Model | Checkpoint | Binary |
  |---|---|---|
  | `hu100` | `8ed5bfb5…` | `1722f0d8…` |
  | `humix` | `06048267…` | `9d39dda9…` |

  Training drew each of the 13 depths for about 4.92M seats.
- **Replay:** all 62 bank-0 traces (507,904 hands) replay independently.
- **Fallbacks:** no fallback violations.
- **Run:** 19:01–20:14 UTC, 1 h 13 min.

  | Stage | Duration |
  |---|---|
  | Build and qualification | 3 min |
  | Smoke | 3 min |
  | `hu100` training | 24 min, plus 1 min of export, audit and conversion |
  | `humix` training | 30 min, plus 5 min of export, audit and conversion |
  | Arena | 4 min |
  | All-in equity | 3 min |

- **Resources:**
  - CPU peaked at 74 °C and VRM at 75 °C.
  - Memory peaked at 8.0 GB.
  - Free space on the HDD stayed at 65 GB or more.
- **Disk:** about 11 GB under `/mnt/data2tb/openpoker-heads-up-20261027/`.
- **No plumbing failures.**
