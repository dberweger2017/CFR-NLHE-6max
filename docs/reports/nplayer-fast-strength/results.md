# PR335 fast mode: completed three-seed strength study

Both predeclared gates pass. At equal 600-second active training time, the fast policies gain in all three paired comparisons. At equal 1B nodes, every 95% lower bound clears the −5 BB/100 noninferiority margin; every interval also includes zero, so equal-node superiority is not established. Recommend merging #335 as an **opt-in** mode, with the existing production default retained until the owner decides adoption. No merge/default/release change is performed by this report.

## Verified strength

Three-player 20 BB, K50, fixed seeds 2026101541/42/43; fast uses 16 logical threads and eight roots per seat, production its original single-thread stream. Each row uses two opponent lineups: a fast singleton against two production copies and a production singleton against two fast copies. The reported statistic is **(fast-singleton BB/100 − production-singleton BB/100) / 2**, averaged within paired six-hand seat-rotation blocks. It is a mean oriented singleton contrast, **not pooled individual-player return**. Intervals are the frozen two-sided Student-t 95% intervals over 8,192 independent blocks.

| Seed | Equal 1B nodes, BB/100 [95% CI] | Equal 600 s, BB/100 [95% CI] |
|---|---:|---:|
| 2026101541 | -0.20 [-3.70, +3.29] | +9.18 [+5.63, +12.73] |
| 2026101542 | +1.42 [-2.04, +4.87] | +9.73 [+6.21, +13.26] |
| 2026101543 | -0.48 [-4.07, +3.10] | +8.86 [+5.13, +12.59] |

Equal-node gate: all three lower bounds > −5, **passed**. Equal-time gate: all three lower bounds > 0, **passed**. Equal-node references are the pinned archived PR292 full averages; equal-time references are fresh production models trained in this run. Each row has 98,304 final hands across its two lineups. All **589,824 final hands** independently replay and all **589,824 reproduction hands** exactly reproduce before the global score readout. All 12 case receipts pass. Nine new full-average exports pass every-row probability audits across **294,564,707 rows**.

## Actual endpoints and costs

Training time excludes loading, checkpoint writing and checkpoint hashing. The 1B fast checkpoint is saved when first crossed at a complete iteration; training then continues to the 600-second checkpoint. Overshoots below are unchanged complete-iteration boundaries. Iteration counts across recipes are not equivalent because fast batches multiple roots per seat.

| Seed | Recipe / endpoint | Actual nodes | Iterations | Entries | Active train s | M nodes/s | Save s | CP GB |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2026101541 | fast / nodes | 1,000,004,051 | 201,886 | 29,512,484 | 203.477 | 4.915 | 106.53 | 1.193 |
| 2026101541 | fast / clock | 2,949,726,632 | 562,488 | 44,661,934 | 600.001 | 4.916 | 165.09 | 1.860 |
| 2026101541 | production / clock | 620,967,410 | 1,025,648 | 24,137,943 | 600.000 | 1.035 | 105.59 | 0.984 |
| 2026101542 | fast / nodes | 1,000,002,364 | 201,918 | 29,305,912 | 196.813 | 5.081 | 96.35 | 1.184 |
| 2026101542 | fast / clock | 3,003,671,483 | 577,172 | 44,216,070 | 600.000 | 5.006 | 150.89 | 1.841 |
| 2026101542 | production / clock | 611,844,588 | 1,022,010 | 24,432,927 | 600.000 | 1.020 | 105.08 | 0.993 |
| 2026101543 | fast / nodes | 1,000,004,699 | 200,237 | 29,465,179 | 205.885 | 4.857 | 104.51 | 1.191 |
| 2026101543 | fast / clock | 2,910,499,919 | 556,892 | 44,406,527 | 600.001 | 4.851 | 160.53 | 1.848 |
| 2026101543 | production / clock | 609,703,125 | 1,007,663 | 24,425,731 | 600.001 | 1.016 | 105.77 | 0.993 |

| Seed / recipe | Load s | Total save s | Stage wall min | CPU min | Sampled peak GiB |
|---|---:|---:|---:|---:|---:|
| 2026101541 / fast | 4.85 | 271.62 | 14.78 | 130.35 | 5.14 |
| 2026101541 / production | 4.84 | 105.59 | 11.89 | 11.89 | 3.27 |
| 2026101542 / fast | 4.91 | 247.24 | 14.37 | 131.05 | 5.10 |
| 2026101542 / production | 4.89 | 105.08 | 11.89 | 11.88 | 3.29 |
| 2026101543 / fast | 5.18 | 265.04 | 14.68 | 131.15 | 5.11 |
| 2026101543 / production | 4.87 | 105.77 | 11.90 | 11.89 | 3.29 |

