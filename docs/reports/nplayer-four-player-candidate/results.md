# Four-player 100 BB: 10B improves against the fixed 3B field; safeguards remain unpassed

The fixed development campaign completed successfully on bb128 on **October 23, 2026, 13:05:16 UTC /15:05:16 Madrid**. All37 main stages returned0; no failure, retry, extra hands or tuning occurred. The **10B-minus3B primary is +53.85 BB/100**, with simultaneous one-sided95% lower bound **+25.35** against the fixed field of three own3B opponents. **None of the seven scripted/mixed safeguards clears its declared −5 margin.** This is a useful four-player development candidate, not v0.7 release qualification or a universal improvement.

[Protocol](../../nplayer-four-player-candidate.md) · [compact verified result/provenance/costs](results.json) · [panel CSV](panels.csv) · [seat/position CSV](seats.csv) · [lookup counts](coverage.csv) · [extreme blocks](tails.csv) · [stage costs](costs.csv) · [qualification/launch](launch.md). PR413 is stacked on paired-arena PR410; the four-player bb128 qualification does not falsely complete the separate pending final all-size M4 receipt.

## All eight predeclared outcomes

Each field uses4,096 independent fresh deal blocks, all24 seat permutations, both focal arms. Opponent policies, deal/button schedule and identity RNG are fixed between arms. Statistic is mean focal10B-minus3B within each block, BB/100, with **no reciprocal halving**. Permutations, hands and reproduction are not independent observations. The eight one-sided Student-t/Bonferroni lower bounds form one family95%; primary requires lower>0, seven safeguards lower>−5.

| Fixed opponent field | 3B absolute | 10B absolute | Paired delta | Ordinary paired95% interval | Adjusted lower | Gate |
|---|---:|---:|---:|---|---:|---|
| trained | +0.71 | +54.56 | +53.85 | [+31.49, +76.21] | +25.35 | Pass |
| random | +357.07 | +301.04 | -56.03 | [-89.68, -22.37] | -98.92 | Unpassed |
| check-call | +219.22 | +210.41 | -8.81 | [-56.27, +38.65] | -69.30 | Unpassed |
| tight-aggressive | +13.80 | +25.48 | +11.69 | [-3.14, +26.51] | -7.21 | Unpassed |
| pot-pressure | +11.07 | +30.92 | +19.85 | [-0.88, +40.57] | -6.57 | Unpassed |
| call-pressure | +166.14 | +192.08 | +25.94 | [-4.99, +56.88] | -13.48 | Unpassed |
| random-tight | +176.33 | +141.26 | -35.07 | [-55.08, -15.07] | -60.57 | Unpassed |
| trained-call-pressure | +106.36 | +127.30 | +20.94 | [-0.74, +42.62] | -6.69 | Unpassed |

Absolute point returns above and ordinary two-sided intervals in the CSV are descriptive and unadjusted. All10B absolute descriptive lower bounds exceed0, but absolute profitability was not the simultaneous acceptance family. Do not relabel that as release acceptance. The generic pair-helper `no_strength_claim` and result `qualification_complete:false` fields describe its engineering/smoke roles; this main run uses the separately declared development gates, with successful same-source qualification bound by config SHA.

