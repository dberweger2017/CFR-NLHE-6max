# Deep CFR from scratch with a 2M advantage network: proposal

Follows [run 1](neural-deep-cfr-scratch.md) ([PR477](https://github.com/dberweger2017/CFR-NLHE-6max/pull/477)) and the M4 advantage-fit studies ([PR478](https://github.com/dberweger2017/CFR-NLHE-6max/pull/478), [PR479](https://github.com/dberweger2017/CFR-NLHE-6max/pull/479), [PR480](https://github.com/dberweger2017/CFR-NLHE-6max/pull/480)). The question: **does a 2M-parameter advantage network learn a better policy than run 1's 0.5M network, per iteration and per day of bb128?**

This is a proposal. Once agreed, it becomes the protocol and is committed before launch. Any change after launch is reported as a deviation.

## What we know

**From the M4 studies** (offline fits on the pilot's reservoir rows, one seed, no play):
- **0.5M → 2M cuts held-out advantage error by 9%** at 4.5M rows. Beyond 2M, size doesn't help at that row count (#478).
- **Rows limit the fit:** each tripling of rows cuts error by 20–25% (#479).
- **At 13M rows the 13M network wins by 3%** over 2M. Card embeddings no longer help. A Huber loss is mixed (#479, #480).

**From run 1** (one seed, 1,375 iterations in 24 hours):
- **It learned from uniform play.** No table read clearly worse than `net1` from iteration 300 on. Against tight-aggressive players it turned from clearly losing to winning.
- **Its gains flattened** between iterations 800 and 1,200.
- **Its advantage loss kept rising**, from 1,500 at iteration 25 to 2,160 at iteration 1,200.

The flattening and the rising loss fit a network too small for its reservoir, but they don't prove it: regret magnitudes also grow under linear weighting. Run 1's final evaluation (E1, E2) is pending and will be linked here.

## The change: one

| | Run 1 | Run 2 | Reason |
|---|---|---|---|
| Advantage network | 612→512→256→128→6 (0.48M) | **612→1024→1024→512→6 (2.2M)** | #478's recommendation. It's the strategy network's shape, which Rust already plays. |

**Everything else is run 1's:**
- the same seed and the uniform first iterate;
- the exploration bound (3 per street, 8 per path) and 20,000 traversals per iteration;
- 30M-row reservoirs with linear weighting;
- 1,000 continued fit steps per iteration (batch 8,192, AdamW lr 1e-3 cosine, fp16);
- the 612→1024→1024→512→6 strategy network and the 24-hour window;
- the checkpoints, the evaluation roots and the stops.

The uniform first iterate doesn't depend on the network's shape, so iteration 1's traversals should match run 1's byte for byte. Qualification checks that. The runs diverge from iteration 2 only through the network.

**Left out, and why:**
- **13M advantage network:** it runs at every decision of every traversal, at 27× run 1's compute per call, for a 3% better fit at 13M rows. Traversal speed would have to be fixed first.
- **More rows:** already in place. The reservoir holds 30M rows, more than #480's 13M, and each iteration's fit draws 8.2M samples from it.
- **Card embeddings:** no gain at 13M rows.
- **Huber loss:** mixed in #479.
- **A bigger strategy network:** it doesn't affect training, and it would change the cost of play. That's a separate follow-up.
- **More fit steps:** the GPU fit isn't the bottleneck, but it would be a second change.

## The cost: fewer iterations

Run 1's last 75 iterations took 40 s of traversal, 10 s of reservoir adds and 16 s of fit.
- The advantage network is called at every decision. A 2M call is about 2.2M multiply-adds against 0.48M, 4.6× more.
- If calls dominate the traversal, iterations take about 3–3.5 minutes, so the run reaches roughly **400–500 iterations** against run 1's 1,375.
- Qualification measures it. The run launches whatever the speed, because the question includes "per day".

**That gives two comparisons:**
- **Equal iterations (E4 and the checkpoints):** does the bigger network learn more per iteration?
- **Equal machine time (E3):** is it the better use of a day of bb128?

## Schedule on bb128

Run 2 starts after run 1's E2, around 16:00 UTC on November 10.

1. **Qualification:** run 1's native and Python tests, plus:
   - the iteration-1 identity with run 1;
   - a fit and export of the 2M advantage network, with f32 parity in Rust;
   - three timed iterations from uniform, reported.
2. **Training window:** 24 hours, under run 1's rules. No iteration starts after the window closes, and the last completed iteration is final.
3. **Monitoring** at iterations 25, 50, 100, 200, 300, 400, 800 and 1,200, if reached. It uses run 1's fits (4,000 steps, fresh) against `net1`, with **run 1's roots**, so each checkpoint plays run 1's deals at the same iteration. These are diagnostics.
4. **Final fit:** 20,000 steps, fresh.
5. **Final evaluation,** one bank of 4,096 blocks per table and field on the eight tables:
   - **E1, run 2 against `net1`:** run 1's E1 roots (`20261109500000…`).
   - **E2, run 2 against the warm pilot's `strategy300-s4000`:** run 1's E2 roots (`20261110500000…`).
   - **E3, equal time: run 2's final against run 1's final** (`strategy1375-s20000`), on fresh roots `20261111500000 + 1000·bank + case`.
   - **E4, equal iterations:** run 2's last checkpoint network against run 1's at the same iteration (both 4,000-step fits), on fresh roots `20261111600000 + 1000·bank + case`.

The evaluation takes about 6 hours: run 1's E1 and E2 took about 3, and E3 and E4 cost about the same. Everything should be done around 22:30 UTC on November 11.

## Reading, fixed now

**E3 and E4** are read per table, Bonferroni 95% within each table group, as "run 2 better", "run 1 better" or "no difference shown". **E1 and E2** are read as in run 1.

**What follows:**
- **E3 shows run 2 better on at least one table and worse on none:** the 2M advantage network becomes the default for the 3-seed follow-up.
- **E4 shows run 2 better but E3 doesn't:** the bigger network learns more per iteration, but slower traversals cancel it. The next step is faster inference (batched calls), not a bigger network.
- **Neither shows a difference:** keep 0.5M. The fit error isn't what limits play at this scale.
- **E3 shows run 2 worse on any table:** keep 0.5M.

The checkpoint contrasts against `net1` are diagnostics, plotted beside run 1's. Each run is one seed, so a difference mixes the network change with run-to-run variance. That's an exploration read, not a strength claim, and no route, default or live play changes.

## Storage, stops and live view

- **Stops:** run 1's.
- **New trees:**
  - `/home/dberweger/neural-deep-cfr-2m-20261110` for the evidence;
  - `/mnt/data2tb/neural-deep-cfr-2m-20261110` for snapshots, every 100 iterations;
  - `/dev/shm/neural-deep-cfr-2m` for the reservoirs.
- **Run 1's RAM reservoirs (37 GB)** are freed after its E2, once its iteration-1,375 snapshot on the HDD is checked.
- **Advantage networks** grow from 1.9 MB to about 9 MB each, about 4.5 GB over the run, against 34 GB free on the NVMe.
- **TensorBoard** (`http://100.99.57.8:6006`) shows run 1 and run 2 side by side.
- **Results** go to this PR and bb128's tree, as for run 1. Packaging and upload are the storage process's job.
