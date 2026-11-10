# Learned baseline qualification on M4

Owner approved November 10, 2026. Experimental estimator qualification only;
no bb128 allocation, playing-policy change, production-trainer change or automatic
training follow-up. Use an isolated `feature/` branch and retain adverse results.

## Question and estimator

Can a learned action-value baseline reduce the error of sampled action advantages
per unit of total compute? Freeze `adv1375.npnet` from scratch run 1, with its
SHA256 `d57c79d81cf5656ce5a7c45912e2047817cb1dd715b8c50666accd90df87d9db`
and the existing K50 hashes recorded before execution. The experimental
continuation uses the frozen regret-matched strategy, expanding focal decisions
up to three per street/eight per path and sampling thereafter. Root actions are
enumerated. Sampling bounds restart at the selected root; this qualifies local
continuation estimates, not equivalence to the whole-hand training distribution.

At a sampled **opponent** node, use

`sum_a p(a)*b(h,a) + p(A)/q(A)*(Y-b(h,A))`.

Here `q=p`; the explicit ratio is retained in the tested general formula. Baselines
are fixed before evaluation. Require q>0 wherever p>0; zero-target actions contribute
zero. The baseline is trained to predict the focal seat's terminal BB payoff,
not the actor's. It sees the actor's normal policy features plus the focal hole
cards and focal position. This is a **training-only critic**: it combines two
seats' simulated information, never enters a playing policy, and never reads the
future deck. Opponent hidden cards do not enter actor/strategy features through
this addition. No chance-node baseline or correction at sampled focal nodes.

## Frozen test design

- Seed 20261110850001 for fitting roots, 20261110850002 for held-out roots.
- Twelve strata: flop/turn/river × 3p100, 4p100, 6p100, 6p mixed-depth.
  For each stratum select the first four eligible roots under the frozen strategy,
  each from a different starting deal; fitting uses separate deals. Eligibility:
  target street, active focal actor, at least two legal menu actions. Never select
  by payoff or estimated benefit. Maximum 20,000 candidate deals per stratum;
  failure to fill any stratum stops admission.
- Fitting: 4,096 independent rollouts, balanced over those twelve strata. Record
  sampled opponent action/payoff pairs. Explore the root's legal actions uniformly
  to cover alternatives; subsequent actions use the frozen strategy. One
  670→64→6 ReLU critic, seed
  20261110850003, AdamW lr .001, 1,000 steps, batch 512, squared error on the
  sampled action. Payoffs scaled by 100 for fitting; export restores BB units.
- Evaluation: 48 held-out roots, 64 independent repeated estimates per root in
  each of two independent batches. These roots include fixed complete deals;
  variation is action sampling conditional on each deal, not a claim about
  posterior hand ranges. Root is the bootstrap cluster. Control/candidate receive
  identical RNG seeds; run order alternates by root/batch. Report elapsed time and
  process CPU time, nodes and baseline calls. No network tuning or seed selection.
- Pooled error is the equal-root mean of unbiased sample variances of each root's
  legal action advantages (then averaged over its legal labels). Also report each
  street and each batch. Do not estimate sampling error from correlated actions.
- Cost-adjusted ratio = candidate variance / control variance × candidate total
  wall time / control wall time. Candidate total includes collection, fitting,
  export and measured estimator work; shared frozen-model/table startup is
  reported separately. No hypothetical future amortization in the main verdict.
  Allocate the fixed collection/fit cost equally across the two batches and
  across streets when reporting those subsets; do not double-charge overhead.
- Bootstrap roots within strata, 10,000 resamples, fixed seed 20261110850004.
  Report 95% intervals for variance and cost-adjusted ratios. Timing uncertainty
  is not represented by the root bootstrap; report batches separately as a check.
- **Advance** only if pooled cost-adjusted ratio's upper 95% bound < .75,
  each batch's point ratio < .75, and no street has ratio lower 95% bound > 1.
  All correctness gates must pass. If pooled lower bound >= .75, reject this
  configuration for this workload; otherwise inconclusive. Any established
  street harm blocks advance regardless of the pooled result. No extra samples.
  A zero sampled control variance in the panel or bootstrap makes that ratio
  unidentifiable; report it and do not advance or discard those roots/draws.

## Correctness and admission

Enumerate a small poker game under nonuniform policies with exact, inaccurate,
zero and deliberately extreme baselines. Verify expected values and root regrets
equal exact enumeration; cover off-policy q and unsupported-action rejection.
Test zero-baseline identity, finite values, deterministic reproduction and
Rust/Python critic parity. A second evaluation batch is replication of the
estimator measurement, not an independent training seed.

M4 only, sequential with other research. Calibration, collection, fitting and
measurement share a **45-minute hard wall cap**, including failed attempts.
Calibration checks fixed counts against the remaining allocation before main
execution; if not admitted, stop with a quote rather than shrink the design.
No automatic retry, extension or changed counts. Limit process-family RSS plus
reported MPS driver allocations conservatively to 6 GiB, available RAM headroom
2 GiB, new output <= 5 GiB and free disk >= 2 GiB. Stop on nonfinite arithmetic,
unexpected process exit, owner STOP or serious/critical thermal pressure. Build
and correctness testing are engineering work outside the research measurement
cap; record them separately. Preserve partial files and failure receipts.

## Deliverables

Protocol, opt-in executable, learner, meaningful correctness tests, admission and
resource receipts, pinned source/input/binary hashes, compact results and
advance/reject/inconclusive report. Ordinary model/data files remain ignored on
M4 for the cleaner; do not archive, remove or upload research payloads here.
A successful result authorizes a proposal for a training comparison, not a launch.
