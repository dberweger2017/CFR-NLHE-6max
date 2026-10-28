# Mixed-stack models for 3, 4 and 5 players: results

This is a run of [the protocol](../../openpoker-short-mixed.md), committed before training. It was one lineage per model on bb128, from source `81e435ac`, with:
- [controller](run.sh), [guard](guarded.sh) and [launcher](after-fallback.sh);
- one disk helper, [`relocate-p4mix.sh`](relocate-p4mix.sh), described under **Plumbing**.

The data files are [`results.json`](results.json) (every field, interval and missing share) and [`fields.csv`](fields.csv).

All values are BB/100, all-in adjusted, over 4 banks × 4,096 blocks. Each contrast is `pNmix` minus the current route's model, with both models seen through the projected view.

## Routes under the prespecified rules

| Size | Off the band | In the band |
|---|---|---|
| 3 players | **`p3mix` replaces `mix`** | `p3` stays |
| 4 players | `mix` stays | `p4` stays |
| 5 players | `mix` stays | `p5` stays |

No depth table reads "six-player mixed better", so there are no adverse findings.

## Home: `pNmix` − `pN` at 100 BB

| Players | Primary (`pN` copies) | Decision interval | Verdict |
|---|---|---|---|
| 3 | −15.7 | [−28.1, −3.3] | inconclusive |
| 4 | −15.0 | [−26.2, −3.7] | inconclusive |
| 5 | −11.6 | [−21.8, −1.4] | inconclusive, plus a harm flag |

The decision intervals are Bonferroni 95% over the three home tables, with a margin of 10.
- **Harm flag at 5 players:** −73.7 [−97.1, −50.2] against the `mixed` field.
- **Other fields at 100 BB:**
  - `pNmix` loses 14–21 against its own copies at every size;
  - it gains +5.6 to +8.7 against pot-pressure, with intervals crossing zero.
- **Reading:** as in six-handed play (#447, −14.6), mixed-stack training costs about 12–16 BB/100 at exactly 100 BB against the dedicated model. The band stays.

## Depth: `pNmix` − `mix` through phantom folds

| Players | 50 BB | 20 BB | 200 BB | Unequal |
|---|---|---|---|---|
| 3 | **+18.1 [+2.6, +33.7]** | +7.4 [−1.4, +16.3] | +8.4 [−31.4, +48.2] | **+19.1 [+0.9, +37.3]** |
| 4 | +4.7 [−8.3, +17.6] | −0.1 [−7.1, +6.9] | +9.5 [−25.5, +44.4] | +6.2 [−8.0, +20.5] |
| 5 | −9.2 [−23.3, +5.0] | −3.2 [−9.8, +3.4] | −22.0 [−69.6, +25.6] | +5.3 [−12.7, +23.2] |

Primary field `mixed`. The decision intervals are Bonferroni 95% over the twelve depth tables. Bold reads "dedicated mixed better".

- **3 players:**
  - `p3mix` also beats `mix` on the other fields: +1.8 to +8.8 against pot-pressure and tight-aggressive.
  - Against copies of itself, it gains +5.6 to +10.8.
- **4 players:** small gains on several other fields, +0.1 to +12.3. The 4-player unequal table against `p4mix` copies reads −4.0. Nothing reaches the primary rule.
- **5 players:** level. At five dealt seats, the six-player model loses only one phantom seat, and a dedicated model adds little.
- **The pattern** fits the phantom study (#445): the fewer real players, the more phantom folds cost.

## Missing shares

These are decisions without a positive-mass row, averaged over a table's fields.

| Table | `pN` or `mix` | `pNmix` |
|---|---|---|
| 100 BB home tables | 0.01–0.06% | 0.14–0.67% |
| Depth tables | 0.12–1.25% | 0.10–1.27% |

## Models

| Model | Entries | Checkpoint | Binary | Size |
|---|---|---|---|---|
| `p3mix` | 134.3M | `41182b65…` | `afddb595…` | 7.5 GB |
| `p4mix` | 192.5M | `06c9df3c…` | `d4218715…` | 10.9 GB |
| `p5mix` | 226.0M | `b77cb67f…` | `ff92f6fe…` | 12.8 GB |

- **No freeze:** all three stayed under the 250M-entry cap.
- **Depth draws:** each of the 13 grid depths was drawn for about 6.79M seats (`p3mix`), 9.00M (`p4mix`) and 11.49M (`p5mix`).
- **Deployment:** `p3mix` adds 7.5 GB to the bb128 decision service, about 31 GB with all routes loaded.

## Checks and costs

- **Qualification:**
  - the library and paired-arena host tests passed on bb128;
  - six-player fixed training at 100M is still `482a0f8f…`;
  - the five-player mixture at 100M is byte-identical at 16 and 8 threads (`0448ff91…`);
  - every comparison model's binary and mass receipt matched their pins;
  - the smoke run passed.
- **Replay:** all 120 bank-0 traces (1,966,080 hands) replay independently.
- **Fallbacks:** no violations in all 480 receipts.
- **Run:** 02:57–07:28 UTC, 4 h 31 min.

  | Stage | Duration |
  |---|---|
  | Build and qualification | 5 min |
  | Smoke | 11 min |
  | `p3mix` | 30 min of training, 15 min of export, audit and conversion |
  | `p4mix` | 28 min of training, 22 min of export, audit and conversion |
  | `p5mix` | 30 min of training, 27 min of export, audit and conversion |
  | Arena, 4 banks | 53 min |
  | All-in equity | 50 min |

- **Resources:**
  - CPU peaked at 77 °C and VRM at 76 °C.
  - Memory peaked at 31.0 GB.
  - Free space stayed at 14 GB or more on the NVMe and 22 GB or more on the HDD.
- **Disk:** 67 GB under `/home/dberweger/openpoker-short-mixed-20261028/` and 18 GB under `/mnt/data2tb/openpoker-short-mixed-20261028/`.

## Plumbing

The NVMe would have fallen below its 10 GB stop during `p5mix`. Later stages read only each model's binary and mass receipt, so the following moved to the HDD mirror path, with symlinks left at the original paths:
- `p3mix`'s checkpoint and average, by hand after `p3mix` finished;
- `p4mix`'s checkpoint, by [`relocate-p4mix.sh`](relocate-p4mix.sh) once its `pins.json` existed.

Each copy's SHA256 matched the model's recorded pin before the original was removed. No result depends on the moves, and the controller never stopped.
