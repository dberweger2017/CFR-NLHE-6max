# Mature inference validation: exact parity, faster jobs, load target missed

The binary derivative preserves the tested policies exactly and cuts a reused
18-case evaluation job from **635.43s to325.99s (1.95×)**. The predeclared
**2× median validated-load target fails**: the two policies improve by1.75×
and1.82×. This is a useful engineering improvement, not a passed joint gate or
a playing-strength result. Retain the optional derivative for repeated work;
do not change defaults or reinterpret the gate after seeing results.

## Terminal evidence and identity

[PR361](https://github.com/dberweger2017/CFR-NLHE-6max/pull/361) follows merged
[PR359](https://github.com/dberweger2017/CFR-NLHE-6max/pull/359) and the unchanged
[protocol](../../nplayer-inference-validation.md). Source `c06fc565` ran on bb128
from October20 **06:52:34 to08:53:01UTC** (08:52–10:53Madrid):120.44min wall.
All33 main stages returned0, root status is complete, no failure file exists,
and the settled result SHA256 is
`4d86548d8fa33c6a215463189d984c76035e6fa7acbf722b5932a89f9621efc6`.
The earlier complete33-stage fixture also passed; no failed mature attempt or
automatic retry is pooled into these measurements.

Both fixed PR357 seed202610200601 averages contain250,001,069 rows. Full
linear audits check every key, action/probability float64 bit and original-mass
tag against the pinned gzip sources. Source/schema/card/menu/game identities
and average scope remain unchanged. The3B source begins `9890286b`, its binary
`41b70ad8`; the10B source begins `fbb0b16f`, its binary `23599816`. Full hashes,
source snapshot/config/executable pins and storage receipts are in
[compact results](results.json).

Each format runs18 cases ×8192 six-hand blocks =884,736 initial hands plus
884,736 exact reproduced hands. Both independent replay/lookup verifiers pass.
Across formats **all884,736 initial hand rows are byte-identical**, including
actions, payoffs and lookup status; headers differ only in artifact hashes.
Within-format reproduction makes the same true for all3,538,944 total hand
instances. These repeated hands are correctness evidence, not independent
strength samples. Four real-K50 first-action probes choose the same fold,
with no lookup miss.

## Loading, memory and storage

Three unprofiled observations per format/policy, fixed alternating ABABAB order,
ordinary warm filesystem cache. Medians below are the reader's validated load
timer, including its file verification; conversion/audit touched inputs first.

| Policy | Gzip load s | Binary load s | Speedup | Gzip child peak GiB | Binary child peak GiB |
|---|---:|---:|---:|---:|---:|
|3B|203.26|115.91|1.75×|32.33|13.18|
|10B|211.52|115.93|1.82×|32.33|13.18|

Peak RSS columns are medians of per-child `wait4` peaks, not a sampled model-only
allocation measure. The corresponding whole-process wall medians are240.13 vs
115.93s for3B and248.46 vs115.95s for10B. Those include process teardown and
are over2× faster; **they do not replace the declared native-load gate**.
All12 load observations have zero major faults. The CSV records minor faults,
CPU, file verification and process costs without excluding slow observations.

Time to the fixed first legal action falls206.27→121.05s (3B) and
216.89→119.68s (10B), measured before process teardown. This is an eager reader:
full validated loading precedes action, with no deferred mmap work to omit.

The two-model evaluator's per-process peak falls **65.94→27.65GiB (58.1% less)**;
sampled entire-family peaks are65.98→27.69GiB. File storage moves in the opposite
direction: each binary is14,148,446,930 bytes (13.18GiB),28.30GB for the pair,
versus11.84GB of gzip sources, **2.39× the logical bytes**. Allocated binary bytes
are28,296,904,704. This pair still exceeds the16GiB M1's physical memory.

## Reused evaluation jobs and one-time costs

| Metric | Gzip | Binary |
|---|---:|---:|
|Arena process wall, including both loads/play/reproduction/teardown s|594.47|285.52|
|Independent replay wall s|40.97|40.47|
|Complete reusable job wall s|635.43|325.99|
|Arena plus replay CPU s|1012.90|707.68|
|Sum of per-case native load timers s|468.78|237.18|
|Sum of per-case native play timers, including reproduction s|27.21|27.33|

Complete reusable job wall improves48.7%; its gate passes. Per-case play times
are task-time sums under8 workers, not an additive wall-time decomposition.
The play sums are almost unchanged; the measured benefit is loading, resident
representation and teardown, rather than faster poker decisions. Every case
shares the already persistent two-model evaluator within its format's batch.

Conversions take317.14s (3B) and324.47s (10B); full parity audits take317.45s
and328.06s. Their **21.45min combined one-time cost is separate** from the
reused-job comparison. At the observed5.16min saved per complete job, conversion
plus audit amortizes after about five equivalent repeated jobs, ignoring storage
staging. A first use that must convert/audit is slower than one gzip job.
All main child processes together consumed6517.98 CPU seconds; that includes
conversion, audits,12 load observations, first-action probes and staging, not
just the two evaluation jobs.

The separate legacy fine profile (excluded from medians) reports18.44s file
verification,54.68s stream decoding,100.91s parse/validate/allocation and29.06s
index insertion within a229.69s total. These instrumented components do not
cover every operation or establish a cross-format causal decomposition. They
support investigating validated-reader work further; they do not show that
gzip decoding is the only bottleneck.

## Preservation, limits and reproduction

All76 verified staging records cover52,739,328,950 bytes of **new owned**
derivatives, working gzip copies and raw initial/reproduction traces. Final
binary staging alone took19.47min and is excluded from reusable-job time.
Original PR350/355/357 inputs stay untouched. No files are deleted. Cache:
`bb128:/mnt/data2tb/research-cloud/PR-361-nplayer-inference-validation/main-v1/`;
NVMe root: `bb128:/home/dberweger/nplayer-inference-validation-20261020/main-v1/`.
Paths remain accessible through verified symlinks. PR362 now depends on these
derivatives; protect them. ZIP/Drive acceptance is **pending**, so a future
`gdrive:PR-361-nplayer-inference-validation/` path is not a verified retrieval
source yet. Archival waits for active dependent work; no competing archival
job was launched during either study.

Observed maxima across all sampled stages wereCPU67°C and Thermistor15 77°C.
All thermal/correctness guards remained intact. Peak family RSS was65.98GiB.
Single host/pair, fixed gzip-first full-job order, ordinary warm cache,
three samples per format/policy, sampled family memory and no independent
hardware replication limit extrapolation. No cold-cache, mmap, default adoption
or scientific strength claim follows. The joint success rule remains false.

[loads.csv](loads.csv) contains every prescribed load observation;
[costs.csv](costs.csv) contains all33 child costs; [results.json](results.json)
contains the precomputed settled result, exact proofs, per-case timing/hashes,
sampled resource aggregates and relocation pins. Reproduce the summaries from
the retained root's `results.json`, `measurements/*/process.json`,
`*-job/evaluation/*/play-*.json` and `relocations.jsonl`; do not rerun science to
regenerate a report. Each reported median uses all three declared observations.
