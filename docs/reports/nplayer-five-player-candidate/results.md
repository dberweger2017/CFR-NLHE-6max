# Five-player 100 BB: improvement against the fixed 3B field, with exploitation safeguards unresolved

The fixed campaign completed on **October 23, 2026, 16:10:16 UTC /18:10:16 Madrid**, in **1h54m**. All 37 main stages returned0. All **655,360 initial hand instances** independently replayed and all 655,360 reproductions matched byte for byte. No scientific failure, retry, extra hands or tuning occurred.

The 10B model improves against four copies of its own 3B ancestor by **+74.05 BB/100**, adjusted one-sided95% lower **+31.35**. Pressure also clears its safeguard. **Six of seven scripted/mixed safeguards remain unpassed**, including adverse random/random+TAG deltas. Keep 10B as the leading five-player research candidate and retain 3B; review the exploitation/support tradeoff before multiplying these into release lineages. This is not v0.7 release acceptance or a general-strength verdict.

[Protocol](../../nplayer-five-player-candidate.md) · [compact result, pins and costs](results.json) · [panels](panels.csv) · [seats/positions](seats.csv) · [lookup counts](coverage.csv) · [street support](support.csv) · [tails](tails.csv) · [stage costs](costs.csv) · [qualification](qualification.json) · [launch/amendments](launch.md) · [release overlap](release-cost-context.json).

## Eight fixed comparisons

Each field uses 4,096 independent fresh deal blocks and ten balanced seatings: five rotations of forward identity order and five of reverse. Only focal 3B→10B changes; all four opponents, deals/buttons and identity RNG stay fixed between arms. The statistical unit is the **mean paired contrast within a deal block**, not each seating, hand or reproduction. No reciprocal halving. One family of eight one-sided Student-t/Bonferroni 95% lower bounds: primary requires lower >0, seven relative safeguards lower >−5 BB/100. Ordinary paired/absolute two-sided95% intervals are descriptive and unadjusted.

| Fixed four-opponent field | 3B absolute | 10B absolute | Paired10B−3B | Ordinary paired95% interval | Adjusted lower | Gate |
|---|---:|---:|---:|---|---:|---|
| trained | -24.84 | +49.21 | +74.05 | [+40.55, +107.55] | +31.35 | Pass |
| random | +378.32 | +294.21 | -84.11 | [-137.60, -30.61] | -152.29 | Unpassed |
| check-call | +280.21 | +268.79 | -11.41 | [-65.14, +42.31] | -79.89 | Unpassed |
| tight-aggressive | +16.56 | +17.77 | +1.21 | [-15.32, +17.74] | -19.86 | Unpassed |
| pot-pressure | -54.40 | -10.25 | +44.15 | [+18.22, +70.07] | +11.10 | Pass |
| call-pressure | +109.62 | +121.54 | +11.92 | [-27.21, +51.05] | -37.96 | Unpassed |
| random-tight | +167.62 | +130.16 | -37.46 | [-62.68, -12.23] | -69.61 | Unpassed |
| trained-call-pressure | +108.04 | +152.54 | +44.50 | [-4.76, +93.77] | -18.28 | Unpassed |

Against pressure, 10B gains +44.15 BB/100 but its **absolute return remains −10.25**, ordinary 95% interval [−31.14,+10.64]. Passing a relative noninferiority safeguard does not establish absolute profitability. The six other unpassed safeguards are not six demonstrated losses: random and random+TAG have adverse means with ordinary intervals below 0; check-call is imprecise, while TAG and both pressure mixtures have nonnegative means but insufficient adjusted precision. Absolute return intervals for every arm are retained in panels.csv.

The baseline's trained-field absolute −24.84 has an interval spanning 0; the primary is a paired comparison, not a claim that identical-policy self-play has negative expectation. Main pair-helper `no_strength_claim` labels its generic engineering role; this campaign's inference follows the separately frozen development gates.

