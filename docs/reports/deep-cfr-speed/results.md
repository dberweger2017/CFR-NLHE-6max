# Deep CFR training speed: profile, ranked optimizations, parity

Where an iteration of the scratch Deep CFR trainer ([run 1](../../neural-deep-cfr-scratch.md), [run 2](../../neural-deep-cfr-2m.md)) spends its time, and what makes it cheaper without changing a single output byte. It builds on [PR483's timing study](../advantage-2m-timing/results.md).

- **Where:** the M1 MacBook (8 cores: 4 performance, 4 efficiency), November 10, 2026. bb128 was running run 1's final evaluation at 100% CPU, so it contributed only read-only data (`progress.csv`, iteration summaries, networks) and two tiny tests: a guard latency test and a CPU-time SHA-256 rate.
- **Code:** run 1's commit `81bb6d1f` (the base) against this branch, both release builds.
- **Settings:** run 1's: seed `20261110000001`, players 3–6, exploration bound 3 per street and 8 per path, 20,000 traversals.
- **Networks:**
  - run 1's `adv0` (uniform), `adv1374` and `adv1375` (0.5M);
  - two trained 2M networks relabelled as advantage networks: `net1` (the optimistic case, sparse) and run 1's `strategy800-s4000` (`s800adv`, the central case, trained on run 1's rows).
- **bb128 numbers below are estimates** from M1 ratios and run 1's records. [bench.sh](bench.sh) measures them on bb128 once it is idle; until then the PR stays a draft.

[Raw data](raw/) · [tools](tools/) · [bb128 benchmark](bench.sh)

## Answer

**Most of run 1's iteration was overhead, not work.**
- Rebuilding the 612 feature names at every decision took 75% of a traversal.
- The stage guard rounded every stage up to a multiple of 5 seconds.
- The 2.3 GB sample file was hashed with SHA-256 three times: once while the traversal waited, and twice in `add`.

Removing these keeps every output byte-identical. With them, run 1's late iteration traverses **4.3× faster** on the M1 (46.2 s → 10.8 s at 8 threads). A trained 2M network traverses **1.7–2.3× faster**.

**Estimate for bb128:** an iteration drops from 66.8 s to about **23–32 s** with run 1's network, and from about 100 s to about **50–70 s** with a 2M network. That is roughly **2,700–3,700 iterations per day instead of 1,375**, and **1,200–1,700 instead of about 860**.

**Parity, end to end:**
- Run 1's production iterations 1 and 1,375, re-run on the M1 with the new code, give bb128's record hashes exactly: `16090fbb4868e7ff…` and `002fb6195848afa9…`.
- `add` and `train` give byte-identical reservoirs, weights and network files.

## Profile

### Traversal

`sample` profile of one thread, 1,500 traversals at iteration 1,375, base code:

| Network | Seconds | Network calls | Feature-name rebuild (formatting, allocation) | Other |
|---|---|---|---|---|
| `adv1375`, 0.5M | 12.14 | 18.7% | 75.1% | 6.2% |
| `net1`, 2M | 8.85 | 49.7% | 45.9% | 4.4% |

`policy_features::encode` called `len()`, which built the 612 feature-name strings to count them, at every decision. This is PR483's "24 µs per decision outside the network".

With `len()` computed once, the same runs take **2.77 s (4.38×)** and **4.14 s (2.14×)** with identical records. The network is then 81% (0.5M) and about 95% (2M) of a traversal. Feature encoding, equity lookups and the hand engine are a few percent.

**Network calls are sparse.** Per forward pass, multiply-adds actually done (zero inputs and ReLU zeros are skipped):

| Network | Dense | Done | Active inputs per layer |
|---|---|---|---|
| `adv1375` | 478k | 69k | 107, 44, 18, 38 |
| `net1` | 2.2M | 295k | 99, 112, 151, 141 |
| `s800adv` | 2.2M | 561k | 113, 292, 284, 158 |

So a 2M call costs 2–8× a 0.5M call, not 4.6×. That fits PR483's 22–41 µs per call.

### `add` and `train` on bb128, from run 1's records

