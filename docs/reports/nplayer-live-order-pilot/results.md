# Live-order key pilot: the six-player table stops overflowing

[#431](https://github.com/dberweger2017/CFR-NLHE-6max/pull/431) follows the [pilot protocol](../../nplayer-live-order-keys.md) committed before training. The six-player recipe of #417 was trained to 2B nodes with one change, `--key-schema live-order`, and compared with #417's own telemetry for the same seed and recipe. It is a feasibility pilot with no strength claim.

**Gate: proceed.** At 600M nodes the live-order table holds **17,787,786 entries**, against the 125M limit and #417's frozen 250M.

## Table growth

From both runs' training telemetry ([telemetry.json](telemetry.json)):

| Nodes | History key (#417) entries | Live-order entries | Decisions without a row, history → live-order |
|---|---|---|---|
| 200M | 112.0M | 12.1M | — → 9.8% |
| 400M | 209.8M | 15.5M | — → 6.4% |
| 600M | 250.0M (frozen at iteration 23,678) | **17.8M** | — → 4.9% |
| 1B | 250.0M | 20.9M | — → 3.5% |
| 2B | 250.0M | **25.5M**, not frozen | **73.6% → 2.2%** |

At 2B nodes, #417 had discarded 58.1% of traverser regret updates; the live-order run discarded none.

**Rows at 2B** (from the mass audit):

| Street | Entries | Regret updates per row | Opponent-only rows |
|---|---|---|---|
| Preflop | 1.06M | 22.0 | 0.35M |
| Flop | 4.73M | 10.0 | 2.29M |
| Turn | 6.99M | 14.3 | 2.94M |
| River | 12.76M | 16.0 | 5.12M |

- **More updates per row:** each row gets 10–22 regret updates by 2B. #417's rows got 2.0–2.8 over the whole 10B run.
- **Opponent-only rows are still there:** 10.7M rows (42%) have only opponent updates, because traverser admission (#430) is not part of this change. With the table far from full, they cost no capacity.
- **Zero-mass rows:** 3.86M.

## Qualification

- **Legacy parity:** without the option, the branch trainer's 100M-node checkpoint is byte-identical to a `main` build (`69fad647…`). That's the same hash as #427 and #430.
- **Determinism:** with the option, 16 and 8 threads give identical 100M-node checkpoints (`482a0f8f…`). They differ from the legacy one and record the live-order schema.
  - At about 100M nodes, the live-order table holds 9.1M rows against the history key's 58.7M.
- **Pipeline:** export, average-mass audit, conversion and binary verification of the 2B checkpoint pass.
- **Mixed-schema arena** ([smoke.json](smoke.json)): #417's 10B (history keys) and the live-order 2B each played 768 hands against pot-pressure, and both traces passed the replay scan.
  - The live-order arm found positive-mass rows for 1,133 of 1,137 focal decisions (99.6%), the control for 1,015 of 1,073 (94.6%).
  - 64 blocks are far too few to read returns. They are not reported as results.

## What it means

- **The key changes the scale of the problem.** The arena measurement predicted 2–3× merging postflop. In training the table is about 14× smaller at 600M nodes and growing slowly at 2B.
  - Training explores far more history variety than play reaches, and the live-order key collapses most of it.
  - Nearly every training decision now finds a row, and rows get several times more updates.
- **The risk is the other side of that merge.** Spots that need different play may share a row, and only a strength comparison can show whether coverage or that loss dominates.
- **Next:** the gate passes. The 10B strength screen gets its own protocol before training.

## Cost

- **Run:** 05:53–06:08 UTC on bb128 (15 minutes), alone. Training to 2B took 282 s; CPU and VRM peaks were 71 °C.
- **Disk:** 6.9 GB on the HDD and 0.7 GB on the NVMe ([costs.json](costs.json)). Nothing was deleted.