The primary establishes improvement against this lineage's earlier checkpoint field. It does not establish Nash convergence, reduced general exploitability or superiority against other trained lineages. The adverse random/random+TAG pattern resembles [four-player PR413](../nplayer-four-player-candidate/results.md) and [three-player PR357](../nplayer-bb100-confirmation/results.md), but player counts, fields and samples differ: their magnitudes are not a controlled scaling comparison. Neither recurrence nor checking frequencies identifies a mechanism. No automatic expansion follows.

## What further training changes inside the fixed table

Both checkpoints retain **250,000,979 identical keys**, keyset SHA256`07d7d3bc561ac8f0991ba41b45efd0f9800c5e31bd05d7719eb252e7df584a6f`. The 250M threshold freezes after whole iteration 26,597, with 979-entry overshoot. Telemetry brackets freezing between **574,049,605 nodes/249,200,216 entries** and **576,383,651 nodes/250,000,979 entries**. This is capped membership, not natural saturation. Further nodes update retained rows and averages; no new keys can be inserted.

| Street | Retained keys | Visits3B | Visits10B | Added visits | Net fewer zero-visit rows |
|---|---:|---:|---:|---:|---:|
| preflop | 20,400,596 | 27,062,486 | 69,043,674 | 41,981,188 | 1,159,756 |
| flop | 36,184,239 | 49,999,428 | 147,979,907 | 97,980,479 | 2,063,124 |
| turn | 65,325,081 | 85,938,584 | 276,709,839 | 190,771,255 | 3,585,363 |
| river | 128,091,063 | 127,137,335 | 402,018,231 | 274,880,896 | 7,923,655 |

Recorded retained visits increase from 290,137,833 to 895,751,651. Zero-visit rows fall from 148,481,977 (59.39%) to 133,750,079 (53.50%), a net 14,731,898. Table-wide zero-average-mass rows fall from 66,137,715 (26.45%) to 60,517,484 (24.21%), net 5,620,231. Zero visits, zero average mass and played missing-key lookups are distinct measurements; do not substitute one for another. These are aggregate endpoint/net changes, not an audited individual-row transition distribution. Full source-audit training missing/discard counters remain in JSON.

Played focal river lookup shares:

| Field | 3B missing | 10B missing | 10B zero mass | 10B river decisions |
|---|---:|---:|---:|---:|
| trained | 16.63% | 10.52% | 0.000% | 3,506 |
| random | 70.03% | 57.95% | 0.530% | 566 |
| check-call | 100.00% | 99.99% | 0.000% | 16,728 |
| tight-aggressive | 6.00% | 3.96% | 0.000% | 1,618 |
| pot-pressure | 11.79% | 8.70% | 0.000% | 2,150 |
| call-pressure | 75.34% | 68.36% | 0.081% | 12,309 |
| random-tight | 17.36% | 11.16% | 0.000% | 3,252 |
| trained-call-pressure | 83.75% | 75.85% | 0.040% | 9,947 |

The 10B check-call river encounters **16,726 missing keys out of 16,728 decisions (99.988%)**; only two have positive mass. Trained-field river misses are 10.52%; call-pressure 68.36% and trained/call/pressure 75.85%. This is a material support limitation despite the continued-training gain. More nodes after freezing cannot expand that membership. Played miss rates decline in these comparisons, but the arms reach different histories, so this does not establish a causal coverage improvement or explain the return delta. A larger table, abstraction/menu mismatch and policy visitation have not been experimentally separated.

Every identity/physical-seat/button-relative-position/street count is retained in coverage.csv; source-bound positive-mass/zero-mass/missing/not-applicable remain distinct. Scripts are not-applicable. Focal rates and changes with denominators are also precomputed in JSON. Primary physical-seat deltas are +62.51/+17.42/+98.22/+78.98/+113.11; their balanced mean is +74.05. All per-seat/position descriptive intervals are in seats.csv. Only two circular opponent orders were sampled; balanced seats do not establish order robustness.

## Rare tails preserved