Run 1, mean of its last 75 iterations: **66.8 s** = traverse stage 40.35 + `add` 10.27 + `train` (with export) 16.18.

| Cost | Seconds per iteration | Evidence |
|---|---|---|
| **Guard rounding** | **≈7.5** (about 2.5 per guarded stage) | `guarded.sh` notices the job's end only after its `sleep 5`. In all 1,374 iterations, traverse and `add` stages ended a median 0.49 s and 0.24 s past a multiple of 5 (p10–p90 0.36–0.65 and 0.21–0.28). On bb128, a 0.3 s job took 5.003 s under the guard. |
| Traversal loop | 32.8 | the iteration summaries' `seconds` |
| ↳ hashing and writing 2.3 GB of records, serially, while all threads wait | ≈4.5–6.5 | bb128 has no SHA instructions. `sha2`'s software rate is about 0.35–0.5 GB/s. |
| Traverse start-up: tables (1.4 GB read and hashed), network | ≈3–5 | 7.55 s outside the loop, minus guard rounding |
| **`add`: SHA-256 of the sample file, twice** | **≈6–7 of the ≈7.8 real** | `sha_file` ran once per record kind. Python's SHA-256 on bb128 measured 0.32 GB/s per CPU-second under load. On the M1, hashing was 65% of `add`. |
| `train`: steps | ≈4.5 | qualification measured 221 steps/s (PR483) |
| `train`: process start (torch, CUDA, model, reservoir map), export process | ≈9 | the rest of 16.18 |

## Ranked optimizations

**"Identical"** means proved by byte comparison against the base code (record SHA-256, reservoir files, network files) and kept by tests.

| # | Change | Measured (M1) | Estimated bb128 gain per iteration | Risk | Parity | Status |
|---|---|---|---|---|---|---|
| 1 | **Feature count computed once** (`policy_features::len`) | traversal 4.3× at 8 threads (0.5M); 2.1–2.3× (2M) | **−20 to −25 s** (0.5M) | none | identical: production iterations 1 and 1,375 reproduce bb128's hashes | done |
| 2 | **Guard wakes when its job ends** (`wait -n` on the job and a 5 s tick) | bb128: 0.3–0.9 s jobs return in 0.3–0.9 s, not 5.0 s, exit status kept | **−7.5 s** | none; controls only | not applicable | pattern below, for the next controller |
| 3 | **Records hashed and written on a writer thread**, overlapping the next chunk | no gain on the M1, which hashes at 2 GB/s | **−4 to −6 s** | none | identical (same bytes, same order) | done |
| 4 | **`add` hashes each file once, on a thread, during sampling** | 3.65 s → 2.07 s (1.76×) | **−3 to −5 s** | none | identical reservoirs and `state.json` (byte comparison) | done |
| 5 | **`train --export`**: export in the training process (same function); **batch prefetch** on a thread | 60 steps + export on CPU: 5.92 s → 3.28 s | **−1.5 to −3 s**; prefetch on CUDA unmeasured | low | identical `weights.pt` and `.npnet` (CPU); CUDA check in bench.sh | done |
| 6 | **Register-blocked f32 kernel**: 64 outputs' partial sums stay in registers over the nonzero inputs | 2M call 38 → 31 µs single-threaded (≈1.2×); part of #1's end-to-end numbers | small | none | identical: bit-exact against the old kernel (test) | done |
| 7 | **Batched walks**: each thread steps W traversals as explicit stacks and batches their calls | **slower on the M1** (width 32–64: −20 to −35% with `s800adv`). In a batch of 32, active weight rows overlap to 5–27% of their sum, so weight traffic would fall 4–20× where it limits. | unknown: bb128's 256 KB L2 per core and shared 16 MB L3 may make it a gain | medium (more code) | identical at every width (tests; production hashes) | done, default off (`--batch 1`); bench.sh decides, and it is removed if it doesn't pay |
| 8 | `-C target-cpu=native` (AVX2 on bb128) | not measurable on the M1 | unknown | low | expected identical: Rust never fuses multiply-adds; checked by record hashes in bench.sh | bench.sh |
| 9 | Resident traverse and learner processes (tables, torch and CUDA loaded once; the reservoir stays mapped) | torch import alone 0.6 s on the M1 | −3 to −8 s | medium: controller redesign, guard around a long-lived process | expected identical (same functions) | not done; proposal for the next controller |
| 10 | Strategy-reservoir `add` overlapped with the advantage fit (the fit never reads it) | — | −1 to −2 s | low | identical (separate reservoirs and random streams) | not done; needs #9 or a controller change |

