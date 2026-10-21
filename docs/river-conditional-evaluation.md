# River policy-expectation evaluation: bounded qualification

Owner approved this next task on October 22, 2026, following merged PR388.
Qualify an evaluation method, not a changed player or a strength claim. Keep the
blueprints, search menu/recipe, fallback, earlier streets and training frozen.
Off-tree re-solving and exact-runtime optimization remain separate work.

## Quantity and inclusion

Use every eligible first-river root in PR388's verified initial search-on traces:
384 roots, including 381 installed profiles and three quality fallbacks. Include
roots whose sampled action did not change. Keep all six lineups and all original
128 six-permutation blocks per lineup; hands with no eligible root contribute
zero to the paired contrast. Do not select observations or methods by returns.

For a fixed dealt world and common pre-intervention history, integrate **all
future action randomness** under the actual on/off policies. The board is
complete; the privileged evaluator owns all dealt cards and settlement. Each
policy still receives only its own legal acting-seat observation. Search beliefs
and strategy construction never receive the evaluator's hidden cards.

The hand contrast is expected terminal net return on minus off, in chips. With
100 chips/BB its six-permutation block average is numerically BB/100. Average
these blocks, including zeros, to preserve the whole-hand estimand. An average
only among eligible roots is a separate conditional diagnostic, not the primary
comparison. Repeated evaluation/reproduction adds no statistical samples.

Query the actual trained policy and existing script likelihoods on every branch.
Use the full legal production action support, including scripted legal actions.
The retained search tree limits the hero's search policy, not the evaluator's
game tree. After the first omitted action, use the existing blueprint for the
remainder of that branch. Quality-fallback roots have identical policies and
therefore exactly zero expected contrast; retain them explicitly.

Reconstruct original profiles at their original work settings and require their
saved profile hashes, installation/fallback status and actual root distributions
to match before evaluating. No additional convergence or configuration tuning.
Keep each counterfactual continuation isolated, with immutable shared profile
payloads and separately owned session progress. Never sample a clairvoyant hero.

## Implementation qualification

1. A native chance-free expectation walker uses the existing integer-chip engine
   for transitions and terminal net returns. It accepts policy rows through an
   acting-observation-only callback and returns explicit complete/incomplete
   status. Never turn partial enumeration into a point estimate.
2. Compare with an independently enumerated small-fixture leaf list, including
   ties, folds, refunds/unequal stacks and stochastic opponent branches. Require
   values within 1e-10 BB on these fixtures, legal action probability mass,
   deterministic reproduction and zero-sum settlements. Reject invalid rows.
3. Qualify actual retained and fallback rows, branch isolation, original-profile
   identity, and evaluator-only hidden-card access. Preserve saved cap/all-in
   cases21/91; no new resolving behavior is introduced.

No positive-probability branch is silently dropped, clipped or assigned a
heuristic value. Skip only exactly zero-probability actions. Float64 arithmetic
is reported with its fixture tolerances; "complete" means all positive-support
branches were visited, not exact real-number arithmetic.

## Bounded saved-data experiment and admission

Inputs stay read-only under
`/home/dberweger/river-whole-hand-pilot-20261021-v2/main-v1/` and its original
model/K50 paths. Main source is PR388 runtime
`46caeceb88d24733f393f567c2b1e2fd6300cc4d`; retain its verified trace pins and
root/profile identities. No new poker deals, training or strength arena.

First freeze the complete inventory and qualify fixtures. Cost calibration uses
the first two root IDs in each of the five nonempty lineups, plus all three
recorded quality misses, deduplicated and sorted by lineup/hand/decision. This
selection uses public work/status metadata, not returns. Check-call/check-call
has no roots and is retained as a no-intervention panel.

The prototype has a fixed **200,000 visited states per arm per root**, including
terminals; it is an algorithmic enumeration qualification limit, not an elapsed,
disk, memory or swap kill guard. A hit produces `incomplete`, with no usable value.
Do not drop that root, raise the limit or swap methods after seeing its result.
No precision claim is made if any required root remains incomplete.

Publish measured calibration time, nodes, completion and a quote before any
full-inventory job. The owner has authorized implementation, small qualification
and bounded calibration; a larger saved-data allocation beyond a routine small
prototype needs an explicit accepted quote. Never start a larger strength study.
Full-inventory assessment, if admitted, uses exactly all 384 roots and one fresh
reproduction, without added roots or scientific retries. No automatic admission
is inferred from a positive expected-return estimate.

All owned remote stages use the normal compute mutex plus this study's mutex.
Only automatic resource stops are CPU90°C / Thermistor15100°C or missing/nonfinite
required sensors. Owner STOP, broken accounting, information/identity/numerical
or replay errors stop this job's children. No time/RSS/disk/swap cutoff; inspect
those resources manually. Use only bb128 for model measurements, new owned
outputs and existing inputs/environments read-only. No fan/driver changes,
other jobs, cleanup, schedules or subagents.

## Efficiency readout and limits

Require complete inventory coverage, original-profile identity and reproducible
values before the global expected-contrast readout. Report sampled and integrated
means, block SD/variance and tail concentration for each lineup, preserving
adverse panels. Sampling/reproduction copies never increase the block count.

Compare variance multiplied by total compute cost at the same independent
six-permutation-block unit. Separate cold model loading/profile reconstruction,
enumeration, trace verification and amortized evaluation cost. An efficiency
ratio below one suggests reduced compute for the same precision; reduced variance
alone does not establish that. Zero-variance no-intervention panels have no
defined variance ratio. Block pairing/covariance means a per-hand reduction is
not automatically the same block-level reduction.

If complete values are available, a fixed 10,000 paired block bootstrap with
analysis RNG seed2026102239001 may describe sensitivity of variance ratios.
Sparse tails and one trained lineage prevent a guaranteed precision forecast.
These saved pilot roots are development data, not fresh strength confirmation.
The evaluator removes future-action sampling noise only; deal/prefix/seed
variation remains. Report failures and incomplete coverage without retry/tuning.

Finish with a measured method verdict and conditional fresh-study quote, or a
concrete explanation of why enumeration did not qualify. No automatic campaign
follows. Raw inputs/profiles/traces remain off Git. Stage intended compact files
before the repository artifact check. Preserve all failures and originals;
archive only owned evidence through the deployed research cache with verified
receipts, no deletion and no cloud-acceptance claim before receipt.
