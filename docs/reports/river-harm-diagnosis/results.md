# Remaining river harms: minimum raises after hero's own opening bet

PR384 / proposal383, October 21, 2026. **The fixed diagnosis completed and independently reproduced for all 24 original profiles.** Among the six selected cases that actually install search, the strongest identified omitted reply is a minimum raise after hero's own opening bet. This is a different entry from the minimum opening bet after a root check already added in PR377/380. The diagnosis provides a focused candidate for a later menu experiment; it does not establish that adding it will improve play.

Keep the model frozen. Exact-solver profiling remains the next implementation task. The existing exact-backend 90–180-minute whole-hand cost/variance pilot remains a separate, deferred proposal with additional integration work.

## Fixed scope, reconstruction and verification

The [predeclared protocol](../../river-harm-diagnosis.md) selects cases **0,53,69,75,79,113,137,195**, with reference projected, expanded projected and expanded exact arms. Cases79/113 and75/53/69 were selected from known adverse results;0 is a fixed comparison control, and137/195 preserve both known blueprint fallbacks. This is a deliberately selected diagnosis from PR380/382's development panel, not fresh or representative confirmation. Case0 is not assumed to beat blueprint.

PR382 saved profile digests, root outputs and audit results, but not complete strategy arrays. Each selected profile was reconstructed **once at precisely its original settings**, including work limits, checkpoints and original stopping result. All 24 profile digests, root strategies, work/quality/status bindings and checkpoint curves match PR382. Float64 snapshots with model/root/card/menu/law/work bindings were then exported. The initial and independent repeated diagnostics load those snapshots; **neither audit advances a solver**. No extra convergence or replacement strategy was supplied to the original misses.

All four main stages return zero. All 24 initial diagnostic records reproduce all strategic quantities and profile digests; only timing fields are excluded. Aggregate blueprint, produced-profile and actual-policy values and both players' gains match PR382 within1e-8BB. Snapshot SHA256s are checked before import and again before settled readout. Original profiles remain unchanged. [Verification](verification.json), [24 snapshot pins](snapshot-pins.csv), [full compact readout](results.json), [1,118 response-mask/counterfactual rows](responses.csv).

Everything is evaluated under the **same exact modeled folded-card law**. This closes an evaluator-law comparison ambiguity, but does not isolate the effect of belief representation from the original finite-work solving trajectories and residuals. Exact means the stipulated model, not true opponent beliefs or safe resolving. Values below are range-weighted modeled river-game BB, not per-hand profit or BB/100.

## What the diagnostics mean

Hero worst-case value is `V(hero) − opponent best-response gain`, equivalently minus the opponent's best-response value in this zero-sum river game. We report profile value, deviation gain and absolute worst-case value separately.

At each opponent decision on a capped-tree history, the fixed-policy audit computes:

- **Capped-response restriction:** the opponent can use capped actions at those nodes; off-tree nodes remain unrestricted.
- **Add-one entry:** allow one omitted response in addition to that restriction. Its increment measures added root best-response opportunity.
- **Leave-one-out:** permit the full menu except that one response at that node. The increase in hero worst-case value measures its marginal effect when all other responses remain available.
- **Blueprint continuation counterfactual:** after the identified response, replace hero's descendant strategy rows with blueprint while keeping all other rows fixed. Evaluate again against a full-menu best response.

These are full-root, reach-weighted restrictions and policy counterfactuals. Effects overlap and **cannot be summed as an additive error breakdown**. Excluding a response is a diagnostic intervention, not a proposed change to poker rules or an improved deployed policy. A hand-calculated native fixture explicitly demonstrates two interchangeable exposing responses with nonadditive add-one gains and zero individual leave-one-out effects.

## Actual-policy values on the selected cases

All numbers are under the exact modeled law, with unchanged full production-menu best responses. The last two rows actually play blueprint in every arm.

| Case / pot | Blueprint WC | Reference projected WC | Expanded projected WC | Expanded exact WC | Exact − projected |
|---|---:|---:|---:|---:|---:|
| 0 / 8 BB | +1.497 | +0.731 | +0.795 | +1.029 | +0.234 |
| 53 / 9 BB | −17.764 | −15.854 | −4.174 | −5.294 | **−1.120** |
| 69 / 18 BB | +4.723 | +3.647 | +3.635 | +3.338 | **−0.297** |
| 75 / 26 BB | −22.318 | −18.119 | −7.811 | −9.146 | **−1.335** |
| 79 / 6.5 BB | −3.614 | −2.644 | −5.299 | −5.139 | +0.160 |
| 113 / 8 BB | +0.138 | −2.507 | −2.454 | −2.301 | +0.153 |
| 137 / 60 BB | −21.124 | −21.124 | −21.124 | −21.124 | 0 |
| 195 / 46.5 BB | +3.294 | +3.294 | +3.294 | +3.294 | 0 |