| Total over three seeds | Fast | Production |
|---|---:|---:|
| Active training min | 30.00 | 30.00 |
| Loading s | 14.94 | 14.60 |
| Checkpoint writing s | 783.90 | 316.43 |
| Training-stage wall min | 43.83 | 35.69 |
| Training-stage CPU hours | 6.54 | 0.59 |

At 600 seconds fast processes **2.910–3.004B nodes**, versus **0.610–0.621B** for production: **4.75×, 4.91× and 4.77×** more nodes for the three seeds. This is stronger play per elapsed training time under the declared allocations, not better efficiency per core: the six training stages use 6.54 CPU-hours for fast versus 0.59 for production. Fast stage wall time totals 43.83 minutes versus 35.69 for production, but fast writes six checkpoints versus three and trains far more nodes. **Production uses checkpoint writer pool 1 versus fast 16**; these end-to-end costs are not a matched writer-pool or matched-output saving benchmark.

The complete v5 attempt ran **102.08 minutes**, 13:00:26–14:42:31 UTC (15:00:26–16:42:31 Madrid), with **9.16 child CPU-hours** over all stages. Summed measured stage wall time is 102.00 minutes; the small remainder is controller/preparation overhead. Model export plus audits took **11.63 minutes**, final evaluation/reproduction/replay **5.52**, and verified readout **30.49 seconds**. Peak sampled aggregate family RSS was **59.86 GiB**, during eight-worker evaluation; peak fast training/save RSS **5.14 GiB**, production **3.29 GiB**, preparation **8.46 GiB**.

Maximum recorded CPU package **74°C**, Thermistor15 **94°C**; v5 stayed below the owner-authorized 90/95°C stops, with only 1°C sensor margin during fast training. Maximum swap growth **6.25 MiB** occurred during evaluation (within 256 MiB); training had none. Minimum available RAM **63.05 GiB**, minimum free NVMe **58.70 GB**. The continuously enforced disk floor plus remaining reservation passed, with a minimum recorded headroom of about **26 MB**. These are measurements from this attempt, not sustained thermal or future-storage guarantees. BIOS fan control and the original sensor driver were unchanged.

## Position and coverage

Equal-time fast-singleton means are +6.35, +9.08 and +7.33 BB/100; the opposite production-singleton lineup means are −12.01, −10.39 and −10.39. Equal-node means are close to zero in both orientations. Full role-specific 95% intervals by physical seat and relative position are in [seats-and-positions.csv](seats-and-positions.csv), with all 72 estimates retained. Physical-seat intervals are broad; no seat-specific superiority claim is made. Relative position 0 is button, 1 small blind, 2 big blind. The following are descriptive equal-time singleton means against their respective pair lineups, not paired position contrasts:

| Seed / singleton role | Button | Small blind | Big blind |
|---|---:|---:|---:|
| 2026101541 / fast | +33.81 | -0.09 | -14.67 |
| 2026101541 / production | +20.63 | -17.18 | -39.47 |
| 2026101542 / fast | +30.17 | -4.12 | +1.17 |
| 2026101542 / production | +14.53 | -18.12 | -27.59 |
| 2026101543 / fast | +34.29 | -11.14 | -1.17 |
| 2026101543 / production | +25.35 | -26.70 | -29.83 |

Coverage below aggregates decisions in the final play only (not reproduction), across the frozen mix of endpoints and opponents. These mixes differ, so it is descriptive support coverage rather than a causal comparison or guarantee of strategy quality.

| Recipe | Street | Decisions | Missing keys | Missing % |
|---|---|---:|---:|---:|
| fast | preflop | 941,146 | 8 | 0.00085% |
| fast | flop | 414,563 | 22 | 0.00531% |
| fast | turn | 248,708 | 68 | 0.02734% |
| fast | river | 142,154 | 74 | 0.05206% |
| production | preflop | 941,494 | 13 | 0.00138% |
| production | flop | 415,210 | 33 | 0.00795% |
| production | turn | 248,219 | 130 | 0.05237% |
| production | river | 140,825 | 171 | 0.12143% |

