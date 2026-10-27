# Phantom folds and stack depth: results

This is a run of [the protocol](../../openpoker-phantom-depth.md), committed before training. It was one lineage on bb128, from source `f4b011fa`, with [controller](run.sh) and [guard](guarded.sh). The data files are [`results.json`](results.json) (every field, interval and missing share) and [`fields.csv`](fields.csv).

All values are BB/100, all-in adjusted, over 4 banks × 4,096 blocks. Each contrast is arm 1 minus arm 0. Decision intervals use the protocol's Bonferroni corrections.

## Phantom folds: inconclusive at all three sizes

The primary contrast is `six` through phantom folds minus the dedicated `pN`, on a field of `pN` copies. The non-inferiority margin is 10.

| Players | Change | Decision interval | Verdict | Harm flags |
|---|---|---|---|---|
| 3 | −13.3 | [−26.0, −0.6] | inconclusive | none |
| 4 | −6.9 | [−18.0, +4.4] | inconclusive | none |
| 5 | −0.7 | [−10.3, +9.0] | inconclusive | none |

- **What it means:** no size meets "phantom adequate". Under the prespecified rule, the router uses the dedicated model at 3, 4 and 5 players, and those three models are now trained. Nor does any size show "dedicated needed": no upper bound falls below −10.
- **By size:** the deficit shrinks as the table fills. At 3 players `six` is likely worse than `p3`, since the interval excludes 0, but it isn't shown to be worse by more than 10. At 5 players the lower bound misses the margin by 0.26.
- **Other fields:** no harm flags. The only intervals that exclude zero are on the `random` field: +39.4 at 3 players and −35.7 at 5.
- **Missing shares** are almost equal for both arms at each size: 0.0% / 0.0% overall at 3 players, 3.4% / 3.2% at 4, and 8.3% / 7.5% at 5. Phantom folds don't push `six` off its trained rows; the deficit is in what those rows say.

## Stack depth: a model loses about 50 BB/100 away from its training depth

The primary contrast is `six50` minus `six`. Each model plays through the projected view where it wasn't trained.

| Table | Primary field | Change | Decision interval | Verdict |
|---|---|---|---|---|
| `50bb` | `six50` copies | +49.9 | [+43.0, +56.8] | 50 BB model better |
| `100bb` | `six` copies | −55.1 | [−65.9, −44.4] | 100 BB model better |
| `unequal` | `mixed` | +18.4 | [−3.1, +39.9] | no difference shown |

- **The cost is symmetric:**
  - Against copies of the model trained at that depth, `six` at 50 BB scores −50.8 and `six50` scores −0.9.
  - At 100 BB, `six` scores +2.7 and `six50` scores −52.4.
- **The direction holds against the scripts:** at `50bb` all five other fields favor `six50`, four of them with intervals above 0. At `100bb`, four of five favor `six`. The largest single gap is against `pot-pressure`:

  | Model | At 50 BB | At 100 BB |
  |---|---|---|
  | `six` | −40.6 | +32.7 |
  | `six50` | +21.5 | −6.9 |

- **Missing shares rise off-depth:**
  - `six` at 50 BB: 24.3% overall (flop 60%), against 10.6% for `six50`.
  - `six50` at 100 BB: 22.6%, against 12.1% for `six`.
- **The unequal table** (100/50/150/75/100/200 BB) separates neither model. Both miss about 30% of decisions, rising to 75–86% after the flop.

## What this decides

- **Routing by player count:** use the dedicated `p3`, `p4` and `p5` at 3–5 players, per the rule. Phantom folds are the fallback for a size without a dedicated model.
- **Depth:** playing at the wrong depth costs about 50 BB/100, far above the protocol's 10 BB/100 margin. The bot doesn't leave and rejoin, so a single fixed-depth model isn't enough. This motivates the mixed-stack training in #447. That model is six-player only; 3–5 players would need dedicated mixed-stack models later.
- **No releases, defaults or promotions.**

## Qualification and checks

- **Qualification:**
  - The branch reproduced the live-order 100M checkpoint `482a0f8f…`.
  - The projection and paired-arena tests passed.
  - `six`'s binary and mass receipt matched their pins.
- **Training:** each model reached 10B nodes, using 18.1M (p3), 29.1M (p4), 34.8M (p5) and 26.8M (six50) entries. All stayed under the 250M cap, with no freeze.

  | Model | Checkpoint | Binary |
  |---|---|---|
  | `p3` | `616bc02d…` | `1a607613…` |
  | `p4` | `389cec2f…` | `66ec2f87…` |
  | `p5` | `0d443f07…` | `bdc5ab50…` |
  | `six50` | `9702f5d5…` | `fbb5212b…` |

- **Replay:** all 70 bank-0 traces (1,425,408 hands) replay independently in the reference engine.
- **Fallbacks:** no fallback violations in any receipt; the report refuses to run otherwise.

## Costs

| Stage | Time (UTC) | Duration |
|---|---|---|
| Build and qualification | 07:25–07:27 | 2 min |
| Smoke (three attempts, see below) | 07:27–07:40 | 13 min |
| Training: `p3`, `p4`, `p5`, `six50` | 07:40–09:32 | 24, 23, 25, 26 min (plus export, audit and conversion) |
| Arena, scan and replay, 4 banks | 09:32–09:47 | 15 min |
| All-in equity | 09:47–11:27 | 1 h 40 min |
| **Total** | | **4 h 2 min** |

- **Resources:**
  - CPU peaked at 76 °C and VRM at 76 °C, under the 90 °C and 100 °C stops.
  - Memory peaked at 8.5 GB.
  - Free space stayed at 60 GB or more on the NVMe and 135 GB or more on the HDD.
- **Disk:** about 21 GB under `/mnt/data2tb/openpoker-phantom-depth-20261027/`.

## Plumbing problems

Two plumbing failures in the smoke stage were fixed and relaunched; no results were affected. Each attempt's stderr is kept on bb128.
- **Models path:** the controller resolved `smoke/out/../models.json` before `out/` existed. It now uses `$(dirname $O)`.
- **Position names:** the trace scanner lacked 3-player position names. Fixed in `f4b011fa`; the smoke outputs from the failed attempt were deleted before relaunch.