The primary supports improved performance against this particular earlier-checkpoint field. Random and random+TAG have adverse paired point estimates, and their ordinary intervals exclude0; the other unpassed safeguards are not seven demonstrated losses. TAG, pressure and both pressure mixtures have positive means but insufficient adjusted precision. The check-call estimate remains imprecise. Preserve these outcomes alongside [PR357's earlier three-player100BB relative scripted regressions](../nplayer-bb100-confirmation/results.md). Neither that recurrence nor aggregate checking establishes Nash convergence, improved mistake avoidance or reduced value extraction. A mechanism claim requires matched-state evidence.

## Capacity, mass and played coverage

Both endpoints retain **250,003,053 identical keys**, keyset SHA256 `9ba0888511781b2661d0b54c9df5550c1c84048fca19f708ab89c9c7d67cc468`. The250M threshold freezes after a whole iteration, giving3,053-entry overshoot, not natural saturation. Freeze iteration40,389 is bracketed by telemetry:822,829,573nodes/249,628,573entries unfrozen and824,846,903nodes/250,003,053entries frozen. Additional training changes retained strategy/average mass; it cannot add missing membership.

Table-wide zero-average-mass rows fall from27.93% at3B to24.75% at10B. These are stored-row statistics, not played fallback shares. The lookup receipt binds original mass: positive-mass, zero-mass and missing remain distinct; scripts are not-applicable. `coverage.csv` retains every arm/street/identity/physical-seat/button-relative-position count. Focal identity0 river lookups show:

| Field | 3B river missing | 10B river missing | 10B river zero mass |
|---|---:|---:|---:|
| trained | 4.23% | 3.36% | 0.066% |
| random | 34.60% | 25.42% | 0.427% |
| check-call | 96.77% | 96.19% | 0.045% |
| tight-aggressive | 1.12% | 0.33% | 0.000% |
| pot-pressure | 2.47% | 2.14% | 0.124% |
| call-pressure | 45.30% | 37.57% | 0.032% |
| random-tight | 4.79% | 3.25% | 0.048% |
| trained-call-pressure | 11.78% | 9.68% | 0.031% |

The **96.19% check-call river miss share** is an important support limitation, versus3.36% against the trained field. The cap's self-play-selected membership poorly covers this passive field's river visitation. This does not establish that missing keys caused the return delta: the arms reach different situations, and key/menu/abstraction effects are not experimentally separated. Training counters and source-audit street entries/visits are retained separately in JSON, without confusing training missing-decision shares with arena queries.

Primary physical-seat deltas are+2.74/+35.48/+63.96/+113.22BB/100; button-relative position0/1/2/3 deltas are+43.17/+65.42/+57.14/+49.67. Both partitions balance all24 permutations and their means reproduce+53.85. Their descriptive intervals in `seats.csv` are not additional adjusted gates; physical-seat differences should not be generalized into a positional theory.

## Tails retained

No block is removed. Largest positive/negative five block IDs and values per field are in `tails.csv`; raw block arrays and replayable hand traces stay on bb128. These block IDs identify deals, not explanations of individual decisions. Top10 blocks' share of total squared deviation from the paired mean:

trained 14.3%; random 8.6%; check-call 8.2%; tight-aggressive 21.5%; pot-pressure 19.2%; call-pressure 7.6%; random-tight 8.1%; trained-call-pressure 8.7%.

That concentration, especially21.5% for TAG, limits small-effect precision; even4,096 independent blocks do not remove rare-tail uncertainty. Largest pots need not be strategy errors. No post-hoc exclusions or additional hands were used.

## Training and complete operation cost

| Endpoint | Nodes | Iteration | Added-node active time | Save | Train process wall | Other train process work |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 3,000,010,183 | 156,638 | 603.16s (4.97Mnodes/s) | 149.20s | 789.56s | 37.21s |
| candidate | 10,000,017,058 | 566,859 | 1374.43s (5.09Mnodes/s) | 140.58s | 1875.07s | 360.05s |

Active timing excludes I/O; the10B row covers only the continuation from3B. Other process work is residual startup/resume/hash/load and overhead, not an isolated load benchmark. Native training uses16 threads; exports/audits/conversions have their declared worker settings. No production-writer/fast-thread speedup claim follows from this candidate run.

| Measured child category | Wall seconds |
|---|---:|
| training (2stages) | 2664.63 |
| export (2stages) | 858.68 |
| source audit (2stages) | 815.90 |
| conversion (2stages) | 657.76 |
| binary audit (2stages) | 663.79 |
| arena (2stages) | 573.05 |
| independent replay (16stages) | 449.80 |
| pair readout (8stages) | 151.28 |
| global readout (1stages) | 215.91 |

Main launch11:04:42→13:05:16UTC: **7234.23s (2h00m34s)**, including validation between stages; child stages sum7050.82s, residual183.41s. Child user+system CPU totals38218.57s (10.62core-hours); this excludes uninstrumented supervisor validation CPU. Build54.49s and qualification155.20s child-stage wall are separate, with source/environment/hash overhead documented in the launch receipt; local report/review/upload time is not included in main runtime. The owner-approved10h allowance includes preparation/report, is not reset, and is not a time stop.

The two arena processes total573.05s wall. Their native summaries attribute476.95s to model loading and49.64s to playing/writing; two readonly models are loaded once per process and reused across all fields. Binary use preserves exact full-row probabilities/actions; it does not make loading negligible. No new loader optimization or large evaluation is authorized by this result.

All **1,572,864 initial hand instances** independently replay; all **1,572,864 reproductions** are byte-identical. Eight verified pairs and the global proof barrier pass. Initial and repeat traces each occupy6,806,983,502bytes; total13,613,967,004bytes (logical file bytes, not disk growth).

Sampled resources over3490main samples: CPU peak75.0°C; Thermistor15 peak90.5°C; entire worker-family RSS peak27.75GiB; available RAM minimum94.68GiB. Swap432.68→437.43MiB. NVMe free minimum55.76GiB; final sampled112.46GiB. Concurrent owner cleanup changes free space, so these observations cannot measure campaign disk growth. No disk/RAM/swap/time cutoff was added. CPU90/Thermistor15 100/missing-nonfinite plusownerSTOP/mutex/correctness remain the only declared automatic stops. No threshold crossed.

## Provenance, preservation and decision

Frozen execution source **6adc28cea5fe29008766142ae5b9af01ef1e0067**,864source/config pins, bundleSHA256`9a6db8efe7107b42566753d17120de6f6eae906f78b23406bde1c29c354b4b2b`; main configSHA256`f3be3047b3c1b5fb781fa5d3e8c41e43ba7a57cf54a74672f8a5125b2f03cd9c`. Later commits publish evidence only. ResultSHA256 **`ef35893dc09968c2b9212ef3dd20df7e290ffe94b3d592a5a160583ae1271cc0`** is the complete precomputed host result; `results.json` here is a compact derivative omitting only per-block arrays from pairs and adding metadata/costs, not an identical copy. All model/checkpoint/policy/mass/binary/full-row/keyset/proof/environment/K50 pins remain in that derivative. Same-source qualificationSHA0602825a7d3d27ebb27584a5bc83c2f6c9b06f9f46f77eeec4927debf25267c0.

Original retrieval root: `bb128:/home/dberweger/nplayer-four-player-candidate-20261023/` (source-v1, build-v1, qualification-v1, main-v1 and failed pre-build mutex admission retained). Main endpoints `main-v1/baseline-train.gz` and `candidate-train.gz`; model binaries/exports/mass catalogs have full paths and SHA256s in JSON. Raw traces under`main-v1/arena-initial/` and`arena-repeat/`, blocks referenced by field/root/zero-based block index. Original400/402/404/K50/binary/environment dependencies remain protected. Owner accepted starting during cleanup with83.98GiBfree, superseding the prospective147.13GiB admission scenario; no count/source/guard was relaxed.

Archive/cache/Drive acceptance is **owner-managed pending**, no verified alternate retrieval path/Drive file ID or receipt claimed. No files deleted, moved or uploaded by this report. The owner-authorized cleaner was notified after natural completion; at13:06:24UTC the original supervisor had exited and the normal compute mutex had no holder. No lock/storage is reserved; v0.6.1 release has priority over heavy cleanup. The one-time read-only lock-release notification finished and was collected; no new timer or watcher was installed.

**Recommendation:** retain10B as the leading four-player research candidate and keep3B. Record the strong primary gain together with adverse random/random+TAG deltas and unresolved safeguards. The capped table's passive-field coverage deserves attention before treating this as release-ready. This one seed/onehost/K50/menu/fixed-field experiment cannot establish independent-seed reliability, general exploitability or universal strength. Any further capacity diagnosis, five/six-player campaign or independent release confirmation needs its own fixed scope and owner-approved allocation. No automatic extension, tuning, search/default/release change or next-player launch follows.
