# Fresh v0.6 acceptance — completed results

**All 30 predeclared acceptance gates pass:** 24 absolute scripted/mixed profits, three own-checkpoint gains and three cyclic noninferiority bounds. These three frozen 100 BB 10B candidates qualify under the owner-approved scientific acceptance protocol. Release packaging/publication, defaults and merging remain owner decisions.

## Fixed prospective design

[PR367](https://github.com/dberweger2017/CFR-NLHE-6max/pull/367), [proposal366](https://github.com/dberweger2017/CFR-NLHE-6max/issues/366), [protocol](../../nplayer-v06-acceptance.md), [launch](launch.md). Three existing independently trained lineages (2026101935003, 202610200601, 202610200602), evaluated on fresh held-out deals; no new training or checkpoint selection. All-street float64 averages, 100 BB/K50, unchanged menu/schema/recipe and each lineage’s frozen membership. Cross-seed key sets may differ.

One-sided simultaneous 95% lower bounds use Student-t over independent six-hand deal blocks with **one Bonferroni 30 family**. All bounds must clear their declared margins. Ordinary two-sided 95% intervals in the tables/CSV are descriptive supplements. Seat permutations and exact reproduction add no independent observations. Counts were sized before fresh hands from 75% historical effects/same variance; the 96.14% planning power bound was conditional, not a prediction or a post-run probability.

**All 36 cases completed 2,635,776 initial hands plus 2,635,776 byte-identical reproductions.** Every initial trace independently replays; all 58 stages return 0, no main failure/guard stop/retry/sample extension. Original pair receives two new full-row (250,000,475 rows), source and mass binary audits; four unchanged derivatives reuse qualified #361/#362 full-row receipts. All six hashes/counts/source-checkpoint and original-mass pins reconcile.

Own-checkpoint score is the **mean oriented singleton contrast**, half the paired difference of reciprocal 10B-vs-two3B and 3B-vs-two10B singleton returns. It is not pooled player return or a heads-up win rate. Cyclic003→601→602→003 is the full candidateA-minus-baselineA singleton-return difference against the same two fixed 3B_B opponents, margin −5BB/100. It is not a 10B population tournament. Mixed trained fields keep the candidate’s own frozen3B partner.

## All 30 acceptance decisions

All values are BB/100. “Lower” is the one-sided simultaneous 95% Bonferroni 30 lower bound; pass requires **strictly above** the margin. Full precision/root/block/SE/pass flags are in [gates.csv](gates.csv) and [compact JSON](results.json).

| Seed | Gate / field | Blocks | Mean | Ordinary95% interval | Lower | Margin | Pass |
|---|---|---:|---:|---|---:|---:|---|
| 2026101935003 | direct: own-3B | 13,312 | +32.79 | [+25.62, +39.96] | +22.06 | +0.00 | Pass |
| 2026101935003 | cross: 202610200601 | 18,432 | +34.93 | [+23.53, +46.32] | +17.86 | -5.00 | Pass |
| 2026101935003 | script-profit: random | 1,024 | +261.89 | [+185.95, +337.84] | +148.03 | +0.00 | Pass |
| 2026101935003 | script-profit: check-call | 2,048 | +255.08 | [+202.21, +307.96] | +175.85 | +0.00 | Pass |
| 2026101935003 | script-profit: tight-aggressive | 5,120 | +49.52 | [+37.51, +61.52] | +31.54 | +0.00 | Pass |
| 2026101935003 | script-profit: pot-pressure | 9,216 | +50.34 | [+38.28, +62.40] | +32.27 | +0.00 | Pass |
| 2026101935003 | script-profit: trained-call | 2,048 | +198.86 | [+157.12, +240.60] | +136.32 | +0.00 | Pass |
| 2026101935003 | script-profit: trained-pressure | 11,264 | +32.88 | [+22.55, +43.21] | +17.40 | +0.00 | Pass |
| 2026101935003 | script-profit: call-pressure | 2,048 | +187.74 | [+147.70, +227.77] | +127.74 | +0.00 | Pass |
| 2026101935003 | script-profit: random-tight | 2,048 | +170.22 | [+134.27, +206.18] | +116.35 | +0.00 | Pass |
| 202610200601 | direct: own-3B | 8,192 | +35.78 | [+26.72, +44.84] | +22.21 | +0.00 | Pass |
| 202610200601 | cross: 202610200602 | 60,416 | +32.48 | [+26.11, +38.85] | +22.94 | -5.00 | Pass |
| 202610200601 | script-profit: random | 2,048 | +355.92 | [+300.68, +411.15] | +273.15 | +0.00 | Pass |
| 202610200601 | script-profit: check-call | 2,048 | +272.71 | [+222.34, +323.07] | +197.24 | +0.00 | Pass |
| 202610200601 | script-profit: tight-aggressive | 5,120 | +52.07 | [+40.24, +63.89] | +34.36 | +0.00 | Pass |
| 202610200601 | script-profit: pot-pressure | 13,312 | +37.70 | [+27.37, +48.03] | +22.23 | +0.00 | Pass |
| 202610200601 | script-profit: trained-call | 2,048 | +185.21 | [+141.84, +228.57] | +120.23 | +0.00 | Pass |
| 202610200601 | script-profit: trained-pressure | 17,408 | +40.32 | [+32.29, +48.35] | +28.29 | +0.00 | Pass |
| 202610200601 | script-profit: call-pressure | 2,048 | +168.09 | [+130.03, +206.15] | +111.06 | +0.00 | Pass |
| 202610200601 | script-profit: random-tight | 2,048 | +171.43 | [+136.03, +206.82] | +118.39 | +0.00 | Pass |
| 202610200602 | direct: own-3B | 12,288 | +33.70 | [+25.88, +41.52] | +21.98 | +0.00 | Pass |
| 202610200602 | cross: 2026101935003 | 29,696 | +30.07 | [+21.20, +38.94] | +16.79 | -5.00 | Pass |
| 202610200602 | script-profit: random | 2,048 | +321.00 | [+258.87, +383.12] | +227.91 | +0.00 | Pass |
| 202610200602 | script-profit: check-call | 2,048 | +257.94 | [+208.53, +307.35] | +183.90 | +0.00 | Pass |
| 202610200602 | script-profit: tight-aggressive | 5,120 | +51.76 | [+40.17, +63.35] | +34.39 | +0.00 | Pass |
| 202610200602 | script-profit: pot-pressure | 13,312 | +33.59 | [+23.09, +44.09] | +17.86 | +0.00 | Pass |
| 202610200602 | script-profit: trained-call | 2,048 | +196.64 | [+152.42, +240.85] | +130.38 | +0.00 | Pass |
| 202610200602 | script-profit: trained-pressure | 45,056 | +23.44 | [+18.53, +28.35] | +16.08 | +0.00 | Pass |
| 202610200602 | script-profit: call-pressure | 2,048 | +136.27 | [+97.75, +174.78] | +78.56 | +0.00 | Pass |
| 202610200602 | script-profit: random-tight | 2,048 | +239.54 | [+200.78, +278.30] | +181.46 | +0.00 | Pass |

Own-checkpoint gains are +32.79/+35.78/+33.70BB/100 (003/601/602); every adjusted lower bound exceeds+21.98. The weakest absolute-profit lower bound is **+16.08 BB/100**, seed 602 versus own 3B+pot-pressure (mean +23.44). Every cyclic lower bound also exceeds 0, stronger than the declared −5 requirement. These are results on the declared fields, not universal superiority or Nash-convergence evidence.

## Earlier relative regressions remain adverse evidence

[PR357](../nplayer-bb100-confirmation/results.md) has a **failed script/mixed relative safeguard** (11/16 lower bounds clear−50, five unresolved). Both fresh training lineages regressed against random and random+TAG under that study’s family 16 two-sided 95% intervals:

| Historical seed | Field | 10B−3B BB/100 | Historical family95% interval |
|---|---|---:|---|
| 202610200601 | random | -53.92 | [-99.60, -8.25] |
| 202610200601 | random-tight | -35.24 | [-64.15, -6.33] |
| 202610200602 | random | -90.34 | [-135.72, -44.96] |
| 202610200602 | random-tight | -39.21 | [-66.90, -11.52] |

Those earlier failures are not erased, pooled away or retrospectively passed. The current protocol fixes **absolute positive profit** against each field, rather than improvement against each script. It does not freshly re-estimate script-relative regressions because fresh baseline-vs-script arms were not declared. None of this proves a causal mechanism, equilibrium convergence, external/human strength or that search will fix a loss. The result satisfies the current owner-approved acceptance criteria; three fixed lineages remain a small training population.

## Positions and lookup coverage

[seats-and-positions.csv](seats-and-positions.csv) includes all 180 descriptive physical-seat/button-relative-position score intervals. Position 0/1/2 means button/SB/BB. Its statistic matches each gate (absolute singleton, half reciprocal contrast or full cyclic difference); these are not additional pass gates.

[lookup-counts.csv](lookup-counts.csv) contains 240 same-observation singleton probe rows by case/street and both 3B/10B models, distinguishing positive original average mass, represented zero mass and missing. Two probes are not two independent policy decisions. [cross-coverage.csv](cross-coverage.csv) reports 24 singleton street rows as represented/missing only; generic cross summaries do not split original mass tags. Missing/zero fractions depend on field, reached paths and unequal predeclared sample sizes and do not identify why strength changed. Raw per-decision traces remain on bb128.

## Actual cost and resources

Main launched 2026-10-20T11:02:37.405555+00:00, finished 2026-10-20T14:31:12.356031+00:00: **3.476h wall (3h 28m 35s), 2.237 child CPU-hours**. Completion 16:31:12 Madrid. Eight evaluation/replay workers, two resident models, 18 total native policy loads. No training/save/export time is charged to this study; two new conversions/audits are separate below. Stage wall includes guarded process setup/accounting and copy/hash work. The sum differs slightly from whole wall due controller metadata work.

| Category | Stages | Wall min | Child CPU min |
|---|---:|---:|---:|
| full-row audit | 2 | 11.13 | 11.13 |
| conversion | 2 | 10.97 | 10.97 |
| native evaluation | 9 | 38.23 | 43.88 |
| restore inputs | 24 | 73.46 | 28.43 |
| verified staging | 11 | 63.21 | 25.38 |
| replay and reconciliation | 9 | 6.55 | 10.96 |
| global barrier/readout | 1 | 4.83 | 3.48 |

Native load counters total **2158.44s (35.97min)**; play including exact reproduction totals **75.67s**. Restore+verified-staging phase walls total **136.68min**. Disk movement/verification dominated end-to-end time. Warm/cold page-cache, fixed order and shared HDD conditions affect these costs; no cache flush, new speedup comparison or cross-machine inference is claimed. [All 58 stage costs](costs.csv).

The initial 2–3h host forecast was exceeded by **28.58 min** above its upper end. The revised 15:30–16:30 Madrid finish range missed by about 1 min. This was a forecast, not an elapsed kill guard; fixed counts/resources/source never changed for speed. No additional experiment was launched.

Sampled family peak **27.69 GiB**, max sampled **CPU 69°C / Thermistor15 67°C**, below the unchanged 90/100°C stops. Sampling is approximately 0.5s; it can miss brief peaks and family RSS can count shared mappings in multiple replay workers. Per-child wait4 RSS/faults are retained separately in CSV/JSON and are not interchangeable with aggregate family RSS. Controller CPU is not included in child CPU totals. Swap was approximately 309 MB in dated manual checks and did not materially grow; there is no continuous swap guard/history and no unsupported final maximum claim.

## Provenance and retention

Frozen runtime source `7f36a93aae7d43d1912d9a93eddd78ca0d4430c5`, source-v2/769 file pins. Configuration `3c711be0c8d05e3750498a59bff8b80887594decf52f3295c010333894b898a9`. Source result SHA256 `15c573e88d9b3b3c9ab81f6f3150eff6b91d577b6aa26fdad0a2af3045f32453`, 200,999 bytes. Main root `bb128:/home/dberweger/nplayer-v06-acceptance-20261020/main-v1/`. Every source/qualification snapshot, original input, failure/partial location and exact input/derivative hash is retained. The read-only snapshot helper failed only after normal supervisor exit (`ps` returned1); direct terminal receipts prove clean completion, not science failure.

Verified owned staging has **224 unique files /112.38GB**, plus metadata/mass/source still in the owned NVMe root. Cache: `bb128:/mnt/data2tb/research-cloud/PR-367-nplayer-v06-acceptance/main-v1/`, accessible through original paths. Relocations include verified releases back to existing identical cache files, so summing repeated records would overstate unique storage. Existing PR350/355/357/361/362 roots remain untouched/read-only; no cleanup or deletion. ZIP/member readback and Drive acceptance are **pending**; `gdrive:PR-367-nplayer-v06-acceptance/` is a future fallback, not a claimed accepted restoration source.

Recommend owner review of v0.6 packaging on these qualified frozen blueprints. No default/release/merge action or additional training was performed. Native river implementation remains the separate planned engineering task; further scaling, pruning schedules and another broad regression investigation remain deferred.
