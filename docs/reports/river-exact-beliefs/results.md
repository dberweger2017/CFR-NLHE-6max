# Exact modeled river beliefs: correct evaluator, missed latency gate

PR382 / proposal381, October 21, 2026. **The exact folded-card evaluator agrees with the independent dense oracle, and all fixed measurements reproduce. Complete exact decisions remain too slow: median 3.567 s, p95 13.229 s.** The expanded menu also improves absolute hero worst-case value at deployment accuracy on most reused cases, closing PR380's strict-versus-deployment audit gap. Neither result supports a long strength campaign yet. Preserve the two convergence misses, full-menu harms and unchanged thresholds.

This is one frozen v0.6 10B blueprint, one host and PR380's reused 200-root development panel. These are modeled local values in BB, not whole-hand BB/100, true opponent beliefs or safe-resolving guarantees. No training, new menu, whole-hand match, default or release change ran.

## Correctness and frozen comparison

The [predeclared protocol](../../river-exact-beliefs.md) retains the action-likelihood law
`P(a,b) ∝ w0(a)w1(b) Σf wf(f) I(disjoint(a,b,f))`, including folded-card correlations. The new weighted rank-prefix operator uses 54 features, blocker corrections and explicit near-cancellation repair. It preserves original action-likelihood ranges rather than feeding projected marginals back into the exact law. The original dense oracle and projected solver remain unchanged.

On all 20 preselected controls, maximum leaf error is **1.64e-14 BB** and same-profile value/best-response error **3.80e-12 BB**, below the declared tolerances. Both orientations, nonuniform and zero reach, fold/tie/showdown basis leaves and identical uniform/prefix/dense-produced profiles are checked. The 600 capped final profiles also agree with dense-oracle quality: maximum error **2.50e-12 BB**. Independent hand-calculated, randomized, sparse, extreme-weight and full 1,081-holding native fixtures supplement these controls. Native library **103/103**, remote focused Python **6/6** and final local driver/readout **9/9** tests pass.

These controls compare operators on the **same profiles**, with fixed 64-sweep timing measurements. They are not new matched-convergence passes of the historical 0.05 BB belief gate. PR380's nine adverse matched-convergence controls remain unchanged; no new tight 0.01 BB reference solves were performed here.

All three arms retain DCFR(1.5,0,2), checkpoints 8 through 2,048, and the per-player target `min(1% of pot, 0.1 BB)`. The arms are reference cap3/projected, expanded root-check-min/projected, and that same expansion/exact. All 400 original projected root strategies, quality values, sweeps and checkpoint curves reproduce PR380 exactly. Original convergence failures are preserved. An unchanged-profile full production-menu audit and retained-row audit each perform **zero additional solver advances**.

All seven main stages return zero. The repeated 20 control, 400 projected and 200 exact records match all deterministic strategic fields, statuses and profile digests; only timing counters and process-local opaque handles are excluded. PR380's trace replay proofs are reused read-only; this round generates or replays no new whole hands. [Verification](verification.json), [compact results](results.json), [all case audits](cases.csv).

## Complete decision cost and declared quality

| Metric, all 200 attempts | Reference projected | Expanded projected | Expanded exact |
|---|---:|---:|---:|
| Complete decision, median | 0.290 s | 0.370 s | **3.567 s** |
| Complete decision, mean | 0.396 s | 0.506 s | **4.829 s** |
| Complete decision, p95 | 1.037 s | 1.389 s | **13.229 s** |
| Complete decision, maximum | 2.029 s | 2.761 s | **26.478 s** |
| Produced capped profiles meet their declared law's target | 198/200 | 198/200 | 198/200 |
| Produced capped profiles meet target under exact law | 152/200 | 147/200 | **198/200** |
| Installed search / blueprint fallbacks | 198 / 2 | 198 / 2 | 198 / 2 |
| Median ≤0.5 s and p95 ≤2 s | Pass | Pass | **Fail** |
| Installed coverage ≥90% | Pass | Pass | Pass |
| Every attempted root meets declared quality | **Fail** | **Fail** | **Fail** |

Complete time includes legal reconstruction, likelihoods, representation/tree preparation, solving, quality checks and worker roundtrip. It excludes model startup and the separate offline audit. These are fixed work/quality schedules, not hard 360 ms time caps. Times retain the two quality misses. The measured five-process setting is not an isolated single-request or concurrency-scaling experiment.

The exact operator removes the representation discrepancy to numerical tolerance; it does not ensure all projected-law strategies are good under the exact law. **51 installed expanded projected profiles** miss the target under exact evaluation. Exact solving makes all 198 installed profiles pass the exact-law target, while leaving two failures as actual blueprint fallback.

