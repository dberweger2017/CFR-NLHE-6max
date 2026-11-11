# Learned action baseline: M4 estimator qualification

**Verdict: reject this configuration for the tested workload.** The learned
baseline passes correctness checks but makes estimation less efficient. Do not
allocate bb128 training to this recipe. This is the fixed
[protocol](../../deep-cfr-variance-qualification.md)'s negative result, not a poker
strength test or a rejection of all variance-reduction methods.

The M4 ran once on November 10, 2026, from **21:44:39 to 21:45:27 UTC**
(22:44:39–22:45:27 Madrid), approximately **48.4 seconds including analysis**,
inside the 45-minute allocation. The existing capacity fit finished first;
the remaining queue resumed afterward. No research stages failed or retried.

## Decision

Ratios are candidate/control; lower is better. The primary statistic multiplies
advantage variance by total measured runtime, including collection and fitting.
The advance rule required an upper 95% bound below 0.75, agreement across both
batches, and no established street regression.

| Panel | Variance ratio | Variance × runtime ratio | 95% interval for cost ratio |
| --- | ---: | ---: | --- |
| Pooled | 1.178 | **2.358** | **[1.527, 3.574]** |
| Batch 1 | 1.141 | 2.284 | [1.450, 3.433] |
| Batch 2 | 1.218 | 2.438 | [1.591, 3.738] |
| Flop | 1.601 | **2.812** | **[1.986, 5.266]** |
| Turn | 0.383 | 0.959 | [0.368, 3.778] |
| River | 0.042 | 0.196 | Undefined; no gain established |

The flop establishes an estimation-efficiency regression and blocks advancement.
It also has an adverse raw-variance interval, [1.143, 2.977]. The pooled raw
variance interval [0.767, 1.758] crosses one, so do not claim that raw variance
increased conclusively overall. The turn is inconclusive.

**River uncertainty is retained.** Fourteen of sixteen river roots have zero
observed control variance. In 611/10,000 stratified bootstrap draws the pooled
river control variance is zero, so its ratio interval is undefined. The small
river point ratio is not a qualified benefit; no roots or draws were discarded.

Some roots with zero observed control variance acquire positive candidate
variance (for example `3p100-1-2`). An inaccurate baseline can add noise even
though its correction preserves expectation. This observation does not identify
one causal defect in the critic or justify tuning on this held-out panel.

[Every root and panel](results.json) · [stage costs](verification/stages.json)

The full readout was reproduced offline on M1 from the unchanged repeated
estimates, including the fixed bootstrap and rejected decision. All fields agree
within 1e-12; no sampling or timing was repeated.
[Reproduction receipt](verification/reproduction.json).

## Cost, correctness and integrity

- Control estimation: **13.371 s**; candidate estimation: **21.430 s**.
  Data collection plus fitting/export supervision: **5.330 s**, charged only to
  the candidate. Shared policy/table startup is separately reported.
- One 43,334-parameter 670→64→6 critic; 4,096 rollouts supply **9,272** sampled
  opponent action/payoff rows. One fixed 1,000-step MPS fit; no architecture,
  seed, count or stopping-rule selection after evaluation.
- Forty-eight roots × two batches × 64 repeats = **6,144 paired estimates**
  (12,288 individual advantage vectors), with **1,512,954** total evaluation
  nodes. The reader checks completeness, duplicate absence, finite values and
  identical sampled-tree node counts between arms.
- All **96** root/repeat zero-baseline comparisons are bit-identical to control;
  control estimates also reproduce on repeat. Rust/PyTorch critic parity passes
  all **32** samples; maximum absolute difference **0.00001049 BB**.
- Exact two/three-player Kuhn enumeration checks nonuniform target/sampling
  policies and wrong baselines, with support/finite-value refusals. The ideal
  action-value baseline removes action-sampling variance in its exact fixture.
  A separate test verifies that future deck changes leave critic features
  unchanged, and focal private cards do not change actor-policy features.
