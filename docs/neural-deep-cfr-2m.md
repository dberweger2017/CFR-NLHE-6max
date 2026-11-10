# Deep CFR from scratch with a 2M advantage network: protocol

Follows [run 1](neural-deep-cfr-scratch.md) ([PR477](https://github.com/dberweger2017/CFR-NLHE-6max/pull/477)) and the M4 advantage-fit studies ([PR478](https://github.com/dberweger2017/CFR-NLHE-6max/pull/478), [PR479](https://github.com/dberweger2017/CFR-NLHE-6max/pull/479), [PR480](https://github.com/dberweger2017/CFR-NLHE-6max/pull/480)). The question: **does a 2M-parameter advantage network learn a better policy than run 1's 0.5M network, per iteration and per day of bb128?**

Proposed in [issue 482](https://github.com/dberweger2017/CFR-NLHE-6max/issues/482). This protocol is committed before launch. Any change after launch is reported as a deviation. Controller: [`run.sh`](reports/neural-deep-cfr-2m/run.sh).

## What we know

**From the M4 studies** (offline fits on the pilot's reservoir rows, one seed, no play):
- **0.5M → 2M cuts held-out advantage error by 9%** at 4.5M rows. Beyond 2M, size doesn't help at that row count (#478).
- **Rows limit the fit:** each tripling of rows cuts error by 20–25% (#479).
- **At 13M rows the 13M network wins by 3%** over 2M. Card embeddings no longer help. A Huber loss is mixed (#479, #480).

**From run 1** (one seed, 1,375 iterations in 24 hours):
- **It learned from uniform play.** No table read clearly worse than `net1` from iteration 300 on. Against tight-aggressive players it turned from clearly losing to winning.
- **Its gains flattened** between iterations 800 and 1,200.
- **Its advantage loss kept rising**, from 1,500 at iteration 25 to 2,160 at iteration 1,200.

The flattening and the rising loss fit a network too small for its reservoir, but they don't prove it: regret magnitudes also grow under linear weighting. **Run 1's final evaluation** (4,096 blocks per table, in PR477):
- **E1 against `net1`:** better on 6p-short-deep (+117) and 6p-unequal (+151), no table worse. That meets the pilot's "promising" rule.
- **E2 against the warm pilot:** better on 4p-short-deep (+57), 6p-short-deep (+87) and 6p-unequal (+114), worse on 3p-5bb (−7) and 6p-5bb (−6). No difference at 6p-100bb against the trained field (−12, −28 to +4).
- **Harm flag in both:** large losses against the random field at 6 players (−114 to −229).

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
**Measured on the M4 ([PR483](https://github.com/dberweger2017/CFR-NLHE-6max/pull/483)), with run 1's code and settings:**
- **The network isn't most of a decision's cost.** About 24 µs per decision goes to features, equity lookups and records. One call costs 5.7 µs for run 1's last network, and 22–41 µs for trained 2M networks. Trained networks are cheaper than untrained ones, because their zero hidden units are skipped.
- **The traversal slows 1.55–2.16×** on run 1's late tree, not the 4.6× the multiply-adds would suggest. On identical uniform trees, untrained 0.5M and 2M networks give byte-identical records, and 2M takes 2.4× as long.
- **13.7 of run 1's 24 hours were outside the traversal loop:** stage overhead, reservoir adds and fits. Most of that doesn't grow with the network. The 2M fit is assumed to take 1.0–1.75× run 1's 16.2 s.
- **So run 2 projects to about 860 iterations** in 24 hours (range 680–1,110), against run 1's 1,375. It should pass iteration 800, where run 1 began to flatten, so the checkpoints and E4 can see whether the bigger network changes the flattening.
- Qualification's three timed iterations check this on bb128. The run launches whatever the speed, because the question includes "per day".

**That gives two comparisons:**
- **Equal iterations (E4 and the checkpoints):** does the bigger network learn more per iteration?
- **Equal machine time (E3):** is it the better use of a day of bb128?

## Schedule on bb128

Run 1's E2 finished at 15:29 UTC on November 10, and run 2 starts once qualification passes.

1. **Qualification:** run 1's native and Python tests, thread determinism with the 2M network, and the pinned run-1 final. Then:
   - **the smoke:** three toy iterations that fit and export the 2M advantage network and traverse with it in Rust. The Rust loader and its f32 parity are the ones that already play the strategy network of the same shape. No separate parity step was added.
   - **the iteration-1 identity:** the run stops if iteration 1's records differ from run 1's (`records_sha256`).
   - **timing:** the first iterations are timed in `progress.csv`, like every iteration.
2. **Training window:** 24 hours, under run 1's rules. No iteration starts after the window closes, and the last completed iteration is final.
3. **Monitoring** at iterations 25, 50, 100, 200, 300, 400, 800 and 1,200, if reached. It uses run 1's fits (4,000 steps, fresh) against `net1`, with **run 1's roots**, so each checkpoint plays run 1's deals at the same iteration. These are diagnostics.
4. **Final fit:** 20,000 steps, fresh.
5. **Final evaluation,** one bank of 4,096 blocks per table and field on the eight tables:
   - **E1, run 2 against `net1`:** run 1's E1 roots (`20261109500000…`).
   - **E2, run 2 against the warm pilot's `strategy300-s4000`:** run 1's E2 roots (`20261110500000…`).
   - **E3, equal time: run 2's final against run 1's final** (`strategy1375-s20000`), on fresh roots `20261111500000 + 1000·bank + case`.
   - **E4, equal iterations:** run 2's last checkpoint network against run 1's at the same iteration (both 4,000-step fits), on fresh roots `20261111600000 + 1000·bank + case`.

The evaluation takes about 6 hours on bb128, or can move to a Runpod CPU pod so bb128 starts the next run: run 1's E1 and E2 took about 3, and E3 and E4 cost about the same. Everything should be done around 22:30 UTC on November 11.

## Reading, fixed now

**E3 and E4** are read per table, Bonferroni 95% within each table group, as "run 2 better", "run 1 better" or "no difference shown". **E1 and E2** are read as in run 1.

**What follows:**
- **E3 shows run 2 better on at least one table and worse on none:** the 2M advantage network becomes the default for the 3-seed follow-up.
- **E4 shows run 2 better but E3 doesn't:** the bigger network learns more per iteration, but slower traversals cancel it. The next step is faster inference (batched calls), not a bigger network.
- **Neither shows a difference:** keep 0.5M. The fit error isn't what limits play at this scale.
- **E3 shows run 2 worse on any table:** keep 0.5M.

The checkpoint contrasts against `net1` are diagnostics, plotted beside run 1's. Each run is one seed, so a difference mixes the network change with run-to-run variance. That's an exploration read, not a strength claim, and no route, default or live play changes.

## Deviations

- **Thermal stop at 18:14 UTC, November 10 (plumbing).** The guard stopped iteration 65's traversal at CPU 91 °C. Run 2's denser network runs the i7-10700KF hotter than run 1, which peaked at 88 °C in 24 hours. The run resumed at iteration 65 with traversals on **12 of 16 threads**. Records don't depend on the thread count, as qualification checks, so only speed changes. The original window end stands, so the stop and the slower traversals count against run 2's equal-time comparison (E3); the report gives the lost time.
- **Resume fix.** The stopped traversal had left an empty `it65.json`, which the resume would have read as a finished traversal and then added its partial samples. That partial output was deleted by hand. The controller now writes the summary under a temporary name and renames it on success.

## Storage, stops and live view

- **Stops:** run 1's.
- **New trees:**
  - `/home/dberweger/neural-deep-cfr-2m-20261110` for the evidence;
  - `/mnt/data2tb/neural-deep-cfr-2m-20261110` for snapshots, every 100 iterations;
  - `/dev/shm/neural-deep-cfr-2m` for the reservoirs.
- **Run 1's RAM reservoirs (37 GB)** are freed before launch, once its iteration-1,375 snapshot on the HDD is checked.
- **Advantage networks** grow from 1.9 MB to about 9 MB each, about 4.5 GB over the run, against 34 GB free on the NVMe.
- **TensorBoard** (`http://100.99.57.8:6006`) shows run 1 and run 2 side by side.
- **Results** go to this PR and bb128's tree, as for run 1. Packaging and upload are the storage process's job.
