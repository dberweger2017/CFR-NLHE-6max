# N-player fast mode

`nplayer_train --fast` is an opt-in training recipe for `multi_cfr.rs` that uses every core and gives identical results for any thread count. Without `--fast`, training is unchanged and byte-identical to the production recipe.

## What changes

The production recipe runs one traversal per seat and iteration and draws each opponent action from that root's random stream (`StdRng`, seeded from SHA-256 of seed, iteration and seat), consumed in depth-first order. Every draw depends on how many draws came before it, so a traversal must run in that order on one core.

Fast mode changes three things:

- **Opponent draws come from the node's path.** Every node has a 64-bit path: the root is 0 and each child is `splitmix(path ^ splitmix(action + 1))`. An opponent at a node draws `u = splitmix(seed ^ path) >> 11`, scaled to [0, 1), and takes the first action whose cumulative probability exceeds `u` (the same rule and zero-probability fallback as production). `seed` is one 64-bit value per root, from SHA-256 of seed, iteration, seat and root under a separate domain (`nplayer-path-sampling-v1`).
- **Several roots per seat.** Each iteration runs `--roots-per-seat` traversals per seat (default 8 with `--fast`), all against the same table snapshot and with the same linear weight `t`. Root 0 of each seat deals the production deal; further roots deal from their own stream (`nplayer-fast-root-v1`). An iteration of a three-player cash game is only a few thousand nodes, too little to share across cores; more roots per iteration give each core enough work.
- **Parallel work in a fixed order.** All roots of an iteration run in parallel, and the traverser's first decision (`FORK_DEPTH = 1`) forks: each action's subtree is traversed in parallel with its own deltas. Forked deltas are added in action order; root deltas are summed per key in seat-then-root order and merged into the table shard by shard. Nothing depends on scheduling, so the checkpoint is byte-identical on any number of threads.

Checkpoints record `"sampling": "path-v1"` and `"roots_per_seat"`. A fast checkpoint resumes only with `--fast` and the same roots per seat, and a production checkpoint only without `--fast`. `--threads N` sets the worker count.

Per-iteration deltas are stored inline (`Delta`, at most eight actions) instead of in two heap allocations per key; this also makes the production recipe about 10% faster, with identical results.

## Why the estimates stay unbiased

External sampling is unbiased when, at every opponent node a traversal reaches, the action is drawn from the current policy, independently of everything else the traversal does. The traverser's sampled counterfactual values are then unbiased estimates of the true ones, whatever the source of randomness.

Fast mode keeps that property:

1. **The right distribution.** `u` is uniform on the same 2^53-point grid as `StdRng`'s `f64`, provided `splitmix` mixes well; it is the SplitMix64 finalizer, a bijection with full avalanche. Picking the first cumulative probability above `u` then draws action `a` with probability `policy[a]`, exactly as in production.
2. **Independent draws.** Distinct nodes of a traversal have distinct paths, so their draws are pseudo-independent. As in production, the same opponent information set reached along two traverser branches gets two independent draws. Two nodes could share a path only through a 64-bit collision: for `m` nodes per traversal that has probability at most `m^2 / 2^65`, about 3e-8 for a million nodes.
3. **Fresh draws every root and iteration.** Seeds and extra deals come from SHA-256 of seed, iteration, seat and root, so roots and iterations do not reuse draws or deals.
4. **Forks change no draw.** A forked subtree draws exactly what it would draw unforked, because draws depend only on paths. Forking changes only the order in which the same deltas are summed: floating-point rounding, nothing else. A test checks that a traversal with and without forks visits the same nodes and gives the same deltas to within 1e-9.
5. **Several roots are an average of unbiased estimates.** Each root is an independent external-sampling traversal from a fresh deal; summing `R` of them with weight `t` is `R` times an unbiased estimate of the same iteration's update. Regret matching is invariant to that common factor, and the opponent-sampled average still adds one `t`-weighted policy sample per opponent visit, only with more visits per iteration; this is external sampling with `R` samples per iteration. The cost is fewer iterations at equal nodes (`R` times fewer), the same trade the HU roots-per-seat study measured.

What fast mode is not: bit-identical to production. Different draws and more roots per iteration give a different, equally valid sample path, so a fast-mode model is a new recipe. Whether it plays as well at matched nodes is the strength question, answered by a predeclared comparison, not by this argument.

## Speed

Laptop i7-14650HX (8 performance and 8 efficiency cores, 24 threads), 3 players, 100 BB, 20M nodes, #163's K50 tables. Training seconds exclude the save; two runs each; package temperature peaked at 85 to 96 C.

| Recipe | Threads | M nodes/s | vs production |
|---|---:|---:|---:|
| production | 1 | 1.56, 1.58 | 1.0x |
| fast, 8 roots per seat | 1 | 1.37, 1.37 | 0.9x |
| fast, 8 roots per seat | 2 | 2.61, 2.53 | 1.6x |
| fast, 8 roots per seat | 4 | 4.41, 4.29 | 2.8x |
| fast, 8 roots per seat | 8 | 6.36, 6.52 | 4.1x |
| fast, 8 roots per seat | 16 | 7.35, 7.56 | 4.7x |
| fast, 8 roots per seat | 24 | 7.63, 7.69 | 4.9x |
| fast, 16 roots per seat | 16 | 8.86, 9.04 | 5.7x |
| fast, 16 roots per seat | 24 | 9.59, 9.57 | 6.1x |

Scaling flattens beyond the eight performance cores. In earlier runs fork depth 1 beat 0 and 2 at 16 and 24 threads, and one root per seat reached only 2.9 M nodes/s at 16 threads.

With `--freeze-at-cap`, the cap is checked after each iteration, as in production; an iteration of `R` roots per seat can add more keys before the table freezes than a production iteration.

## Checks

- `fast_mode_is_identical_for_every_thread_count`: Kuhn and Leduc (3 and 4 players), one and five roots per seat, byte-identical checkpoints on 1, 2, 4, 8 and 16 threads.
- `fast_roots_have_their_own_deals_and_draws`: root 0 deals the production deal; every root of a seat has its own deal stream and path seed, and seats do not share seeds.
- `fast_resume_is_exact_and_keeps_its_sampling`: a resumed fast run (three roots per seat) equals an uninterrupted one; a fast checkpoint cannot continue with the production recipe; checkpoints with roots per seat but no fast sampling, or zero roots, are refused, and so is a trainer with invalid roots per seat.
- `forks_change_only_the_order_deltas_are_summed`, as above.
- `path_draws_follow_the_policy`: 200,000 draws match the policy within six binomial standard deviations; zero-probability actions are never drawn.
- `fast_mode_converges_like_the_production_recipe`: mean exploitability over eight seeds on 3-player Kuhn (20,000 iterations) and Leduc (2,000), fast mode with one root and with four roots at equal nodes, within 25% of production's. Measured: Kuhn 0.0102 production, 0.0097 fast, 0.0104 four roots; Leduc 1.29, 1.49, 1.39. A copy whose roots repeat root 0 fails it (Kuhn 0.0234).
