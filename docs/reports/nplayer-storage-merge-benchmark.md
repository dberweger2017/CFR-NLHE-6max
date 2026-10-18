# N-player compact storage and parallel saving: bb128 results

The fixed comparison completes successfully. **Recommend adopting #331 and #333
as a pair**, subject to their normal review and CI: compact storage cuts peak
RAM, and the parallel writer more than offsets its training cost for this
checkpoint-heavy workload. No PR was merged.

Main + #331 + #333 takes **11.20 minutes versus 31.17 minutes** for main:
**2.78× end-to-end speed, 64.1% less wall time**, and **4.99× faster saving**.
Peak process RSS falls from **9.89 to 4.07 GiB (58.9% lower)**. Relative to
compact storage alone, #333 gives **5.47× faster saving** and **3.03× faster
end-to-end execution**.

## Arm totals

| Variant | Load s | Train s | Train Mnodes/s | Train peak GiB | Save total s | Save peak GiB | Wall min | CPU min |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Main | 40.04 | 280.66 | 1.069 | 9.89 | 1533.85 | 8.65 | 31.17 | 31.16 |
| Main + #331 | 36.89 | 305.55 | 0.982 | 3.90 | 1683.83 | 3.93 | 33.98 | 33.98 |
| Main + #331 + #333 | 36.83 | 314.75 | 0.953 | 4.02 | 307.58 | 4.07 | 11.20 | 12.58 |

Training throughput is new nodes divided by training-phase wall time.
The same 300,000,699 new nodes are traversed in each arm. #331 reduces aggregate
training throughput by **8.1%**; the combined arm is **10.8% below main**.
#331 alone takes **9.0% longer overall** in this pass. Its memory reduction is
useful, but it is not a training-speed improvement. The combined arm's small
additional training slowdown versus #331 is not explained by this fixed-order
single pass; it does not establish a traversal effect from the save change.

The baseline first training phase includes a transient 9.89 GiB peak; its later
training phases peak around 8.1 GiB. Compact training peaks at 3.90 GiB; combined
training peaks at 4.02 GiB. Parallel saving peaks at 4.07 GiB versus 3.93 GiB for
compact serial saving, an extra 0.14 GiB. All memory figures are sampled RSS.

## Every measured checkpoint

| Variant | Target B | Actual nodes | Entries | Train s | Mnodes/s | Train GiB | Save s | Save GiB | File MB | Save MB/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Main | 1.1 | 1,100,001,071 | 30,120,202 | 98.62 | 1.014 | 9.89 | 573.27 | 8.47 | 1248.23 | 2.18 |
| Main | 1.2 | 1,200,001,013 | 31,135,734 | 91.66 | 1.091 | 8.10 | 469.56 | 8.56 | 1293.47 | 2.75 |
| Main | 1.3 | 1,300,000,756 | 32,151,201 | 90.38 | 1.106 | 8.17 | 491.01 | 8.65 | 1338.51 | 2.73 |
| Main + #331 | 1.1 | 1,100,001,071 | 30,120,202 | 106.12 | 0.942 | 3.76 | 544.94 | 3.76 | 1248.23 | 2.29 |
| Main + #331 | 1.2 | 1,200,001,013 | 31,135,734 | 101.06 | 0.990 | 3.83 | 558.25 | 3.83 | 1293.47 | 2.32 |
| Main + #331 | 1.3 | 1,300,000,756 | 32,151,201 | 98.37 | 1.017 | 3.90 | 580.64 | 3.93 | 1338.51 | 2.31 |
| Main + #331 + #333 | 1.1 | 1,100,001,071 | 30,120,202 | 104.88 | 0.953 | 3.76 | 99.51 | 3.91 | 1248.23 | 12.54 |
| Main + #331 + #333 | 1.2 | 1,200,001,013 | 31,135,734 | 105.33 | 0.949 | 3.95 | 102.28 | 3.99 | 1293.47 | 12.65 |
| Main + #331 + #333 | 1.3 | 1,300,000,756 | 32,151,201 | 104.54 | 0.957 | 4.02 | 105.79 | 4.07 | 1338.51 | 12.65 |

