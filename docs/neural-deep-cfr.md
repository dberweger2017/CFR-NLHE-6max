# Deep CFR from the distilled network: pilot protocol

Step 5 of the [neural-policy track](../ROADMAP.md), prepared while [step 4](neural-policy-everywhere.md) runs. This document and its tooling are committed before any pilot run. The owner chose this direction on November 8: start from the distilled network and the table, then keep training by self-play, rather than training a network from scratch.

## Question

Starting from what the tables already learned, can CFR with networks in place of tables improve on step 2's network? Here "improve" means beating it in play at the tables where step 4 tests it.

## Why

- **Step 2's network only imitates.** It copies `widemix`'s average strategy where `widemix` trained, so it can't be better than its teacher there. Step 3 showed it generalizes sensibly where the teacher never trained, but nothing yet trains it to play *well* in those spots.
- **Deep CFR is the same algorithm that built the tables,** with networks in place of tables (Brown, Lerer, Gross and Sandholm, 2019). Its networks generalize across spots, stack depths and player counts, and its memory doesn't grow with the game: one 8.8 MB network against `widemix`'s 14 GB.
- **Starting from the tables keeps their 10 billion nodes of work.** Starting from scratch would throw that away. The repository started as Deep CFR in Python and stalled on throughput; the engine is now native Rust with an f32 network path and a GPU for training.

## The algorithm

Deep CFR with external sampling and linear CFR weighting, over the existing six-label action menu (fold, check, call, minimum raise, pot raise, all-in).

**One iteration *t*:**
1. **Traverse.** Run *K* traversals (`nplayer_deep_cfr traverse`). Each deals a root:
   - a player count drawn uniformly from 3, 4, 5 and 6;
   - stacks from the wide grid `widemix` trained on;
   - a shuffled deck, a random button and a random traverser.

   It then walks the hand by external sampling. At the traverser's decisions every menu action is explored, and the sampled regrets v(a) − v become one **advantage sample**. At other seats' decisions one action is drawn from the current strategy, which is recorded as one **strategy sample**. The current strategy is regret matching on the advantage network's outputs at the acting seat's `policy_features`.
2. **Buffer.** Add the samples to two reservoirs, one per kind. Each keeps a uniform subsample of everything it was offered, and every sample carries weight *t*.
3. **Train.** Fit the advantage network to the advantage reservoir: weighted squared error of the sampled regrets over the legal labels. Each iteration continues from the previous iteration's weights.

**At the end,** and every 50 iterations for checkpoints, fit a strategy network to the strategy reservoir: weighted cross-entropy to the recorded strategies, softmax masked to the legal labels. That network is the one that plays.

**One shared advantage network covers all seats and player counts.** The features already encode the acting seat's position slot, the player count and the stacks.

## The warm start

The table stands for iterations 1–100:
- **Regrets:** step 1's export, extended in this PR, replays step 2's training recipe at half its hands (1.2 million hands at 3–6 players, `widemix` run 1 as the only teacher). At every sample where `widemix` has a positive-mass row it also writes that row's **regrets from `widemix`'s training checkpoint** (`859e0dc1…`).
  - Each is normalized to the expected sampled regret given the spot is reached, in big blinds: cumulative regret ÷ (traverser visits × (T + 1)/2). That's the quantity an advantage network fits.
  - The normalization assumes the row's visits spread evenly over the checkpoint's T iterations.
- **Strategies:** `widemix`'s average strategy at the same samples.
- **Pretraining:** the advantage network first fits the warm regrets alone (20,000 steps). That gives iteration 101 a current strategy close to the table's.
- **Weight in the reservoirs:** the warm rows enter the reservoirs with the total weight of iterations 1–100 at the measured number of rows per iteration, spread evenly over them. After iteration 101 the table holds 98% of the weight, and by iteration 400 it holds 6%.
- **The strategy network** starts from step 2's seed-1 weights (`d222a165…`) every time it's fitted.

## Recipe

| | |
|---|---|
| Iterations | 101–400 (300 of Deep CFR after the warm start) |
| Traversals per iteration | 20,000 |
| Player counts | 3, 4, 5, 6, uniform per traversal |
| Stacks | wide grid (`wide-depth-grid-v1`) |
| Advantage network | 612 → 512 → 256 → 128 → 6, ReLU; 1,000 steps per iteration, batch 8,192, AdamW lr 1e-3 cosine, fp16 on the GPU |
| Strategy network | step 2's 612 → 1024 → 1024 → 512 → 6; 4,000 steps at checkpoints, 20,000 at the end |
| Reservoirs | 30 million rows each |
| Seed | 20261109000001 |

## Engineering in this PR

- **`policy_network`:**
  - an `advantage-6` output kind, played by regret matching (with no positive regret, the legal label of highest regret, as in Deep CFR);
  - `Fast`, an f32 forward pass with input-major weights that skips zero inputs. It agrees with the f64 reference within 1e-4 on random networks (test) and within 1.7e-6 on step 2's network (bench).
