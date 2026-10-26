# Three-player blueprint promotion study

Proposal [#341](https://github.com/dberweger2017/CFR-NLHE-6max/issues/341).

Owner accepted this evaluation and its estimated 15–30 minutes of bb128 compute
(roughly 1–2 hours including implementation and analysis) on October 18, 2026.
No training is needed. This is a new held-out comparison after PR340, not a
repeat of its equal-node or equal-time test. The research proposal records that
existing authorization; it does not request a second approval.

## Question and frozen inputs

Do the three fast 600-active-training-second averages from PR340 improve on the
established PR292 production 1B averages? These candidates reached respectively
2,949,726,632 / 3,003,671,483 / 2,910,499,919 nodes. Both families use three
players, 20 BB, K50, menu v1 and full scope-3 average policies. Read-only paths,
SHA256s and the previously qualified native arena are pinned in
[nplayer-blueprint-promotion-inputs.json](nplayer-blueprint-promotion-inputs.json).
The arena binary comes from PR340 source 8f6fb76d; new orchestration is frozen
in this PR before final play. No PR336, pruning, search or training changes.

## Match matrix and fresh deals

Training seeds are 2026101541, 2026101542 and 2026101543. Primary comparisons
match each fast seed against the same production seed. Secondary comparisons
rotate production seeds: 1541 vs 1542, 1542 vs 1543, 1543 vs 1541. Each comparison
plays fast singleton vs two copies of its production opponent, then production
singleton vs two copies of that fast policy. This cyclic test probes cross-seed
robustness; it is not a diverse population or mixed-opponent test.

Each lineup plays 8192 independent six-hand seat-permutation blocks (49152
hands), with button rotation and domain-separated deck/action streams from the
existing arena. Paired orientations share deals. Six comparison roots are
20261018345101–106, ordered primary seed1541/42/43 then secondary1541/42/43.
They are reserved before play and distinct from PR340 roots. Excluded wiring
smoke uses exactly two blocks per lineup and roots 20261018345001–006.
There are 589824 final hands plus 589824 exact reproduction hands. Every final
hand must independently replay with the pinned pokers engine before any outcome
readout. Models receive only the existing legal observation. Raw private-card
traces are evaluator evidence and never policy inputs.

## Readout and decision

Per independent paired block compute (fast-singleton BB/100 minus
production-singleton BB/100)/2; report its mean and two-sided 95% Student-t
interval, each singleton's interval, and per-seat/position intervals and coverage.
This is an oriented singleton contrast, not pooled individual-player return.

Consistent improvement requires every primary comparison's lower bound >0.
Cross-seed noninferiority requires every secondary lower bound >−5 BB/100.
Recommendation to promote the family requires both gates. These are conjunctive
intersection-union gates; no seed may be selected or hidden, and no pooled or
best-seed result replaces a failed component. Individual intervals are nominal
95%, not simultaneous intervals. A false gate may be inconclusive rather than
evidence of a loss. Keep all results; no extra hands, seeds or tuning.
Passing supports a three-player blueprint candidate for v0.6; release, default
adoption, search and broader population claims remain separate owner decisions.

## Execution and limits

Use bb128 only, up to all 16 logical CPUs, six independent evaluation workers
and single-thread BLAS/OMP. Existing models, tables, arena and pinned Python
venv are read-only dependencies; no build or environment mutation is needed.
Take both a study mutex and the normal exclusive compute mutex nonblocking.
Qualification checks all six model hashes, binary/table pins, engine identity,
and all twelve smoke lineups with full replay/reproduction. Before final play,
freeze source/config hashes, input receipts, measured smoke cost and a bounded
quote. A failed qualification or final scientific/resource check is terminal:
preserve partials, no automatic retry or silent fallback.

Reserve 5,000,000,000 bytes new output growth and retain a 50,000,000,000-byte
NVMe floor. Whole worker-family RSS limit 80 GiB, available RAM floor 8 GiB,
swap growth limit 256 MiB, per-process address-space limit 48 GiB. Hard stop
immediately at CPU package >=90C or Thermistor15 >=95C; missing sensors stop.
Admission requires CPU <70C and Thermistor15 <80C. Preserve exact crossing
samples. Original launch +90 minutes is a malfunction fail-safe, not a target
workload or an extendable budget. Record load/play/replay/total wall and child
CPU time, sampled family RSS, disk, temperatures, swap and concurrent conditions.
No fan, driver, OS, other-job, cache or cleanup changes. Failure preserves all
outputs. Raw traces remain on bb128, indexed with archive pending; only compact
results and receipts enter Git. No unattended work is scheduled by this document.