Every matching target has **the same actual nodes, entries, iteration, compressed
byte count and SHA256 across all three variants**. Gzip mode is compatible/default;
no fast gzip was used. Endpoint identities:

| Target B | Iteration | SHA256 (all three variants) |
|---|---:|---|
| 1.1 | 1,749,396 | `f6b65dbb992d55a86579f0f7595d241c62840acbd452b00f90052491a0e956be` |
| 1.2 | 1,901,734 | `ae0bedee12c882746d44c678e3a66cf089731673e5ab564c2eba03a889f5ee23` |
| 1.3 | 2,053,810 | `81a3c20aaab4f5810ae1181d4a0f034d62fb4b4462a10f21ff5c725cd5ead89c` |

## Validation and limits

The [predeclared protocol](../nplayer-storage-merge-benchmark.md) pins main
`3f9bfbdc`, PR331 `7bcbce9d`, PR333 `16dbe015`, common harness/runner `ce6a3b5a`,
three isolated source trees, default training and a four-physical-core allowance
(logical 0–3, Rayon 4). All three native release builds and library suites
(42/44/44 tests) passed. Fresh 200K fixtures and resumed 300K/400K/500K checkpoints
matched exactly before the 1B continuation. Eight focused Python tests pass;
full CI passed on the prior evidence head `33a5d10d` before this report.

All three main arms exited0 with completion markers, and the supervisor recorded
`complete-identical`. Final validation rechecked 141 source-file hashes and the
input's original size/mtime. No main-run failure or retry occurred. The complete
supervised task, including builds/fixtures, took **79.06 minutes**, finishing
October18 at 10:29:11 UTC (12:29 Madrid). The benchmark released its mutex; another
holder had acquired it by the final 10:35:50 UTC check. No other job was changed.

Across 8,945 main-arm resource samples: max CPU 56°C, max VRM 61°C,
minimum available RAM 113.22 GiB, minimum NVMe free 90.57 GB and zero swap growth.
No resource guard fired. [Completion receipt](nplayer-storage-benchmark/completion.json)
records phase peaks and sampled I/O counters. [Machine-readable summary](nplayer-storage-benchmark/summary.json)
and [all nine rows](nplayer-storage-benchmark/comparison.csv) retain exact measurements.

This is one seed, one fixed baseline→compact→parallel order, one table size and
one machine. The mutex excludes cooperating compute jobs; background host
utilization was not independently logged. Caches were not flushed. RSS samples
are 0.5s apart and can miss brief peaks. Save MB/s is compressed output throughput,
including flush/fsync/rename, not raw formatting throughput; hashing is separate.
No repeated-trial interval or precise small-effect claim is supported.

Checkpoint identity is strong engineering evidence that the tested continuations
preserve training state. It is not a fresh playing-strength evaluation. These
numbers apply to saves every100M nodes; longer intervals reduce the relative
benefit of faster saving. They do not choose a v0.6 training recipe or table size.

## Preservation and reproduction

Raw checkpoints, sources, binaries, complete logs and traces remain in
`bb128:/home/dberweger/nplayer-storage-benchmark-20261018-v2/`. The first setup
root `/home/dberweger/nplayer-storage-benchmark-20261018/` retains its lock refusal
and PR333 harness compile failure; no large input was loaded/trained there.
The corrected adapter explicitly selects `Gzip::Compatible` and is recorded in
the source manifest. [Launch/failure provenance](nplayer-storage-benchmark/launch.json).

Cloud archival is **pending**. PR339 is open, its roots remain protected under
the storage policy, and the compute mutex is now held elsewhere. No large
copy/archive/upload or deletion was started at closeout. All originals remain.
The [results index](../../RESULTS_INDEX.md) records retained roots and the input's
accepted PR292 Drive restoration provenance. No Drive acceptance is claimed.

To reproduce this readout without rerunning training, follow the compact-result
retrieval and summarizer commands in the protocol. Summarizer validation requires
all nine matching endpoint identities, successful completion and nonzero phase
memory samples. Keep the independent source/input pins and preserved failures
with any subsequent archive. Final policy/model export and gameplay evaluation
are outside this engineering comparison.
