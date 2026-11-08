# The network as the fallback at untrained rows: protocol

Committed before any implementation run or arena hand. Step 3 of the [neural-policy track](../ROADMAP.md), on [step 2's networks](reports/neural-policy-imitation/results.md).

## Question

The live `widemix` (#458 run 1) plays uniform random wherever it has no trained row. Does it play better at #461's short tables if, at exactly those decisions, it plays the step-2 network's strategy instead?

## Why

- **Step 2 couldn't answer whether the network generalizes to spots no teacher trained.** Two thirds of its rescue labels were effectively uniform. Where the labels carried information, the network leaned the right way, but that was an exploratory observation. Play is the test that matters.
- **The gaps are large where it counts.** At the six-player short tables, `widemix` has no row for 39–54% of its flop decisions and 61–90% of its river decisions (#461).
- **This isn't another fallback rule.** #426's check-fold and #452's no-all-in and no-raise were fixed rules, and every one lost. Here the fallback is a learned strategy that depends on the cards and the situation, trained on `widemix`'s own trained rows. The decisions with a trained row are unchanged in both arms.

## The network in play

- **Weights:** step 2's three networks, pinned by their weight hashes (`d222a165…`, `734d9b17…`, `3d76edb5…`) and exported as-is to a flat little-endian float32 file with a JSON header (layers, shapes, feature layout hash, source weight hash).
- **Forward pass:** hand-written in Rust (`policy_network`), with no new dependencies. It computes `policy_features::encode` on the real table's observation, then linear and ReLU layers, then a softmax over the legal labels only.
- **Qualification:** on 10,000 fixed test samples, Rust and PyTorch agree within 1e-5 per probability on every sample, for every network.
- **In the arena:** a new `focal_untrained_fallback` mode, `network`, names a pinned network.
  - At a focal decision whose `widemix` row isn't positive-mass (zero mass or missing), the focal samples the network's strategy.
  - Every other decision plays the row, exactly as before.
  - The focal still draws one random number per decision, so its random stream stays aligned with the uniform arm's.
- **Trace checks:** traces record each fallback decision's network distribution. The scan checks that every fallback action is legal and has positive probability there.

## Arms, tables and fields

- **Arm 0:** `widemix` with uniform fallback, the live client today.
- **Arm 1:** `widemix` with the network fallback.
- **Both arms** use the projected view, as #461 does.
- **Tables:** #461's seven short tables in capped form:
  - 3 players: `3p-5bb`, `3p-short-deep`, `3p-unequal`;
  - 4 players: `4p-short-deep`;
  - 6 players: `6p-5bb`, `6p-short-deep`, `6p-unequal`.
- **Fields:** #461's fields: `mixed` (primary), `pot-pressure`, `tight-aggressive`, `check-call`, `random`, and at six players `live-copies` (copies of `widemix` with uniform fallback).
- **Contrast:** arm 1 minus arm 0, all-in adjusted, over blocks, with every block played at every cyclic seating.

## Runs

| Run | Network | Banks × blocks per field | Roots |
|---|---|---|---|
| 1 (decides) | seed 1 | 4 × 4,096 | `20261108700000 + 1000·bank + case index` |
| 2 (replicates) | seed 2 | 1 × 4,096 | run 1's + 100,000 |
| 3 (replicates) | seed 3 | 1 × 4,096 | run 1's + 200,000 |

Model seeds differ between runs, as in #461. The `widemix` comparison model is the same pinned binary (`702e10cf…`) in every run.

## Decision rules, fixed now

**Per table, run 1:** a Bonferroni 95% interval over the seven tables.
- **Network better:** lower bound above 0.
- **Uniform better:** upper bound below 0.
- **Otherwise no difference shown.**
- **Harm flag:** any other field whose Bonferroni 95% interval over the table's other fields lies entirely below −10 BB/100.

**Replication:** runs 2 and 3 replicate a table when both their primary point estimates are above 0.

**Route, per group** (3 players; 4–6 players, decided by the 4p and 6p tables): the network fallback would replace uniform for `widemix` on the short route only if:
- no table reads "uniform better";
- at least one table reads "network better" and replicates;
- no table has a harm flag.

Adopting it would still be its own PR, with a deploy check and your go. This study changes no route or default.

## Also reported

- each arm's share of focal decisions that use the fallback, by table, field and street (the same rows in both arms, up to divergence after differing actions);
- absolute results per arm, realized beside all-in adjusted;
- the `check-call` field, where `widemix` has the fewest rows;
- the `tight-aggressive` field at `6p-5bb`, where #458's wide models lose about 10 BB/100;
- forward-pass cost per decision;
- per-run results.

## Qualification (the run stops on any failure)

1. Native library and paired-arena host tests pass on bb128, including new tests for the network file, the forward pass and the `network` fallback mode.
2. The Rust and PyTorch parity described above, for all three networks.
3. With `focal_untrained_fallback` set to `uniform` in both arms, the host reproduces #461's run 1 traces byte for byte on two cases. The new code mustn't change existing play.
4. The `widemix` binary and mass receipt pins match.
5. Smoke: run 1's network on every table at 64 blocks per field, on separate roots, through arena, scan, independent replay, all-in equity and report.

## Rules

- **Host:** bb128, all 16 threads, one job at a time. No other bb128 job runs alongside it. Stops: CPU 90 °C, VRM 100 °C, below 4 GB of available memory, below 10 GB of free NVMe. The GPU isn't used.
- **Expected cost:** about the same as #461's evaluation, which took 10 h 49 min including three trainings. With no training here, an estimated 7–9 hours.
- **Failures:** a research failure is reported as is, with no retry or retuning. Plumbing problems go in the PR.
