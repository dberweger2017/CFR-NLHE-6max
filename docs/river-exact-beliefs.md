# Efficient exact modeled river beliefs and deployment-profile audits

Owner-authorized October21,2026, following PR380. This is a bounded engineering
round with two linked deliverables, not a strength study. Estimated completion
6–10hours, including roughly1–2hours of bb128 measurements; first correctness
and speed checkpoint after2–3engineering hours. Calibration precedes the fixed
mature measurements. Failure of the proposed representation is a reportable
result, not permission to redesign the solver or extend the experiment.

## Scope and hypothesis

Preserve the stipulated three-seat product action-likelihood law conditioned on
all card removal, including the folded player's hidden cards. This is an exact
representation of the **modeled** joint law, not a true posterior or safe
resolving guarantee. Public observations and own cards are the only policy
inputs; privileged trace identities never enter strategy calculations.

Prototype a weighted rank-prefix terminal evaluator for this structured law.
Compare it to the existing dense exact-joint oracle, then measure complete
first-decision latency and retained continuation. Keep the original projected
solver available and unchanged. No trainer/regret-rule changes, extra menu
expansion, off-tree re-solving, concurrency tuning, default or release changes.
The menu stays `pot-jam-cap3-root-check-min-v1`, DCFR(1.5,0,2), with existing
blueprint fallback. The reference cap3 menu is audited, not redesigned.

## Independent correctness

For active holdings a,b and folded holding f, retain
`P(a,b) ∝ w0(a) w1(b) Σf wf(f) I(disjoint(a,b,f))`.
The candidate must preserve this law through both traversers, profile values,
best responses, averaging and retained-policy execution—not merely root equity.
A folded two-card distribution has single-card and pair-removal terms, so its
compatible mass can be represented by weighted rank prefixes plus explicit
blocker/cancellation corrections. Do not floor impossible worlds into positive
mass. Report sparse/dense fallback and conditioning limits, if any.

Use independently enumerated folded worlds and the unchanged dense oracle.
Cover both player orientations, nonfactorizable laws, board ties, folds,
nonuniform/opponent-zero reach, zero-mass holdings, blocked/near-blocked laws,
unequal range lengths and invalid inputs. Native randomized fixtures use fixed
seeds and include sparse and extreme weights. Required leaf agreement is
`1e-10 + 1e-10*abs(reference)` BB per counterfactual value; profile values and
best-response gains must agree within1e-8BB for the **same** profile. Independent
hand-calculated fixtures retain1e-12BB agreement. Floating-point differences
may change CFR trajectories: identical action probabilities between differently
ordered algorithms are not a correctness requirement. Each reported solve must
satisfy its own declared quality target; no convergence claim from speed alone.

## Fixed development panel and measurements

Reuse PR380's frozen200-root panel and its20 preselected belief controls, model,
K50 tables and replay proofs as read-only development evidence. This is not a
fresh confirmation or population-strength estimate. Panel SHA256
`f5b6b2706a0b6ee8912a52961b6b8e2795158bd982bea18fa43227f74924b919`;
model seed2026101935003, SHA256
`d835f61f4a5407bd47e8f8a5da849ef82c16ad21fce32f15dce72d5997275189`.
No extra deal roots or outcome-selected cases. Declare source/binary/config pins
and measured calibration quote before the mature fixed panel.

1. On all20 frozen controls, compare dense/structured leaf values and quality
   of identical fixed profiles; compare fixed64-sweep solve cost. Preserve
   every mismatch. Dense/profile comparisons are offline and outside decision
   timing. Use the native independent fixtures before mature controls.
2. On all200 roots, reproduce each original projected deployment solve for
   **both menus**, preserving its original checkpoints8..2048 and quality target
   `min(1% of pot,0.1BB)`. Check the original root distributions, sweep counts,
   statuses and quality against PR380. Capture the original final profile and
   audit it against the full production menu **without another solver advance**.
   Report both players' deviation gains, profile values, hero absolute worst-case
   value, and paired differences versus actual blueprint under each law.
   Audit the same fixed profiles under both projected and exact modeled laws.
3. Solve the expanded menu with the structured exact law on all200 roots at
   the same deployment work/quality settings. Audit final profiles against the
   full menu under the exact modeled law, and verify capped-game quality with
   the dense exact oracle. Measure preparation, solving/checks, serialization,
   complete roundtrip, startup, peak memory and offline audit separately.
4. Qualify exact-law retained continuation against the original installed
   profile, with zero new solver advances and existing identity/public-replay
   checks. Nonconverged roots actually deploy blueprint: report their **actual
   fallback policy** and the unconverged solver profile separately. Preserve
   original cases137/195 and diagnose their residuals at the original limit;
   never silently give them more sweeps or move their failure status.
5. Independently reproduce the fixed control, audit and continuation phases.
   All deterministic strategic fields/profile digests must reproduce; timing
   counters and opaque session handles alone are excluded.

Use five ordinary worker processes per panel phase and one16-thread dense-oracle
worker for controls; no unmeasured throughput claim. A small calibration uses
fixed panel cases0,79,137,195 only to forecast cost, never to select a variant.
If it makes the fixed task unaffordable within the quoted scope, stop with the
measurement/quote before launching it; do not reduce counts after seeing results.

## Gates, costs and interpretation

Correctness, information access, accounting, replay and deterministic
reproduction are mandatory. Stop dependent work on a failure, preserve it, and
report it; no automatic scientific retry. Expected nonconvergence remains an
adverse result with labeled fallback, not a correctness exception to suppress.

Preserve the prior latency gates median<=0.5s/p95<=2s, allocation/installed
coverage>=90%, every-decision declared-game quality, and the0.05BB belief
reference-comparison threshold wherever compared. Report all misses and per-case
harms. No new acceptance rule may turn a lower deviation gain into an assertion
of improved absolute hero worst-case value. No whole-hand strength or deployment
adoption follows from this reused engineering panel.

bb128 only for mature work; owned source/build/venv/output roots, normal compute
mutex plus an owned study lock. CPU90C/Thermistor15100C and missing/nonfinite sensor
stops remain. Inspect disk/RAM/swap manually; no added resource/time cutoffs.
Do not alter previous source, inputs, jobs, environments, fans or driver settings.
No subagents, new schedules or other-machine science. Only compact reports/CSV/
JSON/source enter Git; preserve every raw record, partial, failure and binary
under the owned root. Cache/Drive acceptance remains pending until an actual
receipt; no deletion or cleanup is authorized.

Finish with a measured **separate whole-hand cost/variance pilot quote**, including
loading, actual call frequency assumptions, replay, reproduction and off-tree
fallback. Integration time and unknown opponent mix must be explicit. No pilot,
large arena, training or further menu expansion starts automatically.
