# Compact-key pilot: correctness passes; larger comparison not admitted

This is the unchanged historical October18 measurement. See the
[October26 integration and review closeout](integration-20261026.md) for current
compatibility, compact binding requirements and additional regression tests.

The fixed two-hour benchmark stopped at its predeclared cost-admission gate after successful qualification and 100M-node pilots. The 1B/3B growth and repeated steady-state comparison did not start. No failed science was retried and the original deadline was not extended.

| Encoding | Training Mnodes/s | Training speedup | Training RSS GiB | Save s | Wall s | CPU s |
|---|---:|---:|---:|---:|---:|---:|
| v1 | 4.968 | 1.000× | 2.196 | 41.97 | 68.58 | 322.87 |
| compact-blake2b-v2 | 7.124 | 1.434× | 2.192 | 42.73 | 63.23 | 252.86 |
| compact-xxh3-v2 | 7.848 | 1.580× | 2.197 | 41.82 | 61.04 | 235.55 |

Each pilot reaches 100,000,055 nodes, iteration23,142 and11,656,034 rows. A separate audited traversal proves a bidirectional key mapping and bitwise equality of all logical rows for both compact schemas. Their raw checkpoint hashes differ by design. All42 executed stages return0, including native tests,1/2/4/8/16-thread determinism, resumed-training identity, legacy v1 checkpoint/export/play identity, schema refusal checks, every-row policy audits and independent smoke replay. CLI qualification records13 checks.

The forecast was7,606.98s (126.78min) against6,453.96s (107.57min) remaining. Serialization accounts for2,301.10s before the25% growth allowance; the whole-run forecast also includes audited traversal, reloads and overhead. The supervisor exits with the preserved budget-refusal failure at18:31:35UTC; its older status file remains `build-and-qualification` and must not be mistaken for a live process.

Measured pilot end-to-end speedups are only1.085× /1.124×: encoding accelerates active training, while saves dominate these tiny segments. These figures are descriptive: one host, one excluded seed, one fixed-order pass, a small growing table, warm caches and500ms RSS samples. xxh3 is10.2% faster than compact BLAKE2b in this pass. Mature-table performance and repeatability remain unmeasured. Do not claim an overnight speedup or default adoption from this pilot.

Maximum observed CPU67°C, Thermistor15 74.5°C, family RSS5.34GiB; no swap growth. Active artifacts were written to the2TB HDD, so save times do not characterize NVMe. The next strength campaign uses the independently validated v1 fast recipe; compact adoption remains a separate decision.

Frozen source `94682632054cec5304cff68fdc149fe4e45fa82d`; root `bb128:/mnt/data2tb/nplayer-key-benchmark-20261018`; supervisor348826 has exited. All raw checkpoints, mappings, logs, traces and failures remain there. Research-Cloud archival is pending. Compact evidence was retrieved with one SSH JSON extraction of root metadata and per-stage results, excluding progress events; no raw model or mapping was copied. See [receipt](pilot-receipt.json), [CSV](pilot.csv) and [protocol](../../nplayer-compact-key-benchmark.md).