Each case/model/identity/street count is retained in [coverage.csv](coverage.csv); audit street visit density and zero-mass counts remain in [completion.json](completion.json). Low key-miss rates do not establish good decisions in represented states.

## Qualification, provenance and limits

Qualification selected 16 threads on the excluded seed: same 20,001,395-node segment medians 22.695 / 11.811 / 6.656 / 4.361 / 3.972 seconds for 1 / 2 / 4 / 8 / 16 threads. This is **5.71×** versus one fast thread and **9.8%** more throughput than eight. All ten continuation checkpoints are byte-identical, and real-K50 default parity, fast cross-thread identity/resume and 50 native tests pass. Fifteen focused controller/guardian tests pass after the retry boundary/sample-retention change. The pilot is not a production strength measurement or a long-duration scaling estimate.

This is one host, three fixed seeds, three-player 20 BB and direct same-seed policy lineups. No external opponent, cross-policy population, six-player, exploitability or Nash claim follows. The fixed-order training and single 600-second budget limit extrapolation. Confidence intervals describe held-out deal uncertainty conditional on the fixed training seeds; they do not estimate the population distribution over training seeds. Both gates are conjunctions over the declared seeds; no extra hands or favorable-seed selection were used.

Frozen v5 source: `8f6fb76dade872b6ab282f1a0a4f6f3abee7dbfa`; tested PR335 `b9923248cb97bc52c7db34491d9ff70e2845b4ec`; 720 source/config hashes verified and all 48 native files byte-identical to v4. Input model hashes, K50 tables, cases and held-out roots remain pinned in the protocol and completion receipt. Evaluation manifest SHA256: `2ba4a487b3b15be835340c030d0a01d21e006ac2a6cb45c6e84f3256f93c4d45`. Root `results.json` SHA256: `fea5f71b0f39c912e9019fd49749eeb093a8fa09543f589a7239112e4c1eb942`.

Raw root: `bb128:/home/dberweger/nplayer-fast-strength-20261018-main-v5/`. All final stage return codes are zero; root status is complete, no failure exists, evaluation verification passes and the precomputed readout is settled. This report validates the compact receipts without rerunning science. The frozen `scripts.read_nplayer_fast_study` describes exact block reconstruction, interval calculation and global barrier; `scripts.run_nplayer_fast_study` defines the complete execution. [checkpoints.csv](checkpoints.csv) records all nine new checkpoint/export hashes, exact paths, counts and timings; [training-costs.csv](training-costs.csv) and [stage-costs.csv](stage-costs.csv) derive from stage result events/CPU counters; peak resources are maxima over retained samples. Full compact verification/audit/case metadata is [completion.json](completion.json).

Resource sampling is approximately twice per second and can miss short peaks; aggregate RSS sums process RSS, so shared pages may be counted more than once. CPU is summed child user+system time, not power or electricity. Stage timings include startup/hash overhead not assigned to training/load/save. Export/audit are measured together; native evaluation loads and play/replay timings are also retained per case in the completion receipt.

The earlier disk-admission, Python3.13 dependency and pretty-JSON setup stops remain preserved before final training. The v4 first-final-seed thermal stop remains terminal at 12:05:39 UTC with no final strength result; its crossing sample was not recorded. The owner explicitly authorized this one fresh v5 attempt at CPU90/Thermistor15 95 after that stop. No endpoint, held-out root, count or original 18:31:32 UTC deadline changed. See [prior failure](terminal.md), [launch](retry-launch.json), [protocol](../../nplayer-fast-strength-study.md).

PR335 and PR340 remain open, so raw roots, checkpoints, exports, traces, source/binary manifests and prior failures are retained untouched. **Research-Cloud archival is pending** for `PR-340-nplayer-fast-strength-study`; no archive upload/acceptance or cleanup is claimed. PR292 inputs remain protected read-only dependencies. The existing study monitor is disabled following verified completion; no further experiments are scheduled.

Retrieve a compact source into a fresh ignored destination with `scp bb128:/home/dberweger/nplayer-fast-strength-20261018-main-v5/results.json FRESH_DESTINATION/results.json`, then verify the SHA256 above. For any model use the exact raw-root path and checkpoint/policy SHA256 from checkpoints.csv; eventual Drive/cache fallback remains pending and the archived PR292 inputs retain their existing accepted restoration provenance.
