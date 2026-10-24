# Six-player 100 BB: 500M versus 250M capacity at matched 10B nodes

[Proposal418](https://github.com/dberweger2017/CFR-NLHE-6max/issues/418).
Implementation/qualification work authorized; the larger run requires a concrete
accepted quote and frozen exact-source qualification before launch.

## Fixed intervention

Retain all four PR417 checkpoints. The control is its 250M-key, 10B-node average
binary `086938a88f1b302688b00cf52666162350e02e3b1212aa590bb6bf4941c46178`.
Train one new arm **from scratch** to 10B nodes with a 500M-key threshold and
whole-iteration freeze, seed2026102361001. Six players100BB, unpruned K50/v1,
fast16/eight roots, full float64 opponent-sampled averages and parallel gzip stay
unchanged. Same seed does not hold training trajectories fixed after strategies
diverge. The intervention includes later membership freeze and changed visitation.
This is matched nodes, not equal CPU/wall time or another training seed.

One final checkpoint/export/binary is proposed for the new arm. Do not resume the
already-frozen control or silently lift its cap. A tiny fixture may test same-cap
thread/resume equivalence; that is engineering qualification, not another main arm.

## Opponents, fresh deals and statistics

Use the exact eight five-opponent fields from PR417: five own3B; five random;
five check-call; five TAG; five pressure; three-call/two-pressure;
random/fourTAG; own3B/two-call/two-pressure. `peer` always names the frozen PR417
250M/3B model; `control` is its 250M/10B; `candidate` is the fresh500M/10B.
Never replace opponents with either focal. There are **three resident models**
in the full arena, including the trained/mixed fields; planning must count them.

Proposed 4,096 fresh independent deal blocks per field, roots20261024650001–8,
12 balanced forward/reverse seatings from PR417, no overlap with earlier deal roots.
Fixture roots20261024659901–8 and training seed2026102461991 are distinct from main.
Initial786,432 physical hand instances plus byte-identical reproduction, every
initial hand independently replayed. Mean12 seatings within a deal block before
computing uncertainty; seatings/reproduction are not extra observations.

One new family of eight one-sided95% Student-t/Bonferroni bounds, df4095:
trained-field lower>0; seven scripted/mixed lower>−5BB/100. Ordinary absolute/paired
95% intervals, seats/positions and tails descriptive. All outcomes retained;
unpassed means unresolved, not proved loss. This is one-seed development, not
release acceptance, Nash convergence or general superiority. Counts/margins,
effect-size and power scenarios must be published before main. The unmeasured
capacity-pair variance cannot be assumed equal to PR417; this size does not
promise small-effect resolution or passing every safeguard.

## Shared observations

Evaluate both capacity models on every focal legal observation encountered in
both arms, whether actions change or not. Each occurrence gets equal weight in
the pooled multiset; also report each originating arm separately. Do not deduplicate
by abstract key: different legal observations may share a key. Selection is all
focal decisions in the fixed initial panel, with no return/coverage filtering.
Reproduction verifies evidence but adds no observations to estimates.

Both queries receive the **same acting-seat Observation**, without consuming action
RNG or changing player behavior. Retain exact float64 distributions, legal action
ordering, key/action identity, original-mass status and a legal-observation
fingerprint. Only the acting seat's hole cards and public board/history/player
state may enter queries/fingerprints; no opponent holes, deck or future outcomes.
All missing/zero/positive results retained. Unsupported identities/menu mismatches
are correctness failures, not dropped observations.

Shared-state coverage is descriptive, with block-level counts and source-arm
strata. It measures support on identical queried histories; it does not isolate
the causal payoff effect of an individual action or prove that capacity repairs
all missing histories. On-policy coverage remains a separate measurement.

## Qualification and execution gates

Small fixtures must establish: cap-only recipe difference; fresh-arm training;
control and peer source pins; unchanged opponent field; three-model cache reuse;
thread/resume parity within each cap; full-row export/binary/mass audits; shared
query parity with source rows including missing/zero/positive; identical action
and RNG trajectories with diagnostics enabled/disabled; hidden-card/future-card
independence; serial/parallel and reproduction parity; independent replay;
complete inventory, probability normalization and no skipped focal decisions.
Existing three-player and four-to-six-player behavior remains a regression gate.

Freeze source/config/model/K50/environment/binary/proof pins. No main until those
proofs pass and the owner accepts the final full quote. A partial correctness,
replay, accounting, hash or thermal failure is terminal: retain evidence, no
automatic science retry, recovery, outcome extension or reduced acceptance panel.
Network uncertainty never authorizes duplicate science.

Only CPU90°C /Thermistor15 100°C /missing-nonfinite sensors are automatic resource
stops; ownerSTOP and mutex/correctness failures also stop. No time/RSS/disk/swap
cutoff is introduced. Inspect storage/memory/swap manually. Normal compute plus
study mutex nonblocking; no other jobs, fan/driver/environment changes, schedules
or observers. Raw models/traces/source/proofs/partials remain protected; Git compact
summaries only. Owner cleaner manages archival separately; accepted metadata does
not establish research-payload Drive acceptance.

## Preliminary resources and decision

The initial extrapolation is about3h central/~6h reserve; correcting arena loading
for the third resident model and qualifying shared-state work may revise it.
Linear estimates:~41GiB fresh training,~55GiB mixed arena; plan75GiB memory
headroom, not a memory kill limit. New all-NVMe workspace/evidence scenario120GiB,
including~55GiB final model artifacts, traces/shared-state evidence and working
room. Existing protected inputs are additional but already resident. No proposed
500GB cleanup gain is counted: current review has not established that deletion
eligibility. Fresh actual availability is required before quoting admission.

Report strength, matched-state/on-policy coverage, mass/visit changes, freeze
point, key growth, full load/save/audit/play/replay/wall/CPU/RAM/thermal costs,
tails and all eight flags. Different capacities need not share keysets. Keep all
adverse prior panels. An encouraging, mixed or negative result ends this bounded
comparison; any further capacity/seed/node/search/release decision is separate.
