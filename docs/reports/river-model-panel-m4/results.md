# PR436: model-backed second-to-act river qualification on M4

**The bounded engineering panel completes.** Search installs on34/36 second-to-act
roots and12/12 first-to-act roots. All46 installed profiles meet the fixed
capped-game quality target. Two second-to-act roots return the unchanged
blueprint fallback because the acting holding has zero modeled root reach.
All48 current roots and12 historical first-to-act controls reproduce bit for bit;
all12 controls have actual installed-profile parity with the pre429 solver.
This establishes small-fixture behavior, not stronger poker play or adoption.

[Protocol](../../river-model-panel-m4.md), [all48 roots](roots.csv),
[original readout](results.json), [independent saved-output readback](verified-readback.json),
[provenance](provenance.json), [costs](costs.json), [full-row audit](policy-audit.json).

## Fixed inputs and correctness

One history-key three-player100BB fixture, seed2026102643601, reaches25,002,307
nodes with1,010,695 retained keys. Its1M threshold freezes after a whole iteration
at iteration92; the10,695-key overshoot is expected. Training occurs exactly
once. The ordinary float64 average export audits every retained key, menu and
probability against its checkpoint. There are715,366 positive-average-mass rows
and295,329 zero-mass rows; these table-wide counts are not played fallback rates.
No binary conversion, mature model transfer or live-order fixture arm is used.

The48 legal observations retain all four histories, three boards and four entry
conditions from PR433's frozen generator. Current library145/145 tests,
generator2/2 tests, worker metadata4/4 tests and final Python23/23 tests pass,
with no ignored native tests. The pre429 library is unchanged; both libraries
use the same diagnostic worker shell, release profile and pinned historical
registry dependencies. This compares solver versions, not historical unmodified
worker executables.

Every main profile, float64 probability, quality statistic, work count and
fallback classification reproduces in a fresh process. All120 main begins,
re-entries and releases complete. Re-entry preserves strategy/profile bits and
advances the solver zero times. These are same-observation re-entries; later
on-tree continuation and off-tree fallback are covered by native fixtures,
not a new learned-model whole-hand experiment.

| River entry | Roots | Installed | Blueprint fallback | Unsupported |
|---|---:|---:|---:|---:|
| First to act | 12 | 12 | 0 | 0 |
| After opponent check | 12 | 12 | 0 | 0 |
| After opponent minimum opening bet | 12 | 10 | 2 | 0 |
| After opponent pot opening bet | 12 | 12 | 0 | 0 |

Fallback roots14/38 retain all results and uniform missing-row blueprint
probabilities. They are zero-*reach* cases, distinct from stored zero-average
mass. The46 installed roots report287,232 positive-mass and60,850 missing-key
range-likelihood queries, with zero zero-mass/unknown queries. Those are repeated
holding/history queries, not unique keys or population coverage. The two early
fallbacks do not return these counters and are explicitly marked unreported in
the CSV. There are no convergence misses. The fixed targets apply to the
projected modeled law and capped search game, with the existing compatible-action
share scaling on second-to-act subtrees. No full-menu or exact-belief quality
claim follows.

## Latency and cost

First main current pass; complete request latency includes transport and
serialization, while persistent policy/K50 startup is separate. Ordinary host
caches and other macOS activity remain uncontrolled; this is not an isolated
benchmark or a mature-policy forecast.

| Response | n | Median | p90 | p95 | Maximum |
|---|---:|---:|---:|---:|---:|
| Installed search | 46 | 278.5ms | 634.7ms | 1,008.2ms | 1,349.9ms |
| Blueprint fallback | 2 | 10.55ms | 10.64ms | 10.66ms | 10.67ms |
| Unsupported | 0 | — | — | — | — |

Installed-request component medians: reconstruction0.005ms, likelihood3.80ms,
projection6.39ms, tree/preparation2.85ms, solving255.09ms and quality8.39ms.
Component medians need not sum to median total. Same-root re-entry across all48
roots takes48.7μs median/69.0μs maximum. Main cold-process model/K50 startup is
3.076–3.211s across four processes; this is first use within each process,
not a cold-filesystem benchmark. The current initial process reports0.485s
policy loading within3.074s native total startup, including mass metadata/K50.

