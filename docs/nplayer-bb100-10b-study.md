# Fixed 100 BB blueprint: 3B to 10B

[Proposal354](https://github.com/dberweger2017/CFR-NLHE-6max/issues/354).
Owner authorized opening a separate implementation PR on October19. This PR prepares and qualifies the runnable study; it does not launch the main campaign.

## Question

Does extending the fixed unpruned three-player100BB3B model to10B improve the retained blueprint, and where does performance change against mixed opponents?

Owner direction October19: compare the fixed3B model with its10B continuation, preserve250M membership cap/current recipe, include mixed trained/scripted lineups and per-decision positive-mass/zero-mass/missing lookup status.

## Fixed lineage and scientific scope

Resume PR350 checkpoint `3000000000.gz`, SHA256 `ea0c7dca97ae627b08a39d4196cdd824d6e0767d85ca64c829eae5dcceb2da6b`; average `c602c3727df28160a9807716d3c9211d988e420c33ed7b0c04c2fd899afef06b` is immutable3B comparator. Seed2026101935003, three100BB stacks,50/100blinds,K50, current schema/menu, fullfloat64 averaging, unpruned fast8roots/seat,16threads. Membership already froze at250,000,475entries around2.09Bnodes: preserve exact membership/key-set SHA256 `a83858109eed965e73acd76787761d9353f2a66cccb482c0271173e3ff731425`. No compact-key/storage migration or pruning. One declared10B endpoint, first complete iteration at/above target; no outcome-selected checkpoints.

## Proposed final matrix

Let A=the singleton under evaluation (10B or3B), R=the immutable3B reference. All copies own independent action RNGs.

- Direct:10B vs R+R, and R vs10B+10B; mean oriented singleton contrast as in PR352, not pooled player return.
- Homogeneous script safeguards: A vs two random/check-call/tight-aggressive/pot-pressure opponents.
- Mixed trained/scripted: A vs R+check-call and R+pot-pressure.
- Mixed scripts: A vs check-call+pot-pressure and random+tight-aggressive.

Each non-direct configuration plays both A versions on paired deals/action roots. All six permutations rotate identities/positions.18lineups×8192six-hand blocks=884,736initial hands, plus884,736exact reproductions; all independently replayed. The trained opponent is a fixed100BB model from the same seed, not an independent-seed population. Never substitute20BB policies. Freeze exact scripts, assignments, fresh disjoint roots, model/native/config hashes and sample counts before final play. No payoff inspection before global replay/reproduction barrier.

## Required diagnostic instrumentation

The existing normalized export loses original average-mass information. Uniform probabilities cannot identify zero mass. Derive sorted zero-mass membership metadata from each raw checkpoint during its audit, bind it to checkpoint/exportSHA256, verify complete row accounting and refuse missing/incorrect metadata. Keep existing policy bytes and sampling semantics unchanged. Preserve the3B checkpoint/policy read-only; write metadata to the new study root.

For every model decision, record model identity, key hash, `positive_mass`, `zero_mass` or `missing`, street, physical/button-relative position, public pot/number of live players and selected action. Script entries are `not_applicable`, not `missing`. For each reached model decision, probe both frozen policies on the exact same acting-seat observation without sampling, and record both lookup labels; only the acting policy samples an action. This separates mass changes on matched states from changes in which states are reached. Because membership is fixed, a missing/present disagreement on the same key is a correctness failure. Labels never change policy inputs/probabilities or consume RNG. Positive mass means original average accumulator total>0, not necessarily a well-trained row; zero means a represented row with exactlyzero original mass using the historical fallback. Exact positivity/finiteness follows checkpoint semantics, with no invented epsilon.

Qualification must prove: positive-mass uniform and zero-mass uniform rows get different labels, missing keys are distinct, wrong sidecar/model lineage refuses, all per-decision/counter totals reconcile, and instrumented vs old evaluator produce exactly the same deals/actions/payoffs on small realK50 fixtures. A fixed checkpoint-resume smoke must prove unchanged native training/checkpoint bytes and frozen membership. Measure instrumented loading/RAM/trace overhead before the main launch.

## Readout and decision

Report direct95% interval and eight paired opponent-configuration differences with pointwise95% and exploratory family95% Bonferroni intervals across the eight. Independent units are six-hand blocks; reuse neither reproductions nor seats as independent samples. Positive direct lower95% is evidence of improvement for this one continuation. Report adverse configurations and uncertainty; no equivalence claim from a crossed-zero interval and no automatic default/release promotion.

Report both policies' absolute returns, per-seat/position coverage, per-street/lookup-status frequencies and descriptive reached-street returns, zero→positive transitions on matched keys, recurring paths, pot bands and actionable two-live-player river frequency. Coverage/return stratification is descriptive: different policies may reach different states. No causal claim that a missing/zero row caused a loss without a separate counterfactual test. Unsupported histories versus represented-but-untrained states remain separate concepts.

## Cost, host and launch boundary

bb128 only; sequential16-thread continuation followed by a persistent two-model evaluator. No extra model family or additional training seeds. Historical post-freeze4.83Mnodes/s suggests roughly24minutes active training for the remaining7B; this is not a complete-job ETA. Loading/saving/exporting/hashing/audits/evaluation/replay and instrumentation qualification must be measured/quoted separately before launch. Reserve RAM for the host using observed peak/headroom; inspect disk/swap manually. Owner's current temperature-only automatic resource stops remainCPU90C/Thermistor15100C/missing temperature readings, with mutex/manualSTOP and genuine correctness/accounting/replay failures; no new arbitrary runtime/RAM/disk/swap kill thresholds. No automatic extension/retry after a failed scientific attempt.

This issue records the accepted scientific direction; implementation, exact frozen manifest and complete ETA return for review before new training or matches. It does not launch a campaign. PR352/353 source evidence and PR350 inputs remain protected; no cleanup, archive movement, new driver/fan settings or other-job edits.


## Implementation and explicit operator commands

`scripts.nplayer_bb100_continuation` owns the frozen18-lineup manifest, historical
native build, qualification/configuration boundaries, temperature-only process
supervision, exact continuation, audits, persistent mixed evaluation and global
readout. `scripts.qualify_nplayer_bb100_continuation` runs only the small fixtures.
The native training library is archived from PR350 source`b9882e7e`; no current
storage/key changes enter the model. Native example overlays change only shared
checkpoint I/O and the new mixed diagnostic evaluator. A separate historical
host is compiled unchanged for the checkpoint/trajectory qualification.

The optional `--lookup-out NEW_DIRECTORY` flag of
`scripts.audit_nplayer_policy_parallel` emits `zero-keys.bin` plus a passed
`receipt.json` commit marker during its existing row audit. Partial files remain
without a valid receipt on error. Normal audits omit this option and preserve
their previous return format and behavior. The receipt binds all-row keyset,
positive/zero counts, zero-key bytes, checkpoint/export hashes and average scope.
Uniform positive-mass policies and uniform zero-mass fallbacks remain distinct.

Native `nplayer_continuation_arena batch MANIFEST` loads at most the two frozen
models and one K50 table set. Each labeled identity receives its own unchanged
RNG. Per-action`lookups` align with`states`/`actors`/`actions`; script entries are
`not_applicable`. Each model decision records the acting alias, key, both mass
labels in[baseline,candidate] order, street/position/public pot/live count and
chosen action. Summary lookup counts index[identity][street][model][status],
status order[positive_mass,zero_mass,missing]. No diagnostic reaches a policy
input or alters its action distribution/RNG. Checkpoint/policy export bytes
remain in their original format; the mass metadata is an additional artifact.

Example preparation on bb128 using its already qualified venv (do not resolve
its executable symlink):

```sh
python -m scripts.nplayer_bb100_continuation build /ABS/NEW_BUILD
python -m scripts.nplayer_bb100_continuation qualify /ABS/NEW_QUAL \
  --build-root /ABS/NEW_BUILD --tables /ABS/K50 \
  --python /home/dberweger/nplayer-fast-strength-20261018-main-v5/venv/bin/python
python -m scripts.nplayer_bb100_continuation configure /ABS/NEW_MAIN \
  --build-root /ABS/NEW_BUILD --tables /ABS/K50 \
  --python /home/dberweger/nplayer-fast-strength-20261018-main-v5/venv/bin/python \
  --qualification /ABS/NEW_QUAL/qualification.json
```

These commands do not start the main experiment. The separately authorized
launch is`python -m scripts.nplayer_bb100_continuation run /ABS/NEW_MAIN`.
Existing launched roots refuse reuse without modifying their receipts; there
is no automatic failed-science retry. Final readout follows all18verification
proofs and returns one direct contrast plus eight adjusted opponent contrasts,
absolute/seat/position returns, matched lookup transitions, coverage, descriptive
paths with replay references, pot bands and actionable river counts. Reproduction
hands add no statistical samples. All source/native/config/metadata hashes and
training/save/load/audit/play/replay costs remain separate in the receipts.
