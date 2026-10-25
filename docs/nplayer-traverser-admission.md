# Six-player traverser-admission training screen (protocol)

This protocol is committed before any training or evaluation. It is a one-lineage development screen: nothing is promoted, no default or release changes, and #417's control stays the six-player model.

## Why

The six-player key table fills almost at once and then never changes. #417's 10B froze its 250M entries at iteration 23,678 of 390,401, about 6% of training. Its checkpoint and [mass audit](reports/nplayer-six-player-candidate/retained-support.csv) show where that capacity went:

| Rows of #417's 10B | Count | Share | How it plays |
|---|---|---|---|
| Opponent-only: `visits` 0, positive mass | 149,758,755 | 59.9% | Exactly uniform. Its owner never updated it as traverser, so its regrets are zero and its average accumulates the uniform policy |
| Traverser-only: zero average mass | 58,854,501 | 23.5% | Uniform fallback |
| Both regrets and mass | 41,388,298 | 16.6% | A learned strategy |

The training telemetry matches: 66.7% of training decisions found no row, and 68.1% of traverser regret updates (1.24B of 1.83B) were discarded after the freeze.

So 60% of the table plays the same uniform policy as a missing key, while holding capacity that traverser updates can no longer use. Reports so far counted these rows as trained, because their mass is positive.

**The hypothesis:** if new keys enter the table only from a traverser update, the same 250M entries hold far more rows that learn. That reduces discarded training updates and untrained play, and makes the bot stronger at equal nodes.

## The training change

`nplayer_train --traverser-admission`, a fast-mode-only option recorded in the checkpoint as `admission` (`traverser-admission-v1`, with `declined_keys`):
- **The rule:** at each iteration's merge, a key that isn't stored yet is added only if its summed update for that iteration includes a traverser visit. Otherwise its opponent-only average update is declined and counted.
- **Stored keys:** they take every update as before, opponent average mass included.
- **Everything else is unchanged:** traversal, sampling, deals, the cap and freeze rule, and the export.
- **What a declined update would have been:** the opponent sampled a missing key, so it played the uniform policy and would have recorded uniform average mass. A row built only from such updates plays uniform. Declining it changes the play of no key the table would have trained.

Without the option, the trainer's output bytes are unchanged.

## Arms

| Arm | Model |
|---|---|
| Control | #417's six-player 10B, SHA256 `086938a8…c46178` |
| Admission | The same recipe from scratch: seed 2026102361001, fast mode, 8 roots per seat, 250M entries with whole-iteration freeze, average scope 3, trained to 10B nodes, plus `--traverser-admission` |

Only the 10B endpoint exists and is evaluated; no checkpoint is chosen.

## Qualification before training (the run stops on any failure)

1. **Legacy parity:** without the option, the branch trainer and a `main` build produce byte-identical 100M-node checkpoints.
2. **Determinism:** with the option, 16 and 8 threads produce byte-identical 100M-node checkpoints.
   - They differ from the legacy run, record positive `declined_keys`, and store no row with `visits` 0.
3. **Pipeline:** export, average-mass audit, binary conversion and binary verification pass, as for #417.

## Evaluation

- **Fields:** #417's eight fields with its opponents, including #417's 3B in the trained fields.
- **Deals:** [#427](reports/nplayer-opponent-pressure/results.md)'s four fresh banks (roots `20261025900000 + 100·bank + field index`, 4,096 blocks × 12 seatings each). Every earlier pressure arm played these deals, so results line up.
- **Design:** paired arena, control against admission as the focal player.
- **Scoring:** results are scored realized and all-in adjusted, as in #426. The adjusted result is the decision quantity.

**Decision rule, fixed now:**
- **Primary:** the trained-field paired change (admission minus control, against five copies of #417's 3B), all-in adjusted, pooled over the four banks (16,384 blocks). **Improved** if its 95% Student-t lower bound is above 0; otherwise **not shown**.
  - The trained field is the primary because the hypothesis is general: more learned rows everywhere, not an answer to one script.
- **Harm flags:** for the other seven fields, Bonferroni 95% intervals over seven tests. A field whose upper bound is below 0 is flagged as harmed.
  - Pot-pressure, the known six-player gap, is one of these. It is reported with its own 95% interval as a named secondary, with no gate.
- **Mechanism, expected direction declared now (descriptive):**
  - **Table:** more learned rows (both regrets and mass) and no opponent-only rows.
  - **Training:** a lower share of discarded traverser updates and of decisions without a row, and a later freeze iteration.
  - **Play:** per field and street, a higher share of focal decisions on learned rows. Opponent-only rows count as untrained here: missing, zero-mass and opponent-only are reported separately.
- **Also reported:** absolute adjusted returns of both arms per field, per-bank estimates, and `declined_keys`.

A positive primary with no harm flag would justify confirmation with more seeds and then use in the 200 BB six-player work. It doesn't promote anything, and one lineage cannot separate the change from seed-to-seed variation.

## Rules

- **Host:** bb128, 16 threads. Stops: CPU 90 °C, VRM (Thermistor 15) 100 °C.
- **Disk:**
  - Working files go on the NVMe under `/home/dberweger/nplayer-traverser-admission-20261025/`. The HDD has 43 GB free, too little for the ~45–50 GB peak.
  - The run starts only with at least 60 GB free on the NVMe, and stops as plumbing if free space falls below 10 GB.
  - Traces and the model binary are gzip-compressed after use, as in #428.
  - Inputs are read only.
- **Expected cost:** about 2½–3½ hours, from #427's 2h32m with the same stages, plus qualification and a few minutes for row classification.
- **Failures:**
  - A research failure (for example the primary not shown, or harm flagged) is reported as is, with no retry, retuning or extra hands.
  - A qualification failure stops the run before training.
  - Plumbing problems go in the PR for the owner.
- **Evidence:** compact results go in Git; working files stay on bb128 for the vacuum cleaner.
- **Before this protocol:** one #427 control trace (random field, bank 0) was used to time the row join. All 32,305 of its positive-mass keys were found in the control checkpoint. No row classes or results were inspected.
