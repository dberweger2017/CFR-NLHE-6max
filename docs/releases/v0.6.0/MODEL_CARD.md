# v0.6.0 model card — three players, 100 BB

Release preparation; not published yet. This release packages the three frozen
10B-node all-street average blueprints qualified by PR367, seeds 2026101935003,
202610200601 and 202610200602. The binary derivatives preserve every sorted key,
action code, float64 probability bit and original-average mass tag from the
checkpoint-audited averages. No retraining, model selection, ensemble, pruning
recipe change or search is introduced. Explicit seed selection is required.

Each is unraked no-ante three-player Hold'em, equal 100 BB stacks,0.5/1 blinds,
K50 postflop cards and the exact `min-pot-conditional-jam-v1` menu. Averaging
covers every street. Each lineage freezes membership at approximately 250M keys;
continued training refines retained keys and does not expand that membership.
Missing keys and represented zero-mass rows use the unchanged uniform fallback.

## Fresh acceptance

PR367 froze counts and a one-sided simultaneous 95% Bonferroni 30 family before
fresh hands. All 30 decisions pass: 24 absolute profits against identical-script
and mixed fields, three gains over own 3B checkpoints and three cyclic continuation
robustness tests above −5 BB/100 against fixed other-seed3B pairs. All 36 cases
independently replay 2,635,776 initial hands and exactly reproduce the same number.

Own-checkpoint mean oriented singleton contrasts (half paired reciprocal
singleton differences, not pooled player returns):

| Seed | Gain BB/100 | Adjusted lower bound |
|---|---:|---:|
|2026101935003|+32.79|+22.06|
|202610200601|+35.78|+22.21|
|202610200602|+33.70|+21.98|

The weakest absolute-profit lower bound is +16.08 BB/100. Cyclic lower bounds all
exceed 0, above the declared −5 margin. Each cyclic test compares 10B_A with 3B_A
against the same two 3B_B opponents; it is not a 10B-vs10B population tournament.
All results, roots, counts, source/checkpoint/model hashes and exact intervals:
https://github.com/dberweger2017/CFR-NLHE-6max/blob/main/docs/reports/nplayer-v06-acceptance/results.md

## Adverse evidence and limits

PR357's relative scripted safeguard remains failed: both fresh lineages regressed
against random and random+TAG after adjustment, with five unresolved −50 BB/100
bounds across that study's panels. The fresh acceptance criterion is positive
absolute profit; it does not erase or freshly re-estimate those relative losses.
Three fixed training lineages and scripted/internal comparisons do not establish
Nash convergence, human/professional strength, universal superiority or that
future search remedies any weakness. No external three-player benchmark is claimed.

The current runtime loads one model eagerly; recommend 32 GB RAM and 35 GB free
working disk per selected seed. The 16 GB laptops are not a supported full-model
target. Multiple bot seats share the same weights but use separate decision
seeds. Restricted sizing is mandatory because action translation is not part of
this n-player recipe. Search is reserved for v0.6.5; 200 BB requires a separately
trained/qualified model (v0.6.1). Existing heads-up releases remain available.

Code is MIT; the original engine authors' licence remains unresolved as recorded
in the repository licence audit. No new licence grant for third-party work is
implied. Models and runtime are a research preview, with the stated evidence and
limitations rather than a professional-strength claim.
