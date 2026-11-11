# Deep CFR training speed: profile, ranked optimizations, parity

Where an iteration of the scratch Deep CFR trainer ([run 1](../../neural-deep-cfr-scratch.md), [run 2](../../neural-deep-cfr-2m.md)) spends its time, and what makes it cheaper without changing a single output byte. It builds on [PR483's timing study](../advantage-2m-timing/results.md).

- **Profiling:** on the M1 MacBook (8 cores), November 10, 2026, while bb128 ran run 1's evaluation.
- **Measurement:** on bb128 (i7-10700KF, 16 threads, RTX 2070 SUPER) the same evening, with [bench.sh](bench.sh) from commit `8cd6ebc2`. Run 2 was paused for it.
  - The networks were run 1's `adv1374` (0.5M) and run 2's `adv66` (2M, SHA-256 `adcd6a60…`).
  - Peak CPU was 89 °C under the owner's guard.
- **Code:** run 1's commit `81bb6d1f` (the base) against this branch, both release builds.
- **Settings:** run 1's: seed `20261110000001`, iteration 1,375, players 3–6, exploration bound 3 per street and 8 per path, 20,000 traversals.

[bb128 results](raw/bb128-results.json) · [M1 raw data](raw/) · [tools](tools/) · [bb128 benchmark](bench.sh)

## Answer

**Most of an iteration was overhead, not work.**
- Rebuilding the 612 feature names at every decision took 75% of a traversal.
- The stage guard rounded every stage up to a multiple of 5 seconds.
- The 2.3 GB sample file was hashed with SHA-256 three times: once while the traversal waited, and twice in `add`.
- `train` started a second Python process to export.

Removing these, plus a `target-cpu=native` build, keeps every output byte-identical. Measured on bb128:

| Stage, seconds per process | Base | This branch | This branch, `target-cpu=native` | Speedup |
|---|---|---|---|---|
| Traverse, run 1's `adv1374` (0.5M) | 41.2 | 16.0 | **12.7** | 3.2× |
| Traverse, run 2's `adv66` (2M) | 36.8 | 18.4 | **14.1** | 2.6× |
| `add` (2.3 GB file, run 1's keep rate) | 8.57, 8.55 | **4.93, 4.85** | | 1.75× |
| `train`: 1,000 CUDA steps from `adv1374`, plus export | 12.09, 11.95 | **8.58** | | 1.4× |

**An iteration** is these three stages, plus the guard's rounding to 5 s in the current controller:
- **Run 1's network:** 66.8 s → about **26 s**: 12.7 + 4.9 + 8.6 with the guard fix, or about 30 s without it. That's about **3,300 iterations in 24 hours instead of 1,375**.
- **Run 2's network:** run 2 so far takes 64.9 s per iteration (mean of iterations 40–74: traverse 38.5 s, `add` 10.2 s, `train` 16.2 s). Its 2M fit costs the same 16.2 s as run 1's 0.5M fit, so the fit is mostly fixed cost and the measured 3.5 s saving should carry over. That gives about **28 s per iteration (2.35×)** at run 2's current size.
- **Later iterations** grow denser trees and networks, so the absolute times will rise for both.

**Parity holds everywhere:**
- the base reproduces run 1's iteration 1,375 (`002fb6195848afa9…`) on bb128;
- every build of this branch gives the same record hash per network;
- `add` leaves identical reservoirs;
- CUDA training is repeatable (two base runs give the same network), and this branch's network equals the base's byte for byte (`cd766ece…`).

## Profile

### Traversal

`sample` profile of one thread on the M1, 1,500 traversals at iteration 1,375, base code:

| Network | Seconds | Network calls | Feature-name rebuild (formatting, allocation) | Other |
|---|---|---|---|---|
| `adv1375`, 0.5M | 12.14 | 18.7% | 75.1% | 6.2% |
| `net1`, 2M | 8.85 | 49.7% | 45.9% | 4.4% |

`policy_features::encode` called `len()`, which built the 612 feature-name strings to count them, at every decision. This is PR483's "24 µs per decision outside the network".

With `len()` computed once, the same runs take **2.77 s (4.38×)** and **4.14 s (2.14×)** with identical records. The network is then 81% (0.5M) and about 95% (2M) of a traversal.

**Network calls are sparse.** Per forward pass, multiply-adds actually done (zero inputs and ReLU zeros are skipped):

| Network | Dense | Done | Active inputs per layer |
|---|---|---|---|
| `adv1375` | 478k | 69k | 107, 44, 18, 38 |
| `net1` | 2.2M | 295k | 99, 112, 151, 141 |
| `strategy800-s4000` | 2.2M | 561k | 113, 292, 284, 158 |

So a 2M call costs 2–8× a 0.5M call, not 4.6×.

### Where bb128's iteration went

| Cost | Run 1 base, seconds | Evidence |
|---|---|---|
| **Guard rounding** | **≈7.5** (about 2.5 per guarded stage) | `guarded.sh` notices a job's end only after its `sleep 5`. In all 1,374 of run 1's iterations, traverse and `add` stages ended a median 0.49 s and 0.24 s past a multiple of 5. On bb128, a 0.3 s job took 5.003 s under the guard. Run 2's stages show the same pattern (traverse 40.4, `add` 10.2). |
| Traversal loop | 36.3 → 8.8 | bench, base against this branch with `native` |
| ↳ hashing and writing 2.3 GB of records serially, all threads waiting | part of the loop | now overlapped on a writer thread |
| Traverse start-up: tables (1.4 GB read and hashed), network | ≈4–5 | process seconds minus loop seconds, both builds |
| **`add`: SHA-256 of the sample file, twice** | ≈4 of 8.6 | removed by hashing once on a thread: 8.6 → 4.9 s |
| `train` process start and the separate export process | ≈3.5 of 12 | removed by exporting in-process and prefetching: 12.0 → 8.6 s |

## Ranked optimizations

**"Identical"** means proved by byte comparison against the base code (record SHA-256, reservoir files, network files) and kept by tests.

| # | Change | Measured on bb128 | Risk | Parity | Status |
|---|---|---|---|---|---|
| 1 | **Feature count computed once** (`policy_features::len`), plus a **register-blocked f32 kernel** (64 outputs' partial sums stay in registers over the nonzero inputs) | traverse 41.2 → 16.0 s (0.5M), 36.8 → 18.4 s (2M) | none | identical | done |
| 2 | **`-C target-cpu=native`** (AVX2) for bb128 builds | traverse 16.0 → 12.7 s (1.26×), 18.4 → 14.1 s (1.30×) | low | identical: Rust never fuses multiply-adds; checked by record hashes | **recommended for the next controller's build** |
| 3 | **Guard wakes when its job ends** (`wait -n` on the job and a 5 s tick) | 0.3–0.9 s jobs return in 0.3–0.9 s, not 5.0 s; worth ≈2.5 s per stage | none; controls only | not applicable | pattern below, for the next controller |
| 4 | **`add` hashes each file once, on a thread, during sampling** | 8.56 → 4.89 s | none | identical reservoirs and `state.json` | done |
| 5 | **`train --export`** (export in the training process, same function), and **batch prefetch** on a thread | 12.0 → 8.58 s | low | identical network on CUDA | done |
| 6 | **Records hashed and written on a writer thread**, overlapping the next chunk | inside #1's numbers | none | identical (same bytes, same order) | done |
| 7 | Batched network calls across traversals (explicit-stack walks) | **slower at every width**: 0.5M 16.0 → 16.7–17.8 s; 2M 18.4 → 23.5–25.7 s (native: 14.1 → 18.0–18.4 s). It was slower on the M1 too. | medium | identical | **dropped**: the traversal stays the base recursion, to keep the regret-math diff to a scratch type |
| 8 | Resident traverse and learner processes (tables, torch and CUDA loaded once; the reservoir stays mapped) | not measured; traverse start-up alone is ≈4–5 s | medium: controller redesign | expected identical (same functions) | proposal for the next controller |
| 9 | Strategy-reservoir `add` overlapped with the advantage fit (the fit never reads it) | not measured | low | identical (separate reservoirs and random streams) | proposal; needs #8 or a controller change |

**Not pursued, because they change numbers** (each would need its own flagged study):
- **Fused multiply-add:** no gain on the M1, and it rounds differently.
- **f16 weights:** would halve weight traffic, but alters every strategy.
- **GPU inference server for traversals:** cuBLAS sums in another order and doesn't skip zeros, so records would change. Batching across traversals already loses on the CPU (#7), so a server would also have to beat that overhead.
- **Streaming `add` into the traversal, or `add` in Rust:** needs numpy's random draws reproduced bit for bit; #8 and #9 hide what's left of `add` more cheaply.

**What can and can't overlap.** Traversal t needs advantage network t−1. `add` t needs traversal t's samples. The fit t needs the advantage reservoir after `add` t. So the main chain is sequential. Only work off that chain can overlap it:
- hashing and writing records (#4, #6);
- data gathering for the fit (#5);
- the strategy reservoir (#9).

## Parity evidence

- **bb128:** see the Answer.
- **M1:** run 1's production iterations 1 (from `adv0`) and 1,375 (from `adv1374`), re-run with this branch, give bb128's record hashes `16090fbb4868e7ff…` and `002fb6195848afa9…`. Every timed M1 run matched the base binary's hash ([raw/m1-traverse-8t.json](raw/m1-traverse-8t.json)).
- **New tests:**
  - native: `the_blocked_kernel_makes_the_old_kernels_sums_bit_for_bit`, with the old kernel kept as the oracle and layers wider than a block, with remainders and many ReLU zeros;
  - Python: `test_add_hashes_each_file_once_and_records_it_in_both_reservoirs`, `test_prefetching_and_in_process_export_change_nothing` and `test_a_failing_batch_source_fails_training`.

## The guard pattern for the next controller

```bash
while kill -0 $JOB 2>/dev/null; do
  # ... the same sensor and disk checks ...
  sleep 5 & TICK=$!
  wait -n $JOB $TICK 2>/dev/null   # wakes when the job ends or the tick does
  kill $TICK 2>/dev/null
done
wait $JOB
```

Run 1's [guarded.sh](../neural-deep-cfr-scratch/guarded.sh) is left as recorded.

## Limitations

- **One measurement per configuration on bb128,** except `add` and base `train` (two each). The spread between repeats was under 2%.
- **Run 2's `adv66` is an early network.** Late run 2 networks may be denser, which raises traversal cost for every build alike.
- **The bench fit used 800k-row reservoirs.** Run 2's 30M-row reservoir in `/dev/shm` may add page-fault cost that a resident process (#8) would remove.
- **Iteration totals are the sum of measured stages,** not a timed run of the controller.
