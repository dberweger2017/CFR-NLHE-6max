# First four-player 100 BB development candidate toward v0.7

Owner asks for one fresh lineage now, separately from v0.6.1 release preparation. [Proposal411](https://github.com/dberweger2017/CFR-NLHE-6max/issues/411). M4 is offline: qualification moves to **bb128**, using fresh tiny four-player correctness fixtures. No dependence on inaccessible PR406/408 model files, no requirement to wait for M4, and no new mature cost-pilot ladder. The [paired arena implementation](nplayer-paired-arena.md) remains the dependency; its prior M4 receipts and failures remain preserved.

This PR prepares the controller and a complete allocation. **Owner has approved the10-hour allocation. Main launched October23 13:04Madrid after successful56-stage qualification. [Launch and exact receipts](reports/nplayer-four-player-candidate/launch.md).** PR404 is now merged and its main process has exited. Coordinate the normal bb128 mutex with the separate release agent; neither job bypasses it. Qualification was bounded engineering and is now complete; the3B/10B main campaign is a separate running phase.

## Fixed candidate and comparison

Fresh reserved training seed **2026102341001**, four players, **100 BB**, 50/100 blinds; current K50/v1 menu, unpruned deterministic fast mode,16training threads/eight roots per seat, all-street opponent-sampled float64 averages, parallel gzip, **250M-key freeze threshold**. Fixed cumulative3B and10B endpoints, whole-iteration overshoot allowed. Require exact within-lineage keyset equality and preserve both checkpoints. No seed/endpoint selection, more nodes, pruning, search, menu or abstraction change. Independent-seed release confirmation follows separately.

Each field has **4,096 independent fresh deal blocks**, all **24 seat permutations**, focal armA=3B and armB=10B. The same labeled opponents, decks, button schedules and identity action RNG seeds remain fixed between arms. Opponent actions can differ when the focal changes the public history; their policies are unchanged. All opponent orders are included here, rather than using the arena's smaller default cyclic schedule.

| Field | Three fixed opponents |
|---|---|
| trained (primary) | own3B, own3B, own3B |
| random | random, random, random |
| check-call | check-call, check-call, check-call |
| tight-aggressive | TAG, TAG, TAG |
| pot-pressure | pressure, pressure, pressure |
| call-pressure | check-call, check-call, pressure |
| random-tight | random, TAG, TAG |
| trained-call-pressure | own3B, check-call, pressure |

The own3B comparator is frozen before any evaluation. This is one development lineage against declared fields, not independent trained peers or v0.7 release acceptance. Fixed confirming root base20261023450001, in table order; qualification base20261023459901. Main has **1,572,864 initial hand instances +1,572,864 reproduction hands**, counting both arms. Hand instances, permutations and reproduction are not independent observations.

Primary statistic: focal10B-minus3B return, averaged inside each24-permutation independent deal block, BB/100, **no reciprocal halving**. One family of eight one-sided95% Student-t/Bonferroni lower bounds: trained lower>0; each of seven scripted/mixed paired lower>−5BB/100. Publish ordinary descriptive two-sided intervals, both checkpoints' absolute field returns, seat/position breakdowns and full coverage. These development criteria are proposed before playing, not inherited release guarantees. All results remain even if gates fail; no extra hands or automatic tuning/extension. Inconclusive is a valid fixed-budget result.

The 250M cap is a bounded candidate, not adequate-coverage proof. Retained membership cannot expand after freezing. Report pre-freeze key growth, per-street retained entries/visits, positive/zero-average-mass/missing played lookups, table-wide zero mass separately, and both adverse and favorable fields. No natural-saturation claim from capped growth.

## Correctness before main, without the M4

Use one source-pinned bb128 build and the existing managed Python/engine/K50 inputs read-only. Run native library/paired-example/legacy-example tests and focused controller/evidence tests. Fresh tiny fixture seed2026102341991,100K/200K endpoints,10K cap, same recipe; it exists only for correctness, not pricing or strength.

Require1/16thread and fresh/resume checkpoint identity, both full-row export and binary probability/action audits, within-lineage keyset identity, all eight real four-player field shapes at two blocks/all24permutations, separate-process reproduction, independent replay of every initial hand, serial/parallel byte parity, gzip/binary hand-payload parity (headers retain their different file pins), exact-zero identical-policy self comparison and an independent gzip source/mass-tag scan. Compare unchanged legacy three-player20/100/200BB traces with PR404's protected binary and independently replay them. No fresh five/six-player training or M4 fixture copy.

Qualification accounting: eight fields×two blocks×24rotations×two arms =768 instances per pass. Initial/repeat/serial/gzip are four768-instance passes; self initial/repeat add96each; legacy36current+36reference. These repeated fixture instances do not add scientific information. Full counts and actual costs are recorded by the controller. Any failed proof/source/hash/accounting/thermal stage is terminal; preserve it, do not erase or silently retry. Qualification results must bind the exact main source and build. M4's pending final receipt is not falsely relabeled complete.

## Complete prospective quote

[Reproducible quote and storage arithmetic](../configs/research/nplayer-four-player-candidate.json), generated solely from PR404's retained mature metadata by `python3.11 -m scripts.plan_nplayer_four_player_candidate --out NEW_JSON`. PR406's few-second training windows are not a mature forecast.

**4h14m central /9h34m component reserve; proposed10-hour planning allocation**, including build/qualification, two training endpoints and saves, capped resume, exports/full-row audits, binary conversion/parity, both arena passes, replay/pair validation, global/tail readout and report. No archive/upload/release work included. Owner accepted this allocation with "approvfed"; it is not an elapsed-time stop or completion guarantee.

Fourth-player mature costs are unmeasured. Scenario applies2× PR404's slowest active-node cost,1.5× save/load/export/audit/conversion costs and4× per-hand play/proof cost, then explicit further reserves. These are conservative choices, not measured4P penalties or bounds. Two readonly model aliases are shared by eight arena workers; memory and storage inspected manually before launch, with all model and trace paths remaining readable.

Storage scenario:100GB for two endpoints and derivatives (200bytes/retained key per endpoint),25.77GB initial+repeat traces at8KiB/hand, plus30GiB manual headroom = **147.13GiB free requested**. This is an admission scenario, not a runtime disk stop or guaranteed upper bound. Last read-only bb128 observation was **125.19GiB free**: about22GiB additional space is needed for that plan. Owner vacuum-cleaner owns all cleanup/staging/upload; this controller does none, cannot assume future cleanup, and protects existing PR400/402/404/K50/build/environment inputs. A different accessible storage plan needs an explicit verified owner arrangement; none is silently inherited.

Power is deliberately conditional. No four-player outcome informs counts. Assuming independent paired-block SD200/400/800BB100 gives approximate adjusted lower-distance7.81/15.61/31.22BB100. A true+10 primary gain has about76%/18%/4.5% power; a neutral script clears−5 only18%/4.5%/1.8%. These arbitrary variance scenarios are not observed4P estimates. This fixed screening can establish large effects or reveal weaknesses; it cannot promise all safeguards or release readiness. Use actual block variance and retained tail concentration to plan any later independent confirmation, not extend this run until positive.

## Execution and closeout

`nplayer_four_player_candidate build|configure|run --root NEW_ROOT` is bb128-only. Qualification config uses `--smoke`; main configure additionally requires the completed same-source qualification and exact accepted36,000-second planning allocation. One-use attempt roots, normal research mutex plus owned mutex, frozen source/config/build/Python/engine/K50/model/mass hashes, node/recipe checks and global replay/reproduction proof barrier are required. Only CPU90°C/Thermistor15 100°C/missing-nonfinite sensors are automatic resource stops; ownerSTOP/mutex/correctness failures terminal. **No time/RSS/disk/swap cutoff**. Manual checks continue; no fan/OS/environment changes.

Report both absolute and paired results, adjusted gates separately, physical seats/positions, lookup coverage, extreme positive/negative blocks and top10 squared-deviation share without excluding tails, active/save/load/export/audit/conversion/play/replay/readout/wall/CPU/RAM/thermal/storage costs and exact provenance. Keep full block arrays/raw traces/models on bb128; Git gets compact summaries. No outcomes inspected until all eight fields pass replay/reproduction. Main development success does not authorize release, merge, further nodes, seeds or automatic progression to five/six players. Archive remains owner-managed pending; retain originals and all failures.


## Earlier admission state (preserved)

[Readiness receipt](reports/nplayer-four-player-candidate/readiness.md): source-pinned preflight refuses the busy bb128 normal mutex at10:25:27UTC October23, before a build/qualification/main directory is created. The separate v0.6.1 release qualifier holds it; left untouched.19controller/evidence+8prior-campaign tests pass locally. Native build and real-engine fixture remain pending, no automatic retry. This is an external admission blocker, not a completed fixture or a scientific failure. Main is not configured or launched. M4 remains unnecessary for this4P qualification.


## Owner approval and storage-sequencing amendment

Owner approves the proposed10-hour allocation with "approvfed", then instructs "sotrage is beling cleared out, but you can get started". This authorizes main after successful qualification while the cleaner continues, superseding the147.13GiB-before-launch wait; record actual free space at admission. All scientific counts, seeds, recipe, source and thermal stops stay fixed. No disk/RSS/swap/time stop is introduced. Latest manual free-space check is84.01GiB, with cleanup owned by the owner's separate agent. Earlier admission failure/source/logs remain preserved. PR413 full CI passed on report headf83995fb (execution code unchanged from6adc28ce).


## Main running after complete qualification

[Launch record](reports/nplayer-four-player-candidate/launch.md):56qualificationstagesRC0, native121library/8paired/1legacy (oneexistingignored),19focusedPython and8localpriorcampaign regressions pass. All768initial+768reproduced field hands independently replay, self-zero/keyset/thread/resume/serial/gzip-binary payload/full-row/legacy proofs pass. Source6adc28ce/864pins; mainconfigf3be3047b3c1b5fb781fa5d3e8c41e43ba7a57cf54a74672f8a5125b2f03cd9c. Main started11:04:42UTC/13:04Madrid, supervisor872177,83.98GiBactualfree under ownerstorage amendment. Baseline first390.82Mnodes at13:06Madrid,CPU61/T1570°C,no failure. Initialcompleteforecast17:00–17:30Madrid conditional; no outcomes inspected, no retry/extension/newplayer/search/default/release/merge change. Source/model/rawtraces preserved, ownerarchive pending.
