# Wide-depth models for short Open Poker tables: results

This is a run of [the protocol](../../openpoker-wide-stacks.md), committed before training and amended once before any main training (the dropped copy fields). It ran on bb128 from source `d030095d`, with the [controller](run.sh) and [guard](guarded.sh), from November 6, 10:30 UTC, to November 7, 00:21 UTC ([stage log](stages.jsonl)).

Data files, per run: `results.json` (every field, interval and missing share), `fields.csv`, the model catalog and pins, the training receipts and the independent replay receipt in [`run1/`](run1), [`run2/`](run2) and [`run3/`](run3).

All values are BB/100, all-in adjusted, arm 1 (wide model) minus arm 0 (today's live route), both through the projected view. Run 1 is 4 banks × 4,096 blocks per field; runs 2 and 3 are 1 bank each.

## Routes under the prespecified rules

| Group | Decided by | Verdict |
|---|---|---|
| Heads-up | `2p-3bb`, `2p-5bb`, `2p-8bb` | **`huwide` plays hands with a seat under 10 BB** |
| 3 players | `3p-5bb`, `3p-short-deep`, `3p-unequal` | **`widemix` plays hands with a seat under 10 BB** |
| 4–6 players | `4p-short-deep`, `6p-5bb`, `6p-short-deep`, `6p-unequal` | **`widemix` plays hands with a seat under 10 BB** |

In every group, no table reads "current better", at least one table reads "wide better" and replicates, and no table has a harm flag. 5-player hands follow the 4–6 group without a table of their own, as the protocol states. Changing the live client is a separate PR and needs the owner's go.

## Primary contrasts

| Table | Primary field | Run 1 | Run 1 decision interval | Run 1 verdict | Run 2 | Run 3 | Replicates |
|---|---|---|---|---|---|---|---|
| `2p-3bb` | `wide-copies` | +35.0 | [+33.3, +36.8] | **wide better** | +35.6 | +35.4 | yes |
| `2p-5bb` | `wide-copies` | +45.8 | [+43.3, +48.3] | **wide better** | +43.5 | +44.4 | yes |
| `2p-8bb` | `wide-copies` | +45.0 | [+40.6, +49.4] | **wide better** | +43.9 | +38.5 | yes |
| `3p-5bb` | `mixed` | +29.4 | [+26.2, +32.6] | **wide better** | +28.8 | +31.9 | yes |
| `3p-short-deep` | `mixed` | +29.4 | [+14.1, +44.7] | **wide better** | +14.8 | +17.4 | yes |
| `3p-unequal` | `mixed` | +4.7 | [−4.1, +13.5] | no difference shown | +8.4 | +0.4 | — |
| `4p-short-deep` | `mixed` | +22.2 | [+7.6, +36.9] | **wide better** | +20.1 | +16.6 | yes |
| `6p-5bb` | `mixed` | +54.2 | [+51.5, +56.9] | **wide better** | +53.1 | +53.2 | yes |
| `6p-short-deep` | `mixed` | +40.4 | [+15.8, +65.0] | **wide better** | +46.2 | +13.6 | yes |
| `6p-unequal` | `mixed` | +21.1 | [−1.1, +43.3] | no difference shown | +19.7 | +30.5 | — |

Decision intervals are Bonferroni 95% over the ten tables. All 30 primary point estimates (10 tables × 3 runs) are positive. Runs 2 and 3 have one bank, so their own intervals are about twice as wide: run 2 shows "wide better" on 5 tables and run 3 on 5, and neither shows "current better" anywhere.

**Heads-up:** today's `humix` loses 35–46 BB/100 to `huwide` copies at 3–8 BB, while `huwide` breaks even against itself (run 1: −0.1, −0.3, +0.4). The current route is not just weaker at these depths; it has no trained rows (below).

## Other fields and harm

No table has a harm flag in any run. The closest is `tight-aggressive` at `6p-5bb`: −11.3 [−13.5, −9.1] in run 1, −9.2 in run 2 and −9.9 in run 3, so its upper bound stays above −10 every time.

`tight-aggressive` is the one script the wide models do worse against than the current routes, and it repeats across seeds:

| Table | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| `2p-3bb` | −2.3 | −2.7 | −3.0 |
| `2p-8bb` | −4.0 | −4.4 | −3.8 |
| `6p-5bb` | −11.3 | −9.2 | −9.9 |

Those are the tables whose interval lies entirely below 0 in every run. The same small loss also shows at `3p-5bb`, `3p-short-deep` and `3p-unequal` in run 1. Against `pot-pressure`, `check-call` and `random`, the wide models gain at almost every table. This is the price the rule accepts, but it is the first thing to watch live: tight opponents at very short tables.

## Untrained decisions (run 1)

Share of each arm's decisions with no positive-mass row, the mechanism of the live bust:

| Table | Current: all | Current: preflop | Wide: all | Wide: preflop | Wide: river |
|---|---|---|---|---|---|
| `2p-3bb` | 54% | 24% | 0% | 0% | 0% |
| `2p-5bb` | 95% | 91% | 0.0005% | 0% | 0.01% |
| `2p-8bb` | 35% | 0.05% | 0.002% | 0% | 0.007% |
| `3p-5bb` | 93% | 93% | 7.7% | 0.002% | 56% |
| `3p-short-deep` | 48% | 29% | 2.6% | 0.001% | 17% |
| `3p-unequal` | 10% | 0.2% | 3.9% | 0% | 26% |
| `4p-short-deep` | 34% | 22% | 9.6% | 0.003% | 43% |
| `6p-5bb` | 83% | 78% | 11% | 0.10% | 90% |
| `6p-short-deep` | 25% | 7.6% | 16% | 0.09% | 67% |
| `6p-unequal` | 18% | 2.2% | 16% | 0.12% | 64% |

- **Heads-up:** `huwide` covers essentially every decision; its table never filled (40M entries).
- **3–6 players:** `widemix` covers preflop, where the live bust happened, but postflop gaps remain, worst at six-handed 5 BB rivers (90%). Its table hit the 250M-entry cap and froze at about 283k of 1.21M iterations in all three runs, as `mix` did. Most of the gain at 3–6 players is preflop coverage; the postflop gap is a limitation of this size, not something this study fixes.

## Realized beside adjusted (run 1, primary)

Adjusted and realized agree within about 2 BB/100 at 8 tables. The exceptions are `4p-short-deep` (adjusted +22.2, realized +17.0) and `6p-unequal` (+21.1, +14.0), the two tables with the widest intervals.

## Models

| Model | Run | Entries | Frozen | Train time | Binary |
|---|---|---|---|---|---|
| `widemix` | 1 | 250.0M | iteration 283,474 | 42 min | 14.13 GB |
| `widemix` | 2 | 250.0M | iteration 282,486 | 36 min | 14.13 GB |
| `widemix` | 3 | 250.0M | iteration 284,645 | 37 min | 14.13 GB |
| `huwide` | 1 | 39.6M | no | 43 min | 2.19 GB |
| `huwide` | 2 | 39.7M | no | 43 min | 2.19 GB |
| `huwide` | 3 | 39.7M | no | 43 min | 2.19 GB |

All at 10B nodes. `widemix` is the same size as today's `mix` (14.12 GB) and `huwide` as `humix` (2.16 GB), so deploying one of each in their place does not add memory. The pins (checkpoint, average, mass receipt, binary) are in each run's `*-pins.json`.

## Qualification and checks

- **Qualification** ([receipt](qualification-receipt.json)) passed: native tests, the six-player live-order checkpoint `482a0f8f…`, the live-grid `p5mix` 100M checkpoint `0448ff91…`, and byte-identical `widemix` checkpoints at 16 and 8 threads.
- **Comparison pins:** `humix` `9d39dda9…`, `p3mix` `afddb595…` and `mix` `64c693c4…`, with mass receipts, matched in every run.
- **Independent replay:** all 106 bank-0 traces of every run replayed through the engine and passed.
- **Fallback violations:** 0 in every arena.

## Plumbing

- **Smoke identity stop:** the first smoke arena stopped with "policy/game identity differs". Copies of the current models cannot sit at tables with a seat under 10 BB. The protocol was amended before any main training (see the protocol's Evaluation section), and the smoke rerun passed.
- **Cost:** all-in equity took 4.5 hours for run 1, against "a few hours" planned; the whole run took about 14 hours, against 9–12 hours planned.
- **Thermals:** peak package 83 °C, VRM 61 °C; no stop fired.

## Limitations

- One lineage per run; the three runs differ in training seed and deal roots, not in recipe.
- No 5-player table.
- `widemix` still lacks many postflop rows at short multiway tables (above).
- All opponents are scripts or copies; no live hands were played.
