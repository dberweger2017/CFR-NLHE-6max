# Deep CFR from scratch: protocol

Follows the [warm-start pilot](neural-deep-cfr.md) ([PR476](https://github.com/dberweger2017/CFR-NLHE-6max/pull/476)) and answers the question in [issue 475](https://github.com/dberweger2017/CFR-NLHE-6max/issues/475): **without any table, can Deep CFR learn a policy that plays, and how does it compare with the warm-started one?** This document is committed before the main run. Any change after launch is reported as a deviation.

## Why now

- The warm-start pilot's iteration-300 network reads promising against its start (four of eight tables better, none worse), but it starts from `widemix`'s regrets and step 2's imitation network. It can't tell us whether the learning comes from Deep CFR or from the teacher.
- A scratch run removes the teacher. If it reaches similar strength, the tables aren't needed as a starting point. If it doesn't, the warm start matters, and the 3-seed follow-up should keep it.
- bb128 is free, so the run costs only machine time.

## What changes from the pilot, and why

The recipe stays the pilot's wherever possible, so the scratch-versus-warm comparison differs mainly in the starting point.

| | Pilot (PR476) | Here | Reason |
|---|---|---|---|
| Start | 100 table iterations, pretrained advantage network | iteration 1 plays **uniformly** over legal labels | The usual first CFR iterate. A zero network would fold or check everywhere at iteration 1 (first label of highest zero regret). |
| Strategy networks | start from step 2's imitation weights | **fresh initialization** | No teacher weights anywhere. |
| Traverser exploration | every action at every traverser decision | every action at the traverser's first **D** decisions on a path, then one action drawn from the current strategy | The pilot stopped at iteration 310 when one traversal passed 50M nodes. See below. |
| Length | iterations 101–400 | a **24-hour** window | Fixed wall time instead of a fixed count, so the run can't stall on a slow tail. |
| Final strategy fit | 20,000 steps | 20,000 steps | Unchanged. |
| Reservoirs | HDD, moved to `/dev/shm` mid-run | `/dev/shm` from the start, with linger enabled and compressed snapshots | The pilot's HDD adds took 16–19 minutes. Its RAM copies were deleted at the stop because linger was off. |

Unchanged: player counts 3–6 (uniform), the wide stack grid, 20,000 traversals per iteration, the 612-feature encoding and six-label menu, the 612→512→256→128→6 advantage network continuing from the previous iteration with 1,000 steps (batch 8,192, AdamW lr 1e-3 cosine, fp16 on the GPU), the 612→1024→1024→512→6 strategy network, 30M-row reservoirs and linear weighting.

### Bounded exploration

External sampling explores all six labels at each traverser decision, so a traversal grows about sixfold per traverser decision. Long minimum-raise sequences at deep stacks give the traverser dozens of decisions in one hand. In the pilot, nodes per traversal rose from 135 to about 300, and then one traversal passed the 50M limit.

**The rule:** after the traverser has explored at D decisions on the current path, it draws one action from the current strategy at later decisions instead.
- The value passed upward is still an unbiased estimate of the node's value under the current strategy profile, so regrets at the explored decisions stay unbiased. Their variance rises. A test checks the root value against full exploration.
- Decisions past depth D write no advantage sample, and the network predicts them by generalization. Each iteration reports how many traverser decisions were sampled instead of explored.
- The bound only applies past D. With an unbounded D, traversals are byte-identical to the pilot's (tested).

**Choosing D, before the run:** at iteration 1 (uniform play, the most raise-heavy strategy the run is likely to see), on 2,000 traversals, take the largest D in {4, 5, 6, 7, 8} whose mean is at most **600 nodes per traversal**. That's twice the pilot's late-run size, and about 100 s of traversing per iteration on bb128. The measurements and the chosen D go in the PR before iteration 1.

## Schedule on bb128

1. **Qualification:** native tests with the K50 tables, including the new depth tests; Python tests; GPU check; f32 parity; thread independence (16 versus 7 threads, bounded traversals).
2. **Smoke:** three toy iterations from the uniform network, a strategy network and a smoke evaluation.
3. **Depth calibration,** as above.
4. **Training window:** 24 hours from the start of iteration 1. No iteration starts after the window closes; the last fully completed iteration is final, chosen by time, not by score.
5. **Monitoring** at iterations 25, 50, 100, 200, 300, 400, 800 and 1,200, if reached inside the window. Each one fits a strategy network (4,000 steps, fresh) and plays it against step 2's network (`net1`) on the eight tables' primary fields, 512 blocks each. These are learning diagnostics, not gates, and no checkpoint is selected from them. Iteration 300 also gives an equal-iteration look against the pilot's `strategy300-s4000`.
6. **Final fit:** 20,000 steps, fresh, at the final iteration.
7. **Final evaluation, one bank of 4,096 blocks per table and field on the eight tables of step 4:**
   - **E1, scratch against `net1`:** the pilot's own roots (`20261109500000…`), so the scratch and warm readings play the same deals.
   - **E2, scratch against the warm pilot's `strategy300-s4000`:** fresh roots `20261110500000 + 1000·bank + case`.

## Reading, fixed now

- **E1** uses the pilot's rule. *Promising:* no table reads "start better" and at least one reads "scratch better". Harm flags as in step 4, reported per table.
- **E2** is per table, Bonferroni 95% within each table group. "Scratch better", "warm better" or "no difference shown". The compute differs (the warm start carries ten billion table nodes plus 209 Deep CFR iterations), so E2 is a practical comparison, not a controlled estimate of warm starting.
- One seed, one bank: a pilot read, not a strength claim. No route, default, live play or follow-up run comes from it.

## Not done here, and why

These parts of issue 475 are deliberately left out:
- **RunPod:** bb128 is free.
- **Two-player roots, heads-up anchors and the off-grid stack panel:** they need new arena cases and baselines. Keeping the pilot's root law and evaluation makes the scratch-versus-warm comparison direct, which is the decision this run informs. Transfer to new stacks and player counts is a follow-up once a recipe works.
- **Fresh advantage initialization every iteration with 1,000 steps:** that's under a third of an epoch on a full 30M reservoir, so the fits would be mostly noise. The pilot's continued fit learned in practice, and changing it would confound the comparison.
- **An exact-exploitability small game:** the traversal is hold'em-specific, so a separate small game wouldn't test the code that runs. Instead, the depth bound gets direct tests: an unbounded depth equals the pilot's traversal byte for byte, and the root value is unbiased.

## Stops

- Thermal: CPU 90 °C, VRM 100 °C, GPU 87 °C.
- Plumbing: below 10 GB free on the NVMe or 20 GB on the HDD, below 4 GB of available memory.
- The traversal node limit (50M) stays an error.
- A research failure is reported as is, with no retry or retuning. Plumbing failures go in the PR.

## Where the results go

- **In this PR:** the report, per-iteration history (`iterations.csv`), stage log, resources, qualification receipts, evaluation summaries and every network's SHA-256, under [`docs/reports/neural-deep-cfr-scratch/`](reports/neural-deep-cfr-scratch).
- **On bb128:** the full evidence tree in `/home/dberweger/neural-deep-cfr-scratch-20261109`: every advantage and strategy network, evaluation traces and receipts. The latest reservoir snapshot goes to `/mnt/data2tb/neural-deep-cfr-scratch-20261109`. A SHA-256 manifest of the whole tree is committed here before merging.
- **Long-term:** bb128's storage process packages that tree into `gdrive:PR-477-neural-deep-cfr-scratch/` and records it in `RESULTS_INDEX.md`, with retrieval commands for the final network.
