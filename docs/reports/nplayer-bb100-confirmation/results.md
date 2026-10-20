# Independent 100 BB seed confirmation — results

Both fresh 3B→10B primary gains repeat, and every cyclic cross-seed safeguard passes. The scripted safeguard fails: random and random+TAG regress on both fresh seeds after family adjustment. Keep 10B as a conditional research candidate and retain 3B; this is not universal-strength or release qualification.

## Verified design and decision

Two fresh unpruned three-player 100 BB/K50 lineages, seeds 202610200601/02, each 0→3B→10B with its own fixed nominal 250M-key membership. Same float64 average, menu/key schema, fast 8 roots/seat and 16 threads as PR355. Original seed 2026101935003 is discovery evidence and a cyclic reference, not a third fresh primary.

All 42 cases (8192 independent six-hand blocks each) passed independent initial replay and byte-identical reproduction: **2,064,384 initial +2,064,384 reproduced hands**. All four full row/export audits and all 18 stage return codes pass. No final scientific retry, guard stop or endpoint extension occurred. Reproductions and seat permutations do not add independent samples.

Primary statistic is the **mean oriented singleton contrast**: half the difference between reciprocal singleton returns, not pooled player return or a heads-up win rate. Script/cyclic contrasts are full singleton return differences. Predeclared simultaneous family 95% intervals use Bonferroni 2/16/3 respectively; no nested historical family 8 flags are used.

| Seed | Panel | 10B−3B BB/100 | Family 95% interval | Declared lower-bound test |
|---|---|---:|---|---|
| 202610200601 | own-3B | +35.79 | [+25.68, +45.91] | Pass >0 |
| 202610200601 | random | -53.92 | [-99.60, -8.25] | Unresolved >-50 |
| 202610200601 | check-call | -27.79 | [-71.30, +15.73] | Unresolved >-50 |
| 202610200601 | tight-aggressive | +7.95 | [-5.90, +21.80] | Pass >-50 |
| 202610200601 | pot-pressure | +12.36 | [-9.41, +34.13] | Pass >-50 |
| 202610200601 | trained-call | +44.66 | [+9.26, +80.05] | Pass >-50 |
| 202610200601 | trained-pressure | +27.02 | [+5.45, +48.59] | Pass >-50 |
| 202610200601 | call-pressure | +26.77 | [-3.59, +57.14] | Pass >-50 |
| 202610200601 | random-tight | -35.24 | [-64.15, -6.33] | Unresolved >-50 |
| 202610200602 | own-3B | +31.49 | [+20.33, +42.66] | Pass >0 |
| 202610200602 | random | -90.34 | [-135.72, -44.96] | Unresolved >-50 |
| 202610200602 | check-call | +22.41 | [-18.27, +63.09] | Pass >-50 |
| 202610200602 | tight-aggressive | +7.33 | [-6.18, +20.84] | Pass >-50 |
| 202610200602 | pot-pressure | +4.61 | [-17.06, +26.27] | Pass >-50 |
| 202610200602 | trained-call | +41.90 | [+6.50, +77.30] | Pass >-50 |
| 202610200602 | trained-pressure | +10.05 | [-11.51, +31.61] | Pass >-50 |
| 202610200602 | call-pressure | +25.64 | [-5.55, +56.84] | Pass >-50 |
| 202610200602 | random-tight | -39.21 | [-66.90, -11.52] | Unresolved >-50 |
| 2026101935003 | 202610200601 | +35.80 | [+15.59, +56.00] | Pass >-5 |
| 202610200601 | 202610200602 | +18.15 | [-3.27, +39.56] | Pass >-5 |
| 202610200602 | 2026101935003 | +26.26 | [+6.59, +45.93] | Pass >-5 |

**Repeated primary gain: pass. Cyclic safeguard: pass (all 3). Script/mixed safeguard: fail (11/16 bounds pass).** Five unresolved −50 bounds are seed 601 random/check-call/random+TAG and seed 602 random/random+TAG. Both random and random+TAG intervals lie below zero on both fresh seeds: these are demonstrated panel regressions. None of their family95 upper bounds is below −50; a loss beyond that tolerance is not established at the declared simultaneous level. Check-call does not show consistent direction across seeds.

Both fresh own-3B improvements are established. Two cyclic gains clear zero after adjustment; the third is inconclusive for improvement but clears the −5 safeguard. Meaningful adverse scripted evidence remains. They do not demonstrate multiplayer Nash convergence, explain the causal mechanism, establish that search will fix the losses, or justify default/release adoption. Three fixed seeds including discovery are still a small training population; the cyclic panel is not a full population tournament.

