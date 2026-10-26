# Making the 100 BB overnight campaign fit

Implementation plan for [PR350](https://github.com/dberweger2017/CFR-NLHE-6max/pull/350),
following the [completed admission pilot](reports/nplayer-bb100/results.md).
Scope is three players at **100 BB**, targeting **10B nodes per seed across three
fresh seeds**. The 200 BB campaign is separate. This document proposes the next
implementation and qualification; it does not launch another experiment or
change the completed pilot's limits.

## What the measurement establishes

We observed 113M entries and 10.53 GiB sampled process RSS at 500M nodes. The
131.8 GiB figure at 10B is an extrapolation from the last measured interval, not
an observed allocation or proof that 10B cannot fit. New keys per added node are
already declining: 0.371, 0.252 and 0.169 across the three intervals. We need a
longer growth curve before choosing a campaign entry ceiling.

There are three separate constraints:

1. The training table's entries, index and regret/average values.
2. Checkpoint/export formatting, compression and subsequent load/audit costs.
3. Evaluation policy storage and simultaneous resident models/workers.

The pilot spent 97.77 seconds training and 686.84 seconds saving. Solving only
training throughput or only bytes per training entry does not admit an overnight
campaign.

## Historical precedent changes the recommended route

The closest previous solution is **fixed-capacity training**, not only storage
compression:

- [PR262](https://github.com/dberweger2017/CFR-NLHE-6max/pull/262) added frozen-table
  training. After a predeclared entry ceiling is reached, existing keys keep
  learning while new keys are not retained; unseen states use the existing
  uniform fallback. The [engineering report](reports/frozen-table.md) records
  exact recovery, discarded-update accounting and why fixed entries are not a
  fixed-RAM guarantee.
- [PR265](https://github.com/dberweger2017/CFR-NLHE-6max/pull/265) used it to continue
  HU200 from 752.6M to 20B nodes on exactly 85,373,907 keys, on the 16 GiB M4.
  Its measured family peak during continuation was 8.79 GiB, including supervision;
  after-save RSS was not used as a substitute for that peak.
- [PR268](https://github.com/dberweger2017/CFR-NLHE-6max/pull/268) then found
  +76.95 [71.93, 81.96] BB/100 for the 20B model over the starting model. The
  5B-to-20B change against that same parent was +0.09 [-8.36, 8.54], inconclusive.
  This supports trying density-focused learning, not assuming every extra node
  helps or transferring a heads-up result to three players.

**Recommended candidate for owner decision:** grow each fresh 100 BB table to a
predeclared affordable capacity, save its freeze-boundary anchor, then keep
training its existing entries to 10B. A **250M-entry cap is a starting quotation
candidate**, not an admitted main setting. Qualify it against fully allocated
regret/average storage, transient deltas and save peaks before selecting it.
The current N-player CLI/library already supports `--freeze-at-cap`; the overnight
wrapper currently refuses it and needs explicit integration and qualification.

This is an explicit change from unrestricted table growth, not a lossless storage
optimization or an automatic fallback. No capped-table campaign is launched by
this plan. Keeping full averages, float64, K50, the same action menu and unpruned
fast sampling does not remove the limited-coverage tradeoff of a frozen table.

Other earlier fixes are also directly useful:

- [PR206](https://github.com/dberweger2017/CFR-NLHE-6max/pull/206) made HU storage
  compact (3.17 to 0.71 GB peak at its measured endpoint); PR331 ported that
  store to N-player training. [PR339](https://github.com/dberweger2017/CFR-NLHE-6max/pull/339)
  measured 9.89 to 4.07 GiB peak and 2.78x faster overall with PR331/333.
  These improvements are already in the current pilot; do not count them again.
- [PR186](https://github.com/dberweger2017/CFR-NLHE-6max/pull/186) replaced Python
  policy objects with exact float64 arrays (3.05 to 0.47 GB loading peak on its
  measured model). [PR259](https://github.com/dberweger2017/CFR-NLHE-6max/pull/259)
  added verified read-only binary caches: a measured HU200 load fell from 805s to 12s.
  These are HU loader precedents, not claimed N-player speedups; adapt their
  format-validation and sharing patterns to the native N-player policy path.
- [PR202](https://github.com/dberweger2017/CFR-NLHE-6max/pull/202) streamed export
  and independent audits with bounded memory, trading additional disk/time for
  memory. The N-player audit already streams; its exporter still reloads a whole
  trainer. Avoid regressing to whole-policy JSON collections or duplicating tables.
- [PR320](https://github.com/dberweger2017/CFR-NLHE-6max/pull/320) introduced the
  existing opt-in parallel gzip members (about 25s to 5s saving on its measured HU
  case). PR333 brought the writer to N-player. Their compatible writer is already
  used here; the separate parallel compression mode still needs this host/model's
  measured qualification.
- [PR301](https://github.com/dberweger2017/CFR-NLHE-6max/pull/301) attempted to
  measure whether larger coverage beats denser training. Its final comparison
  stopped on an evaluation-configuration failure before global outcome readout;
  it supplies no valid strength verdict that a larger table is better or worse.

## Implementation order

### 1. Qualify existing parallel compression and add cheap allocation telemetry

`native/hu20-trainer/src/gz.rs` already supports `Gzip::Parallel`, exposed by
`nplayer_train --fast-gzip`. The pilot deliberately used compatible single-stream
compression. Keep that historical result intact; measure the existing parallel
mode as a new candidate before inventing a binary checkpoint format.

- Compare decompressed checkpoint bytes, every accumulator/counter and resumed
  training state. Compressed SHA256 values are expected to differ between modes;
  each resulting file keeps its own exact pin.
- Exercise native and Python multi-member gzip readers, export and independent
  audit paths. Measure save/load time, file size, peak RSS and thermals on the
  same mature checkpoint. Keep the writer's bounded formatting/compression queue.
- Extend progress events with the existing cheap `Table::allocation()` totals
  for index, fixed fields and numeric values, plus entries, nodes and RSS.
  Do not scan every row or clone the table at each progress/probe point.

This can reduce serialization stalls; it does not reduce the live training table
or guarantee a speedup until measured.

### 2. Qualify the selected growth-and-freeze policy before main

Prepare a fresh calibration trajectory, excluded from final strength evidence,
with the selected candidate cap and `--freeze-at-cap` enabled from initialization.
Observe fixed 1B/2B cost milestones and the first actual freeze boundary. Starting
with the flag from the beginning avoids changing existing checkpoint metadata or
adding a special resume-cap migration feature. Keep the completed pilot intact.
If the proposed cap is not reached by the fixed qualification endpoint, report
that result rather than extending the calibration until it freezes.

Before freeze, show parity of rows/counters with the unfrozen CLI at a matched
complete-iteration prefix where neither cap binds. After freeze, prove constant
key membership, continuing updates to existing keys, explicit discarded-update
accounting and exact interrupted/resumed training. Do not reuse the pilot's
zero-discard success gate: discards after a declared freeze are expected and must
be reported, while unexpected pre-freeze discards remain an error. Include the
actual boundary iteration, nodes, entries and any complete-iteration overshoot.

Quote memory for every retained key eventually allocating its regret vector:
new vectors can appear after key growth stops. Include fixed K50 storage,
transient deltas, index/chunk slack and bounded save queues. Publish the numeric
cap, source/binary pins, disk reservation, deadline and stage commands before
launch. No automatic cap changes or selection using poker outcomes.

A **60–90 minute planning allowance, with a proposed two-hour qualification
maximum**, covers growth/freeze measurements and mature export/load/audit checks.
These are planning allowances, not measured completion promises. A prospective
new profile can allow up to80 GiB whole-family RSS and96 GiB process address
space, retaining at least8 GiB available RAM, CPU90°C/Thermistor15 100°C stops,
swap telemetry only, both mutexes and50 GB physical-disk floors. The larger
virtual-address ceiling is explicit because the old48 GiB limit would otherwise
prevent qualification of a larger resident table; it is not permission to use
96 GiB physical RAM. Historical profiles are never changed in place.

The fully populated training/save envelope with25% allowance must fit the RSS
ceiling and host headroom; the largest evaluation model pair must independently
fit. If it does not, refuse main and bring a new proposal. A bounded key count
alone is not an adequate memory admission check.

### 3. Take lossless storage improvements where they are qualified

[PR347](https://github.com/dberweger2017/CFR-NLHE-6max/pull/347) packs each table
entry into one contiguous record. Its author reports about 10% less requested
table memory and a single-core speed improvement on smaller 20 BB tables. Review
and benchmark it at 100 BB, 16 threads and a mature table, with exact checkpoint
and resume parity, before selecting it for a new frozen campaign build.

Ten percent is useful but cannot alone make the pilot's conservative 10B scenario
comfortable. Do not multiply several unmeasured savings together in the quote.
[PR344](https://github.com/dberweger2017/CFR-NLHE-6max/pull/344) shortens the payload
used to compute keys; its stored hashes are still 128 bits. It is not a demonstrated
training-RAM fix and has compatibility review work outstanding. Keep it separate
from this minimum path.

### 4. Keep evaluation policies resident once and share them across block workers

The current policy loader builds a `HashMap` with one boxed probability array per
row. The existing duplicate arena already shares an identical pair's table through
`Arc`, but independent lineup processes load additional copies.

First change scheduling: run one native lineup host at a time, load its distinct
policies once, and parallelize independent deal blocks inside that host. Each
block gets its own existing deck/action streams, policy instances and counters;
only immutable policy tables are shared. Use a bounded result queue and write
blocks/permutations in the original order. A serial/parallel comparison must
produce byte-identical hand traces, coverage counts and rewards. Independent
replay remains separate, streams traces, and needs no resident model weights.

If one required model pair still consumes too much memory, adapt the PR186/259
patterns into a compact read-only N-player policy table: contiguous full-precision probability arrays and a sharded
index, with owner/street/action metadata and the complete existing key. Return
stored probabilities exactly; do not renormalize them again or quantize to float32.
Validate all exported probabilities, missing-key behavior, legal observations,
seeded actions and trace identity against the existing loader. Measure savings
rather than assuming a fixed factor. This reduces inference memory, not training
memory. Reuse PR259's verified read-only binary-cache pattern if repeated parsing still
dominates. Mapped resident pages still consume physical RAM. Qualify cold reads,
working-set residency and any HDD backing explicitly; memory mapping does not
make random-access disk training fast or remove its bytes from accounting.

### 5. Make the overnight host explicitly support the new game

`examples/nplayer_overnight.rs` and `examples/nplayer_arena.rs` currently hardcode
20 BB. Add explicit100 BB configuration, fresh initialization and the selected
freeze-at-cap mode, with strict checkpoint/policy identity checks. Replace the
unconditional capacity-stop branch with a declared-mode check; a full table may
continue only in the explicitly frozen recipe. Emit and verify the first freeze
boundary and its exact key-set fingerprint. Keep the older 20 BB path and its fixtures exact.
Use the admitted entry ceiling and selected compression profile explicitly in
configuration; none becomes an implicit default.

Keep one mutable training table resident. Probes borrow it immutably. At checkpoint
boundaries, write recovery state and the selected anchor/final averages directly
from that table after pinning the source checkpoint, rather than reloading a second
copy for export. Do not clone the table to perform asynchronous saves. Resume,
export and monitors must match the plain qualified CLI's training trajectory.

Every-row independent audit must remain affordable. Profile it on the mature
qualification outputs. If the current single Python stream dominates the quote,
parallelize the same independent calculation over bounded, indexed gzip members;
verify indexes against pinned files, row counts and key ordering across member
boundaries. Corrupted probabilities, parents and counts must still fail. Reusing
the production normalization function is not an independent audit. This work is
conditional on the measured bottleneck, not a reason to add a new storage format
before using the existing parallel writer.

## The admitted overnight shape

Once the above checks pass, freeze the source, exact new limits, three final seeds,
reserved deal roots, full resource/cost quote and failure policy before main:

- Train seeds sequentially, using all 16 logical threads for the active trainer.
  Free each table before loading the next. Retain recovery checkpoints at
  1B/3B/10B plus the first freeze boundary; export full averages at the freeze
  boundary and10B. The freeze-boundary average becomes the proposed primary
  anchor, so final and parent share exactly the same stored keys. Record each
  seed's actual anchor nodes rather than calling every anchor1B.
- TensorBoard gets nodes, iteration, entries, allocation bytes, RSS, temperatures,
  node throughput and checkpoint/monitor costs. Run the qualified in-memory
  four-script probes every 1B with 128 six-hand blocks. No model copy or full
  checkpoint/export per monitoring point. Monitoring overhead must stay below 10%.
- Run the fixed final comparison after training, with memory shared within a lineup
  and bounded work queues. Keep the proposed 36 × 8192 six-hand-block matrix,
  exact reproduction, independent replay and global readout barrier. Preserve
  all same-seed, cross-seed, scripted, per-seat and coverage results and the
  predeclared decision rules, with a prospectively declared freeze-boundary
  anchor replacing the earlier1B-anchor proposal. Report unknown-state coverage
  by street/opponent alongside gains within retained states. If a secondary3B
  comparison is desired to inspect a plateau, declare and quote its extra cases
  before main; do not add it after reading outcomes.
- Keep the main's proposed eight-hour outer maximum distinct from qualification.
  The full measured forecast, including exports/audits and play/replay, must fit
  the remaining allocation with 25% allowance. An eight-hour main allocation plus
  preparation is not a promise of eight hours from now. Do not count traversal
  time alone as the campaign ETA.

## Remaining choices and limits

The freeze route prevents continuing key-count growth, but trades coverage for
more learning within a fixed set. It does not establish unrestricted convergence,
adequate coverage against new opponents or a three-player strength gain. The
uniform fallback for unseen histories is a real strategic limitation and must be
visible in the report. The old HU200 result is a precedent, not a transferred gate.

PR336 training pruning may change growth, but does not evict existing entries or
impose a hard memory bound; periodic full iterations still explore them. Its NLHE
strength and compute-normalized benefits need testing before adoption. Restricted
averaging, float32 accumulators, key eviction and history merging are additional
recipe changes, not part of this capped-table proposal.

The proposed minimum path is therefore: qualify existing capped-table training
and parallel compression, adapt the compact-policy/cache patterns where needed,
then run the explicitly bounded100 BB campaign. PR347 is a useful separately
qualified improvement; PR344, pruning and new abstraction work are not prerequisites
for this first density-focused experiment. Retain the alternative unrestricted
route if the owner prefers coverage growth and a newly admitted memory budget.
