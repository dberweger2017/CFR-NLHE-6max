# Three-player 200 BB feasibility toward v0.6.1

Owner priority after [PR398](https://github.com/dberweger2017/CFR-NLHE-6max/pull/398):
three-player200BB blueprint play for v0.6.1; defer v0.6.5 search adoption.
[Proposal399](https://github.com/dberweger2017/CFR-NLHE-6max/issues/399) precedes
implementation. This PR prepares one bounded feasibility pilot, not a full training
campaign, strength confirmation, release or default change.

## Frozen scope

Use fresh three-player200BB (20,000chips/seat),50/100blinds, no rake/ante, pinned
K50, the existing min/pot/conditional-jam menu, unpruned fast path-v1 sampling,
eight roots/seat,16training workers, all-street opponent-sampled float64 averages,
parallel gzip, and the existing250M-entry freeze-at-cap recipe. The cap controls
membership; reaching it does not kill training. Existing states continue learning
and new states use the existing uniform fallback. Record all discards and the
freeze marker; neither cap saturation nor low RAM proves sufficient coverage.

Fresh pilot seed2026102240001, **cumulative100M/200M/500M nodes**, resumed in that
order with a save at each endpoint; record complete-iteration overshoot and use
actual added nodes in rates. Preserve all three checkpoints. No automatic endpoint
extension, rerun, added seed, pruning, compact key, abstraction, search or bet-menu
change. Never resume or relabel a100BB model at200BB. There is no prospective
strength effect to select on: this is cost/correctness/coverage evidence only.

## Qualification before pilot training

- An isolated build of current committed source; full native library tests and
  arena example tests, including200BB key/depth fixtures. Native production
  change is only adding200 to the arena's20/100stack whitelist. The trainer and
  policy formats already accept200BB; regret math/rules/observations do not change.
- Real pinnedK50 seed2026102240091:100K fresh at1and16threads,100K→200K resume,
  fresh200K, with10K-entry freeze enabled so the fixture exercises frozen
  membership. Single/parallel and uninterrupted/resumed compressed checkpoint
  SHA256s must agree. Reject a deliberately attempted200BB→100BB resume before
  output; its expected nonzero exit is a recorded successful refusal, not a failed
  scientific stage. Every other stage must return0.
- Resume/fresh full-average exports must match bytes. Independent parallel audit
  checks every key/owner/street/action/probability row (existing float64 tolerance
  1e-14), original mass tags and canonical raw key-set hash. Check game/seed/
  averaging/sampling/cap/parent/checksum identities. Do not compare source policy
  bytes across different depths or claim full key-encoding parity from a smoke.
- Four two-block scripted fixtures (random, check-call, TAG, pot-pressure), roots
  2026102240901–904, all6seat permutations.48initial+48repeat hands; every initial
  hand independently replayed through pinned `pokers`, reproduction byte-identical.
  These exercise legal200BB play with real K50 observations, not just synthetic
  card assignments. Native key unit checks stack binding and button rotation;
  full-row audits and resume parity do not constitute exhaustive cross-language
  key parity over every200BB state.

No failing correctness, hash, numerical, accounting or replay gate can be bypassed.
Preserve failure and partial output; no automatic scientific retry. A qualification
failure means no cost-pilot training. A model/path/source mutation also stops it.

## Measurements and interpretation

At100M/200M/500M record actual nodes/iterations/entries, active training time and
added-node throughput, native save seconds, compressed bytes, startup/load/hash/
other wall overhead, child CPU, sampled family RSS and telemetry key growth.
Native active timer excludes loading/checkpoint save; overhead is not falsely
labeled a pure load measurement. Export/audit final500M separately; report their
complete process costs. No inference-loading redesign is bundled here.

At the final endpoint use128six-permutation blocks against each of the four
identical-script pairs, roots2026102240101–104. Exactly3,072initial+3,072repeat
hands, all initial hands independently replay. Report by-street focal decisions,
misses, zero-mass audit rows, visits/key and lookup coverage; preserve all raw
traces and zero-root/poor-coverage results. This tiny, single-seed descriptive
panel is not v0.6.1 acceptance and the controller performs no strength readout.
The scripted opponents and different stacks alter the reached state distribution;
self-play coverage or a smaller key slope cannot establish strong poker.

Growth projections are explicitly local, uncapped linear scenarios, not memory
bounds or a saturation claim. If the last interval includes capacity freeze, no
uncapped projection is emitted. Mature-table throughput/RAM/I/O are unmeasured
unless the pilot reaches that regime. End at the fixed endpoint even if an
additional calibration would be useful; quote it separately rather than extending.

The report must propose a fixed later training allocation and checkpoint schedule,
with load/save/export/audit/evaluation/reproduction/staging costs and uncertainty.
It may conclude that a larger mature-table calibration is needed before that
allocation. It must not silently admit full training or promise effective learning.

## Pilot quote and authorization boundary

**Proposed bb128 allocation: about30–45minutes centrally,90minutes planning
reserve**, including isolated build/native tests, real-K50 qualification, three
checkpoint processes, final export/full-row audit, coverage and reproduction/replay.
This is a planning estimate before any200BB measurement, not an admitted quote,
measured ETA, timeout or completion guarantee. A novel deeper tree/rare slow path
can exceed it; never change counts to fit. Publish actual costs, including failed
preparation, rather than hiding them.

Reference: [the100BB pilot](reports/nplayer-bb100/results.md) took16.16minutes
for100M/200M/500M with compatible gzip;97.77s active traversal versus686.84s save.
Its3.99GB final checkpoint and10.53GiB sampled peak are **not**200BB forecasts.
This pilot uses the already adopted parallel writer, so the historical total is
context, not a controlled speed comparison. Independent final audit/export and
real qualification add work that that historical cost-only pilot did not include.
A generous manual disk allowance is50GB; actual bytes/RAM may differ. There is no
50GB floor or RSS kill guard. Inspect current disk/RAM/swap before allocation;
128GiB installed RAM is not all available to this worker.

The owner accepted this concrete90minute pilot allocation in this thread with
“yes” on October22, after the implementation and quote were published. `prepare` never starts science. `run`
requires the operator to pass `--accepted-planning-seconds 5400` **only after the
owner accepts this quote**; a CLI flag alone is not evidence of owner permission.
Execution is frozen to735e3d3b; later commits record evidence only. Owner approval
and exact source/bundle pins are recorded before launch in the owned root. Existing earlier-campaign
permission cannot be reused to launch a full200BB campaign.

## Execution and preservation

Use only an isolated source snapshot and fresh owned bb128 paths. The following
commands are templates, not launch authorization; substitute absolute source,
managedPython3.11, K50 and root paths before use:

```sh
python3.11 -m scripts.nplayer_bb200_feasibility build --root OWNED_BUILD_ROOT
python3.11 -m scripts.nplayer_bb200_feasibility prepare \
  --root FRESH_PILOT_ROOT --tables PINNED_K50 \
  --binary-dir OWNED_BUILD_ROOT/target/release/examples \
  --build-receipt OWNED_BUILD_ROOT/build-receipt.json --python MANAGED_PYTHON_311
# Only following acceptance of the concrete pilot quote:
python3.11 -m scripts.nplayer_bb200_feasibility run \
  --root FRESH_PILOT_ROOT --accepted-planning-seconds 5400
```

Build/test source/binary receipts are pinned before preparation. ManagedPython
must include the pinned engine. Config/source/K50/binary/Python checksums are
verified before any fixture; a fresh completed preparation is not a scientific
retry. Never overwrite any existing attempt, build, model, fixture, failure or
trace. A second `run` on an existing launch/status/failure/measurement is refused.

Normal bb128 mutex plus owned pilot mutex prevent overlap; build takes the normal
mutex too. Each child owns a process group, including audit descendants, so a
failure stops only its owned group. Use owner STOP and the current hard stops:
CPU90°C/Thermistor15100°C, including missing/nonfinite required sensors. Sample
RAM, swap and both disks every~2s for manual inspection; **no wall/RSS/disk/swap
cutoff** or address-space limit. The generic trainer requires `--max-seconds`:
`1e100` is a finite practically nonbinding sentinel, not a new stopping budget.
No changes to BIOS/fans/drivers/other environments/jobs/cache/schedules.

All heavy activity and writes stay on the fresh NVMe root. No existing PR350/355/
357/367/398 input is copied, modified, relocated or deleted. Retain every raw
checkpoint/export/audit/trace/resource record and failed partial. Archival follows
[artifact storage](artifact-storage.md) only after owning-PR status/dependency
checks; report cloud acceptance pending until deployed-tool receipt. No automatic
HDD relocation, cleanup or publication upload in this runner.

## Later v0.6.1 acceptance remains unchanged

Three independent200BB lineages must each pass absolute profit against every
declared identical and mixed scripted field, improve over its **own200BB** earlier
checkpoint, and pass cyclic continuation noninferiority. Freeze counts, roots,
margin, adjustment families and estimated pass chances before confirming hands,
using200BB variance/cost evidence, not100BB's sample counts. Preserve any adverse
scripted result even if the final models pass another gate. See [v0.6 acceptance](nplayer-v06-acceptance.md)
for the established question and oriented-singleton/cyclic definitions; this pilot
does not reduce its evidence standard. A future3B/10B schedule is a candidate to
price after measurements, not an automatic choice. Search adoption stays deferred
until a concrete evidence-supported improvement hypothesis warrants new work.

## Current preparation evidence

Local source checks pass: six focused Python tests;121 optimized native library
tests; the new200BB scripted-arena example test. The existing real-K50 resource
example remains explicitly ignored without its on-host tables. Owner-approved bb128 preparation has started under the existing durable
supervisor; real-K50 save/resume/export qualification and the fixed pilot follow
automatically after build/tests. No completed pilot or v0.6.1 acceptance result
is claimed at this update. The unchanged engine and recipe stay
subject to the prospective host qualification above.
