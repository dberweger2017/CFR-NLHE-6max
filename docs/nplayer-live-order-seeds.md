# Six-player live-order keys: two-seed confirmation (protocol)

This protocol is committed before any training or evaluation. It tests whether [#431](reports/nplayer-live-order-screen/results.md)'s gain from [live-order keys](nplayer-live-order-keys.md) repeats on independent training seeds. It promotes nothing and changes no default or release.

## Why

On one lineage (seed 2026102361001), live-order keys improved the six-player trained field by +105.4 BB/100 [+92.9, +117.9] and pot-pressure by +58.4 (−31.0 → +27.3), and harmed check-call by −110.7. Seed-to-seed variation is unknown, and that trained field was the control's own 3B. Settled results need three seeds. This adds two, each with its own control, against a trained field that is foreign to both arms.

## Arms

For each new seed, **2026102661001** and **2026102661002**, two models are trained from scratch to 10B nodes with #417's recipe: fast mode, 8 roots per seat, 250M entries with whole-iteration freeze, average scope 3, 100 BB, 16 threads.

| Arm | Keys |
|---|---|
| Control | history keys (the default) |
| Live-order | `--key-schema live-order` |

Only the 10B endpoints exist and are evaluated; no checkpoint is chosen.

## Qualification before training (the run stops on any failure)

1. **Legacy parity:** without the option, the branch trainer and a `main` build produce byte-identical 100M-node checkpoints at seed 2026102661001.
2. **Determinism:** with the option, 16 and 8 threads produce byte-identical 100M-node checkpoints at seed 2026102661001.
3. **Pipeline:** export, average-mass audit, binary conversion and binary verification pass for all four models.

## Evaluation

- **Fields:** the screens' eight fields. The trained fields use **#417's 3B** (`6cd50bf1…`), a different lineage from both arms of each new seed.
- **Deals:** one new set of four banks, roots `20261026700000 + 100·bank + field index`, 4,096 blocks × 12 seatings each. Both seeds play the same deals, and no earlier run used them.
- **Design:** for each seed, a paired arena with its control against its live-order model as the focal player. Each model keys lookups with its own schema.
- **Scoring:** realized and all-in adjusted; the adjusted result is the decision quantity.

**Decision rule, fixed now:**
- **Primary:** for each new seed, the trained-field paired change (live-order minus that seed's control), all-in adjusted, pooled over the four banks (16,384 blocks).
  - **Confirmed** if its 95% Student-t lower bound is above 0 **on both new seeds**; otherwise **not confirmed**.
- **Harm flags:** per seed, Bonferroni 95% intervals over the other seven fields. A field whose upper bound is below 0 is flagged. Check-call is expected to be flagged, and a flag doesn't block the primary.
- **Across seeds, descriptive:** per field, the mean of the three seeds' changes (#431's and the two new ones) with a Student-t 95% interval over seeds (2 degrees of freedom). Pot-pressure is the named secondary.
  - #431 used other deals and its own 3B as opponent, so this interval mixes designs and is not a gate.
- **Mechanism, descriptive:** per seed, training telemetry (entries, missing and discarded shares) and the share of focal decisions on learned rows, by field and street.

**What follows:**
- **If confirmed:** live-order keys become the recommended six-player recipe for the next step, six players at 200 BB, which gets its own protocol. Nothing is promoted or released by this run.
- **If not confirmed:** #431 is recorded as partly lineage-specific before building on it.

## Check-call diagnosis (descriptive, already run)

Before this protocol, `scripts/nplayer_preflop_ranges.py` compared both #431 arms' first preflop actions by hand-strength tier on #431's saved traces ([results](reports/nplayer-live-order-seeds/check-call-preflop-ranges.json)). It uses no new deals and doesn't enter the decision rule.

## Rules

- **Host:** bb128. Stops: CPU 90 °C, VRM (Thermistor 15) 100 °C, below 20 GB free on the HDD, and below 10 GB free on the NVMe.
- **Disk:** all working files on the HDD under `/mnt/data2tb/nplayer-live-order-seeds-20261026/`, about 80 GB. Traces and binaries are gzip-compressed after use.
- **Expected cost:** about 5 hours.
  - Four trainings of 22–35 minutes and four pipelines.
  - Per seed: about 30 minutes of arena and about 70 minutes of all-in scoring.
- **Failures:**
  - A research failure is reported as is, with no retry, retuning or extra hands.
  - A qualification failure stops the run before training.
  - Plumbing problems go in the PR.
