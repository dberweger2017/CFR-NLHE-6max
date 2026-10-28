# Restricted fallbacks at untrained rows: results

This is a run of [the protocol](../../openpoker-untrained-fallback.md), committed before running. It was one evaluation on bb128, from source `9fb2481a`, with [controller](run.sh) and [guard](guarded.sh). The data files are [`results.json`](results.json) (every field, interval and missing share) and [`fields.csv`](fields.csv).

All values are BB/100, all-in adjusted, over 4 banks × 4,096 blocks. Each contrast is the candidate minus `uniform`, both played by `mix` through the projected view.

## Outcome

**Neither candidate qualifies, so the uniform fallback stays.** Every primary table reads "uniform better" for both candidates, and every table has a harm flag against check-call.

| Table | `no-all-in` − `uniform` | `no-raise` − `uniform` |
|---|---|---|
| `100bb` | −20.0 [−32.2, −7.7] | −32.1 [−49.8, −14.4] |
| `50bb` | −23.3 [−31.1, −15.5] | −33.5 [−43.8, −23.3] |
| `unequal` | −16.6 [−26.2, −7.1] | −20.2 [−34.7, −5.7] |
| `deep-outlier` | −30.6 [−43.1, −18.1] | −71.5 [−92.3, −50.6] |

Primary field `mixed`. The decision intervals are Bonferroni 95% over each candidate's four tables.

## Other fields

| Field | `no-all-in` | `no-raise` |
|---|---|---|
| `check-call` | −55 to −72, harm at every table | −131 to −196, harm at every table |
| `random` | −7 to −13; −37.8 at `deep-outlier`, harm | −7 to −19; −107.5 at `deep-outlier`, harm |
| `pot-pressure` | −0.3 to −3.0 | +0.1 to −5.7 |
| `tight-aggressive` | −0.6 to +0.2 | −2.8 to +0.1 |
| `mix` copies | −0.8 to −0.3 | −0.3 to +0.1 |

Ranges are over the tables where the field sits. No field gains anywhere.

## What it means

- **The random raises and shoves at untrained rows are where `mix` earns against calling stations.**
  - Against check-call at 100 BB, `uniform` makes +207. `no-all-in` makes +141, and `no-raise` makes +12.
  - Together with #426's check-or-fold result, every passive restriction tested so far costs more than it saves.
- **Untrained rows are concentrated where the stations are.** Arm 0's share of focal decisions without a positive-mass row, pooled over tables:

  | Field | Share without a positive-mass row |
  |---|---|
  | `check-call` | 56–57% |
  | `mixed` | 11% |
  | `random` | 2% |
  | `pot-pressure`, `tight-aggressive`, `mix` copies | 0.1–0.5% |

  - By street at `100bb`, averaged over fields: 0.04% preflop, 39% flop, 50% turn and 61% river.
  - The protocol expected 1–4%, from studies whose fields had no check-call. That expectation was wrong; the live session's 9.5% sits between `mixed` and the strong fields.
- **Against strong opponents the fallback barely matters.** Against pot-pressure, tight-aggressive and `mix` copies, untrained rows are rare, and the changes stay within a few BB/100 either way. The live bust came from two all-in calls against unknown opponents; this study can't reproduce that table.
- **What would help** is fewer untrained rows: training that reaches multiway passive lines, not a different default. That matches #426's conclusion for pot-pressure lines.

## Checks and costs

- **Qualification:**
  - the paired-arena host tests passed on bb128;
  - the `mix` binary and mass receipt matched their pins;
  - the smoke run passed.
- **Fallback rule:** zero violations in all 368 receipts. No candidate arm played an excluded raise at an untrained row. Trained decisions use their row in both arms by construction.
- **Replay:** all 92 bank-0 traces (2,260,992 hands) replay independently.
- **Run:** 23:10–02:57 UTC, 3 h 47 min.

  | Stage | Duration |
  |---|---|
  | Build, qualification and smoke | 4 min |
  | Arena, scan and replay, 4 banks | 26 min |
  | All-in equity | 3 h 17 min |

- **Resources:**
  - CPU peaked at 77 °C and VRM at 77 °C.
  - Memory peaked at 18.1 GB.
  - Free space stayed at 55 GB or more on the NVMe and 42 GB or more on the HDD.
- **Disk:** about 7.4 GB under `/home/dberweger/openpoker-untrained-fallback-20261028/`.
- **No plumbing failures.** The run's first status watch misreported an exit because it searched for the wrong process name; the controller itself never stopped.