No block is excluded. Largest positive/negative five block IDs and returns per field are in tails.csv; raw arrays and replayable hands remain on bb128. Top 10 blocks' share of total squared deviation around the paired mean:

trained 8.7%; random 6.8%; check-call 6.9%; tight-aggressive 19.5%; pot-pressure 17.3%; call-pressure 6.1%; random-tight 9.0%; trained-call-pressure 5.2%.

Tail concentration reaches 19.5% for TAG and 17.3% for pressure. The declared Student-t bounds remain the precomputed analysis, with rare-tail uncertainty retained. Extreme block IDs locate deals; they are not explanations of individual strategy errors. No selection, additional hands or causal hand-story claim follows.

## Actual training and complete cost

| Endpoint | Nodes | Iteration | Added-node active time | Save | Train-process wall | Other process work |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 3,000,023,329 | 131,966 | 584.06s (5.14Mnodes/s) | 134.61s | 755.26s | 36.60s |
| candidate | 10,000,007,380 | 451,803 | 1353.62s (5.17Mnodes/s) | 134.61s | 1849.84s | 361.61s |

Active timing excludes I/O. The 10B row is added 7B work after 3B; native elapsed includes its save but excludes external startup/resume/hash/load work. The residual is not an isolated load benchmark. Both checkpoints/exports/binaries remain unchanged and retained.

| Measured category | Child stages | Wall seconds | Child CPU seconds |
|---|---:|---:|---:|
| training | 2 | 2605.10 | 27786.06 |
| export | 2 | 850.52 | 3213.29 |
| source audit | 2 | 825.69 | 5541.59 |
| conversion | 2 | 671.28 | 666.01 |
| binary audit | 2 | 671.26 | 669.61 |
| arena | 2 | 534.47 | 667.80 |
| independent replay | 16 | 252.10 | 229.01 |
| pair readout | 8 | 88.73 | 81.68 |
| global readout | 1 | 167.42 | 164.55 |

Main 14:16:17→16:10:16UTC: **6839.30s /1h53m59s**. Child stages sum 6666.57s; residual 172.73s includes validation/between-stage work. Measured child CPU 39019.61s /10.84core-hours excludes uninstrumented supervisor validation CPU and separate release work. Two arena processes take 534.47s: native summaries attribute 481.93s to loading and 27.02s to playing/writing; this is persistent reuse of two readonly models across eight fields, not eight full reloads. Full-row conversion/audits preserve exact probabilities, action order and source-mass tags.

Exact-source build + qualification 380.88s /6m21s is separate from main, with 56 qualification stages and 320 initial +320 reproduced hands. Previously passed 121 native library/eight paired/one legacy tests (one existing ignored),26 pinned Python and 43 local tests are in the build/qualification receipts. Preparation/report/CI/upload time is not instrumented main cost. The accepted 6h complete planning allocation included those activities and was not reset or an elapsed-time kill. Original quote 2h59m36s central /5h54m42s reserve remains dated planning evidence, not a measured five-player result.

**Concurrency label:** v0.6.1 release integrity/native checks overlapped **15:44:54–15:59:37UTC**,883.067s, on CPU15/nice19/ioniceidle/single-thread/HDD-only. Independent compact receipt SHA verification passes. Integrity CPU 163.367s, physical read 33,998,786,560B/write 42,919,002,112B; native CPU 384.692s, physical read 2,523,136B/write 18,300,928B; native peak 14.66 GiB. Model reads were mostly served from cache. All three checks and reconstructions pass; this is release integration, not new strength evidence. PR415 kept normal mutex PID888459/inode46 and unchanged config. The one-use exception is **consumed/finished**, with no general bypass remaining. Do not subtract the overlap from PR415 wall time or infer its causal slowdown. Exact PIDs/intervals/costs/receipt are linked in release-cost-context.json. This was not an isolated-host benchmark.