- **`deep_cfr`:** traversal roots and external-sampling traversals that write fixed-size sample records. Everything is a function of (seed, iteration, traversal index), so files don't depend on the thread count. Tests cover determinism and centred regrets.
- **`nplayer_deep_cfr`:** `traverse` (one iteration's sample file and summary) and `bench` (f32 against f64 parity on real traversal features, forward-pass speed, traversals per second).
- **`nplayer_features`:** the optional `regrets` teacher and its `.npreg` sidecar.
- **`scripts/neural_deep_cfr.py`:** `init`, `warm`, `add`, `train` and `export`, with tests for reservoir determinism and uniformity, weighting, training and export.
- **`scripts/neural_deep_cfr_eval.py`:** the pilot evaluation on step 4's harness.
- **[`docs/reports/neural-deep-cfr/`](reports/neural-deep-cfr):** the controller [`run.sh`](reports/neural-deep-cfr/run.sh), its [guard](reports/neural-deep-cfr/guarded.sh) and the warm-start [manifest builder](reports/neural-deep-cfr/make_manifest.py).

**Measured on the M1** (8 threads), November 8:

| | f64 reference | f32 path |
|---|---|---|
| Step 2's network (1024-1024-512), one forward pass | 1.93 ms | 38 µs (50×) |
| The pilot's advantage network (512-256-128) | 0.40 ms | 15 µs (26×) |

- **Traversals:** with step 2's network setting realistic hand lengths, a traversal averages 162 nodes and 97 samples. The M1 runs 476 traversals per second on 8 threads.
- **Checked end to end on the M1:** two iterations (traverse, add, train, export, traverse again). A traversal file is byte-identical at 1 and 8 threads.
- **Regret sidecar:** run against a tiny wide-grid model with its real checkpoint, it found that model's rows at 21% of samples, with no regret on an illegal label.
- **Warm weighting:** checked against the formula on that tiny model's export.

## Evaluation (pilot)

The final strategy network ("Deep CFR") is compared with its starting point, step 2's network ("start"), both playing every focal decision.

| | |
|---|---|
| Tables | step 4's eight: #461's seven short tables and 6-player 100 BB |
| Fields | step 4's fields, the same peer 10B and live copies |
| Hands | 1 bank × 4,096 blocks per field, roots `20261109500000 + 1000·bank + case index` |
| Contrast | Deep CFR minus start, all-in adjusted, Bonferroni 95% over the tables of each group |

**Reading, fixed now (a pilot read, not a gate):**
- **Promising:** no table reads "start better", and at least one reads "Deep CFR better". The next step is a 3-seed run with step 4's gates against the live client.
- **Otherwise:** the recipe is reported as is. Changing it (iterations, traversals, network size, warm weight) needs a new protocol.

**Also reported:**
- the loss history of every network;
- samples and nodes per iteration, and the time of each stage;
- the checkpoint strategy networks' sizes and hashes;
- the comparison with step 4's network-everywhere results, which use the same tables and fields: descriptive only, because the arms differ.

## Qualification (the run stops on any failure)

1. Native library tests, with the K50 tables, and paired-arena host tests pass on bb128, and so do the Python tests for Deep CFR, step 4 and step 3.
2. The GPU check passes.
3. Pins: `widemix` binary `702e10cf…`, its checkpoint `859e0dc1…`, step 2's seed-1 weights `d222a165…`, and `net1` `5e276263…`.
4. `bench` on bb128: the f32 path agrees with the f64 reference on step 2's network within 1e-4.
5. Thread independence: 5,000 traversals at 16 and at 7 threads write identical records.
6. Smoke: three toy iterations from a zero network (500 traversals each), a strategy network, and a smoke evaluation through the arena, scan, independent replay, all-in equity and report.

## Rules

- **Host:** bb128, after step 4 finishes, one job at a time. Stops: CPU 90 °C, VRM 100 °C, GPU 87 °C, below 4 GB of available memory, below 10 GB free on the NVMe, below 20 GB free on the HDD.
- **Storage:** the warm export (about 8 GB) and the reservoirs (about 39 GB) go on the HDD (`/mnt/data2tb/neural-deep-cfr-20261109`). Each iteration's sample file (about 1.3 GB) goes on the NVMe and is deleted once it's in the reservoirs; its summary stays.
- **Expected cost:** about 8–9 hours.

  | Stage | Estimate |
  |---|---|
  | Warm export | 1–1.5 h, mostly loading the 12 GB checkpoint |
  | Pretraining | 10 min |
  | 300 iterations, at about 1 minute each (20–40 s traversing at about 1,000 traversals per second, plus buffering and training) | 5 h |
  | Strategy networks | 20 min |
  | Evaluation | 1.5 h |

- **Failures:** a research failure is reported as is, with no retry or retuning. Plumbing problems go in the PR.
- **Determinism:** traversals and reservoirs are deterministic given the networks. GPU training isn't guaranteed bit-identical across runs, so every network is pinned by its hash in the receipts.

## Launch

Once step 4's controller has written `stage done`:

```bash
W=/home/dberweger/neural-deep-cfr-20261109
mkdir -p $W/source && git archive COMMIT | tar -x -C $W/source && cp $W/source/docs/reports/neural-deep-cfr/guarded.sh $W/
cd $W/source && setsid nohup bash docs/reports/neural-deep-cfr/run.sh > $W/run.log 2> $W/run.err < /dev/null &
```

## Limitations, known now

- **One seed.** This is a pilot; a settled result needs three.
- **Approximate warm regrets.** They assume a row's visits spread evenly over training. Rows admitted late are under-weighted, and their regrets carry pruning's gaps.
- **One shared advantage network** for every seat and player count, as the features allow. Brown et al. used one per player.
- **The advantage network continues from the previous iteration** instead of retraining from scratch each iteration as Brown et al. did. It's cheaper, but can carry stale fits.
- **External sampling at six players is high-variance.** 20,000 traversals per iteration may be few for six-player spots.
- **The menu abstraction is unchanged.** No new bet sizes.
- **Opponents in the evaluation are scripts and copies.** There are no live hands.
