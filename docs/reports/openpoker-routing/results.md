# Depth band and short-handed routes: results

This is a run of [the protocol](../../openpoker-routing.md), committed before running. It was one evaluation on bb128, from source `a4cd3b24`, with [controller](run.sh) and [guard](guarded.sh). The data files are [`results.json`](results.json) (every field, interval and missing share) and [`fields.csv`](fields.csv).

All values are BB/100, all-in adjusted, over 4 banks × 4,096 blocks. Each contrast is `mix` minus the fixed model. Decision intervals are Bonferroni 95%: over the five band tables, or over the nine short tables.

## Routes under the prespecified rules

- **Six-handed:** `six` when every dealt stack is within **[89.4, 136.9] BB**, and `mix` otherwise.
- **3, 4 and 5 players:** `p3`, `p4` and `p5` within the same band, and `mix` otherwise.
- **No adverse findings:** `mix` beats the dedicated models at 50 BB and at unequal stacks for every size.

## Six-handed band (`six` vs `mix`, primary field `mixed`)

| Table | `mix` − `six` | Decision interval | Verdict |
|---|---|---|---|
| `65bb` | −9.6 | [−29.5, +10.3] | no difference shown |
| `80bb` | −16.9 | [−40.8, +6.9] | no difference shown |
| 100 BB (#447) | −14.6 | [−22.2, −7.0] | fixed better |
| `125bb` | −39.0 | [−74.4, −3.5] | fixed better |
| `150bb` | −25.2 | [−64.9, +14.5] | no difference shown |
| `near-100` (80–125, unequal) | +28.0 | [−0.6, +56.6] | no difference shown |

- **How the band grows:** from 100 BB, 80 doesn't read "fixed better", so the band stops below 100. 125 does, so it is included, and 150 doesn't. The band is {100, 125}, with edges at the geometric midpoints √(80·100) = 89.4 and √(125·150) = 136.9.
- **Near-100 check:** it doesn't apply, because the band doesn't contain 80. `near-100` leans toward `mix` (+28.0), and `mix` wins on all three of its other fields (+20 to +34).
- **Caveat:** the band rests on the primary field. On the other fields between 80 and 150 BB the picture is mixed: `mix` is ahead at 150 BB on all three, behind at 125 BB against `mix` copies (−13.1), and level elsewhere. The point estimates against `mixed` favor `six` at every equal depth from 65 to 150 BB. That field is two check-call, two pot-pressure and one tight-aggressive.
- **Away from the band, at 65 BB:** `mix` wins on every other field: +21.8 against `mix` copies, +42.4 against `pot-pressure` and +17.4 against `tight-aggressive`.

## Short-handed (`pN` vs `mix` through phantom folds)

| Players | 100 BB (`pN` copies) | 50 BB (`mixed`) | Unequal (`mixed`) |
|---|---|---|---|
| 3 | −25.4 [−40.4, −10.5], fixed better | +33.8 [+17.5, +50.1], mixed better | +80.8 [+60.9, +100.6], mixed better |
| 4 | −25.9 [−38.9, −12.8], fixed better | +29.8 [+16.6, +43.0], mixed better | +57.2 [+42.0, +72.4], mixed better |
| 5 | −21.1 [−33.0, −9.3], fixed better | +31.7 [+17.3, +46.1], mixed better | +80.9 [+62.3, +99.5], mixed better |

- **At 100 BB** the dedicated model wins by 21–26.
- **At 50 BB and at unequal stacks,** `mix` wins by 30–81 at every size, and on every other field (+20 to +51).

## Missing shares

These are decisions without a positive-mass row, averaged over a table's fields.
- **At the six-player tables,** both models are low: 1.1–4.4% for `six` and 2.7–3.8% for `mix`. The one exception is `near-100`, where `six` misses 11.7%.
- **At 3–5 players:**

  | Model | 100 BB | 50 BB | Unequal |
  |---|---|---|---|
  | `pN` | 0.0–0.1% | 11.2–20.3% | 22.5–31.5% |
  | `mix` | 0.2–1.2% | 0.2–1.2% | 0.2–1.2% |

These tables' fields are mostly scripts, so the shares are lower than in the earlier studies, whose fields included model copies. Compare them only within this study.

## Checks and costs

- **Qualification:**
  - the models' binaries and mass receipts matched their pins;
  - the paired-arena host tests passed;
  - the smoke run passed.
- **Replay:** all 94 bank-0 traces (1,867,776 hands) replay independently.
- **Fallbacks:** no fallback violations.
- **Run:** 17:40–19:01 UTC, 1 h 21 min.

  | Stage | Duration |
  |---|---|
  | Qualification | 4 min |
  | Smoke | 2 min |
  | Arena | 23 min |
  | All-in equity | 51 min |

- **Resources:**
  - CPU peaked at 75 °C and VRM at 76 °C.
  - Memory peaked at 23.9 GB.
  - Free space on the HDD stayed at 70 GB or more.
- **Disk:** about 22 GB under `/mnt/data2tb/openpoker-routing-20261027/`, 18 GB of it decompressed model copies.
- **No plumbing failures.**