The expansion still gives large local improvements on53/75 versus the reference, even though exact solving regresses relative to expanded projected on those cases. Cases79/113 remain worse than blueprint. These distinct comparisons must not be collapsed into one verdict. [Full-precision values and paired accounting](cases.csv).

## Responses exposing cases79/113

For the **expanded exact** profiles:

| Case | Opponent response after hero's root action | Omitted? | WC increase when this response alone is removed from the full BR menu | Add-one increment over capped response set |
|---|---|---|---:|---:|
| 79 | Hero opens1BB → opponent raises to2BB | Yes | **+2.5119 BB** | +2.6154 BB |
| 79 | Hero opens6.5BB → opponent raises to13BB | Yes | **+1.0915 BB** | +1.0915 BB |
| 113 | Hero opens8BB → opponent raises to16BB | Yes | **+4.5101 BB** | +4.5101 BB |

The public path is one hero opening bet followed by the opponent's minimum raise. The native CSV stores exact action paths/amounts:100chips=1BB; for example `[["raise",800]] → ["raise",1600]` is the 8→16BB response in113.

For79, allowing all omitted replies jointly adds **3.9914BB** of opponent gain to a capped-response-only residual of0.0313BB. Its actual WC is1.5254BB below blueprint. For113, omitted replies jointly add **4.6326BB** to a residual of0.0528BB, and actual WC is2.4388BB below blueprint. The root-check minimum opening bet is already included in the expansion; it is not the dominant remaining exposing entry here.

Across all six selected installed expanded-exact profiles, capped-response-only opponent gains are0.0313–0.0927BB, while full omitted-response access adds0.9654–4.6326BB. In this fixed-policy experiment, the remaining full-menu action access matters far more than those small restricted-game residuals. This is not an estimate of how often the weakness occurs in play.

## Largest exact-versus-projected regressions

The same original profiles reveal more exposure to particular minimum raises under exact solving. Compare both profiles under the **same single response restriction**, rather than comparing a restricted candidate to an unrestricted baseline:

| Case | Common removed opponent response | Expanded projected WC increase | Expanded exact WC increase | Exact − projected WC before / after restriction |
|---|---|---:|---:|---:|
| 75 | After hero1BB lead, raise to2BB | +1.0005 | **+2.3581** | −1.3353 / **+0.0224 BB** |
| 53 | After hero1BB lead, raise to2BB | +0.4420 | **+1.2993** | −1.1201 / **−0.2628 BB** |
| 69 | After hero18BB lead, raise to36BB | +2.1700 | **+2.2859** | −0.2969 / **−0.1811 BB** |

Case75's paired regression reverses under that particular response restriction. The same restriction reduces but does not remove53's paired gap. In69, a minimum raise after hero's1BB lead is also relevant: its removal improves projected/exact WC by0.5393/0.7077BB, leaving a paired gap of−0.1285BB. Do not add this effect to the separate18→36BB restriction.

The accounting distinguishes exposure from changes in the candidate-pair profile value:

| Case | Exact − projected profile value | Exact − projected opponent gain | Resulting WC difference |
|---|---:|---:|---:|
| 75 | −0.0201 BB | +1.3152 BB | −1.3353 BB |
| 53 | −0.0118 BB | +1.1084 BB | −1.1201 BB |
| 69 | +0.0126 BB | +0.3095 BB | −0.2969 BB |

The large differences are mainly in available best-response gain, rather than a comparable shift in profile value. This locates vulnerability in the original deployment strategies; it is not proof that exact beliefs themselves cause weaker play or that tighter convergence would leave the differences unchanged. No new tightly matched-convergence solves ran.

## Continuation: neither zero effect nor blanket fallback is a cure

Every omitted entry already leaves the retained tree and uses blueprint. Replacing hero continuation with blueprint after such an entry therefore changes zero rows and has zero effect, as confirmed across all corresponding audit rows. **That does not establish that blueprint continuation is good or harmless**: it simply confirms what the current extension does. This round does not test a new off-tree continuation or re-solve.

On-tree continuation remains valuable. Replacing hero's continuation with blueprint after `hero check → opponent pot bet` worsens expanded-exact WC by **12.2529BB in75** and **10.6349BB in53**. A blanket return to blueprint would discard useful solved play. The root-check/minimum-opening branch's positive blueprint-swap effect is only0.00024BB in79 and0.07081BB in113, much smaller than their remaining WC deficits; these are individual counterfactuals, not additive shares.

A focused later experiment could admit the opponent's minimum raise on the **first response to hero's root bet**, covering both minimum and pot openings while preserving the existing root-check minimum bet, other menu limits and fallback rules. This is one candidate rule supported by the diagnosis. It still needs actual re-solving, cost/quality measurement and later fresh confirmation; removing an action from an audit does not predict the benefit of adding it to search. Broader minimum-raise ladders and off-tree re-solving are not justified automatically.

