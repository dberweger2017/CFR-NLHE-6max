# Final frozen river assessment: defer this candidate

The predeclared closeout is **defer the frozen search candidate and resume blueprint depth/player-count progress**. Only one of three peer improvement tests passes; none of three scripted safeguards passes. No panel establishes material harm worse than −5 BB/100. These are unresolved safeguards, not five proven losses. No extra hands, tuning, model selection, defaults or release changes follow this result.

[PR398](https://github.com/dberweger2017/CFR-NLHE-6max/pull/398), [proposal397](https://github.com/dberweger2017/CFR-NLHE-6max/issues/397), [frozen protocol](../../river-three-lineage-assessment.md). All three existing 100 BB 10B models remain frozen. Labels003/601/602 denote2026101935003/202610200601/202610200602. Cyclic peers are respectively601/601,602/602,003/003. Scripted lineup is check-call plus pot-pressure; it does not cover every script or mixed field.

## Six fixed panels

Expected on-minus-off singleton contrast, BB/100. Independent unit is the six-permutation deal block. Two **separate** one-sided Bonferroni95% Student-t families: three peer lower bounds must exceed0; three scripted lower bounds must exceed−5. The opposite one-sided upper bound below−5 reports material harm. Lower and upper columns are separately adjusted one-sided bounds, **not** a joint two-sided95% interval. The pointwise interval is unadjusted. Neither family gives one overall95% claim.

| Focal | Lineup | Blocks | Mean | Pointwise95% CI | Family lower | Family upper | Gate |
|---|---|---:|---:|---|---:|---:|---|
| 003 | Peer | 2,048 | +2.75 | [-1.49, +6.98] | -1.85 | +7.35 | Unresolved |
| 003 | Call/pressure | 4,096 | -3.41 | [-7.68, +0.87] | -8.05 | +1.23 | Unresolved |
| 601 | Peer | 2,048 | +1.36 | [-2.59, +5.32] | -2.93 | +5.66 | Unresolved |
| 601 | Call/pressure | 4,096 | -0.73 | [-4.79, +3.33] | -5.14 | +3.68 | Unresolved |
| 602 | Peer | 2,048 | +5.69 | [+1.74, +9.63] | +1.40 | +9.97 | Pass |
| 602 | Call/pressure | 4,096 | -2.18 | [-6.63, +2.28] | -7.02 | +2.66 | Unresolved |

All peer point estimates are positive; all scripted estimates are negative. Seed602's peer result is encouraging, but selecting that lineage would change the agreed three-lineage question. Seed601's scripted lower bound misses−5 by0.14 BB/100; relaxing the margin or multiplicity afterward would also change the question. The limited pass chances were disclosed before launch: this result can justify a practical stop without proving the candidate is harmful.

Keep the fixed expected-return estimator. For example,003's sampled peer mean is+8.52 and its adjusted sampled lower bound barely clears0, while the declared expected estimator gives+2.75 and does not pass. Both are retained in [the unchanged readout](results.json); selecting the favorable estimator would be invalid. Expected variance/sample variance is0.292–0.298 for peers (about3.35–3.43× sample efficiency) and0.578–0.654 for scripts (1.53–1.73×). This does not eliminate heavy tails or imply the same total-cost improvement in every workflow.

## Behavior, coverage and latency

21,261 initial root attempts,21,237 installed strategies,24 declared-game quality fallbacks,1,228 retained-strategy continuation decisions and5 off-tree hands. Off-tree events occur only in peer panels; none occurs in scripted panels, so off-tree fallback cannot explain their negative means. Installed strategies occur in about8.8–9.0% of peer search-on hands and24.2–24.5% of scripted search-on hands. All roots, unchanged sampled actions, fallbacks and no-root zeros remain included. Reproduction counters are not additional samples.

| Panel | Attempts/installed | Quality fallback | Continuations | Off-tree hands | Root median/p95/max s | Variance ratio | Lookup not found/recorded |
|---|---:|---:|---:|---:|---|---:|---:|
| 003 Peer | 1,105/1,100 | 5 | 406 | 2 | 0.441/1.590/3.156 | 0.292 | 30/26070 |
| 003 Call/pressure | 5,953/5,951 | 2 | 0 | 0 | 0.431/0.964/3.125 | 0.654 | 243/66975 |
| 601 Peer | 1,098/1,096 | 2 | 425 | 1 | 0.452/1.614/3.197 | 0.298 | 18/26084 |
| 601 Call/pressure | 6,033/6,030 | 3 | 0 | 0 | 0.446/0.992/3.667 | 0.578 | 280/66944 |
| 602 Peer | 1,084/1,080 | 4 | 397 | 2 | 0.449/1.594/3.183 | 0.298 | 17/25569 |
| 602 Call/pressure | 5,988/5,980 | 8 | 0 | 0 | 0.438/1.007/3.266 | 0.622 | 236/66760 |

These are measured complete root-decision latencies, including legal belief construction/preparation/solving. This candidate is **not a fixed360ms player**: DCFR checks declared quality at frozen sweep checkpoints through2,048 sweeps, with target min(1% pot,0.1 BB); it falls back on failure. Per-panel p99 reaches1.82–3.12s; maximum3.67s. Four workers share two read-only models. Ineligible three-live decisions are13/260,9/294,19/220 for peer/script panels by seed; complete eligibility counters are preserved. Lookup diagnostics expose only `blueprint_found`, not separate positive-mass/zero-mass classifications. No unsupported distinction is inferred.

[Physical-seat results](per-seat.csv) are descriptive, not extra confirmation tests or positional effects (button rotates across blocks). Peer seat means range−1.43 to+7.20; scripted−9.91 to+3.16 BB/100. They do not replace block-level gates.

## Tails and decision examples

The fixed selection retains three most positive and three most negative blocks per panel: [all36 selected blocks](tails.csv), with up to three recorded root examples each in [results.json](results.json). No trimming or exclusions. Below are the largest positive and negative block from each panel. Block contrasts average six hands and scale to BB/100; they are not literal thousand-BB single-hand pots. Root contrast is conditional expected remaining return in BB. Raise amounts are recorded raise-to amounts.

| Panel | Block | Block BB/100 | Centered variation share | Largest recorded root | Dominant blueprint → search mix | Root delta BB |
|---|---:|---:|---:|---|---|---:|
| 003 Peer | 1224 | +1093.0 | 6.08% | `trained/7348/0009` | raise to 1 BB 99.2% → check 96.9% | +65.58 |
| 003 Peer | 10 | -915.9 | 4.31% | `trained/0063/0008` | raise to 45 BB 41.7% → raise to 1 BB 66.0% | -27.48 |
| 003 Call/pressure | 333 | +1261.3 | 2.01% | `call-pressure/2000/0008` | raise to 45 BB 96.8% → check 98.7% | +44.72 |
| 003 Call/pressure | 4024 | -1120.8 | 1.57% | `call-pressure/24147/0007` | raise to 1 BB 80.8% → raise to 73 BB 87.2% | -67.39 |
| 601 Peer | 1771 | +1925.7 | 21.70% | `trained/10626/0008` | check 86.6% → raise to 39.5 BB 98.9% | +115.54 |
| 601 Peer | 1022 | -693.4 | 2.83% | `trained/6134/0009` | check 93.7% → check 95.4% | -20.80 |
| 601 Call/pressure | 143 | +2176.1 | 6.58% | `call-pressure/0859/0008` | check 51.6% → raise to 78 BB 99.8% | +69.06 |
| 601 Call/pressure | 994 | -1180.5 | 1.93% | `call-pressure/5967/0007` | raise to 54 BB 35.1% → raise to 1 BB 77.2% | -35.47 |
| 602 Peer | 586 | +1069.0 | 6.66% | `trained/3516/0009` | check 89.5% → check 97.4% | +32.07 |
| 602 Peer | 8 | -1018.1 | 6.17% | `trained/0050/0008` | raise to 40.5 BB 82.4% → raise to 1 BB 88.1% | -46.03 |
| 602 Call/pressure | 1686 | +1231.8 | 1.76% | `call-pressure/10118/0008` | raise to 78 BB 64.9% → check 98.0% | +50.72 |
| 602 Call/pressure | 558 | -1628.5 | 3.05% | `call-pressure/3351/0008` | check 75.8% → raise to 66.5 BB 84.4% | -54.96 |

The601 peer panel is particularly tail-sensitive: one positive block contributes21.7% of centered squared variation and about0.94 BB/100 to its+1.36 mean. Top-three shares for peer panels are16.6%,28.8%,18.8%; scripted5.9%,10.1%,6.5%. Student-t bounds remain approximate under these tails; absence of an observed rarer event is not proof it cannot matter.

There is no single “checks more” explanation. Checking replaces betting in both beneficial and harmful examples; some large effects retain the same most-probable root action and differ in probabilities or continuation. The rows describe fixed-deal action mixtures and downstream expectations, not controlled causal attribution or prescriptions to change the player. Hidden cards appear only in privileged evaluation, never in player observations. This is a modeled projected-belief solver, not true opponent beliefs, a Nash-convergence proof or safe resolving.

## Proofs, timing and resources

All9 main stages return0; no scientific failure, retry or exclusion. Each of three aliases qualifies before final deals; original003 matches known traces/values. 120 native library tests,27 original focused host tests,29 focused local tests and10 amendment-specific host tests pass. The sole native change is the CLI block limit1,024→4,096; player/solver libraries remain frozen. 221,184 initial hand instances independently replay through pinned `pokers` commit5db20e3d;221,184 fresh reproductions match traces byte for byte and every expected value/profile/work record. All21,261 initial roots reproduce. Evaluation advances zero solvers and reconstructs zero profiles. Reproduction adds no observations.

| Component | Actual cost |
|---|---:|
| Preparation start → final completion, Oct22 08:13:40–13:06:59UTC | 4h53m19s |
| Preparation (model staging, build, native tests) | 3,223.68s |
| Main supervised stages, including qualification | 14,299.18s |
| Three final measurements + readout | 12,868.70s (3h34m29s) |
| Final measurement model/K50 loads, six process starts | 1,421.33s (23m41s) |
| Final measurement play/write, both passes | 11,306.78s (3h08m27s) |
| Inline expectation evaluation, included in play above | 16.600s |
| Final independent proof/reproduction verification | 111.59s |
| Final readout | 18.15s |
| Preparation + main child CPU (user+system) | 26,671.18s (7h24m31s) |
| Final measurement + readout child CPU | 24,967.63s (6h56m08s) |

Components overlap where noted; remaining wall covers orchestration, qualification, hashing and other I/O. Child CPU excludes supervisor accounting and later archival/publication. No training, saving or conversion occurs. Cold staging from HDD took27m34s/23m59s for the latter two policy copies, materially longer than the early rough forecast. Qualified admission revised overall central/reserve to4h54m48s/11h37m57s within the original12h allocation; actual near central. Original execution completed normally, so the owner-approved budget-only continuation was **not used**.

Sampled family peak RSS29,738,618,880bytes =27.70 GiB; minimum available RAM94.006 GiB. CPU max68°C/Thermistor15 max70°C. Main swap growth5.75 MiB; whole preparation-to-main growth10.25 MiB, final378,445,824bytes. Minimum sampled NVMe free197.22 GiB/HDD393.16 GiB. Resource samples are approximately2s apart, not exact high-water measurements; main7,087/preparation1,558 samples. Thermal limits90/100°C and missing/nonfinite sensor stops remain; no time/RSS/disk/swap cutoff or host-setting change.

## Reproduction and preservation

Frozen execution/source `930843ba019f067cf64343b1bdd6cea7b0040199`; binarySHA256 `d3c9047aa449f14ac5a341443239d714709183d70ed1409e8fc1937db3bff0f3`; configSHA256 `138a431c26331b3d0551b7a2fd58a681182a88209d6e385314a9b081c87a003c`. Final deal roots2026102239701–706. [Provenance and exact model/proof hashes](provenance.json), [costs/resource aggregates](costs.json), [exact compact receipts](receipts.json), [supplement](supplement.json), [lineupsCSV](lineups.csv). Later commits publish evidence only. Rebuild the publication without poker execution:

```sh
python3.11 -m scripts.summarize_river_three_lineage_assessment   docs/reports/river-three-lineage-assessment/receipts.json   --supplement docs/reports/river-three-lineage-assessment/supplement.json   --out results/pr398-publication-fresh
```

The helper validates all receipt SHA256s, counts, six proofs, replay coverage, stage codes and settled closeout, then preserves precomputed result bytes; it does not rerun statistics or poker. An initial local publisher assertion used the wrong bridge field name and stopped before output creation; corrected to the recorded `status` field, then all validation passed. This did not affect science.

Raw models/traces/partials/source remain on bb128 at `/home/dberweger/river-three-lineage-assessment-20261022`; protected earlier inputs are untouched. **Archive pending:** the archive preflight stopped before copying because `gh` is absent on bb128. [Failure/status receipt](archive.json) records this accurately; no cache/ZIP/member verification or Drive acceptance is claimed. Intended destinations are `/research/PR-398-river-three-lineage-assessment/` and `gdrive:PR-398-river-three-lineage-assessment/`; neither is a completed restore path yet. Use the original root until verified archival is completed under storage policy. No originals were deleted.

Preserve earlier evidence: [PR357 relative scripted regressions](../nplayer-bb100-confirmation/results.md), [PR388 whole-hand pilot](../river-whole-hand-pilot/results.md), [PR391 conditional evaluation](../river-conditional-evaluation/assessment.md), [PR396 fresh screen](../river-fresh-screen/results.md). These are separate data/questions, not pooled here to rescue a gate. Three fixed models on one host do not estimate training-seed population uncertainty; this panel excludes broader scripts and genuine three-way resolving. The engineering remains a useful research tool. The frozen player has not earned deployment: **defer it, keep the blueprint frozen, and end this assessment without automatic extension.** PR398 is ready for review, not authorized for merge.
