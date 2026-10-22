# Three-player 100 BB pruning: final cost and strength results

Completed October 19, 2026 at 18:13:14 UTC on bb128, under
[PR352](https://github.com/dberweger2017/CFR-NLHE-6max/pull/352) and proposal351.
**The tested pruning configuration provides no measured training-time saving.
Neither direct strength comparison establishes an improvement, a loss or
equivalence. Recommend retaining the unpruned recipe for long campaigns and
keeping this pruning configuration experimental.** No default or release change
and no further run follows automatically.

Both frozen comparisons completed: 983,040 initial hands plus 983,040 exact
reproduction hands, all independently replayed. Both every-row policy audits
passed. Recovery status is complete, final results settled, all recovery stages
returned zero and the supervisor exited. The original pre-hand interpreter
failure remains preserved separately.

## Strength

All differences below are **pruned minus unpruned**, in BB/100. The direct
statistic is the mean oriented singleton contrast across the two reciprocal
lineups, **not pooled individual-player return**. Script rows compare singleton
returns against two copies of the named script. A negative script difference
does not imply an absolute loss to that script.

Each phase has ten lineups, each with 8,192 independent six-hand blocks covering
all seat permutations. Paired orientations or script comparisons share reserved
deal roots. Pointwise intervals use block-level Student-t uncertainty; the
family intervals apply the predeclared Bonferroni correction across the two
direct contrasts, and separately the eight scripted contrasts.

| Budget | Comparison | Pruned − unpruned BB/100 | Pointwise 95% interval | Family 95% interval |
|---|---|---:|---|---|
| 3B nodes | Direct | +4.35 | [-5.84, +14.55] | [-7.31, +16.01] |
| 3B nodes | random | +25.91 | [-6.56, +58.38] | [-19.39, +71.21] |
| 3B nodes | check-call | -33.59 | [-64.21, -2.96] | [-76.32, +9.14] |
| 3B nodes | tight-aggressive | -7.41 | [-17.87, +3.06] | [-22.01, +7.19] |
| 3B nodes | pot-pressure | -8.21 | [-23.38, +6.97] | [-29.37, +12.96] |
| 630.741 s | Direct | +1.99 | [-8.00, +11.97] | [-9.43, +13.40] |
| 630.741 s | random | +24.12 | [-9.47, +57.70] | [-22.74, +70.98] |
| 630.741 s | check-call | -29.18 | [-59.94, +1.59] | [-72.10, +13.75] |
| 630.741 s | tight-aggressive | -0.85 | [-10.55, +8.84] | [-14.38, +12.68] |
| 630.741 s | pot-pressure | -6.39 | [-21.85, +9.06] | [-27.96, +15.17] |

Both direct intervals cross zero widely. These results do not establish
noninferiority: a small positive point estimate is insufficient to conclude
that strength was preserved. Every family-adjusted scripted interval also
crosses zero. The equal-node check-call difference has a negative pointwise
interval, but does not survive the multiple-comparison correction. Treat it as
an adverse signal, not a confirmed family-adjusted regression.

The screen has one fixed training seed, one host and historical baseline timing.
Intervals describe held-out deal uncertainty conditional on these particular
models, not variation across independent training seeds. No automatic adoption
threshold was declared; the decision concerns the measured cost/strength tradeoff.

## Training and serialization costs

Recipe: three players, 100 BB, K50, full float64 opponent-sampled averages,
fast mode with eight roots per seat, 16 threads, seed2026101935003, and membership
frozen near250M entries. The sole algorithm change is opt-in pruning with
`bb=0.05`, `after=200` iterations. PR347 storage changes are excluded by the
historical native-source pin.

| Endpoint | Nodes | Iterations | Active training seconds | Nodes/second |
|---|---:|---:|---:|---:|
| Historical unpruned 3B | 3,000,011,203 | 212,132 | 630.740595 | 4,756,331 |
| Pruned 3B | 3,000,010,865 | 212,514 | 631.895520 | 4,747,637 |
| Pruned equal-time snapshot | 2,994,344,973 | 212,096 | 630.742457 | 4,747,334 |

Pruning takes **1.154925 seconds more, or 0.1831% longer**, at3B; active-time
speedup is0.99817×. This single historical timing comparison shows no useful
speed benefit, rather than a replicated claim that pruning is slower.
The equal-time snapshot was saved on the way to3B because pruning was slower;
its0.001862-second overshoot is within the final iteration's0.003026seconds.
No further training was needed for the second evaluation.

Pruning skipped32,499 actions by3B. At the baseline's212,132-iteration landmark,
it had reached2,994,850,387nodes in630.846161seconds, with32,496skips. It gains
about0.18% iterations per node while iterations per second remain essentially
unchanged. A skip count is not a percentage of compute saved.

| Pruned artifact | Checkpoint save seconds | Full-average export seconds |
|---|---:|---:|
| Equal time | 139.720 | 86.732 |
| 3B | 134.774 | 86.846 |

Active time excludes checkpoint/export I/O, hashing and audits. The combined
training/export stage took2,011.217seconds wall and13,869.019child CPU seconds.
Historical baseline training-stage wall was3,053.459seconds, but its save/resume
cadence differs: **do not interpret that wall ratio as a pruning speedup**.
Sampled worker-family RSS peaked at21.81GiB during training,22.79GiB during
saving and22.77GiB during export. Both pruned endpoints contain250,000,119entries;
there is no evidence here of a useful table-memory reduction.

## Evaluation overhead and coverage

| Phase | Evaluation stage wall seconds | Native model loading seconds | Native play seconds | Independent replay seconds |
|---|---:|---:|---:|---:|
| 3B nodes | 571.218 | 424.820 | 9.165 | 16.650 |
| Equal time | 663.856 | 423.723 | 9.076 | 16.471 |

Play time sums initial and reproduction passes. Two policies are loaded once
per phase and retained across its ten cases. Loading and verification dominate
evaluation cost; hand-playing is comparatively cheap. Other wall overhead also
includes trace handling and hashing, so these columns are not an additive
decomposition. The two-model evaluation peaks at **66.03GiB sampled family RSS**;
this is distinct from the training peak.

Original attempt stage totals:2,457.968seconds wall,16,592.340child CPU seconds,
including the zero-hand failed startup. Recovery stages:1,751.098seconds wall,
4,362.321child CPU seconds. Together these are70m09s executed stage wall and
5h49m15s child CPU. First launch to final completion is91m39s, including the
21m30s repair/idle gap. These totals exclude earlier qualification and code work.
RSS is sampled and can miss brief peaks; CPU is child-process accounting, not
an isolated active-traversal counter.

Both audits checked every250,000,119row: all exports are averages, with79,715,556
zero-mass rows at3B and79,734,186 at equal time. The earlier prose said seven
and79 because a truncated preview was misread; the committed audit JSON always
contained the full counts. This correction changes neither strength nor timing
results. Zero-mass rows are retained table entries, not a decision-frequency
measurement. At3B, represented keys by street are
3.38M/13.53M/50.43M/182.65M; visits per key are5.60/4.14/2.97/1.85.
Training's cumulative missing-decision shares are4.97%/8.67%/13.66%/22.66%.
These training diagnostics are different from evaluation coverage.

In the four scripted lineups, first-pass singleton missing-key rates at3B are
0.038%/0.246%/0.550%/6.820% for pruning versus
0.042%/0.194%/0.516%/7.125% for baseline, by preflop/flop/turn/river.
Equal-time pruning gives0.041%/0.241%/0.574%/6.831%, versus baseline
0.049%/0.207%/0.622%/6.720%. These are descriptive rates on each policy's
encountered states, not a causal coverage improvement. Per-case counters,
per-seat/position return estimates and full audit summaries are retained below.

## Interpretation and next decision

The promised tradeoff did not materialize with this configuration: no training
time saved, and uncertain strength differences. That supports continuing with
the unpruned trainer, without claiming pruning is generally ineffective.

The earlier small PR336 pilot showed only about5% more iterations per node and
roughly1.5% more iterations per second on different hardware and20M-node work.
The much larger current table receives very sparse visits per key. The global
quadratic eligibility threshold may therefore allow very few skips; this remains
a hypothesis, not a causal finding. Any follow-up should first diagnose pruning
eligibility by street and visit density, before changing regret mathematics or
spending on a longer campaign. No such follow-up is started by this report.

## Reproduction, failure history and retention

[Protocol](../../nplayer-pruning-strength-study.md),
[verified precomputed results](results.json), [ten-row CSV](results.csv),
[completion/proof/cost/coverage receipt](metadata.json),
[singleton coverage CSV](coverage.csv).
The results JSON preserves model paths/SHA256s, both endpoint clocks, per-seat
and position intervals, historical timing and both attempts' stage accounting.
Its SHA256 is`6a14ad28314f98770db9bf6665b4513cef09a336e0ad0fd8c95d88a524eb7a9a`.
The metadata receipt records both verified manifests, per-case trace identities,
row audits and final completion. CSV rows directly project the JSON's`score`
fields; coverage CSV aggregates identity0's counters only from the four
`*-candidate` or`*-baseline` scripted first passes.

Frozen native source:`b9882e7e728847a58691995e64eabd4563ea0991`.
Original controller:`66150f3b5089edc4c4dabf66c2a3a439d565953f`.
Recovery controller:`5ce973c98c152ebb08a5a717cc76d4dbfe0bbd08`;
config SHA256`a2c00c6bb71e38bda8a5a63e9901f218c53b8ed1e5cc2ef01ec15d6046b8748c`.
The original configuration resolved the qualified venv executable to its
package-free base Python. It stopped before any evaluation hand. The owner
authorized evaluation-only recovery, which preserved native/model bytes,
matrices, deal roots, counts and statistics. No training was repeated and no
strength outcome was inspected before both global proof barriers passed.
[Failure and correction](startup-failure.md),
[recovery qualification](evaluation-recovery-qualification.json).
All five CI checks passed on evidence head64fed9dc;21 focused Linux tests pass.
This closeout changes reports only; no new science ran for publication.

Raw roots remain on bb128:

- `/home/dberweger/nplayer-pruning-strength-20261019/study-v1`
- `/home/dberweger/nplayer-pruning-strength-20261019/evaluation-recovery-v1`
- Qualification, environment-fix and recovery source roots under their same
  owning parent; preserve their failures and logs.
- Protected read-only PR350 input under
  `/mnt/data2tb/research-cloud/PR-350-nplayer-bb100/bounded-20261019-v3/calibration-continuation/`.

To retrieve only compact final results into a fresh ignored directory:

```sh
mkdir -p results/pr352-retrieval
scp bb128:/home/dberweger/nplayer-pruning-strength-20261019/evaluation-recovery-v1/results.json results/pr352-retrieval/
shasum -a 256 results/pr352-retrieval/results.json
```

Use the recorded SHA256 before analysis. Raw audit/replay/readout commands are
defined in the pinned controller/config; do not rerun the campaign launcher to
read these settled results. Research-Cloud namespace
`PR-352-nplayer-pruning-strength` is reserved; archival and Drive upload
acceptance remain pending. The PR is open, so its raw roots and dependencies
remain untouched. No deletion, upload coverage or Drive restoration is claimed.
