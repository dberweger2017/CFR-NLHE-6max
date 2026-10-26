# Planned model-backed second-to-act river qualification on M4

Proposal [435](https://github.com/dberweger2017/CFR-NLHE-6max/issues/435).
**Planning only. No implementation, fixture training, model load, preflight or
panel has started.** The owner requested preparation of this PR; execution is
a separate next step after implementation and admission.

## Question and scope

Does the corrected optional second-to-act path produce reproducible,
correctly accounted model-backed decisions, and what is their complete latency
on a small M4-local policy? This completes the input-limited part of
[PR433](https://github.com/dberweger2017/CFR-NLHE-6max/pull/433), whose
[native fixtures passed](reports/river-second-to-act-m4/results.md).

This new proposal explicitly permits one small engineering-fixture training;
PR433 did not. There is no strength comparison, release/default change, mature
model transfer, new arena hands, solver tuning, live-order fixture arm, exact
belief backend, full-menu audit or off-tree re-solving. PR434 retains bb128.
No bb128 SSH, payload I/O, compute, storage or changes to cleaner uploads.

Use a fresh worktree from `origin/main`, initially
`d5700417043dc08b804fc8ffcd4a7c1bde560ce7`. Freeze the final clean implementation
commit, all relevant source files, compiler/architecture, native binaries,
configuration, runtime, thermal helper, input hashes and manifests before
execution. Separately build the pre429 worker from
`e6ae0bec74159e7c81ba65f48da6e9b3903c9b80`. Do not edit either frozen snapshot.

## One fixed engineering policy

| Setting | Fixed value |
|---|---|
| Host and game | M4; three-player100BB; stacks10,000 chips, blinds50/100 |
| Fresh seed | `2026102643601` |
| Key schema | `history`: `nplayer-button-live-actor-history-equity-k50-v1` |
| Training | Existing unpruned K50 fast recipe; two threads; eight roots/seat |
| Endpoint | 25,000,000 total nodes, reached at a native iteration boundary |
| Capacity | 1,000,000-key freeze threshold; record whole-iteration overshoot |
| Averaging | Full-street scope3; ordinary opponent-sampled average |
| Endpoint selection | Exactly one endpoint; no extension or replacement seed |
| Derivative | One ordinary float64 average export; no binary conversion |

Build/test and estimator correctness gates precede this training. No game,
information-access or regret-math change is proposed. Any such required change
must receive the repository's independent review before dependent training;
this plan does not authorize a reviewer agent or assume that review has passed.

Audit the saved checkpoint identity, seed, recipe, actual node/row counts,
freeze point and full average scope. Independently audit every export key,
legal action and float64 probability against the checkpoint. Preserve original
checkpoint/export bytes, audit outputs and hashes. Verify that both workers
accept this exact same history-schema export with matching game/menu/K50.

K50 is borrowed read-only from the existing M4 directory
`~/Local/overnight-equity-hu100-20261009/stage-a/results/equity-bench/tables`.
Verify all three production `cards::EQUITY_K50_SHA256` pins locally before use.
Existing runtime and inputs remain unchanged; no package/environment upgrade.

The tiny, early-frozen policy is an engineering fixture. Its missing rows and
weak learning are expected limitations. Do not substitute synthetic weights,
train longer or choose a different fixture because panel results are sparse.
If genuine profiles cannot be installed, report that limitation rather than
claiming learned-strategy qualification from fast fallback responses.

## Fixed observations and solve settings

Reuse the exact48-root generator from PR433: four legal public-history recipes,
three boards and four entry conditions. There are12 first-to-act roots and36
second-to-act roots after a check, minimum opening bet or pot opening bet.
Generate/hash the complete manifest before reading model or solver outcomes;
its expected SHA256 is
`9394fad0bba108f75cf6fbcb7955d259598b2da919711dadf0a753618098eb76`.
The [original protocol](river-second-to-act-m4-qualification.md#fixed-panel)
declares all cards, buttons, public histories and chip accounting. It remains
the panel definition. No new deal bank or observation selection.

Requests contain only the acting seat's legal observation. Representative hidden
cards belong to the fixture engine and never enter policy requests, hand IDs or
RNG inputs. IDs are fixed public ordinals. Validate legal generation, exact
menus/payments, own cards and chip conservation independently of solve results.

Settings stay projected beliefs, `dcfr-1.5-0-2`, menu
`pot-jam-cap3-root-min-responses-v1`, maximum2,048 sweeps and checkpoints
`[8,16,32,64,128,256,512,1024,2048]`, stop at the existing quality target:
`min(1% of river-start pot,0.1BB)` times compatible joint action probability
for the second-to-act subtree. No target, menu or work-level sweep.

Each process loads one policy/K50 once. Versions run sequentially, with one
worker and one retained session at a time, `RAYON_NUM_THREADS=1`.

## Fixed accounting: 144 root solves

| Phase | Current root IDs | Pre429 root IDs | Passes | Root solves |
|---|---|---|---:|---:|
| Cost-only preflight | `0,5,10,15,24,29,34,47` | `0,12,24,44` | Initial +fresh-process reproduction | 24 |
| Main fixed panel | All `0..47` | All first-to-act: `0,4,8,12,16,20,24,28,32,36,40,44` | Initial +fresh-process reproduction | 120 |
| **Total** | | | | **144** |

The preflight spans all four histories, all boards and all entry types. Its
repeated roots are explicitly calibration repeats, not independent samples.
Main processes are fresh; do not reuse preflight profiles or exclude repeated
roots. No main outcome inspection before complete reproduction verification.

Use `retained-begin` with identical semantic observations/settings across
versions. For each returned session, re-enter the same observation once with
`retained-continue`, then release. There are at most144 root re-entries and144
releases in addition to144 begins: at most432 transport requests, with no
additional solves. Unsupported roots without a session get no fabricated
re-entry. Record all statuses and reasons. Confirm that re-entry preserves
installed/fallback semantics and original profile/row bits, with zero solver
advances.

These learned-model re-entries validate capture at the same root. Later on-tree
continuation, sticky off-tree fallback, actual-hero blocked-action fallback and
second-to-act audit refusal must additionally pass the existing native fixtures.
Do not describe root re-entry as a measured whole-hand continuation experiment.

## Correctness gates and evidence

1. Full current native library, generator and relevant Python tests pass on M4.
   Retain tests for compatible1/3 and2/3 versus marginal1/2 action mass, actual
   hero support, legal boundaries and retained/fallback behavior.
2. Every actual first-to-act profile is bitwise equal between current/pre429:
   exact actions, float64 rows/profile SHA, law, targets, quality and stopping
   work. Equal unsupported/fallback classifications are recorded separately,
   not counted as solved-profile parity. Profile absence must never pass as
   positive evidence of an installed strategy.
3. All144 declared root requests remain accounted for, including unsupported
   states, zero modeled reach, quality misses and unchanged blueprint rows.
   Report positive-mass, zero-mass and missing lookups separately; expose whether
   range construction mostly queries uniform fallback rather than learned rows.
4. Fresh-process deterministic signatures match. Preserve float64 bits and signed
   zero. Freeze the explicit canonicalization schema in tests: omit measured
   times/resources and opaque session handles/nonces only. Retain those fields
   in raw evidence; never omit quality, probabilities or work to obtain parity.
5. Full-row export audit, input/source/binary post-checks and transport accounting
   pass. Numeric, information, accounting, parity or reproduction failure stops
   the attempt, retaining the first divergent request/context. No automatic retry.

Quality misses and unsupported roots are results, not correctness failures.
If no installed second-to-act profile exists, state that the learned-panel
evidence is insufficient for that path. Do not add roots, nodes, seeds or sweeps.

## Prospective cost and resource admission

Implementation/review is provisionally1–2 working hours, separate from compute.
The following is a planning scenario, not a measured M4 forecast:

| Component | Central minutes | Planning allowance minutes |
|---|---:|---:|
| Source/input preparation and hashes | 2 | 4 |
| Current/pre429 builds and correctness fixtures | 4 | 8 |
| One fixture training, save, export and full-row audit | 2 | 6 |
| Cold starts and fixed24-request cost preflight | 3 | 8 |
| Main120 requests including reproduction | 5 | 24 |
| Verification, readout and ordinary evidence | 4 | 10 |
| **Total** | **20** | **60** |

Before the main120 requests, publish a cost-only admission receipt. Include
already-spent preparation/build/fixture/preflight work and all future startup,
transport, quality checks, reproduction, proof and reporting. Centrally project
main current/baseline costs from their preflight means. For the conservative
planning forecast use four times the largest measured per-request complete
latency for each version,96 current +24 baseline requests, twice measured
full-panel startup and a600s proof/report reserve, plus actual already-spent
work. Report assumptions: this is not a completion bound, and unmeasured roots
may cost more. Outcomes do not influence sample counts or admission.

If the forecast exceeds60minutes or input/memory/storage admission fails,
preserve preflight and stop before main for a revised owner budget. No wall-time
kill, automatic extension or reduced panel masquerading as a complete result.

Reserve an **8GiB new M4 SSD envelope**:4GiB source/builds,1.5GiB fixture/audits,
0.5GiB request/response/resource evidence,1GiB provenance/scratch and1GiB reserve.
Require at least20GiB actual SSD free before preparation, leaving at least12GiB
modeled headroom. Recheck before the panel; count all new study bytes and retain
all failed/partial files. No cleanup or archival gain may be assumed.

PR433 measured0.892GiB sampled native/build family peak. Start build/fixture
planning conservatively at4GiB family plus1GiB available headroom. Before loading
the exported policy, bind actual row count/file size and conservative resident
policy/solver/scratch estimates. The model/solver family forecast must fit actual
available memory with1GiB headroom and remain at most6GiB; the ceiling is not an
instruction to reserve6GiB for a smaller measured workload. Reprice from
preflight measurements and supported solver allocations before main. Never infer
RAM use from compressed file size alone or weaken admission silently.

Read-only snapshot October26 09:35:50UTC:30.52GiB free SSD,6.50GiB available RAM,
1MiB swap, AC power, nominal thermals; the proposed M4 root was absent. This is
not a reservation. No apps/services are closed as part of this task. Preserve
Google apps, system/network services, and other jobs.

Acquire `~/Local/.hu20-m4-research.lock` and an owned study lock nonblocking,
preserving inodes. Occupied locks do not authorize a bypass. Use an owned,
source-bound thermal helper: serious/critical, missing/unknown readings,
ownerSTOP or correctness failures stop owned processes and preserve evidence.
No automatic during-run time/RSS/disk/swap cutoff, fan/power change or new timer.

## Readout and closeout

Report all48 roots, all12 baseline controls and preflight separately. Include
classification, installation/fallback reasons, learned lookup exposure,
profile/quality/work, first-to-act parity and reproduction proofs. Give
p50/p90/p95/max complete request latency separately for installed search,
nonconverged/fallback and unsupported responses; always state each denominator.
Separate reconstruction, likelihood/ranges, projection, preparation, solving,
quality, transport/serialization and startup. Do not count a fast fallback as
fast successful search. Record session re-entry work and latency separately.

Publish actual training/save/export/audit/build/load/play-request/proof wall and
CPU, sampled family RSS, available RAM, swap, thermal states, disk use, source and
input pins. Include concurrency context; do not claim an isolated benchmark or
transfer tiny-policy/M4 timings to mature models/bb128. There is no universal
15ms gate, strength verdict, safe-resolving proof or automatic next campaign.

Keep ordinary files in a fresh M4 root
`~/Local/river-model-panel-m4-20261026/`. Preserve all original fixtures,
checkpoint/export/audits, source/config/binaries, requests/responses, logs,
failures and proofs. Source and compact summaries only enter Git.

Cleaner owns eventual ZIP-set packaging and verified bb128/Drive archival after
coordination under [artifact storage](artifact-storage.md). Do not transfer,
compress, upload or delete evidence while preparing/running this task. Future
cache/Drive locations are prospective only; use M4 originals until acceptance
receipts and a complete extraction/retrieval manifest exist.