## Absolute returns, positions and lookup diagnostics

| Fresh seed | Field | 3B absolute BB/100 | 10B absolute BB/100 |
|---|---|---:|---:|
| 202610200601 | random | +369.76 | +315.84 |
| 202610200601 | check-call | +297.78 | +270.00 |
| 202610200601 | tight-aggressive | +44.76 | +52.70 |
| 202610200601 | pot-pressure | +27.19 | +39.55 |
| 202610200601 | trained-call | +141.32 | +185.97 |
| 202610200601 | trained-pressure | +5.55 | +32.56 |
| 202610200601 | call-pressure | +124.29 | +151.06 |
| 202610200601 | random-tight | +225.54 | +190.30 |
| 202610200602 | random | +387.00 | +296.66 |
| 202610200602 | check-call | +230.78 | +253.19 |
| 202610200602 | tight-aggressive | +43.84 | +51.17 |
| 202610200602 | pot-pressure | +35.42 | +40.03 |
| 202610200602 | trained-call | +157.61 | +199.51 |
| 202610200602 | trained-pressure | +8.67 | +18.72 |
| 202610200602 | call-pressure | +133.42 | +159.06 |
| 202610200602 | random-tight | +208.48 | +169.26 |

[seats-and-positions.csv](seats-and-positions.csv) contains every within-seed absolute return and ordinary 95% interval by physical seat and button-relative position (0=button,1=small blind,2=big blind). These are descriptive strata, not additional adjusted primary tests. Direct 10B singleton returns by button/SB/BB are 202610200601: +52.39, +15.77, +36.03; 202610200602: +64.07, +2.11, +5.95 BB/100.

[lookup-counts.csv](lookup-counts.csv) retains singleton decision counts by case, position, street and **both probed policies at the same reached state**. Status order is positive original average mass / represented zero mass / missing; do not interpret two probes as two independent decisions. Compact JSON retains matched transitions, reached-street/pot-band counts, river eligibility and own-missing cross coverage. Cross tables can differ; represented cross rows cannot be labeled positive mass without matching metadata. Cross per-seat payoff intervals were not precomputed and are not invented here.

| Seed | Endpoint | Positive-mass rows | Zero-mass rows | Missing singleton probes / all probes |
|---|---|---:|---:|---:|
| 202610200601 | baseline | 170,197,626 | 79,803,443 | 10,066 / 1,809,929 |
| 202610200601 | candidate | 181,590,424 | 68,410,645 | 10,066 / 1,809,929 |
| 202610200602 | baseline | 170,034,032 | 79,966,284 | 10,296 / 1,810,008 |
| 202610200602 | candidate | 181,434,181 | 68,566,135 | 10,296 / 1,810,008 |

Lookup fractions depend on the evaluated field and reached paths. Lower zero-mass coverage or different pot/river distributions are descriptive associations; they do not establish why returns changed. Exact path examples remain in the retained settled raw readout, rather than selecting a few large losing pots as a causal explanation.

## Actual training and end-to-end costs

| Seed | Segment | Nodes reached | Iterations | Active s | Mnodes/s | Save s | Export s | Stage wall s | Child CPU s | Peak GiB |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 202610200601 | 0→3B | 3,000,010,507 | 213,379 | 634.18 | 4.731 | 136.02 | 87.16 | 1338.30 | 10293.39 | 22.79 |
| 202610200601 | 3B→10B | 10,000,007,784 | 759,207 | 1495.87 | 4.680 | 141.42 | 84.76 | 2274.88 | 19118.97 | 23.37 |
| 202610200602 | 0→3B | 3,000,005,353 | 210,426 | 626.96 | 4.785 | 140.82 | 90.79 | 1332.13 | 10154.87 | 22.79 |
| 202610200602 | 3B→10B | 10,000,004,165 | 754,514 | 1439.13 | 4.864 | 142.00 | 85.16 | 2218.82 | 18616.35 | 23.36 |

Whole campaign: **4.331h wall, 20.971 child CPU-hours**; active traversal 69.94min. Sampled peak family RSS **66.04GiB**; max sampled CPU **74°C**, Thermistor 15 **93.5°C**, below unchanged 90/100°C stops. Launch/finish were 2026-10-19T22:16:03.467469+00:00 / 2026-10-20T02:35:55.223460+00:00 (MadridUTC+2).