## Both original convergence failures remain actual blueprint

All three arms on137/195 preserve their original nonconverged status and actually deploy blueprint. The actual WC values are−21.1236/+3.2940BB. Produced expanded-exact profiles, reported separately, have WC−11.3150/+4.9464BB and full-menu opponent gains0.1543/0.6728BB. These are **uninstalled** profiles: their original declared-game failures and0.1BB threshold are unchanged, and the apparent local WC values do not authorize bypassing the gate. There are no additional sweeps, silently substituted profiles or inferred release gains.

## Cost, qualification and provenance

Main capture/initial/repeat/verify wall is **859.50s (14.32min)**, within the pre-main13.68–24.58min quote. Child CPU is **856.99s (14.28CPU-min)**. Capture takes199.79s; each audit pass328.85/328.84s; verification2.02s. Three sequential worker startups total359.80s, of which345.07s is policy loading, included in main wall. Each audit pass performs about209s of work after startup. Calibration adds3.60min, for17.92min of successful calibration+main stage wall, excluding orchestration gaps and report work. There is no new complete-decision latency benchmark here.

- One model worker with RAYON1; no concurrency-speedup claim.
- Sampled worker-family peak **14.81GiB**, minimum available107.92GiB; CPU/Thermistor15 peaks **60/59.5°C** under unchanged90/100°C stops.
- Host swap remains367,697,920bytes; no growth. Final NVMe/HDD free242.76/495.06GiB. These are sampled telemetry, not exact instantaneous peaks or page attribution.
- Native library107/107 and focused Python7/7 pass on bb128; local focused Python11/11 pass. Independent fixtures cover snapshot bits/bindings/corruption, actual fallback, response-mask accounting and overlapping effects.
- Saved-data readout returns0 in0.1045s, with0.1041childCPU-s. Its wrapper `RUSAGE_CHILDREN.ru_maxrss` is cumulative across earlier children and includes main, so the recorded high-water value is **not isolated readout RSS**. The main's separate sampled peak above is the resource figure used.
- No setup, scientific, thermal or reproduction failure occurred. Old PR382 failures/evidence remain preserved. Existing full CI on the pre-report head69ff55b1 has shard0 passed and shard1 still running at report preparation; the final report head receives its own CI. No all-checks-green claim is inferred from the earlier security-only notification.

[Every stage, startup and resource/accounting limit](costs.json) · [source/binary/model/panel/output hashes and dependencies](provenance.json) · [pre-main calibration/quote](calibration.json).

Measured runtime **895f853f407f6f618fce396f1a5c36c17f778941**. PR history was rebased onto merged PR382 (`75f2864e`); the rebased checkout tree was verified byte-identical and the remote source/config/binary stayed frozen. Later commits are evidence/integration only. The original blueprint remains seed2026101935003, SHA256 `d835f61f4a5407bd47e8f8a5da849ef82c16ad21fce32f15dce72d5997275189`.

## Decision and retention

**Proceed next with the separately bounded exact-solver profiling PR**, measuring traversal, prefix accumulation, blocker corrections and scalar repair before choosing an optimization. This diagnosis has identified a specific future root-bet/minimum-response menu candidate; it does not launch that experiment. The frozen model, original harms/fallbacks/gates and need for fresh confirmation all remain. The whole-hand cost/variance pilot is still a conditional90–180compute minutes plus integration, not a strength verdict or an authorized continuation.

All raw requests, initial/repeated records, source/bundle/binary and **24 float64 snapshots (26,435,977bytes)** remain at `bb128:/home/dberweger/river-harm-diagnosis-20261021/`: `main-v1/`, `readout-v1/`, `calibration-v1/`. Only compact derived tables/proofs/metadata were retrieved locally. Published JSON deduplicates identical installed actual/produced policies (`same_as`) and repeated ranked-response rows (index rankings); exact expansion was checked against the original full readout without changing numeric fields. PR382/380 sources and Git object stores, parent records/model/K50 are protected read-only dependencies. The owning PR remains open; cache/Drive archival and acceptance are pending. No originals, failures or other jobs' files were removed or changed.

To repeat only the readout, with the measured source and a fresh destination:

```sh
STUDY_ROOT=/home/dberweger/river-harm-diagnosis-20261021
cd "$STUDY_ROOT/source"
PYTHONPATH="$STUDY_ROOT/source" "$STUDY_ROOT/venv/bin/python" -m scripts.diagnose_river_harms summarize \
  --capture "$STUDY_ROOT/main-v1/capture" --out FRESH_READOUT_DIRECTORY
```

The readout requires complete, failure-free fixed stages, passed reproduction proofs and unchanged record/manifest/snapshot bytes. Original snapshots and raw diagnostic records remain necessary to audit or reproduce the compact tables; they are not contained in Git.