Cleaner reports its exact three approved PR404 old 3B checkpoint copy/readback started only after the 16:10:26 UTC completion/lock check; no overlap with main science is reported. Final relocation/reclaimed-byte receipt is cleaner-owned pending. No PR415 input was moved by this agent. Release had no NVMe scratch/reservation; fresh HDD reconstruction scratch was cleared by release operations.

Across 3,300 main resource samples: **CPU peak 74°C /Thermistor15 peak 91°C**, worker-family RSS peak 27.74 GiB, available RAM minimum 84.98 GiB. Worker RSS excludes the separate release family; available RAM reflects the whole host. Swap 440.18→442.93MiB. NVMe free 111.54→47.77GiB sampled; HDD minimum 72.49 GiB reflects concurrent release scratch. Free-space changes are not isolated campaign disk growth. Initial/repeat logical traces each 3,600,287,031 B, total 7,200,574,062 B. Only thermal/missing-sensor/ownerSTOP/mutex/correctness stops were configured; no automatic time/RSS/disk/swap cutoff and no threshold crossing.

## Provenance and closeout

Frozen execution **6a01b327eb56c7678cb702e1c9106c98ba614699**,874 source/config pins;81 native files byte-identical PR413; bundleSHA256`26b83becea886eb02c087e8b802f5f0a12b7ff7214ad7845518babf0bfb90024`. Main configSHA256`aafa94da23019db594cc305e6a96d735f2f04178fc5f171d52395dc4d345fe22`. Same-source qualificationresultSHA256`272e619bac9ffb40cc72e562882bbe3b972424b24eb2dc9aa3dceb56f668f1c6`. Full host resultSHA256 **`cdf3d1430b216afdbe28f4d9728f8668f76cd6e42932cb7f6f2e25902a3306be`**; results.json here is a compact derivative omitting bulky per-block arrays and adding costs/provenance, not byte-identical to the host result. Model/checkpoint/export/binary/mass/keyset/replay/manifests/environment/K50/source hashes remain in JSON. Initial source-bootstrap prerequisite correction before any build/science is preserved and is not a scientific retry.

Main-targeted PR415 integrates main`d8b17868` and paired/four-player tip`9452f973` via`d511a6c6`; reporting preserves both documentation conflict sides. This carries required PR410 paired-arena source and PR413 evidence; it does not merge/close PR410 or relabel its separate pending final all-size M4 receipt as completed. The fresh exact-source five-player qualification is the gate used here.

Original retrieval: `bb128:/home/dberweger/nplayer-five-player-candidate-20261023/` with source-v1/build-v1/qualification-v1/main-v1, endpoints `main-v1/baseline-train.gz` and`candidate-train.gz`, exports/binaries/mass catalogs perJSON. Raw traces `main-v1/arena-initial/` and`arena-repeat/`, identified by field/root/zero-based block ID. Owner accepted launch duringcleanup at 111.54 GiB free instead of waiting for 133.13 GiB scenario; immutable launch/owner/storage records retained. All prior parents and pinned K50/build/venv/shared runtime/source/proofs stay protected.

Archive/cache/Drive acceptance is **owner-managed pending**. No verified alternate retrieval path, Drive ID, remote acceptance, deletion or upload is claimed. All originals/partials/source remain retained. The original supervisor exited, normal mutex inode46 has no holders on final compact readback, and release/cleaner were notified. No lock/storage reservation, new timer/observer or follow-up science remains active from this campaign.

**Recommendation:** keep both checkpoints and10B as the leading research candidate; follow the frozen direction to **review scripted exploitation/support before replication**. Strong own-ancestor improvement and pressure improvement coexist with adverse random/random+TAG and near-total passive-field river misses. This one seed/onehost/K50/menu experiment cannot identify whether capacity, abstraction, visitation or another mechanism causes those limitations. Prospectively define the acceptable strength/exploitation tradeoff before release lineages; any capacity experiment or six-player development allocation needs its own fixed protocol and budget. No more nodes, samples, tuning, search, defaults, release adoption or merge is automatically authorized.
