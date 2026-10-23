# Fixed five-player 100 BB development candidate

**Main running since October23 16:16Madrid under the owner's start-during-cleanup amendment. [Launch/source/config/storage record](reports/nplayer-five-player-candidate/launch.md).**

Proposal[414](https://github.com/dberweger2017/CFR-NLHE-6max/issues/414), owner-requested after[PR413's four-player result](reports/nplayer-four-player-candidate/results.md). One new lineage asks whether continuing a capped five-player blueprint from3B to10B improves against the same fixed fields, and where it loses value. No search, capacity/menu/recipe change, release/default adoption or automatic replication. Both four-player checkpoints stay unchanged.

## Frozen experiment

Fresh training seed **2026102351001**, fixture seed2026102351991; check for existing reserved paths/seed collisions before source freeze. Five players100BB/50-100blinds, K50/v1 menu, unpruned fast16/eightroots, all-street opponent-sampled float64 averages, parallelgzip,250M-key freeze after merging whole iterations. Exactly cumulative3B and10B endpoints; retain both and require exact keyset/entry/freeze identity during continuation. Threshold overshoot is permitted; capped growth is not natural saturation.

| Name | Four fixed opponents |
|---|---|
| trained (primary) | own3B, own3B, own3B, own3B |
| random | random×4 |
| check-call | check-call×4 |
| tight-aggressive | TAG×4 |
| pot-pressure | pressure×4 |
| call-pressure | check-call, check-call, pressure, pressure |
| random-tight | random, TAG, TAG, TAG |
| trained-call-pressure | own3B, check-call, check-call, pressure |

Each field has **4,096 independent fresh deal blocks**, ten predeclared balanced seatings: the five cyclic rotations of forward identity order and five rotations of reverse order. Every identity occupies every physical seat/button-relative position twice per block. This samples only two circular opponent orders, not all120permutations; opponent-order sensitivity remains unresolved. Fixed main roots20261023550001–8 in table order; fixture roots20261023559901–8. Same decks/buttons/identity RNG and opponent specifications across focalA3B/focalB10B; public histories and hence opponent actions may differ. Two shared readonly model tables; arena8workers,16trainingthreads. No opponent retraining or additional aliases.

Initial **655,360hand instances**, same number of byte-identical reproductions; all initial independently replayed. Reproduction and seating are not independent observations. **First average the ten seating contrasts within each independent deal block**, focal10B-minus3B inBB/100, no reciprocal halving; then estimate uncertainty over4,096block values. One family of eight one-sided95% Student-t/Bonferroni bounds: primarylower>0, seven scripted/mixedlower>−5. Preserve ordinary paired and absolute-return95%intervals as descriptive and unadjusted. No outcome-dependent sample sizes, exclusions, extra checkpoints or tuning. All eight proofs must pass before global outcome inspection.

Primary success establishes improvement against four copies of this lineage's own3B ancestor, not general superiority, Nash convergence or robustness against other trained lineages. One-seed deal uncertainty does not estimate training-seed uncertainty. Scripted/mixed outcomes are central, including adverse effects. Margins are not weakened after seeing PR413; separate release/exploitation criteria must be prospective before independent release lineages.

## Support analysis

Record pre-freeze node/key growth and the bracket around freezing; source-audit retained entries, accumulated visits and zero-visit rows bystreet at both checkpoints. On identical membership report added visits and net reductions in zero-visit/zero-average-mass rows, without claiming a matched individual-row transition audit, a visit distribution or unique new keys. Table-wide original positive/zero average mass is separate from played lookup classifications.

For every arm/field, report positive-mass/zero-mass/missing/not-applicable counts byidentity,physicalseat,buttonrelativeposition,street; focal rates and changes accompany returns. A row found with uniform probabilities is not automatically zero-mass. Preserve training missing/discard counters separately. Different visited decisions prevent a causal interpretation of played-rate changes; this does not estimate a larger-table counterfactual. Report allseat/position contrasts, extremes/top10squaredvariation and no exclusions. No hidden cards/deck/seeds reach policies; privileged replay evidence stays evaluator-owned.

## Source and qualification gate

An isolated branch integrates currentmain and PR410/413 source; preserve both conflicting documentation sections and exact merge parents. No merge/close of410 or defaults/release work is implied. This proposal includes required paired-arena dependency code; exact five-player snapshot is freshly qualified onbb128. PR413's four-player proof cannot replace that five-player proof; M4 remains offline/unneeded.

Tiny five-player realK50 fixture100K/200K/10Kcap:1/16thread/fresh-resume checkpoint bytes, full-row export/binary parity, exact membership, all eight field shapes/two blocks/tenseatings, self-identical zero contrast, serial/parallel bytes, source-bound mass tags, gzip/binary payload parity, everyinitial replay/separate-process byte reproduction. Fixture320instances per pass, serial/gzip each320, self40perpass; source zero-mass played sample may be absent and must be labeled. Legacy3P20/100/200 traces compare protected PR404 build; native121library/eightpaired/legacy tests and focused controller/evidence tests run on exact snapshot. No extra mature pilot or other player training. Failure is retained, never silently retried.

## Component budget and storage

Publish a deterministic metadata-only quote from completed PR413, **separating active traversal, checkpoint saves, resume/startup residual, exports, source audits, conversion, binary audits, model loads, play/write, replay, paired/global readout, validation, build/qualification and reporting**. Five-player mature rates/support/loading are unmeasured: penalties/reserves are scenarios, not observations. Ten instead of24seatings scales only hand-dependent work, not training/model loads/row tools. [Published reproducible quote](../configs/research/nplayer-five-player-candidate.json): **2h59m36s central /5h54m42s component reserve, proposed6h allocation**. This is a provisional five-player scenario, not a measured forecast. Complete allocation includes preparation/report; no archive/upload, reset or new implicit allocation. A planning reserve is not a completion guarantee or automatic elapsed stop.

Main requires successful exact-source qualification, explicit acceptance matching the published allocation and a manual storage/memory/lock check. NVMe plan reserves model/derivative and trace scenarios plus30GiB headroom; cleaner supplies space, no controller cleanup/staging/upload. Shared K50/env and all400/402/404/410/413source/models/proofs/runtime inputs remain protected. v0.6.1release has priority while this is preparing; acquire normal mutex nonblocking, no bypass/reprioritization or new observer/timer. Only CPU90/Thermistor15100/missing-nonfinite andownerSTOP/mutex/correctness cause automatic stops; disk/RAM/swap inspected manually, no automatic time/RSS/disk/swap cutoff or machine settings changed.

## Incomplete-run and recovery policy

Output roots and attempts are one-use. Never overwrite/reconfigure/restart an existing attempt. Failed scientific correctness/hash/accounting/replay/numerical/thermal proofs are terminal; retain every successful receipt, failed stage, partial checkpoint/export/trace/source/log and exact crossing sample. No reduced-case acceptance and no global statistical readout from partial proofs. A failed partial campaign remains incomplete evidence, not a smaller experiment.

A network loss says nothing about remote failure: inspect the existing supervisor/children/status before acting; never substitute or duplicate. An interrupted controller is reported incomplete with exact stage identity. No automatic recovery or stage retries. Any owner-authorized recovery must be a separate recorded amendment binding verified unchanged successful outputs and only previously unstarted stages; never bypass a failed correctness proof or repeat completed science. This implementation deliberately has no recovery command.

If actual costs exceed the scenario, report consumed/current costs and revised estimate. There is no elapsed-time kill or automatic extra allocation. Owner can stop; any new unstarted allocation outside the accepted scope needs an explicit decision. Without owner response, never invent extra samples, branches, experiments or retries; the already accepted fixed attempt and thermal/correctness policy remain unchanged.

## Fixed closeout

Use the precomputed settled result only after all stagesRC0/no failure/global proof barrier. Publish all eight panels, simultaneous gates, descriptive absolute/paired intervals, coverage/visit changes, tails, costs (active/save/resume/load/export/audit/conversion/play/replay/wall/CPU/RAM/thermal/storage), exact source/config/build/model/mass/proof hashes and archival status. Raw models/traces/arrays remainbb128; Git gets compactreport/CSV/JSON. Stage intended files before artifactchecker/diffcheck. Owner cleaner owns archive; originals retained/no Drive receipt claim without evidence.

- Broad gains/safeguards passing: consider independent five-player lineages.
- Primary gain/scripted regressions: review exploitation tradeoff before replication.
- Weak gain/substantial support gaps: consider controlled capacity experiment.
- Weak gain/healthy measured support: revisit recipe/allocation before more nodes.

These are follow-up directions, not causal findings or automatic launches. Do not tune, extend hands, change margins or add lineages to rescue an inconclusive result. Search remains deferred.


## Owner-approved main launch (supersedes earlier admission wait)

"Start with the training, we are cleaning up while you do" accepts fixed6hcompleteallocation and permits launch at111.54GiBfree instead of waiting for133.13GiBscenario. [Launch](reports/nplayer-five-player-candidate/launch.md), [source/owner/config receipt](reports/nplayer-five-player-candidate/main-launch.json), [storage growth ledger](reports/nplayer-five-player-candidate/storage-ledger.json). Source6a01b327/874pins, qualified56stagesRC0, mainPID888459/configaafa94da23019db594cc305e6a96d735f2f04178fc5f171d52395dc4d345fe22. Counts/recipe/guards unchanged. Allstagesautomatic; no scientificretry/extension/interimoutcome. Manualstorage accounts already-writtenmainpayload and separates release scratch, no live133GiBfloor or time/RSS/disk/swapstop. Ownercleaner owns only specificallyauthorizedrelocations; all415andotherprotectedinputsretained. Source/bootstrap/readiness history above remains dated provenance.