Fixed 64-sweep controls take median **0.694 s prefix versus 1.285 s dense**, with median paired dense/prefix ratio **1.91×**. Controls use one process with RAYON=16; ordinary panel workers use RAYON=1. This is an exact-backend comparison at fixed work, not a speedup over projected solving or a parallel-scaling claim.

Exact complete decisions are **9.64× slower by medians** than expanded projected decisions (9.54× by means). Exact mean solve time excluding quality checks is 4.631 s, about 95.9% of the complete mean; quality checks add 0.157 s. Median likelihood, projection and tree/solver preparation are only 8.89, 15.48 and 14.80 ms. Solving is the next measured bottleneck. Scalar cancellation repair is used: median 3,747 cumulative repaired rows per solve, maximum 416,375; these are repeated row operations, not distinct holdings, and no repair-time attribution was measured. The data do not establish which internal optimization would help most.

## Full-menu audit of the actual deployment profiles

Hero worst-case value is `profile_value(hero) − opponent_best_response_gain`. A smaller deviation gain alone need not improve that absolute value. All comparisons below use **actual deployed policies**: search for qualified roots, plain blueprint for the two failures. The CSV separately preserves produced unconverged profiles, both players' gains, profile values, law, root identity and digest.

| Matched comparison | Hero worst-case improves / worsens / equal within tolerance | Median paired WC change | Mean paired WC change | Worst paired harm |
|---|---:|---:|---:|---:|
| Expanded projected − reference, projected-law audit | 178 / 20 / 2 | +0.1583 BB | +0.8137 BB | −2.6837 BB |
| Expanded projected − reference, exact-law audit | **175 / 23 / 2** | **+0.1569 BB** | **+0.8138 BB** | **−2.6549 BB** |
| Expanded exact − expanded projected, exact-law audit | **105 / 93 / 2** | **+0.0021 BB** | **+0.0225 BB** | **−1.3353 BB** |

Classification uses the disclosed 1e-8 BB numerical tolerance, not a practical strength margin. No population interval or strength conclusion follows from this reused development set.

Under the exact-law full-menu audit, reference/expanded-projected/expanded-exact median opponent deviation gains are **0.7155 / 0.3546 / 0.3207 BB**. Actual policies with worse absolute hero WC than blueprint number **46 / 23 / 23**. The menu change removes 25 blueprint regressions but introduces two (cases79/123). The projected-to-exact change removes case48 and introduces case172; the total stays23. These absolute-WC counts must not be compared as a trend with PR380's strict-profile regression counts, which used different accuracy and the deviation-gain diagnostic.

The largest menu harm is case79, **−2.6549 BB** under exact audit. The largest exact-versus-projected harm is case75, **−1.3353 BB**; case53 also loses1.1201 BB. Case113 remains the worst regression against blueprint for expanded exact, **−2.4388 BB**. All harms remain in the CSV and JSON. Exact modeling improves declared-game residuals, but these local full-menu changes are mixed and do not establish a compensating whole-hand strength gain for its extra cost.

## Preserved convergence misses and retained continuation

Both original failures remain at 2,048 sweeps and a 0.1 BB target:

| Case / public pot | Reference projected gains (players 0,1) | Expanded projected gains | Expanded exact gains |
|---|---:|---:|---:|
| 137 / 60 BB | 0.11025, 0.18423 | 0.11453, 0.19426 | 0.08812, **0.14382** |
| 195 / 46.5 BB | 0.10843, 0.12088 | 0.10639, 0.11209 | 0.09116, **0.12102** |

These large-pot roots require relatively tight absolute accuracy. Their checkpoint curves generally reduce residuals, but neither new exact strategy reaches the target for player1. Exact modeling improves the final maximum residual on137 and worsens it on195 versus expanded projected; projection alone therefore does not explain the original misses. No numerical mismatch or hidden extra sweeps occurred. Reaching the fixed limit is the measured cause of fallback; whether another schedule would qualify them is untested. Exact solve-plus-check time at the final checkpoint is22.76/26.44 s. All original curves are retained in [convergence-misses.csv](convergence-misses.csv) and results JSON.

Retained continuation verifies **1,482 original profile rows** for each expanded arm:198 roots and1,284 later hero rows, zero new solves. Exact continuation's median batched native check cost is15.86 μs per checked row; it is not individual continuation RPC tail latency. Retained profile payload median333,266 bytes, maximum437,938 bytes, excludes engine/allocator/JSON state. Exact chance features/corrections are separately reported, not included in that retained-profile payload. Law/hand/history/profile identities and actual blueprint fallback are preserved. No whole-hand arena integration was performed.

