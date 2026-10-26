# M4 qualification of second-to-act river search

Proposal [432](https://github.com/dberweger2017/CFR-NLHE-6max/issues/432).
Owner authorized implementation and execution after the planning review.
The bounded input inventory has not identified a compatible local three-player
model. The first execution therefore follows the fixture-only branch below;
the model-backed preflight, version comparison and latency panel remain unrun.
The first fixture-only attempt and a later owner-requested continuation stopped
before builds/tests at memory admission; see the
[admission report](reports/river-second-to-act-m4/results.md). Both remain retained.

The question is whether the corrected optional path from
[PR429](https://github.com/dberweger2017/CFR-NLHE-6max/pull/429) behaves correctly
and has affordable complete decision cost on a fixed small engineering panel.
This is not a playing-strength experiment or search-adoption gate. PR431 keeps
bb128; this task does not use its compute, storage, inputs, locks or network
payloads. The cleaner's existing bb128 upload is unchanged.

## Scope and prerequisites

- M4 only; three-player100BB, two active players, neither all-in, one contested pot.
- Frozen post429 source including blocker-conditioned fallback and target scaling.
  Preparation starts from `b3a62198eaeddb65a64b59d6fd46d400f366783c`.
- One existing small three-player full-street-average policy, read-only, with
  recorded source/checkpoint/policy provenance and matching game/key/menu/K50.
- Projected beliefs, `dcfr-1.5-0-2`, menu
  `pot-jam-cap3-root-min-responses-v1`, checkpoints
  `[8,16,32,64,128,256,512,1024,2048]`, stop at the existing target:
  `min(1% of river-start pot,0.1BB)` times compatible joint action probability.
- One persistent request worker at a time, `RAYON_NUM_THREADS=1`; two native test
  threads. Report actual settings and architecture; do not transfer M4 timings
  to bb128 or small-policy findings to mature models.

No training, new arena hands, mature10B model loading, model export/conversion,
policy/menu/default change, search tuning or parameter sweep. Do not add exact
belief/full-menu audits or off-tree re-solving. The second-to-act API explicitly
refuses those audits; their absence is a limitation, not a reason to enable them.

**Input gate is open.** A bounded metadata inventory found existing four-, five-
and six-player fixtures, which do not match this three-player solver. No compatible
small three-player policy has yet been confirmed. The bounded inventory is not
an exhaustive assertion that none exists. Before execution, pin one compatible
M4-local policy of at most25M rows and2GiB physical bytes, with a conservative
complete process-family memory forecast no greater than6GiB. Compressed size
alone is insufficient. Source/input provenance and the loader format must support
the forecast; otherwise do not admit the model.

The existing M4 K50 candidate is
`/Users/dberweger/Local/overnight-equity-hu100-20261009/stage-a/results/equity-bench/tables`.
Verify all three production hashes from `cards::EQUITY_K50_SHA256` locally before
use. Existing shared inputs/runtime remain unchanged. An absent/invalid model
permits native fixture qualification only; record the model-based panel unrun.
Do not silently substitute an untrained policy, fetch a mature model or train one.

The implemented fixture-only command is
`python -m scripts.qualify_river_second_to_act_m4 ROOT --catalog PATHS.json --thermal EXISTING_HELPER`.
It checks M4/AC/free-space/RAM admission, takes the ordinary and owned study locks
nonblocking, records only bounded policy headers from the existing paired-arena
catalog, then builds a source-bound thermal helper. Under thermal/STOP supervision
it runs the full native library, the legal panel generator tests and relevant
Python fixtures, and generates the48-root manifest twice. It does not load a
policy or send any solve request. A potential three-player catalog entry stops
this branch for complete input admission; wrong-game entries cannot be substituted.
No pre429 worker build or latency preflight is useful without the matching model.

## Fixed panel

Create and hash the complete legal-observation manifest before reading solver
results. The panel is synthetic and stratified; it cannot estimate population
coverage, decision frequency or playing strength. There are48 roots:
four public-history recipes ×three boards ×four entry conditions.

With100 chips/BB and equal10,000-chip starting stacks, the button folds preflop;
the remaining two seats use the following fixed recipes. All unspecified actions
are check/call. Use the existing legal engine/menu to generate and validate every
action/payment, not hand-written player snapshots.

| History index | Public recipe before the river | River-start pot |
|---|---|---:|
| 0 | Limped pot; check through flop and turn | 2BB |
| 1 | Small blind minimum-raises preflop, big blind calls; check through | 4BB |
| 2 | Limped pot; first live player makes a pot bet on flop, opponent calls; check turn | 6BB |
| 3 | Minimum-raised preflop pot; check flop; first live player pot-bets turn, opponent calls | 12BB |

Boards, in the existing native0–51 card encoding, are fixed:
`[0,13,26,39,48]`, `[4,5,18,31,44]`, `[0,8,16,28,44]`.
Use button `(history_index+board_index)%3`, rotating each history across all seats.
For each of these12 river starts, create the following four cases in order:

1. Hero is the first actor; own cards `[1,2]`.
2. Hero acts second after a check; own cards `[21,22]`.
3. Hero acts second after the minimum opening bet; own cards `[45,46]`.
4. Hero acts second after a pot-sized opening bet; own cards `[50,51]`.

All own cards are distinct and outside the declared board. Hidden representative
cards belong to the evaluator and never enter policy queries. Hand identifiers
are public ordinals, independent of any hidden-deck or action seed. These choices
are engineering fixtures, not random poker deals. Validate panel construction
against the legal engine in small harness fixtures before it can run.

The current worker receives all48 roots. A separately built pre429 `river_live`
at `e6ae0bec74159e7c81ba65f48da6e9b3903c9b80` receives the12 first-to-act controls.
One initial plus one fresh-process reproduction totals120 root requests.
Model/K50 bytes and semantic requests are identical between versions. Both
versions run sequentially, each loading its model once per process.

Before that panel, a separate cost-only preflight uses the first four current
roots and first baseline root, plus reproduction:10 additional requests,130 in
the complete declared allocation. Publish its cold-start/cost/resource forecast
before final panel admission. Calibration cases are explicitly repeated fixtures;
they do not become independent observations or additional strength samples.

Every requested root remains in the report, including zero modeled reach,
unsupported trees and missed quality targets. Never replace a difficult root,
select a different policy based on outcomes or add cases until a rate improves.

## Correctness and evidence

The harness must bind clean source, binary, compiler/target, policy, K50, panel,
configuration, thermal helper and Python/runtime hashes before execution.
Pin borrowed input paths and post-check hashes; preserve failures and partials.

Required checks:

1. Full native library suite and relevant Python fixtures pass on M4. Explicitly
   retain the blocker-only opponent bet regression, compatible1/3 and2/3 versus
   marginal1/2 controls, and constant/no-overlap controls.
2. First-to-act actions, float64 rows, profile digests, stopping checkpoints and
   quality match the baseline exactly. Equal unsupported/fallback classifications
   are recorded separately; they are not counted as solved-row parity.
3. Native retained-session fixtures validate later on-tree rows, original strategy
   reuse, replay of the opponent prefix, sticky off-tree blueprint fallback and
   fallback at the actual hero decision. This does not claim support for the
   currently refused second-to-act audit/export interfaces.
4. Fresh-process reproduction matches deterministic rows, statuses, reasons,
   profiles, work and quality. Exclude measured timings/resource fields and opaque
   session handles/nonces from the canonical comparison; retain them separately.
   Transport IDs must never enter a strategy or solver-quality comparison.
5. Legal-observation boundaries, chip accounting and all root identities are
   complete. A mismatch retains its context and stops; no automatic retry.

Report p50/p90/p95/max complete request latency, plus reconstruction, likelihood,
projection, tree/preparation, solving, quality and transport/serialization costs.
Separate model/K50 startup, compilation/tests, proof, report and total wall/CPU.
Record per-root quality/gains/target/sweeps, installation/fallback/unsupported
reason and model lookup positive/zero/missing diagnostics. Quality misses and
support limitations are results, not exclusions or automatic correctness failures.
The criterion is trustworthy accounting and correctness, not a preselected
support rate, universal15ms target or inferred strength gain.

## Prospective budget and resource admission

Read-only M4 snapshot:16GiB unified RAM, AC power, approximately28.64GiB free SSD;
`memory_pressure -Q` reported77% system-wide free percentage. This is not a byte
reservation or proof that no other process is active. No M4 research has launched.

| Component | Central minutes | Planning allowance minutes |
|---|---:|---:|
| Source/input preparation and hashing | 3 | 6 |
| Current/baseline builds and correctness fixtures | 10 | 20 |
| Cold starts and cost-only preflight | 3 | 6 |
| Fixed panel and fresh-process reproduction | 5 | 16 |
| Verification and compact readout | 4 | 6 |
| Report and ordinary-file preservation | 5 | 6 |
| **Total** | **30** | **60** |

These are planning scenarios, not measured M4 forecasts or completion guarantees.
Harness implementation/review is separate, provisionally1–2 working hours, and
must finish before the cost-only preflight. If its conservative measured total
forecast exceeds60minutes, preserve preflight and reprice before the final panel.
The time allowance is not an elapsed-time kill.

Plan at most8GiB additional local SSD for source/builds/evidence and no copied
large inputs; require at least20GiB actually free before preparation. This leaves
at least12GiB modeled disk headroom at the8GiB envelope. Recheck actual space,
manual RAM/swap and the6GiB family-memory forecast before the model load. Hold
`~/Local/.hu20-m4-research.lock` nonblocking and a new study lock, preserving their
inodes. Occupied normal lock means wait for a later owner decision, not bypass.
Prospective fixture-only resource amendment, October26: the initial6GiB family
forecast plus1GiB headroom refused two attempts before any build/test. After the
owner requested closing non-Google apps and continuation, we checked preserved
same-host PR406 receipts: native tests sampled904,413,184B peak and release builds
924,106,752B. These are older source and sampled peaks, not exact current bounds.
The fixture-only branch is now priced at4GiB family RAM plus1GiB available
headroom, more than4.6times the largest prior sample, with two build/test threads.
The initial attempts remain immutable; this is a new prospective engineering
attempt, not a changed result or a model admission. The separate model forecast
ceiling remains6GiB and needs its own provenance-based admission. No thermal/STOP
guard or during-run cutoff changes; no additional solves or samples.

Use the existing M4 thermal-state interface (`nominal`, `fair`, `serious`,
`critical`) through an owned source-bound helper. Serious/critical, missing or
unknown state, ownerSTOP, numerical/accounting/information failure or comparison
mismatch stop the owned process and retain evidence. AC power is required at
admission. There is no during-run time/RSS/disk/swap kill. Do not change fans,
power settings, other jobs, mutexes, the cleaner or PR431.

No bb128 SSH/payload work, model transfer, compression or upload is part of the
run. Small source fetches may briefly share network bandwidth; do not promise
zero shared-network effect. Do not allocate large payload transfers to fill an
input gap. Record actual costs and any concurrent M4 load without claiming an
isolated benchmark.

## Closeout

Publish every root in a compact report/table with provenance, parity,
reproduction and complete resource/cost receipts. A fixture-only completion
states explicitly that learned-policy latency/coverage remains unmeasured.
Success supports only a separately priced mature-model qualification when
bb128 is free. It neither changes PR398's result nor automatically launches a
strength campaign; any later adoption study needs a blueprint-only comparator.

Keep ordinary files under a fresh owned M4 root, provisionally
`~/Local/river-second-to-act-m4-20261026/`. Borrowed inputs remain read-only.
Source, logs, partials/failures, panel, requests/responses and all proofs remain
retained. Cleaner owns eventual ZIP-set packaging and accepted Drive publication
through its bb128 cache, after PR431/upload coordination. Until then use M4
originals; no populated cache, archive or Drive acceptance is claimed. Do not
delete, compress, upload or stage evidence onto bb128 as part of this task.
