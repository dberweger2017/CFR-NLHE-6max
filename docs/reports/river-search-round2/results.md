# River search round 2: keep the small opening bet as a research candidate

[PR377](https://github.com/dberweger2017/CFR-NLHE-6max/pull/377) tests one expansion of round 1's capped river game: retain the opponent's minimum opening bet immediately after hero checks at the root. The root menu, other deeper menus, three-raise cap, projected beliefs, DCFR(1.5,0,2), model and blueprint fallback are unchanged. There is no training, whole-hand match, retained-strategy deployment, concurrency study or default change.

**Recommendation:** retain the expansion for fresh representative validation. It reduces the declared opponent-deviation metric on the selected cases, but does not qualify search for play. Five qualified cases worsen, one new regression against the blueprint appears, and latency/quality tails still miss the earlier engineering goals. Do not start a strength campaign from these results.

## Frozen inputs and decision

The [diagnostic set](diagnostic-set.json), SHA256 `a58f433b54eff144df65a843d6d59d4a0a171be79a605964096ca07817570e5b`, contains 20 deliberately selected observations from round 1: both improvements and regressions, pot bands, target misses and extremes. Former held-out observations are now development evidence. These cases cannot estimate population benefit.

The [comparison configuration](comparison-config.json), SHA256 `efb768b8fc128ec9c41b3ef2e6a9b53c42ef7e6785e3f8f493faed596b88ee50`, was committed before the comparison. Strict accuracy is each player's gain at most min(0.2% of root pot, 0.02 BB), with fixed checkpoints through 8,192 sweeps. Both menus must meet that target to qualify a pair. The deployment-cost phase separately uses the unchanged min(1% pot, 0.1 BB) target through 2,048 sweeps.

The primary outcome is the paired reduction in the **opponent's** full-menu best-response gain against hero. The frozen retention rule requires a positive median reduction and no increase in the number of regressions versus the unchanged blueprint, while reporting individual harms and cost. This is an exploratory engineering decision, not a strength or release gate.

The model is frozen v0.6 seed 2026101935003, SHA256 `d835f61f4a5407bd47e8f8a5da849ef82c16ad21fce32f15dce72d5997275189`. No model bytes were changed.

## What the diagnosis found

Nineteen of 20 capped solves meet the strict target. Their opponent best-response gains using only capped actions are at most 0.0191 BB, while full-menu gains are much larger. The strongest measured entry is the opponent's minimum opening bet after hero checks, not just a minimum raise facing a bet. In the 28 BB case `panel-2026102101/242`, this entry adds 14.2211 BB over the restricted-response baseline, against a full-menu gain of 14.4358 BB.

The [diagnostic summary](diagnosis-summary.json) retains every case. Omitted-action increments overlap and are not an additive attribution of total error. Three cases contribute 63% of the sum for minimum opening bets; the selection deliberately includes extremes. The diagnosis locates an entry into vulnerable fallback play, rather than separating the omitted option from the fallback's quality.

## Matched-accuracy comparison

Both menus converge on the same 19 pairs. `panel-2026102103/1934` remains inconclusive because neither reaches the strict target within budget. It is retained in all raw data and the [20-row comparison](comparison.csv), and excluded from the primary matched-accuracy cohort. Its large descriptive gain is not included in the headline result.

| Strict-accuracy metric, 19 qualified pairs | Cap 3 | Add opening minimum bet |
|---|---:|---:|
| Median opponent full-menu gain | 1.1587 BB | 0.3940 BB |
| Mean opponent full-menu gain | 3.4727 BB | 0.6521 BB |
| Maximum opponent full-menu gain | 14.4358 BB | 2.2914 BB |
| Regressions versus blueprint-only | 9 | 4 |

The **median paired reduction is 0.4163 BB** (mean 2.8206 BB); it is not the difference between the two marginal medians. Fourteen pairs improve and five worsen. Six former regressions disappear and one new regression appears. The new regression, `panel-2026102101/607` (2 BB pot), moves opponent gain from 0.2599 to 1.0790 BB, versus blueprint-only 0.3687 BB. The largest paired worsening is 0.8191 BB.

The declared retention rule passes, but no population confidence interval or stronger-play claim follows from this selected sample. Lower opponent deviation gain is not itself a whole-hand return estimate. A separate [post-hoc descriptive check](hero-worst-case-posthoc.json) computes hero's full-menu worst-case value as profile value minus opponent deviation gain: 14/19 improve, median change +0.4169 BB, worst change -0.8302 BB. This check did not change the frozen decision rule.

## Tree, memory and cost

| Metric, all 20 attempted cases | Cap 3 | Add opening minimum bet |
|---|---:|---:|
| Median tree nodes (ordinary median) | 31.5 | 42 |
| Maximum tree nodes | 39 | 51 |
| Median solver f64-array bytes | 2,788,980 | 3,727,288 |
| Strict-target complete decision median | 1.135 s | 2.285 s |
| Strict-target complete decision maximum | 7.694 s | 10.546 s |
| Deployment-target complete decision median | 0.300 s | 0.380 s |
| Deployment-target p95 / maximum | 1.951 s | 2.692 s |
| Deployment-target cases reaching quality target | 18/20 | 18/20 |

The strict and deployment timings use their respective accuracy targets and are not interchangeable. Two deployment-target misses in each arm remain reported. At deployment accuracy the expanded menu's median is under 0.5 s but its selected-panel p95 exceeds 2 s; this is not a new held-out gate pass. The summary also retains the means and quantile convention; the ordinary median averages the two central observations in an even sample, whereas the historical `p50` helper selects the upper central observation.

Measurements use five concurrent loaded workers, alternating arm order by case, ordinary cache, and one i7-10700KF host. Decision latency includes reconstruction, ranges, tree preparation, solving, quality checks and worker roundtrip; model loading is separate. The strict phase subtracts the separately timed offline full-menu audit; deployment requests do not run that audit. Solver memory counts f64 arrays only, not the loaded blueprint or entire process.

The successful run finishes in **173.78 s**, including **129.82 s worker startup/loading**, with 14.09 child CPU-minutes. Sampled peak family RSS is **72.94 GiB**, mostly five loaded model copies. Peak CPU/Thermistor15 is **71/73.5 C**. Manual checks show about 41 GiB NVMe free and swap unchanged at 350 MiB; neither is an automatic stop. CPU90/Thermistor15 100 C and missing/nonfinite sensors are the only automatic resource stops; legacy and PR377 mutexes prevent duplicate science.

## Qualification, failure and provenance

The initial comparison source `1e3581cf14189fc4a6d1ff98e0d431b964e8f277` stopped before any solve: the live endpoint rejected the already-declared 8,192-sweep request because its separate validation still allowed only 4,096. Its output, logs, source and binary remain preserved as `comparison-v1`, `comparison-run`, `comparison-source-1e3581cf` and `comparison-target`. This cost 131.34 s, including loading; it is excluded from the successful-run time above. Both launches together cost 305.12 s wall, excluding builds/tests/operator work.

The fix aligns live solve validation with the existing diagnostic/checkpoint limit, without changing the frozen budget. Source **`a8078b9d14addc721d1567ff15230cc47c7049cc`** passes all **88 native library tests**, three focused Python accounting tests, and the release build, all return code 0. The new tests check that only the first opponent response after a root check gains the minimum opening bet, that other branches retain their menus, and that solve/checkpoint limits agree. Accounting tests verify opponent orientation, inconclusive-pair retention and belief/blueprint mismatch rejection.

The [verification receipt](verification.json) independently checks all 40 strict and 40 deployment records, exact input identities, identical root options, belief laws and blueprint controls. Baseline sweep counts and gains reproduce the original diagnosis exactly (maximum gain difference 0). The successful supervisor returns 0, with no thermal or scientific failure. [Compact comparison](comparison-summary.json) and [cost receipts](costs.json) preserve the figures above.

Raw originals remain on bb128 under `/home/dberweger/river-search-round2-20261021/`, including both attempts, logs, sources and qualification evidence. Active comparison outputs are `comparison-v2`, supervision is `comparison-run-v2`, and the source is `comparison-source-a8078b9d`. Archive/Drive acceptance is pending; no deletion, cleanup or changes to other jobs took place.

## Reproduce the comparison

From the measured source, build `river_live` with `cargo build --release --locked --manifest-path native/hu20-trainer/Cargo.toml --example river_live`, then use a **fresh output path**:

```sh
python3 -m scripts.river_search_round2_compare \
  --config docs/reports/river-search-round2/comparison-config.json \
  --set docs/reports/river-search-round2/diagnostic-set.json \
  --out FRESH_OUTPUT --binary PATH_TO_RIVER_LIVE --k50 K50_PATH --model PINNED_MODEL
```

This command is reproducibility documentation, not authorization to repeat science. Any next validation needs fresh representative observations and a declared protocol. Belief/solver-error separation and retained-strategy correctness remain open; this PR authorizes no arena or automatic follow-up.