## Whole-job cost, provenance and preserved reporting failure

Main measurement/reproduction/verification wall is **2,352.62 s (39.21 min)**; child user+system CPU is **3.0748 h**. The pre-main quote was48.60–81.01 min; it was conservative, and all declared counts ran unchanged. Controls total5.52 min, projected panels16.68 min, exact panels16.98 min and verification2.05 s. The exact panel has half as many roots as the projected panel; their similar stage walls are not a per-decision speed comparison.

There are **22 model-load instances** across both passes, not five total. Worker startup spans120.30–130.43 s. Summed worker startup is2,844.38 s, of which2,724.98 s is policy loading; parallel overlaps mean these sums are neither stage wall nor CPU time. Main wall includes loads. Ordinary stages use five independent processes; controls use one16-thread process. No shared-model throughput result is claimed.

Sampled family peak RSS is **74.80 GiB**, minimum available RAM47.79 GiB, CPU/Thermistor15 peaks **71/81.5°C**, below unchanged90/100°C hard stops. Swap remains367,697,920 bytes throughout; last NVMe/HDD free are163.47/495.06 GiB. RSS is a sampled worker-family aggregate, not exact peak or resident model bytes. [Stage/startup/resource accounting](costs.json).

The scientific supervisor completed normally. The following reporting wrapper exited127 because `/usr/bin/time` is absent on bb128; **analysis had not started**. The error and `readout-v1-failure.json` remain. Python resource accounting ran saved-data `readout-v2` successfully, then analysis-only `49f49fc3` added detailed startup/component accounting in `readout-v3` (0.381 s wall, 0.380 child CPU-s, 61,180 KiB maxRSS). No solver, measurement, trace or hand was repeated as part of recovery. The earlier setup-v1 bundle-ref failure also remains preserved and occurred before build/science.

Measured runtime **e2a91181f77d9c5b0a4de545bccbe498391875fe**; readout source **49f49fc3**. [Exact source, binary, model, panel, environment and report hashes](provenance.json). Existing CI at8f85a176 passes all five checks; later report/readout changes require their own CI. Original model bytes, K50 tables, PR380 panel/proofs and PR380's Git object store remain protected read-only dependencies.

## Decision and separate conditional pilot quote

**Keep the exact evaluator as a qualified research tool; defer a long strength study.** The menu benefit now survives direct deployment-profile/full-menu auditing, but it has specific harms. Exact beliefs close the representation error and improve capped exact-law quality, yet miss speed and every-root quality gates. A focused profile of exact traversal/terminal work is justified before another implementation change; further loading work is not the dominant per-decision opportunity here. No optimization or additional science starts from this report automatically.

For a possible separately approved cost/variance pilot, use the previous scale of three declared lineups ×128 six-hand blocks ×two arms plus independent reproduction:4,608 initial and4,608 repeated hands. Of these,4,608 search-on hands across both passes could trigger first solves. PR380 designated-hero self-play frequency is9.63–10.28%, **not** the all-seat29.61%. Mixed/pressure frequency remains unmeasured; assuming10–30% gives461–1,382 solves. At the measured exact mean4.829 s, that is **37–111 serial solve minutes**;1,000 solves alone cost80.5 min. Eight startups at the observed mean add17.2 min. Allowing play, replay, continuation/off-tree fallback bookkeeping and reserve yields a **conditional90–180 minute compute quote**, with no unmeasured concurrency speedup. Integration engineering is additional and unmeasured; recalibrate if call frequency, latency or model-startup assumptions fail. This would measure cost/variance, not settle strength. Failed gates argue for addressing latency first. No pilot or arena is authorized by this quote.

## Retention and reanalysis

All source, binaries, model dependencies, calibration, raw request records, failures and logs remain at `bb128:/home/dberweger/river-exact-beliefs-20261021/`; completed main is `main-v1/`, guarded final readout `readout-v3/`. Only compact verified summaries were retrieved locally. Open PR root/dependencies are protected; cache/Drive archival and acceptance remain pending. No files were deleted, and no other jobs, environments, fans or drivers were modified.

Reanalyse saved evidence without solving, using the pinned script and a fresh output:

```sh
PYTHONPATH=ROOT/source ROOT/venv/bin/python ROOT/analysis-49f49fc3.py \
  ROOT/main-v1 --out FRESH_READOUT_DIRECTORY
```

The readout refuses incomplete/failed science, changed qualified source/binary/protocol, altered verified strategic records, changed model identities or broken worst-case/fallback accounting. Raw records and protected parent inputs are required for independent reanalysis; compact tables are not a substitute archive.