**Not pursued, because they change numbers** (each would need its own flagged study):
- **Fused multiply-add in the kernel:** no gain on the M1 (7.76 vs 7.71 µs, 30.8 vs 31.1 µs), and it changes rounding.
- **f16 weights:** would halve weight traffic, but alters every strategy. Unmeasured.
- **GPU inference server for traversals:** cuBLAS sums in another order and doesn't skip zeros, so records would change. Calls are 30–60 µs of sparse work per decision across 16 threads, so a server would need cross-thread batching plus PCIe round trips. Not worth it before #7 and #9 are measured.
- **Streaming `add` into the traversal, or `add` in Rust:** needs numpy's PCG64 and bounded-integer draws reproduced bit for bit. After #4, the file hash is what's left of `add`'s cost, and #9 or #10 hide it more cheaply.

**What can and can't overlap.** Traversal t needs advantage network t−1. `add` t needs traversal t's samples. The fit t needs the advantage reservoir after `add` t. So the main chain is sequential. Only work off that chain can overlap it:
- hashing and writing records (#3, #4);
- data gathering for the fit (#5);
- the strategy reservoir (#10).

## Parity evidence

- **Production iterations re-run on the M1** (20,000 traversals, 8 threads):
  - iteration 1 from `adv0`: `16090fbb4868e7ff…`, bb128's `it1.json`;
  - iteration 1,375 from `adv1374`: `002fb6195848afa9…`, bb128's `it1375.json`.

  The base code on the M1 also gives `002fb619…`, so the records don't depend on the machine either.
- **Every timed run** compares its `records_sha256` with the base binary: batch widths 1–64 and kernels, at 1 and 8 threads, with three networks ([raw/m1-traverse-8t.json](raw/m1-traverse-8t.jsonl)).
- **New native tests** (`cargo test --lib`, 198 pass with the K50 tables):
  - `the_walk_reproduces_the_recursive_traversal_byte_for_byte`: the old recursion is kept as a test oracle. Records, counts and value bits are compared on random-weight and constant networks, bounded and unbounded.
  - `batched_walks_equal_single_traversals_at_every_width`: widths 1, 2, 7, 16, 64 and 100.
  - `batched_forward_passes_equal_single_ones_bit_for_bit`: also against the old kernel, with wide layers and many ReLU zeros.
- **New Python tests:**
  - `test_add_hashes_each_file_once_and_records_it_in_both_reservoirs`;
  - `test_prefetching_and_in_process_export_change_nothing`;
  - `test_a_failing_batch_source_fails_training`.
- **One-off byte comparisons against the base script:**
  - `add` on the 2.3 GB iteration-1,375 file into full reservoirs at run 1's keep rate: all six files identical;
  - `train` (60 steps from `adv1375`) plus export: `weights.pt` SHA-256 and `.npnet` identical.
- **One semantic detail:** the 50M-node limit now counts per traversal. Before, it counted across everything one `Traversal` object ran, and the CLI runs one traversal per object.

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

- **The M1 stands in for bb128.** Its 12 MB L2 per cluster holds a 2M network's 9 MB of weights. bb128's i7 has 256 KB of L2 per core and 16 threads sharing a 16 MB L3. So the inference numbers (#6–#8) and every bb128 gain above are estimates until [bench.sh](bench.sh) runs.
- **No trained 2M advantage network exists yet.** `net1` and `s800adv` bracket it. Run 2's own late network is the right test case once it exists; bench.sh accepts it.
- **The laptop was shared:** its load average varied from 3 to 25. Timings are the order of magnitude, from repeated runs; the parity results don't depend on load.
- **CUDA training parity is unchecked:** whether a fresh-process fit is even repeatable on the 2070 SUPER is checked first in bench.sh.
