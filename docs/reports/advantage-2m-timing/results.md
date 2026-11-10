# How much slower is a 2M advantage network in traversals?

An exploration timing for the [run 2 proposal](https://github.com/dberweger2017/CFR-NLHE-6max/issues/482), which estimated 400–500 iterations in 24 hours on bb128 against run 1's 1,375. That estimate assumed network calls dominate the traversal. This measures it.

- **Where:** the M4 (base M4 MacBook Pro, 16 GB, 4 performance + 6 efficiency cores), November 10, 2026, about 14:40 UTC. bb128 was busy with run 1's final evaluation.
- **Code:** run 1's commit `4a4bf2b`, the release `nplayer_deep_cfr` example. Run 1's settings: exploration bound 3 per street and 8 per path, players 3–6, seed `20261110000001`.
- **Networks:**
  - untrained ("uniform") 0.5M and 2M advantage networks, built by `neural_deep_cfr.py init --uniform`;
  - run 1's last advantage network `adv1375` (0.5M);
  - two trained networks of the 2M shape: `net1`, and run 1's `strategy800-s4000`.
- **Runs:** 5,000 traversals at 10 threads (3 repeats), and 500 at 1 thread (2 repeats). The `bench` mode measures the cost of one network call on real traversal inputs.

[Runner](bench.sh) · [raw JSON](raw/) · [summary](summary.json)

## Answer

**The 2M network costs about 2× in traversal, not 4.6×.** The projection is **about 860 iterations in 24 hours** on bb128 (range 680–1,110), not 400–500.

### The same deals, both sizes

The uniform networks play the same uniform strategy, so both sizes traverse identical trees: 960,773 nodes, 615,329 decisions. Their records match byte for byte (`2f0d45d2aea7…`), as the proposal's iteration-1 identity check expects.

| | 0.5M | 2M | Ratio |
|---|---|---|---|
| 10 threads, median seconds | 4.44 | 10.55 | 2.38× |
| 1 thread, median seconds | 2.09 | 5.12 | 2.45× |

### Where a decision's time goes

At one thread, each decision costs about **24.3 µs outside the network**: features, equity-table lookups and records. That held for both the uniform and the late tree. The network adds the rest.

| Network | One call (µs) | Notes |
|---|---|---|
| `adv1375`, 0.5M (trained) | 5.7 | run 1's last network |
| uniform 0.5M | 12.0 | |
| `net1`, 2M (trained) | 22.2 | |
| `strategy800-s4000`, 2M (trained on run 1's rows) | 40.5 | |
| uniform 2M | 63.4 | |

**Trained networks are cheaper than untrained ones,** because many hidden units output zero and the fast path skips them. So the untrained 2M network overstates the cost, and the uniform-tree ratio (2.4×) is close to an upper bound.

On run 1's late tree (`adv1375`, iteration 1,375) a decision costs 30.0 µs. A trained 2M network would make it 46–65 µs, which is **1.55–2.16× slower**, or 2.93× with the untrained network's cost.

### Projection for bb128

Run 1's 24 hours on bb128, from its `progress.csv` and iteration summaries:

| Part | Hours | Scales with the network? |
|---|---|---|
| Traversal loop | 10.3 | yes, by the ratio above |
| Traversal stage outside the loop (start, table load, flush) | 2.9 | no |
| Reservoir adds | 3.7 | no |
| Advantage fit (1,000 steps, 16.2 s each) | 6.2 | partly |
| Other | 0.9 | no |

**The 2M fit is estimated, not measured:** run 1's fit takes 16.2 s per iteration. Its qualification measured 221 steps per second for a 0.66M network on the 2070 SUPER, about 4.5 s per 1,000 steps. So most of the 16 s is fixed cost. I assume a 2M fit takes 1.0–1.75× as long.

| Case | 2M call | Traversal ratio | Fit | Iterations in 24 h |
|---|---|---|---|---|
| Optimistic | 22.2 µs (`net1`-like) | 1.55× | ×1.0 | **1,111** |
| Central | 40.5 µs (run 1's own 2M net) | 2.16× | ×1.4 | **858** |
| Pessimistic | 63.4 µs (untrained) | 2.93× | ×1.75 | **680** |

The projection scales run 1's measured bb128 time per part by M4 ratios. It assumes bb128 splits a decision's cost the way the M4 does.

## What it means for run 2

- **Run 2 likely reaches iteration 800,** where run 1 started to flatten, and may reach 1,000. So equal-iteration comparisons can look at the flattening. The proposal's 400–500 estimate should be replaced by about 860, to be checked by qualification's three timed iterations.
- **The network is no longer most of the bill.** Even in run 1, 13.7 of 24 hours went outside the traversal loop:
  - the traversal stage outside its loop, about 7.5 s per iteration on bb128 against 0.8 s for a full process start on the M4;
  - reservoir adds, 10 s;
  - the fit's fixed cost.

  Speedups that give exact parity there, such as a resident process or a cheaper add, would buy more iterations than the 2M network costs. They're a candidate for the next run.
- **The M4 traverses faster than bb128:** about 7.0 µs per late decision at 10 threads, against bb128's 10.2 µs at 16 threads. It can't hold run 1's 37 GB of RAM reservoirs, though.

## Limitations

- **One machine stands in for another.** The ratios come from the M4's ARM cores. bb128's i7-10700KF runs 16 threads on 8 cores, and its L2 is 256 KB per core. The 2M network's 9 MB of weights miss cache differently there, so the real ratio could be higher.
- **No trained 2M advantage network exists yet.** Two trained 2M policy networks bracket its cost (22 and 41 µs).
- **The fit factor is an estimate** from qualification's speed test. The 2070 SUPER wasn't available.
- **The cause of the 7.5 s overhead is unmeasured.** Hashing the 1.4 GB tables and writing about 2.3 GB of records per iteration are the likely causes.