| Recorded work, including preserved plumbing failures | Stage wall seconds | Child CPU seconds |
|---|---:|---:|
| Thermal helper, current builds/tests and baseline wrapper work | 162.89 | 422.97 |
| Python/adapter tests | 3.14 | 0.28 |
| Panel generation | 1.04 | 0.04 |
| Fixture training, save included | 12.28 | 21.31 |
| Average export | 3.07 | 2.27 |
| Full-row audit | 5.15 | 5.17 |
| Preflight, including rejected follow-up | 29.65 | 28.03 |
| Main, both versions and reproduction | 60.34 | 58.56 |

Training's native active elapsed9.362s includes1.192s save; process/stage overhead
is reported separately above. Total recorded stage wall277.56s and child CPU
538.63s include both failed setup paths. Source preparation plus all controller
segments account for309.98s (5m10s); this excludes repair/idle gaps and final
readback/publication. First dispatch09:59:41UTC to successful completion10:23:48UTC
is24m07s including those gaps. No attempt/failure cost is relabeled as free.

The cost-only gate before main admitted9.05min central/24.89min reserved within
the60min allowance. All final continuation stages return0. Across271 samples,
peak family RSS is1.446GiB, minimum available RAM5.974GiB, swap at most1MiB and
thermal state always nominal. No Celsius sensors were measured. Full owned
root, including all sources/builds/failures, uses2.486GiB allocated; post-readback
free SSD31.455GiB. RSS is sampled; source-preparation/publication CPU and exact
machine-wide peaks are unavailable. Normal and study locks are released with
unchanged inodes.

## Preserved plumbing failures and explicit limitation

1. `run-v1`: baseline wrapper omitted its new root package from the copied Cargo
   lockfile. `--locked` refused the build before any fixture training or root
   request. The fix retains every historical dependency/version/checksum and
   adds only the wrapper root entry. All original evidence remains.
2. `run-v2`: the first valid root0 begin succeeded, then the harness mistakenly
   included solve controls inside a continuation observation. The strict native
   API returned `unexpected field in legal river request`; release was unrun.
   The corrected adapter whitelists the eight public-observation fields.

The explicit `completion-v1` transport continuation reuses the audited fixture,
unchanged native binaries and original completed root0 begin. It does not train
again or repeat that initial begin. Raw wires independently count exactly144
begins,144 continuation requests (one rejected) and143 releases:431 requests,
430 successful. Original preflight root0 follow-up/release remain **incomplete**;
its planned fresh repeat and both main passes validate the corrected path.
Every root-begin reproduction gate remains strict; no root is excluded. The
main panel has no exception. This disclosed preflight limitation prevents
claiming that every original transport probe passed.

## Interpretation and retained evidence

PR429's optional second-to-act path now has genuine model-backed qualification
beyond PR433's synthetic fixtures. The fixture is tiny, early-frozen and immature;
its34/36 installation rate is a fixed-panel result, not deployment coverage.
Projected beliefs, capped-menu weaknesses and whole-hand strength remain open.
There is no universal15ms claim, safe-resolving proof, default/release change or
automatic science continuation. Keep search adoption deferred while PR434's
blueprint confirmation has bb128 priority.

Native execution source `469ffa3c4811f571bd6dc4fd4ed72de203cef9c3`, transport
adapter `116f1be60bafa34ef1ec940a5000083e381840ba`, historical solver
`e6ae0bec74159e7c81ba65f48da6e9b3903c9b80`. All6,017 native-source,6,017
adapter-source and5,974 baseline-source files rehash unchanged. Exact policy,
checkpoint, mass, panel, executable, runtime/config and raw-wire pins are in
[provenance](provenance.json).

Ordinary evidence remains on M4 at
`/Users/dberweger/Local/river-model-panel-m4-20261026/`: all three sources,
`baseline-e6ae0bec`, failed `run-v1`/`run-v2`, successful `completion-v1`,
checkpoint/export/mass sidecars, raw wires, logs, resources and receipts.
Use these original paths for retrieval. Cleaner-owned packaging and verified
bb128/Drive archival remain pending. No transfer, compression, upload, deletion,
bb128 access, new timer or app/service termination occurred in this task.
