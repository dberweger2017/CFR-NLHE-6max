# Six-player live-order key screen (protocol)

This protocol is committed before any training or evaluation for the screen. It is a one-lineage development screen: nothing is promoted, no default or release changes, and #417's control stays the six-player model.

## Why

The [pilot](reports/nplayer-live-order-pilot/results.md) passed its gate. With the [live-order key](nplayer-live-order-keys.md), the six-player table holds 17.8M entries at 600M nodes instead of overflowing 250M. At 2B nodes:
- training decisions without a row fall from 73.6% to 2.2%;
- no update is discarded;
- rows get 10–22 regret updates, where #417's got 2–3 over 10B.

**The hypothesis:** at equal nodes, nearly complete coverage and denser regret estimates make the bot stronger. The risk is that the coarser key merges spots that need different play.

## Arms

| Arm | Model |
|---|---|
| Control | #417's six-player 10B, SHA256 `086938a8…c46178` |
| Live-order | The same recipe from scratch: seed 2026102361001, fast mode, 8 roots per seat, 250M entries with whole-iteration freeze, average scope 3, trained to 10B nodes, plus `--key-schema live-order` |

Only the 10B endpoint exists and is evaluated; no checkpoint is chosen. Traverser admission (#430) stays off, so this screen changes one thing.

## Qualification before training (the run stops on any failure)

1. **Legacy parity and determinism:** as in the pilot.
   - Without the option, the branch trainer and a `main` build produce byte-identical 100M-node checkpoints.
   - With it, 16 and 8 threads produce byte-identical 100M-node checkpoints.
2. **Pipeline:** export, average-mass audit, binary conversion and binary verification pass.

## Evaluation

The evaluation matches [#430](reports/nplayer-traverser-admission/results.md):
- **Fields:** #417's eight fields with its opponents, including #417's 3B in the trained fields.
- **Deals:** #427's four fresh banks (roots `20261025900000 + 100·bank + field index`, 4,096 blocks × 12 seatings each).
- **Design:** paired arena, control against live-order as the focal player.
- **Keys:** each model looks up rows with its own schema.
- **Scoring:** realized and all-in adjusted; the adjusted result is the decision quantity.

**Decision rule, fixed now:**
- **Primary:** the trained-field paired change (live-order minus control, against five copies of #417's 3B), all-in adjusted, pooled over the four banks (16,384 blocks). **Improved** if its 95% Student-t lower bound is above 0; otherwise **not shown**.
- **Harm flags:** for the other seven fields, Bonferroni 95% intervals over seven tests. A field whose upper bound is below 0 is flagged as harmed.
  - Pot-pressure is reported with its own 95% interval as a named secondary, with no gate.
- **Mechanism, expected direction declared now (descriptive):**
  - **Training:** fewer decisions without a row and fewer discarded updates.
  - **Table:** more regret updates per row.
  - **Play:** per field and street, a higher share of focal decisions on learned rows. Missing, zero-mass and opponent-only rows are reported separately.
  - **Exception:** check-call's multiway rivers may still be unvisited, because self-play rarely reaches them.
- **Also reported:** absolute adjusted returns of both arms per field, per-bank estimates, and table telemetry.

A positive primary with no harm flag would justify confirmation with more seeds, then the 200 BB six-player work. One lineage cannot separate the change from seed-to-seed variation.

## Rules

- **Host:** bb128, 16 threads. Stops: CPU 90 °C, VRM (Thermistor 15) 100 °C, below 10 GB free on the NVMe, and below 5 GB free on the HDD.
- **Disk:**
  - The checkpoint, average and audit go on the HDD under `/mnt/data2tb/nplayer-live-order-screen-20261026/`.
  - The binary and arena traces go on the NVMe under `/home/dberweger/nplayer-live-order-screen-20261026/`.
  - Traces and the binary are gzip-compressed after use.
- **Expected cost:** about 2½–3 hours, mostly arena and all-in scoring.
- **Failures:**
  - A research failure is reported as is, with no retry, retuning or extra hands.
  - A qualification failure stops the run before training.
  - Plumbing problems go in the PR.

## Completed — October 26

The run is complete. The primary is **improved** (+105.4 [+92.9, +117.9]); pot-pressure changes by +58.4 [+50.2, +66.5], from −31.0 to +27.3. Check-call is **flagged as harmed** (−110.7 [−163.6, −57.8]). [Results](reports/nplayer-live-order-screen/results.md).
