# Matched-teacher imitation at six-player 100 BB

Research proposal: [#473](https://github.com/dberweger2017/CFR-NLHE-6max/issues/473).
Protocol fixed before export, training or evaluation. The owner authorized this
study and RunPod operation in the planning conversation on November 8, 2026.
The bb128 Deep CFR pilot is independent and is not modified or interrupted.

## Question

Can step 2's imitation recipe preserve the strength of `six` when both teacher
and training hands match Gate D's six-player, equal-stack 100 BB configuration?
Step 4 copied wide-grid `widemix` and failed Gate D. This study changes both
teacher and data distribution; it does not isolate those two changes separately.

## Frozen inputs and data

- Teacher/baseline: #431's `six`, binary SHA256
  `f894a59f8a92424d735438726d16834901a7dcaf6d560c98b950fb72a143c9ea`;
  audited mass receipt
  `806e7b9c92b7fbfd8f6ea2de30535d4dc7a525cc096091c458fe1e6c15000bda`.
- Gate D's foreign peer: #434 seed 2026102661001, binary
  `ab7f8e166448b51cd54be3c9163936126f2b6cff2925b2fa374e7a1db783488b`;
  mass receipt
  `366507548dfdd5d9fd4aa44386f02ac8838947766c8f9b6378878f3d0872188b`.
- Existing K50 tables and 612-feature encoding; unchanged legal six-label menu.
  The input bundle records every member hash, including the K50 files and mass
  directories. The native readers verify their existing formats and pins.
- Six players with 10,000 chips each, 50/100 blinds, no rake or ante.
- Six fields, equally weighted by hands: self-play (`six` in all seats), mixed
  (one `six`, two check-call, two pot-pressure, one tight-aggressive), and one
  `six` against five copies of each of the four scripts. Export every seat's
  decisions; only positive-mass `six` targets enter training.
- Train: 400,000 hands per field, 2.4M total. Held-out: 20,000 per field,
  120,000 total. Fixed roots: train `20261110000000 + 1000*field_index`,
  held-out `20261111000000 + 1000*field_index`.
- Qualification: two identical 2,000-hand mixed jobs, threads 1 and host limit,
  root `20261112000000`, equal record digests. Qualification samples are never
  used for training. Their measured size determines disk admission for the
  fixed full export; an oversized projection stops rather than shrinks data.

## Frozen training recipe

Reuse `neural_policy_imitation.train`: 612 -> 1024 -> 1024 -> 512 -> 6,
ReLU, masked softmax, teacher-distribution cross-entropy, AdamW lr 1e-3 with
cosine decay to zero, weight decay 1e-4, batch 8,192, four epochs, CUDA fp16,
seeds 1, 2 and 3 on identical data. No hyperparameter selection, retraining or
early stopping based on test results. All three seeds are retained.

An optional disk-backed array cache avoids full-dataset concatenation and
pinned-memory copies. It preserves the original positive-row order, targets,
random permutation and batches. Cache parity is tested against the original
in-memory arrays. It changes memory placement, not the optimization recipe.

## Evaluation and decision

Reuse **Gate D only**, from [step 4](neural-policy-everywhere.md), with fresh
roots `20261113000000 + 100000*(run-1) + 1000*bank + field_index`.
Smoke roots add 500, use one bank and 64 blocks, and never enter the decision.

- Arm 0: `six`, native view, original uniform fallback.
- Arm 1: the corresponding seed's network at every focal decision, native view.
- Six players, 100 BB. Fields and ordering exactly match Gate D: foreign peer
  copies (primary), pot-pressure, tight-aggressive, check-call, random, mixed.
- Run 1: 4 banks x 4,096 blocks per field; runs 2 and 3: 1 bank x 4,096 each.
  Every block plays all six cyclic seatings; arms share deals. Contrasts are
  network minus table in all-in-adjusted BB/100.
- Pass iff run 1's primary one-sided 97.5% lower bound is strictly above -10,
  no secondary harm flag, and both replication primary estimates exceed -10.
  Secondary fields retain Bonferroni 95% intervals over five fields; harm means
  upper bound below -10. Check-call is reported but exempt, exactly as Gate D.
- Every trace is scanned, with zero fallback violations required. All bank-0
  traces per seed are independently replayed. Rust/PyTorch parity must pass
  within 1e-5 on up to 10,000 held-out samples per network before any main arena.

Report training loss, held-out TV, masked cross-entropy and top-label agreement
by field and street, positive/zero/missing teacher status, absolute and paired
realized/adjusted results, each seed, source/input/network pins, stage costs,
peak resources and failed attempts. A fixed first 2,000 records per train field
give training-set fidelity diagnostics; the full held-out set is evaluated.
These fidelity diagnostics are descriptive, never selection criteria.

## Qualification, operations and budget

New manifest/gate/cache tests, existing sample/imitation/everywhere tests,
native library and paired-host tests, GPU availability, pinned input bundle,
export determinism, network parity, and the complete smoke pipeline must pass.

One RunPod GPU, preferring RTX 4000 Ada at the quoted $0.28/hour. Actual CPU
and RAM entitlement is recorded on launch; no assumption of 16 physical cores.
Use Python 3.11, PyTorch 2.5.1 CUDA 12.4 and the repository's pinned engine.
The default template's PyTorch is not the experiment environment.

Maximum 12 hours of billed pod lifetime, including setup and retrieval. A
work deadline 10.5 hours after rental leaves 1.5 hours for retrieval. Proposed
working disk: 200 GB, with final storage rate recorded before deployment.
Total authorized envelope: $4 including compute and working storage; do not
rent if the displayed 12-hour total exceeds it. No paid extension or auto-topup.
The exact host offer is recorded; a short benchmark informs runtime estimates,
not scientific data sizes. No automatic change to the frozen recipe.

The controller stops on deadline, STOP file, failed subprocess, nonfinite
training loss, less than 4 GiB available RAM, less than 10 GiB free disk, or GPU
temperature >=87 C. It terminates the owned subprocess group. CPU temperature
is recorded when exposed by the container; absence is recorded, not reported
as a successful thermal measurement. Work does not continue after a failure.

T3 scheduled check-ins inspect durable status, retrieve and hash-verify the
evidence, then terminate this exact pod through Chrome and verify billing has
stopped. A separate scheduled hard cutoff enforces the billing deadline.
If the provider offers an independent termination timer, use it too. A job
timeout alone does not stop provider billing. No main run starts without
armed termination/check-in tasks and a verified retrieval path.

Large inputs, samples, traces, model weights and archives stay outside Git.
Commit only protocol, code, small receipts/results, hashes and restoration
locations. Never delete pod storage before verified retrieval. Preserve partial
evidence on failure. No live play, route change, release or merged default change.

## Interpretation

A pass supports matched-teacher network play at six-player 100 BB under Gate D.
It does not show that adding these examples to a shared wide-grid network will
preserve short-stack strength; that combined model needs both gates again.
A failure implicates this imitation recipe, not a proof of insufficient network
capacity or a prediction that the separate Deep CFR pilot must fail.