- Scientific source **`89b6f308075bc7a27316dae76d5ecbd3435e0111`** has all five
  GitHub checks green: both full-suite shards, scope, aggregate test and
  GitGuardian. CI includes **197 native library tests**; the five focused Python
  tests include an actual CPU fit/export and independent BB-unit reconstruction.
  The native probe was release-built on M1 and executed on M4; the exact binary
  hash is retained. Closeout changes do not replace that source pin.

The original qualification summary counts nodes for its two comparison arms,
excluding the extra control reproduction. That metadata counter was corrected
afterward for future executions. The original receipt remains unchanged; actual
qualification runtime already includes the reproduction. Evaluation counts,
timings, estimates and the decision are unaffected, and no measurement was rerun.

Peak sampled worker-family RSS is **1.30 GiB**, with at least **9.03 GiB**
available RAM and **4.66 GiB** free disk. All 104 resource samples report
**fair** thermal state and pressure level 1. Fitting conservatively reserved
2 GiB for Metal in addition to RSS; the fit reports 40.7 MiB of Metal driver
allocation at completion, not a continuous Metal peak. No guard fired.

[Input/source/binary pins](verification/config.json) ·
[qualification](verification/qualification.json) ·
[critic parity](verification/parity.json) ·
[resource summary](verification/resources.json) ·
[complete measured-file manifest](verification/files.sha256.json)

## Consequence

Keep the experimental implementation and the negative evidence. Do not adopt
this critic or start a longer run. A future baseline design would need a new
prospective protocol; this experiment neither qualifies the mechanism for
training nor rules out stronger critics, different representations or other
variance-reduction estimators. No bb128 compute, live play, model default,
release, archive upload or cleanup follows this result.

## What is being tested

One fixed payoff critic estimates the focal player's return at sampled opponent
actions. It is used only as a control variate, not as a playing strategy or an
uncorrected replacement for simulated returns. For fixed history h and a frozen
baseline b, the estimator is

`Vhat = sum_a p(a)b(h,a) + p(A)/q(A) * (Y_A - b(h,A))`.

Taking expectation over A sampled from q gives

`E[Vhat] = sum_a p(a)b(h,a) + sum_a p(a)(E[Y_a] - b(h,a))`
`          = sum_a p(a)E[Y_a]`.

The correction requires sampling support wherever the target policy has positive
probability. The executable uses q=p and rejects invalid distributions. Recursive
child estimates preserve expectation; enumerated focal values and root regrets
are linear combinations of these estimates. A bad fixed predictor can increase
variance, so mathematical correctness does not imply an efficiency gain.

The critic sees the actor's ordinary features together with the focal seat's
hole cards and position. These combined simulated-seat inputs remain inside the
experimental training-time estimator and use a distinct non-policy file format.
The playing network receives only its unchanged seat observation. Future deck
cards are never critic inputs.

## Scope and interpretation

- Forty-eight fixed complete-deal roots, stratified by street and table family.
- Two evaluation batches with 64 repeated estimates per root and arm.
- Variance of legal action advantages, averaged over actions and then roots.
  Units are BB squared, not a poker win rate.
- Conditional action-sampling variance, not card-deal variance or exploitability.
- One fixed policy and one fitted critic. No claim about training-seed robustness,
  stronger poker, deployment, or six-player convergence follows.
- The primary cost ratio charges collection, fitting and inference. Any cheap
  predictor that fails to reduce total cost is not an advance under this protocol.

## Retained evidence

Ordinary files are retained on M4 under
`/Users/dberweger/deep-cfr-variance-20261110/`: exported source and revision, the
native executable, queue handoff receipts, and the `run/` evidence tree. Model,
training rows, repeated-estimate payloads and full logs stay off Git. Packaging,
cleanup and archive acceptance are separate work; this PR makes no Drive claim.
