# Covering short multiway tables: results

[Protocol](../../openpoker-short-coverage.md), committed before training. Run on bb128, November 7, 14:56–18:56 UTC, under the owner's exclusive lock.

**Verdict: no candidate advances, so Stage B didn't run and the live `widemix` stays.** Effective-stack keys cut the six-player postflop gap the most, by 7.3 points alone and 8.3 points with short-heavy deals, but neither reaches the 10-point bar fixed in the protocol. Short-heavy deals alone help only the all-short table and are slightly worse at the two deep-mixed six-player tables.

## Stage A: the screen

Metric: each model's share of postflop decisions without a positive-mass row, pooled over the three six-player tables and all their fields, in arenas where each candidate played `ctrl` on the same deals (one bank, 512 blocks per field). [screen.json](screen/screen.json) holds every number below.

| Candidate | `ctrl` | Candidate | Reduction | Below `ctrl` at each 6p table | Advances (needs ≥ 10 and each) |
|---|---|---|---|---|---|
| `eff` (effective-stack keys) | 53.65% | 46.33% | **7.31** | yes | no |
| `short` (short-heavy deals) | 53.65% | 52.18% | 1.46 | no | no |
| `effshort` (both) | 53.65% | 45.39% | **8.25** | yes | no |

### Postflop untrained share by table, `ctrl` → candidate

| Table | `eff` | `short` | `effshort` |
|---|---|---|---|
| `3p-5bb` | 24.6 → 3.3 | 24.6 → 5.8 | 24.6 → 2.2 |
| `3p-short-deep` | 5.5 → 3.1 | 5.5 → 5.2 | 5.5 → 3.1 |
| `3p-unequal` | 9.0 → 6.9 | 9.0 → 9.2 | 9.0 → 7.1 |
| `4p-short-deep` | 25.7 → 19.7 | 25.7 → 26.3 | 25.7 → 19.3 |
| `6p-5bb` | 68.9 → 44.5 | 68.9 → 54.5 | 68.9 → 42.9 |
| `6p-short-deep` | 52.3 → 48.0 | 52.3 → 53.1 | 52.3 → 46.6 |
| `6p-unequal` | 49.2 → 45.4 | 49.2 → 50.3 | 49.2 → 45.2 |

### River untrained share, the street #461 targeted

| Table | `ctrl` | `eff` | `short` | `effshort` |
|---|---|---|---|---|
| `6p-5bb` | 94.0 | 69.9 | 71.6 | 66.7 |
| `6p-short-deep` | 68.9 | 67.1 | 69.9 | 65.8 |
| `6p-unequal` | 65.9 | 65.5 | 67.2 | 64.9 |

## What it means

- **Effective-stack keys are the stronger lever, and the gain doesn't come from table size.** `eff`'s table froze as early as `ctrl`'s (iteration 276k against 283k) and its training-time missing shares are about the same. It covers more play anyway, because its rows merge play states that `ctrl` splits by the depth of opponents who are deeper than the hero.
- **They don't close the deep-mixed six-player tables.** At `6p-short-deep` and `6p-unequal` the gain is 4–6 points postflop and almost nothing on the river (65–67% stay untrained). The big gains are at all-short tables: `6p-5bb` drops 24 points and `3p-5bb` 21.
- **Short-heavy deals help only where every seat is short.** At `6p-5bb` the river gap drops from 94% to 72%. Elsewhere, half the training budget goes to all-short deals and the deep-mixed tables get slightly worse (+0.8 to +1.3 points).
- **The six-player deep-mixed postflop gap remains.** That's the case where one seat is short and five are deep. After #461 (table size) and this study (key shape and deal mix), about half of those postflop decisions and two thirds of river decisions still have no trained row. Self-play just doesn't reach those multiway lines often enough under any of these levers.
- **Coverage isn't strength.** #461 showed that better coverage at three players didn't measurably improve play. Testing whether `effshort`'s coverage gain at all-short tables plays better would take a new protocol. This screen doesn't support one, and it isn't repeated or retuned here.

## Models

All four are six-player, 4B nodes and a 250M-entry cap, with #458's recipe otherwise. Pins are in `screen/<arm>-pins.json`, training reports in `screen/<arm>-train.json`.

| Model | Key schema | Stack law | Seed | Frozen at | Iterations | Training missing (pre/flop/turn/river) | Train time | Binary |
|---|---|---|---|---|---|---|---|---|
| `ctrl` | live-order | wide-depth-grid-v1 | 20261108920001 | 283,227 | 475,178 | 1.3 / 18.4 / 15.4 / 18.4% | 17 min | 14.13 GB |
| `eff` | live-order-effective | wide-depth-grid-v1 | 20261108920002 | 276,314 | 489,458 | 2.6 / 17.5 / 16.7 / 20.9% | 18 min | 14.19 GB |
| `short` | live-order | short-wide-mixture-v1 | 20261108920003 | 567,507 | 806,683 | 0.9 / 16.9 / 15.1 / 18.3% | 18 min | 14.10 GB |
| `effshort` | live-order-effective | short-wide-mixture-v1 | 20261108920004 | 538,758 | 840,938 | 2.0 / 16.4 / 16.6 / 21.3% | 24 min | 14.15 GB |

Training-time missing shares are each model's own deals, so `short` and `effshort` aren't comparable with the others there; the screen arenas are.

## Qualification and checks

- **Qualification** ([receipt](qualification-receipt.json)) passed on commit `89d8d1db`:
  - native library and paired-arena host tests pass;
  - #458's `widemix` recipe at 100M still writes `ca8f357b…`;
  - `effshort` at 100M is byte-identical at 16 and 8 threads;
  - the live `widemix` pins (`702e10cf…`, `afd951ff…`) match.
- **Smoke:** 100M models completed the screen pipeline and Stage B's full pipeline (arena, scan, replay, all-in equity, report).
- **Traces:** every screen arena's 76 traces replayed independently through the engine and passed (177,152 hands each), with no fallback violations. See `screen/<candidate>-replay-b0.json`.
- **Binaries:** the tool hashes are in [binaries.sha256](screen/binaries.sha256).

## Plumbing

- **Attempt 1:** the first smoke screen arena stopped at 14:40 UTC because the projected view allowed only plain live-order models. Effective-stack keys read live chips only, so `89d8d1db` allows both. Qualification was re-run from scratch on the new build. Attempt 1's stages are in [attempts/](attempts/attempt1-stages.json).
- **Monitoring:** the controlling Mac lost its Tailscale connection twice (about 16:40–16:53 UTC, and again for a stretch ending at 18:12 UTC). The run on bb128 was unaffected.
- **Cost:** 4 h 0 min from the restart, inside the 3–15 hours planned for the whole study. Peaks: CPU package 83 °C, VRM 61 °C, 45.1 GB used. At least 23 GB was free on the NVMe and 95 GB on the HDD. No stop fired.
- **Storage:** as the protocol says, each average was removed once its binary verified. After the decision, the four screen binaries and their HDD checkpoints were removed. Pins, mass receipts, training reports and traces stay on bb128 under `/home/dberweger/openpoker-short-coverage-20261108/`. The 100M smoke models (7.5 GB) also stay there.
