# Six-player 100 BB: gains against pressure, unconfirmed trained-field improvement

**The fixed four-checkpoint development run is complete and verified.** The 10B and 15B models have positive ordinary paired intervals against five copies of their own 3B ancestor, but **none of the five trained-field tests clears the predeclared 40-test adjustment**. Only 6/40 development gates pass. The 10B→15B trained-field contrast is−2.19 BB/100 with a wide interval; this run does not establish useful marginal strength from that extra 5B.

Retain all four checkpoints. Treat 10B as a useful working comparator, not a selected release winner. Before more nodes or independent release lineages, prioritize a controlled support/history/visitation investigation with a prospectively defined exploitation tradeoff. Search stays deferred. Missing support is measured here; its causal contribution and the benefit of larger capacity are not.

## Fixed scope and verification

One fresh training seed 2026102361001; six players 100 BB, unpruned K50/v1, deterministic fast16/eight roots, full float64 average and 250M whole-iteration membership freeze. Fixed 3B/6B/10B/15B checkpoints, no player/recipe/menu/guard changes, extensions or retries. Proposal[#416](https://github.com/dberweger2017/CFR-NLHE-6max/issues/416); [protocol](../../nplayer-six-player-candidate.md).

Eight fields, each 4,096 independent deal blocks and 12 balanced forward/reverse seatings. Each checkpoint faces the same opponents, including the same frozen 3B ancestor. A deal block’s mean across 12 seatings is the statistical unit. Neither seatings, repeated 3B arms nor reproduction count as independent observations. The five contrasts reuse the same arms and are correlated.

**115/115 main stages passed**, after 139 exact-source qualification stages. All 2,359,296 physical initial hand instances independently replay; the same count reproduces byte-for-byte. There are 1,572,864 distinct checkpoint/deal/seating instances. Cross-job 3B trace identity, full-row/export/binary/mass/keyset checks, and adjacent/direct block-delta additivity pass. No outcomes were opened until complete status, all stages RC0 and settled global readout. [Completion/proof pins](completion.json).

Main 2026-10-23T18:37:07.292193+00:00→2026-10-23T22:42:24.399002+00:00: **4.09 hours /4h05m17s**, versus 5h51m central /11h37m reserved component scenario under the accepted 12h planning allocation. Coding/report publication is outside that main wall. Separate cleanup tasks overlapped it as documented below; they were outside the scientific allocation. Both normal/study mutexes were observed unheld after completion; cleaner notified without adding a watcher.

## All five paired contrasts

Values below are later minus earlier focal return in BB/100. Brackets are **ordinary two-sided 95% descriptive intervals**. Decision flags use a separate **one-sided 95% family of 40 Student-t/Bonferroni bounds**, df 4095: trained lower>0; seven other fields lower>−5. An unpassed flag does not establish loss or equivalence. No release acceptance rule or best-checkpoint selector is inferred.

| Field |3B→6B|6B→10B|10B→15B|3B→10B|3B→15B|
|---|---:|---:|---:|---:|---:|
|trained|+28.39 [-5.98, +62.76]|+17.80 [-10.85, +46.44]|-2.19 [-27.42, +23.04]|+46.19 [+7.99, +84.38]|+44.00 [+3.45, +84.56]|
|random|+13.84 [-29.73, +57.40]|-19.83 [-56.51, +16.86]|+18.74 [-12.98, +50.47]|-5.99 [-57.79, +45.81]|+12.75 [-42.30, +67.81]|
|check-call|+4.67 [-39.05, +48.39]|-1.27 [-47.27, +44.73]|-16.87 [-58.88, +25.13]|+3.40 [-55.20, +62.00]|-13.47 [-78.93, +51.98]|
|tight-aggressive|+20.45 [+2.57, +38.34]|+0.74 [-11.98, +13.45]|+8.72 [-2.09, +19.52]|+21.19 [+1.82, +40.56]|+29.91 [+10.07, +49.75]|
|pot-pressure|+36.86 [+10.63, +63.08]|+43.03 [+22.05, +64.01]|-12.87 [-29.78, +4.04]|+79.89 [+50.79, +108.98]|+67.01 [+36.42, +97.61]|
|call-pressure|+19.17 [-15.46, +53.80]|+16.14 [-14.82, +47.11]|-20.32 [-48.60, +7.97]|+35.31 [-7.25, +77.88]|+15.00 [-30.86, +60.85]|
|random-tight|-5.36 [-29.10, +18.38]|-0.03 [-19.17, +19.12]|-16.14 [-32.79, +0.50]|-5.39 [-31.06, +20.28]|-21.53 [-48.24, +5.17]|
|trained-call-pressure|+39.40 [+1.19, +77.61]|+9.65 [-23.51, +42.80]|+33.05 [+3.03, +63.07]|+49.05 [+3.65, +94.45]|+82.10 [+33.80, +130.40]|

All 40 exact means,SEs, ordinary intervals, adjusted lower bounds, margins and flags are in [comparisons.csv](comparisons.csv) and [compact results](results.json).

| Contrast |Trained mean|Adjusted trained lower|Trained gate|Passed field gates|
|---|---:|---:|---|---|
|3b-6b|+28.39|-24.64|unpassed|pot-pressure|
|6b-10b|+17.80|-26.40|unpassed|pot-pressure|
|10b-15b|-2.19|-41.12|unpassed|none|
|3b-10b|+46.19|-12.75|unpassed|pot-pressure|
|3b-15b|+44.00|-18.57|unpassed|tight-aggressive, pot-pressure, trained-call-pressure|

The clearest adjusted improvement is pressure 3B→10B: **+79.89**, adjusted lower **+35.00**. Pressure 3B→15B remains +67.01/lower+19.80. The other two 3B→15B passes are TAG (+29.91/lower−0.71 clears the −5 safeguard, not an adjusted improvement claim) and trained/call/pressure (+82.10/lower+7.58). No 10B→15B field clears its gate.

The extra checkpoint is informative: trained-field point gains rise 3B→6B→10B, then flatten; pressure peaks at 10B; trained/call/pressure continues upward. Random and check-call show no uniform monotonic regression here. This is a descriptive multi-opponent trajectory, not proof of saturation, a causal mechanism, or that 15B is worse overall.

## Absolute returns and exploitation safeguards

Ordinary95% descriptive intervals, not adjusted acceptance tests:

| Field |3B|6B|10B|15B|
|---|---:|---:|---:|---:|
|trained|-0.72 [-41.48, +40.05]|+27.68 [-10.72, +66.07]|+45.47 [+10.22, +80.72]|+43.29 [+8.66, +77.91]|
|random|+318.57 [+246.48, +390.66]|+332.41 [+262.82, +402.00]|+312.58 [+245.72, +379.44]|+331.32 [+265.31, +397.34]|
|check-call|+284.89 [+207.16, +362.62]|+289.56 [+210.89, +368.23]|+288.29 [+208.32, +368.26]|+271.42 [+191.83, +351.01]|
|tight-aggressive|-37.58 [-60.14, -15.03]|-17.13 [-35.52, +1.26]|-16.39 [-31.99, -0.79]|-7.68 [-22.02, +6.67]|
|pot-pressure|-78.64 [-112.34, -44.94]|-41.78 [-71.03, -12.53]|+1.25 [-24.91, +27.41]|-11.63 [-34.68, +11.42]|
|call-pressure|+62.24 [+4.66, +119.83]|+81.41 [+24.96, +137.87]|+97.56 [+42.61, +152.51]|+77.24 [+22.80, +131.69]|
|random-tight|+122.39 [+93.22, +151.56]|+117.03 [+91.56, +142.50]|+117.00 [+93.49, +140.52]|+100.86 [+79.59, +122.13]|
|trained-call-pressure|+9.04 [-49.42, +67.50]|+48.44 [-7.31, +104.20]|+58.09 [+3.28, +112.90]|+91.14 [+37.56, +144.72]|

[Absolute return CSV](absolute-returns.csv). Large returns against random/check-call coexist with very poor postflop support; beating these scripts does not establish good general strategy.15B pressure−11.63[−34.68,+11.42] and TAG−7.68[−22.02,+6.67] remain imprecise. Preserve prior PR413/415/357 adverse panels: this different six-player game and fresh seed neither erases them nor establishes a controlled cross-player-count improvement.

## Retained support and actual played coverage

All four checkpoints retain the same **250,001,554 keys**, keyset`b23d1cacca6dff0a4b0af901e1be5c50b2c038e93a931b49116ce0e365c10de7`. Freeze marker iteration23,678; first frozen telemetry at 486,433,044 nodes (iteration23,700), so the cap was reached by approximately486M, well before 3B. That is a telemetry bracket, not an exact freeze-node measurement. Overshoot1,554 keys is whole-iteration semantics, not cap failure.

| Checkpoint |Retained visits|Zero-visit retained rows|Zero-average-mass rows|
|---|---:|---:|---:|
|3b|195,456,439|161,659,000|62,960,890 (25.18%)|
|6b|355,995,663|154,825,500|60,526,234 (24.21%)|
|10b|582,124,755|149,758,755|58,854,501 (23.54%)|
|15b|872,700,036|145,798,131|57,589,054 (23.04%)|

Visits here are retained trainer updates, not all sampled decisions. A zero own-update count does not imply zero strategy mass. Aggregate zero-row reductions are net changes, not row-by-row transition classifications. Fixed membership permits refinement and changes in reached histories, but no new retained keys after freeze. [All street counts/visits](retained-support.csv).

Focal river coverage as positive /zero-mass /missing percentages; decisions in parentheses:

| Field |3B|6B|10B|15B|
|---|---:|---:|---:|---:|
|trained|60.92/0.57/38.51 (2,449)|65.79/0.16/34.05 (2,435)|71.95/0.23/27.82 (2,171)|75.60/0.17/24.23 (2,324)|
|random|9.84/0.94/89.23 (427)|14.96/0.48/84.56 (421)|12.61/0.57/86.82 (349)|15.57/0.00/84.43 (334)|
|check-call|0.00/0.00/100.00 (25,424)|0.00/0.00/100.00 (23,572)|0.00/0.00/100.00 (22,082)|0.00/0.00/100.00 (20,936)|
|tight-aggressive|84.19/0.12/15.69 (1,695)|85.59/0.06/14.35 (1,589)|83.49/0.00/16.51 (1,781)|86.33/0.00/13.67 (1,770)|
|pot-pressure|76.78/0.33/22.88 (2,102)|80.65/0.00/19.35 (2,139)|83.26/0.00/16.74 (2,180)|84.23/0.00/15.77 (2,163)|
|call-pressure|0.15/0.00/99.85 (17,078)|0.24/0.00/99.76 (15,850)|0.24/0.00/99.76 (14,717)|0.29/0.00/99.71 (14,001)|
|random-tight|61.60/1.28/37.12 (3,047)|68.25/0.33/31.42 (2,998)|71.67/0.10/28.24 (3,127)|74.68/0.16/25.16 (3,168)|
|trained-call-pressure|5.23/0.19/94.58 (11,589)|6.79/0.15/93.07 (10,330)|8.03/0.04/91.93 (9,568)|9.27/0.02/90.71 (9,033)|

At 15B, **all 20,936 check-call river decisions are missing** (3B:all 25,424); turn misses99.86%. Trained-field river misses fall38.51%→24.23%, with reached histories and denominators changing. Random 15B river misses84.43%. These are supported-menu keys absent from this retained model, not evidence of unsupported legal actions. Both missing and found-zero-mass use the frozen uniform fallback. Rates must not be interpreted as a controlled same-state coverage improvement or proof that missing keys caused returns.

[All 128 focal checkpoint/field/street rows](lookup-coverage.csv); [complete identity/physical-seat/button-relative-position lookup counters](coverage.json); [all 480 seat/position contrasts](seats-and-positions.csv). Seat/position intervals are descriptive, with no extra multiplicity gate or independent seeding. The two circular opponent orders are balanced but leave general opponent-order robustness unresolved.15B−3B trained physical-seat means range−33.27 to+85.91; all six ordinary seat intervals span zero.

## Tail concentration

Largest positive/negative five blocks for every contrast/field are retained in `results.json`; no exclusions or extra hands. Top10 blocks’ share of total squared deviation:

| Field |3B→10B|3B→15B|
|---|---:|---:|
|trained|6.60%|7.05%|
|random|7.47%|5.54%|
|check-call|6.51%|6.09%|
|tight-aggressive|13.05%|12.37%|
|pot-pressure|8.94%|9.90%|
|call-pressure|5.55%|4.89%|
|random-tight|8.62%|8.61%|
|trained-call-pressure|6.10%|5.89%|

These summaries locate finite-sample concentration; they do not replace the declared block intervals or establish a heavy-tail model. Whole-terminal returns do not isolate the value of an individual decision.

## Complete measured cost

| Component |Wall minutes|CPU minutes|Sampled peak family GiB|
|---|---:|---:|---:|
|training including save/startup|72.27|717.20|20.65|
|export|27.54|102.27|19.21|
|source audit|26.63|183.26|0.36|
|binary conversion|21.15|21.14|0.01|
|binary audit|21.08|21.04|13.19|
|arena initial+reproduction|27.77|37.32|27.69|
|independent replay|17.71|16.85|0.03|
|paired summaries|10.52|9.88|0.09|
|global readout|12.41|12.40|0.10|

| Training segment |Actual endpoint nodes|Iterations|Active seconds|Save seconds|Startup/resume/hash/other seconds|Stage wall seconds|Active Mnodes/s|
|---|---:|---:|---:|---:|---:|---:|---:|
|3b|3,000,016,089|122,812|555.87|138.97|34.24|729.08|5.397|
|6b|6,000,008,427|237,922|543.75|126.26|343.51|1013.52|5.517|
|10b|10,000,011,802|390,401|727.06|128.19|346.50|1201.74|5.502|
|15b|15,000,004,001|582,042|913.20|124.81|354.09|1392.09|5.475|

Across six arena processes (initial+reproduction), reported model/K50 loading totals **1438.13s**, play/write work **112.63s**; arena stage wall totals 1666.40s. Each process loads two read-only models once and reuses them across eight fields/eight workers. Loading, trace hashing and proof rereads remain substantial; this PR implements no further loader optimization.

Active training totals 2739.87s; save totals 518.23s. Active throughput uses added nodes per segment and excludes save/load/hash I/O. The external residual is not an isolated loader benchmark. Native writer/traversal16 and arena8 are fixed; no new scaling experiment.

Sampled campaign-family peak **27.69 GiB**; training peak 20.65 GiB. CPU max **75°C**, Thermistor15 max **93°C**, below 90/100°C guards. Minimum available RAM 94.07 GiB. Swap sampled 442.93→451.64 MiB, max 455.68 MiB; no swap guard. NVMe minimum 68.67 GiB amid active cleanup, so it is not campaign growth alone.

Retained trace files: 96, total 32,116,749,312 bytes. [Exact model/checkpoint/export paths, sizes and SHA256](models.csv), [training costs](training-costs.csv), [arena costs](arena-costs.csv), [full compact cost/resource receipt](costs.json). Sampled peaks are not unsampled maxima or whole-host/cleanup RAM. No whole-host isolated performance claim.

## Cleanup overlap and archival provenance

Owner-authorized cleanup ran concurrently on old PR369/412 HDD duplicates and PR402/404 inactive outputs. NVMe source copy/hash stayed in fresh native-traversal windows with pre-save buffers; explicit model processing windows allowed single 64 MiB/s HDD-only verification/readback plus guarded metadata cutover. Copy cap 128 MiB/s, nice 19/idle; final private flush batch 256 MiB. No NVMe tail-copy exception during processing/arena. Source-prefix comparisons, interrupted attempts, a cleanup receipt-logging fix/repeated hash, yields and exact timing windows are preserved in [cleanup cost context](cleanup-cost-context.json). Journal worker overlap is 5,587.843 seconds and payload-operation overlap 5,505.894 seconds. These include waits, throttling and guard checks; they are neither measured cleanup CPU seconds nor a causal slowdown estimate. Continuous historical cleanup CPU/block-I/O totals are unavailable; two partial process samples are not extrapolated. Shared CPU/cache/I/O means the observed campaign timings are not isolated speed measurements.

All exact approved cleanup actions are complete: 87 HDD groups /129 replacement paths /213 canonical aliases retained; all 12 NVMe links verified. Net NVMe recovery is 139,112,652,800 bytes (129.559 GiB) after link overhead. The final two old PR404 average exports ran 23:05:38–23:08:59 UTC, entirely after main completion at 22:42:24 UTC. Final reported free space was 98.720 GiB NVMe /19.248 GiB HDD; these figures are separate from campaign output growth. PR417 inputs and original scientific paths remain unchanged/readable.

Cleanup **metadata-only** receipt [Drive1m4Yo17eexVc3oVfwEufa5MDzymz7Snmm](https://drive.google.com/file/d/1m4Yo17eexVc3oVfwEufa5MDzymz7Snmm/view):1,493,969 bytes,SHA256 `171f15a36976d9d0bc750e4ae25bfe08413e2898689797df0aef905b149e5dba`,165 members; acceptance reported by cleaner. It is **not research-payload Drive acceptance**. The final 184-member metadata ZIP is sealed locally, SHA256 `be9af8df6f5d906f9aa0ef538eecc31e9204efa0b73a2374897e2bca8fb7933d`; two bounded uploads failed with Google API per-project per-minute rate limits. Final metadata acceptance is pending, with no retry timer; this is not storage-capacity evidence. New PR417 raw archive/Drive acceptance remains owner-managed pending. All models, raw traces, block arrays, source, proofs, partials and protected inputs remain on bb128/HDD KEEP; no deletion/upload by this task.

## Limits and next decision

This is one training seed, one capped table and a fixed own-ancestor field. It measures deal uncertainty for this lineage, not training-seed variability, general opponent strength or Nash convergence. The family of 40 adjustment was frozen before play and is retained despite imprecision; passing only 6 gates is not evidence that the other 34 are losses. Ordinary positive intervals do not override the adjusted trained-field gate.

The four checkpoints answer the requested trajectory question without extending the run: no demonstrated trained-field marginal gain 10B→15B, some adjusted pressure/mixed gains, broad unresolved safeguards and severe field-dependent missing support. Retain all checkpoints and all prior adverse results; do not select a release or add nodes/hands to chase significance. A bounded, controlled support/history/visitation comparison is more justified than simply extending beyond 15B or multiplying release lineages. Its mechanism, capacity and acceptable exploitation tradeoff still need a separate prospective proposal.

Frozen source `128f021b8abb5c237574aeec9522592ec77a63d5`; 879 source/config pins; 81 native files byte-identical PR415. Config `b7289278d33eb938694a56e7c275404b0b2c648fbb705aa208f961ba50b6b881`. Raw result SHA256 `361e40b70f195d578592d1155738340917d753fdd2cbd3866236adee3bd3e5c1`. Read-only original result: `ssh bb128 cat /home/dberweger/nplayer-six-player-candidate-20261023/main-v1/results.json` (includes block arrays; verify SHA). Compact Git reports contain only precomputed summaries, not models/raw traces. PR417 remains owner-review only; no merge/default/release authority exercised.
