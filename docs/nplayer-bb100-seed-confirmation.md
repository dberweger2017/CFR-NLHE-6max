# Two independent 100 BB 3B→10B confirmations

[Proposal356](https://github.com/dberweger2017/CFR-NLHE-6max/issues/356).
Owner authorized the new PR, qualification and one overnight training/evaluation
attempt on October20 Madrid. This prospective protocol precedes final training.
The original PR355 lineage remains the leading research candidate, with 3B kept.

## Fixed training

Fresh seeds **202610200601 and202610200602** each train from zero to3B, then
resume their own raw3B checkpoint to10B. Stop at the first complete iteration
at/above each endpoint. Preserve three100BB stacks,50/100blinds, K50 pinned
tables, the PR355 menu/key schema, fullfloat64 opponent-sampled average,
unpruned fast8roots/seat and16threads. Build against historical training library
`b9882e7e728847a58691995e64eabd4563ea0991`, using the qualified PR355 native
binaries when their build/overlay hashes match. No pruning, compact-key migration,
new storage recipe or search enters this strength comparison.

Each fresh lineage has nominal250,000,000-entry capacity, with the same native
iteration-boundary overshoot rule. Once capacity freezes, preserve its exact key
set, entry count and freeze marker through10B. Different seeds need not retain
the same keys or precisely the same number of entries. Audit every checkpoint
row/export and derive original-mass metadata at both endpoints. Preserve raw
checkpoints, average exports, full audit proofs, source/binary/config pins and
all failures. Do not select checkpoints using poker outcomes.

## Fixed evaluation

For each new seed, repeat PR355's18lineups: reciprocal own3B/10B matches,
two copies of each random/check-call/TAG/pot-pressure script, fixed own3B plus
check-call or pot-pressure, check-call+pot-pressure, and random+TAG.

Add a **cyclic cross-seed panel**, not a full population tournament. Let S0 be
PR355's original seed2026101935003, S1/S2 the two fresh seeds. Compare each
focal3B and10B singleton against two copies of a fixed3B from another seed:
S0→S1, S1→S2, S2→S0. These are six additional lineups. Opponents do not change
between a focal lineage's paired versions. Cross-seed contrast is the full
singleton return difference, unlike the reciprocal direct statistic's factor½.

Each of **42lineups** uses8192 independent six-hand blocks with all six
identity/seat permutations: **2,064,384 initial hands plus2,064,384 exact
reproductions**. Reproductions and seats are not independent statistical samples.
Fresh final roots are20261020610001–009 forS1,20261020610101–109 forS2,
and20261020610301–303 for the cyclic panel. Only adjacent paired versions share
a root; qualification roots are disjoint and never enter final results.
The frozen generator in`scripts.nplayer_bb100_confirmation` is authoritative.

At most two inference models are resident. Within-seed matches retain PR355's
matched per-decision positive-mass/zero-mass/missing probes and fixed-membership
assertions. Cross-seed play uses the already-qualified ordinary native arena:
independent tables can legitimately disagree on presence, so those assertions
must not be applied across seeds. Retain cross-seed own-missing/seat/street
counts; do not mislabel every represented row as positive mass without metadata.

Every initial trace must independently replay and every reproduction must match
its trace SHA256 before the **whole42-case payoff readout**. No interim scores,
outcome-driven extension, checkpoint selection or automatic scientific retry.
Partial failed runs remain terminal evidence. One failure stops the owned group.

## Statistical decisions, fixed before final hands

Report absolute and paired returns, per-seat and button-relative-position
results, street/lookup counts, table-wide mass changes and actual costs.
Independent units are six-hand blocks, as in PR355.

- Two new reciprocal direct primary contrasts: mean oriented singleton contrast,
  not pooled player return or a heads-up win rate. Report ordinary95% intervals
  and simultaneous family95% intervals across the two new primaries
  (Bonferroni2). **Repeated gain** requires both adjusted lower bounds>0.
  The original single-seed result is discovery evidence, not a third fresh test.
- Sixteen script/mixed differences: ordinary95% plus family95% across16.
- Three cyclic differences: ordinary95% plus family95% across3.
- Conservative recommendation safeguards: every cyclic lower bound>−5BB/100,
  and every script/mixed lower bound>−50BB/100. These are declared tolerances,
  not a claim that a loss of that size is desirable. The present sample can be
  inconclusive, particularly on high-variance scripts. Report each failed bound;
  crossing zero or failing noninferiority does not prove harm or equivalence.
  An adjusted upper bound below its negative margin establishes a loss beyond
  that tolerance in this panel. Do not retune margins after observing outcomes.

A primary pass with unresolved safeguards remains conditional research evidence.
Do not turn averaged seeds into a pass if either fresh primary fails. Three fixed
training seeds including discovery are still a small population; no universal
superiority, Nash-convergence, external-strength or release claim follows.
Owner decides adoption, release and additional computation after final review.

## Cost and overnight readiness

Planning allocation: **roughly4–6hours**, up to40childCPU-hours on bb128. This is
a forecast/manual allocation, not a new coded runtime kill guard. Expected work:
about21minutes fresh0→3B training plus50minutes continuation across both seeds,
~16minutes save/export, ~27minutes four full audits, ~17minutes within-seed policy
loads, ~38minutes cross-panel policy loads, plus verification, replay, readout,
qualification and verified HDD staging. The whole-job forecast must be updated
from actual progress; active training alone is not the completion ETA. No loader
speedup is assumed. Weak results never justify extending the declared samples.

Reuse the qualified native build by exact hashes; do not spend overnight time
rebuilding unchanged Rust. Qualification must still run the existing realK50
historical-vs-resumed parity and diagnostics-on/off fixtures, then an end-to-end
small confirmation with both new seeds, distinct frozen key sets, every matrix
shape, audits, cross-seed cache transitions, every replay/reproduction proof,
global readout and the exact staging path. Verify thermal crossings, changed
configuration refusals, wrong inputs and partial-copy preservation. Stage intended
files and pass the repository artifact check before committing/deploying.

Training is sequential16threads; audits/replay use8workers. Required automatic
resource stops remain CPU90°C, Thermistor15100°C and missing/nonfinite required
readings. Retain both compute mutexes, owner STOP and signal cleanup of owned
process groups. There are no automatic time, RSS, disk or swap stops. Inspect and
report disk/swap/RAM manually. Do not change fans, drivers, BIOS, other jobs or
machines. Do not restart failed final science automatically.

## Owner-authorized new-output placement

ObservedNVMe free38.4GB cannot retain the forecast85–100GB. On October20 the
owner specifically approved staging **this new study's** completed checkpoints,
exports and verified traces onto2TB between phases, with verified copies and
accessible paths. This does not authorize moving PR350/355 inputs.

Training and initial save/export stay onNVMe. After a checkpoint's export and
full audit complete, copy that checkpoint to the new per-PR HDD cache, verify
source/destination SHA256 plus original size/mtime, fsync the copy/restoration
record, and atomically replace its original pathname with a destination symlink.
Stage verified case traces/exports/metadata after each lineage's evaluator exits,
before starting the next lineage. At-rest inputs may then load through their
preserved paths; account for HDD-read costs. Never relocate an actively written
file. Source/destination hash mismatch preserves both and stops the attempt.
A partial destination is never overwritten by automatic retry.

The per-file`relocations.jsonl` records old path, destination, bytes, SHA256,
mtime and time before pathname replacement. Each destination remains an ordinary
unpacked research file; the operation is relocation, **not Drive acceptance or
purge**. Keep all originals' accessible paths, partials and receipts. Final Drive
archival remains governed by[artifact storage](artifact-storage.md); no upload,
eviction or current-input cleanup is implied. Record actual per-PR roots and
retrieval commands inRESULTS_INDEX after launch.

## Engineering work, separate from the overnight contrast

### Cheaper inference loading

PR355 recorded502.13s loading and22.50s playing, including reproduction, within
624.39s native evaluation and4366.16s whole campaign. Loading is about80% of
native evaluation but11.5% of whole campaign, not80% of total training work.
The evaluator already reuses loaded tables. Optimize parsing/decompression/
allocation and resident representation rather than merely adding persistence.

A subsequent implementation should add a versioned binary or memory-mapped
inference artifact derived from an exact existing average. Bind source SHA256,
key/menu/card/game schema, average scope, dtype, byte order, row count, offsets
and payload hash. Validate full-row lookup/action-code/probability parity,
including missing/zero-mass behavior and original-mass tags; no float32 shortcut.
Reject truncation, corruption, wrong schema and source mismatches. Retain the
original average and conversion provenance; no raw model entersGit.

Benchmark the same mature policies, same host, with conversion reported
separately and a fixed alternating order: three loads per format under ordinary
warm-cache conditions, plus first-use observations labelled honestly. Do not
clear the global page cache or disrupt other jobs. Report time-to-first-action,
full-parse/page-fault costs, physical/file/resident bytes and complete18-lineup
wall, including any lazy work during play. A useful target is at least2× median
warm load improvement without altered action trajectories; it is not a measured
promise. Quote its compute before that separate benchmark; do not insert it
midway into the confirmation. PR344 compact keys remain a separate fresh-training
optimization and cannot be resumed by relabelling existing hashes.

### Separate native CPU river prototype

Build on existing native search and the linear-leaf analysis in
[issue328](https://github.com/dberweger2017/CFR-NLHE-6max/issues/328), without
modifying the active M4[PR317](https://github.com/dberweger2017/CFR-NLHE-6max/pull/317).
Start with two-live-player river subgames, float64, sorted ranks, blocker sums,
identical-holding corrections, reusable buffers and a persistent native process.
Profile range construction/tree preparation/profile transfer as well as leaves.
No GPU blueprint training or full three-way river claim.

Separate prepared-tree/ranges→strategy solver latency from legal-observation→
action latency. Compare leaf values, game values and best-response quality on
small known games and fixed river fixtures; tiny rounding changes can alter CFR
policies, so exact policy equality is not the solver acceptance criterion.
Declare numerical tolerances against the reference before benchmarking, and
measure quality at0.25/1/5/15/50ms work budgets and fixed iteration counts,
including overruns. Sub15ms complete decisions are a target, not established.

Ranges use public history and the acting player's private information only,
never the real opponent's hidden holding, deck or evaluation seed. Search is
not automatically opponent adaptation or a remedy for the scripted declines.
Adoption needs its own prospective paired poker test and regression safeguards.
The prototype is an engineering follow-up, not an extra overnight science arm.