Active traversal excludes checkpoint I/O and is distinct from phase wall time. Continuation checkpoint-load sample spans were 370.37s, 372.82s (first-to-last samples, approximate). Stage wall also includes launch, hash/verification, export, accounting and monitoring overhead; save/export counters are native event timings and do not partition total wall exactly. All segments use the same 16-thread recipe; no historical production-writer allocation is used for a speed claim.

| Evaluation | Policy loads | Native load s | Native play s incl. reproduction | Replay wall s | Stage wall s |
|---|---:|---:|---:|---:|---:|
| 202610200601-evaluation | 2 | 486.00 | 22.69 | 40.49 | 694.23 |
| 202610200602-evaluation | 2 | 480.40 | 22.48 | 40.49 | 688.18 |
| cross-evaluation | 9 | 2656.51 | 5.72 | 10.53 | 3032.57 |

Four audits: 27.43min wall. Verified staging: 29.51min. Final statistical readout/revalidation: 483.71s. Full per-stage costs and sampled phase RSS are in the compact JSON. CPU sums are child user+system time, not host electricity; one host, two fresh fixed seeds, sequential order and sampled RSS/temperatures limit generalization.

Repeated inference loading is the clearest engineering cost: the cross panel spends 2656.51 s loading versus 5.72 s in native play. Cheaper exact inference loading remains a separate proposed work package; no loader or river-search implementation was tested by this study.

## Provenance, retention and reproduction

Frozen upstream `edd5bc767bdeea6bc41e695bbe2cc0f089042f62`; standalone source-v3 snapshot `312a33b6f99977c618b19ba00fafe1ab015b4001`, 700 matching source/config hashes. Config `6d15cb8b9630eb0e22665d50cd35de68aa2f3dd7b3e0614d5093fa5372b523b0`. Exact binaries/qualification are pinned in [launch.json](launch.json). Four endpoint checkpoint/export/keyset hashes and all 42 replay/manifests are recorded in [results.json](results.json). Both within-lineage keysets match; between-seed sets differ as expected.

The earlier miniature fixture readout-phase error and setup clone/import failures remain preserved; the corrected fresh qualification passed 47 focused tests, 216 real K50 diagnostic hands / 120 legacy parity hands, and 504 initial + 504 reproduction full-fixture hands before the main attempt. No final main failure was discarded or retried.

Owner-approved staging verified **232 new files / 82,498,076,625 bytes** in `/mnt/data2tb/research-cloud/PR-357-nplayer-bb100-seed-confirmation/main-v1/`, preserving accessible original paths with symlinks. Every relocation SHA256/path/size/mtime is in results.json and the remote relocations.jsonl. Existing PR350/355 inputs remain protected. Other controls, cross traces and source roots stay at their original NVMe paths. **Research-Cloud ZIP/Drive upload acceptance remains pending; nothing was deleted.**

Compact evidence retrieval is stored locally under ignored `results/pr357-completed-20261020T0449/`. `evidence.json` contains only settled results, configs/endpoints/audit/proof/cost JSON, resource maxima and relocation receipts; `cost-detail-v2.json` contains evaluation-cost JSON and sampled load spans. Their SHA256 values are in results.json. The first cost-only retrieval had a shell-quoting NameError, before writing any remote state; its empty local output is retained. No models or raw hand/resource traces were downloaded.

To reproduce the compact aggregation after retrieving those JSON receipts:

```sh
python3.11 docs/reports/nplayer-bb100-confirmation/summarize.py \
  results/pr357-completed-20261020T0449/evidence.json \
  results/pr357-completed-20261020T0449/cost-detail-v2.json \
  --out FRESH_REPORT_DIRECTORY
```

Restore an exact model/trace member from its recorded HDD destination with `rsync -a bb128:EXACT_RECORDED_DESTINATION FRESH_IGNORED_DIRECTORY/`, then verify the indexed SHA256. Nonstaged controls remain under the exact main root above; use `scp bb128:EXACT_CONTROL_PATH FRESH_IGNORED_DIRECTORY/`. Drive fallback is pending, not an accepted archive. See [RESULTS_INDEX](../../../RESULTS_INDEX.md).

Recommendation: retain 10B as the leading research candidate for trained-opponent play, keep 3B and all adverse panels, and address inference loading before repeating large evaluation campaigns. Primary gain repeats, but the predeclared overall safeguard combination does not pass. Adoption/release, more nodes, compact-key recipes and search remain separate owner decisions.
