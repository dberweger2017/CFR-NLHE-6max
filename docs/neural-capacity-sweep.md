# Is the advantage network too small? A capacity sweep

**Result (November 9):** 2M parameters is a clear gain over the pilot's 0.5M. Beyond that, a bigger network mostly memorizes noise. [Results](reports/neural-capacity-sweep/results.md).

An exploration run on the neural-policy track: one seed and a quick read, not a gate.

## Question

Deep CFR's advantage network is 612 → 512 → 256 → 128 → 6, about 0.5 million parameters. It's shared by every player count from 3 to 6 and every stack depth. Does a bigger network fit its targets better, or is the fit already limited by the noise in the sampled regrets?

**Why it matters now:**
- The [warm-start pilot](reports/neural-deep-cfr/results.md) lost ground at the 3- and 4-player short tables.
- Its advantage loss rose throughout the run.
- The next big Deep CFR run should use a network size chosen by evidence.

The strategy network (1024-1024-512, about 2.2 million parameters) is not in question here. Imitation of `six` reached 0.065 held-out TV with it ([#474](reports/neural-six-imitation/results.md)).

## What runs

**Data:** a seeded uniform subsample of 5 million rows from the pilot's advantage reservoir after iteration 122, split 90/10 into training and held-out rows. That copy is still on bb128's HDD. It holds two kinds of rows:
- **Warm rows,** from the table's normalized checkpoint regrets (iteration 0). These are averaged, so they're low-noise.
- **Deep CFR rows,** from external sampling at iterations 101–122. These are sampled, so they're noisy.

**Fits:** each architecture fits the training rows with the pilot's loss, weights and optimizer: weighted squared error over legal labels, AdamW at 1e-3 with a cosine schedule, batch 8,192. Each gets 10,000 steps, about 18 passes over the data.

| Name | Shape | Parameters |
|---|---|---|
| `mlp-0.5m` | 512-256-128, the pilot's network | 0.48M |
| `mlp-2m` | 1024-1024-512, the strategy network's shape | 2.2M |
| `mlp-13m` | 6 × 1,536 | 12.8M |
| `res-15m` | 1,536 wide, 3 residual blocks with layer norm | 15.1M |
| `cards-15m` | `res-15m` behind learned card embeddings | 15.5M |

`cards-15m` sums card, rank and suit embeddings per group, as Brown et al. (2019) did, with one group for the hole cards and one for the board. Only the `mlp-*` shapes can be played by the Rust engine today.

**Scored on the held-out rows:**
- squared error, both weighted (the training loss) and unweighted;
- squared error split into warm and Deep CFR rows, by street and by player count;
- how far the regret-matched strategy is from the targets' own regret matching (TV);
- the error on as many training rows, to show overfitting.

## Reading

- **Held-out error keeps falling with size, especially on the low-noise warm rows:** size is a ceiling. The next Deep CFR run should use the bigger network. If `cards-15m` wins, Rust inference needs that architecture.
- **It flattens by `mlp-2m`:** size isn't the limit. Noise in the targets is, so more traversals per iteration or variance reduction come first.
- **Big networks overfit,** meaning training error well below held-out error: 5 million rows are too few to tell, and the next step is a larger subsample.

## Where it runs

| Step | Machine | How |
|---|---|---|
| `run.sh prepare` | bb128 | lowest CPU and IO priority, next to the running scratch job (PR477); a few minutes of sequential HDD reads |
| `run.sh sweep` | the M4, a base M4 MacBook Pro with 16 GB | Apple GPU (MPS, fp32), one architecture after another |

The subsample is about 3.2 GB in memory.

**Measured on the M1's GPU,** per training step at batch 8,192: 0.02 s (0.5M), 0.09 s (2M), 0.54 s (13M) and about 0.6 s (15M). On the M4, with held-out scoring included, they took 0.02 s (0.5M), 0.04 s (2M), 0.28 s (13M) and 0.43 s (both 15M networks), so the whole sweep took 3.5 hours.

[Runner](reports/neural-capacity-sweep/run.sh) · [script](../scripts/neural_capacity_sweep.py) · [tests](../tests/test_neural_capacity_sweep.py)

## Limitations

- **One seed, one subsample,** taken from early in the pilot (iteration 122). Later Deep CFR rows, for example from PR477's snapshots, may be noisier.
- **Held-out error on noisy targets has a floor nobody knows.** Differences between sizes are what count, not the level.
- **A better offline fit doesn't guarantee better play.** It's evidence for choosing the next run's network, not a strength claim.
