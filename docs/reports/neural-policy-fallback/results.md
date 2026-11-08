# The network as the fallback at untrained rows: results

This is a run of [the protocol](../../neural-policy-fallback.md), committed before any implementation run or arena hand and not amended. It ran on bb128 on commit `e0e51166` with the [controller](run.sh) and [guard](guarded.sh), from November 7, 23:27 UTC, to November 8, 05:44 UTC ([stage log](stages.json)).

Step 2 ([#467](https://github.com/dberweger2017/CFR-NLHE-6max/pull/467)) failed its offline test. Its exploratory breakdown suggested the test mostly measured near-uniform labels, so step 3 went ahead with the owner's go to test generalization in play. The step-2 networks are used exactly as trained, with no retraining.

Data files, per run: `results.json` (every field, interval and untrained share), `fields.csv`, the model catalog and the independent replay receipt, in [`run1/`](run1), [`run2/`](run2) and [`run3/`](run3). The smoke run's results are in [`smoke/`](smoke), the network pins in [`networks.json`](networks.json), and the binary hashes in [`binaries.sha256`](binaries.sha256).

All values are BB/100, all-in adjusted, arm 1 minus arm 0, both through the projected view:
- **arm 0:** the live `widemix` (#458 run 1) with uniform fallback;
- **arm 1:** the same `widemix` binary, playing the step-2 network wherever it has no positive-mass row.

Run 1 (seed-1 network) is 4 banks × 4,096 blocks per field. Runs 2 (seed 2) and 3 (seed 3) are 1 bank each.

## Routes under the prespecified rules

| Group | Decided by | Network better and replicated | Verdict |
|---|---|---|---|
| 3 players | `3p-5bb`, `3p-short-deep`, `3p-unequal` | `3p-5bb`, `3p-unequal` | **passes** |
| 4–6 players | `4p-short-deep`, `6p-5bb`, `6p-short-deep`, `6p-unequal` | all four | **passes** |

Both groups meet all three route conditions:
- no table reads "uniform better";
- at least one table reads "network better" in run 1 and replicates (both runs 2 and 3 above 0);
- no table has a harm flag.

Under the protocol, the network fallback would replace uniform for `widemix` on the short route at 3–6 players. Adopting it is its own PR with a deploy check and the owner's go. This study changes no route or default.

## Primary contrasts (`mixed` field)

| Table | Run 1 | Run 1 decision interval | Run 1 verdict | Run 2 | Run 3 | Replicates |
|---|---|---|---|---|---|---|
| `3p-5bb` | +0.33 | [+0.00, +0.67] | network better | +0.28 | +0.63 | yes |
| `3p-short-deep` | +1.26 | [−0.55, +3.07] | no difference shown | −0.32 | +0.77 | — |
| `3p-unequal` | +1.17 | [+0.08, +2.26] | network better | +0.25 | +2.52 | yes |
| `4p-short-deep` | +3.40 | [+0.96, +5.85] | network better | +1.52 | +1.81 | yes |
| `6p-5bb` | +0.94 | [+0.57, +1.31] | network better | +0.39 | +0.59 | yes |
| **`6p-short-deep`** | **+20.5** | [+13.7, +27.3] | network better | **+33.6** | **+22.4** | yes |
| **`6p-unequal`** | **+17.4** | [+12.4, +22.4] | network better | **+19.7** | **+14.8** | yes |

Decision intervals are Bonferroni 95% over the seven tables. `3p-5bb`'s lower bound is +0.002, so that verdict is marginal.

Runs 2 and 3 on their own also read "network better" at `6p-short-deep` and `6p-unequal`, with lower bounds of +20.4 and +9.7 (run 2) and +9.1 and +5.1 (run 3). Every other table reads "no difference shown" in those runs. Realized results agree with the adjusted ones within about 2 BB/100 everywhere (run 1: +21.1 and +16.1 at the two deep six-player tables).

**The six-player tables with one short seat and five deep seats are where this matters.** That gap survived #461's larger table and #462's coverage keys. Three independently trained networks close about 15–34 BB/100 of it. In absolute terms, run 1's `widemix` goes from +117.8 to +138.3 against `mixed` at `6p-short-deep`, and from +124.6 to +142.0 at `6p-unequal`.

The gains are small where the network rarely plays (the 3-player tables, at 3–8% of decisions) and large where it plays often (the deep six-player tables, at 16%; see below).

## Other fields and harm

No table has a harm flag in run 1, the run that decides. Run 1's lowest other-field decision bound is −0.67 (`check-call` at `6p-5bb`), far from the −10 margin.

| Field | Pattern across the three runs |
|---|---|
| `pot-pressure` | −0.7 to +1.2 everywhere |
| `tight-aggressive` | −0.4 to +0.4 everywhere |
| `random` | positive almost everywhere, up to +10.6; the lowest is −1.6 (`6p-unequal`, run 3) |
| `live-copies` (6p) | +0.1 to +4.5; run 1 at `6p-short-deep` is +3.1 [+1.0, +5.2] |
| `check-call` | large gains at 3–4 players: +36.8, +45.6, +24.6 at `4p-short-deep`; mixed at the deep 6p tables (below) |

**`check-call` at the deep six-player tables doesn't replicate.**

| Table | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| `6p-short-deep` | +11.6 [+1.7, +21.6] | −8.6 [−30.1, +12.9] | −5.2 [−27.2, +16.7] |
| `6p-unequal` | +10.3 [+1.1, +19.5] | +3.0 | −5.9 |

The one-bank intervals are about 40 BB/100 wide, so this may be noise. It isn't a harm flag under the rules, which use run 1. Still, it's the one place where a network other than seed 1 leans the wrong way, and a deploy check should look at it again.

**`tight-aggressive` at `6p-5bb`:** #458's wide models lose about 10 BB/100 here. The network fallback leaves this unchanged (+0.0, +0.1, +0.0), because the leak isn't at untrained rows.

## Where the network plays

Share of the focal's decisions without a positive-mass row in run 1. These are the decisions the network plays in arm 1. Arm 0 is within 0.5 points everywhere, and the arms differ only after their actions diverge. Runs 2 and 3 are within 3 points.

| Table | All | Preflop | Flop | Turn | River |
|---|---|---|---|---|---|
| `3p-5bb` | 7.4% | 0% | 10% | 37% | 54% |
| `3p-short-deep` | 2.6% | 0% | 1% | 5% | 17% |
| `3p-unequal` | 3.9% | 0% | 1% | 6% | 26% |
| `4p-short-deep` | 9.5% | 0% | 10% | 32% | 43% |
| `6p-5bb` | 11.2% | 0.1% | 54% | 73% | 90% |
| `6p-short-deep` | 16.3% | 0.1% | 41% | 54% | 67% |
| `6p-unequal` | 15.8% | 0.1% | 39% | 51% | 64% |

`6p-5bb` has the most postflop gaps but gains only about +0.4 to +0.9. At 5 BB most pots are decided preflop, where `widemix` has its rows, so postflop play is worth less there.

## The networks

| Run | Network | Source weights (#467) | File SHA-256 | Parity: max difference over 10,000 samples |
|---|---|---|---|---|
| 1 | `net1` | `d222a165…` | `5e276263…` | 6.6e-7 |
| 2 | `net2` | `734d9b17…` | `ae573149…` | 6.9e-7 |
| 3 | `net3` | `3d76edb5…` | `f5fd32c6…` | 5.5e-7 |

Each file is 8.8 MB: MLP 612→1024→1024→512→6, float32.

- **Forward pass:** about 1.8 ms per decision on one bb128 core. That's 10,000 passes in 17.6–17.9 s over three repeats, including the load and hash. It's a plain scalar f64 loop, with no SIMD or batching.
- **In the arena:** an arena bank, with its scan, took 4 min 19 s – 5 min 20 s for both arms together, at all 16 threads.

## Qualification and checks

**Qualification** ([receipt](qualification/receipt.json)) passed:
- native library and paired-arena host tests, including the new network-file, forward-pass and `network`-mode tests, plus 11 Python tests;
- Rust–PyTorch parity within 1e-5 for all three networks ([`qualification/parity-net*.json`](qualification));
- with uniform fallback in both arms, byte-identical reproduction of #461 run 1's traces on `3p-5bb` and `6p-5bb` against `mixed`, both arms ([receipt](qualification/repro-receipt.json), [expected hashes](qualification/repro-expected.json));
- the `widemix` binary (`702e10cf…`) and mass receipt (`afd951ff…`) pins.

**Further checks:**
- **Smoke:** run 1's network completed the full pipeline on every table at 64 blocks per field.
- **Trace checks:** every fallback decision in every receipt has a recorded network distribution, and the action played is legal there with positive probability. There are 0 violations across all runs and the smoke.
- **Independent replay:** all 76 bank-0 traces of each run (1,417,216 hands per run) replayed through the engine and passed.

## Plumbing

- **Cost:** 6 h 17 min in all, under the 7–9 hours planned. All-in equity for run 1 took 3 h 44 min, the longest stage.
- **Resources** (5-second samples):
  - peak CPU package 84 °C and VRM 59 °C;
  - at least 54 GB free on the NVMe and 135 GB on the HDD;
  - host-wide used memory peaked at 37.4 GB.

  No stop fired. The GPU wasn't used.
- **No failures or retries.**

## Limitations

- **The networks were trained to imitate `widemix` where it has rows,** and play here only where it doesn't. Nothing in this study shows how they would do on every decision (step 4).
- **The opponents are scripts or copies,** with no live hands. Copies of the live client (`live-copies`) are the closest to a real field.
- **There's no 5-player table.** 5-player hands follow the 4–6 group.
- **One recipe, three seeds.** The runs differ in network seed and deal roots, not in architecture or training.
- **The `check-call` reversal at the deep 6p tables** in runs 2 and 3 is unresolved.
- **The 1.8 ms forward pass is fine for the arena.** A deployment's latency budget still needs checking in the deploy check.
