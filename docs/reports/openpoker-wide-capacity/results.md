# A larger wide-depth model for short multiway tables: results

This is a run of [the protocol](../../openpoker-wide-capacity.md), committed before training and not amended. It ran on bb128 with the [controller](run.sh) and [guard](guarded.sh) from November 7, 01:35 UTC, to 12:24 UTC ([stage log](stages.jsonl)).

Data files, per run: `results.json` (every field, interval and missing share), `fields.csv`, the model catalog, `widecap`'s pins and training receipt, and the independent replay receipt, in [`run1/`](run1), [`run2/`](run2) and [`run3/`](run3).

All values are BB/100, all-in adjusted, arm 1 (`widecap`, 400M entries) minus arm 0 (the live `widemix`, 250M), both through the projected view. Run 1 is 4 banks × 4,096 blocks per field; runs 2 and 3 are 1 bank each.

## Routes under the prespecified rules

| Group | Decided by | Verdict |
|---|---|---|
| 3 players | `3p-5bb`, `3p-short-deep`, `3p-unequal` | **the live `widemix` stays** |
| 4–6 players | `4p-short-deep`, `6p-5bb`, `6p-short-deep`, `6p-unequal` | **the live `widemix` stays** |

No table reads "400M better" in run 1, so neither group can switch. No table reads "250M better" either, and no table has a harm flag. No route change and no deploy check follow from this study.

## Primary contrasts

| Table | Run 1 | Run 1 decision interval | Run 1 verdict | Run 2 | Run 3 |
|---|---|---|---|---|---|
| `3p-5bb` | −0.6 | [−3.2, +1.9] | no difference shown | +3.0 | +4.7 |
| `3p-short-deep` | −0.9 | [−12.9, +11.1] | no difference shown | −8.0 | −16.4 |
| `3p-unequal` | −1.9 | [−10.3, +6.4] | no difference shown | +14.4 | −0.9 |
| `4p-short-deep` | −6.1 | [−19.7, +7.4] | no difference shown | −0.8 | −1.5 |
| `6p-5bb` | −0.6 | [−2.3, +1.1] | no difference shown | −0.9 | +0.7 |
| `6p-short-deep` | −22.8 | [−45.8, +0.1] | no difference shown | −24.9 | −31.6 |
| `6p-unequal` | +3.5 | [−17.3, +24.4] | no difference shown | −12.0 | −10.4 |

Decision intervals are Bonferroni 95% over the seven tables. Runs 2 and 3 also show "no difference shown" on every table, with intervals about twice as wide. 16 of the 21 primary point estimates are negative.

**`6p-short-deep` leans against the larger model in all three runs:** −22.8, −24.9 and −31.6. Realized results agree (run 1: −26.8). Run 1's upper bound is +0.1, just short of "250M better", and the one-bank intervals of runs 2 and 3 are wide ([−70.9, +21.1] and [−77.5, +14.3]). It is not a verdict under the rules, but it is consistent across three independently seeded models: at a table with one 3 BB seat and five 100 BB seats, more table entries did not help and may hurt. `3p-short-deep` leans the same way in runs 2 and 3, but not in run 1.

The two pure 5 BB tables, the ones with the largest untrained shares, are flat: every run lies within ±5 BB/100.

## Other fields and harm

No table has a harm flag in any run. Every other field's decision interval contains 0 in run 1 except one: `tight-aggressive` at `3p-5bb`, −1.1 [−2.0, −0.2], far from the −10 margin and not repeated in runs 2 (−0.0) or 3 (+1.0). At `6p-5bb`, where #458's wide models lost about 10 BB/100 to `tight-aggressive`, the larger model makes no difference (−0.2, −0.0, +0.6): the extra entries don't fix that leak.

## Untrained decisions

Share of each arm's decisions with no positive-mass row, run 1 (runs 2 and 3 are within 1 point everywhere):

| Table | 250M: all | 400M: all | 250M: flop | 400M: flop | 250M: river | 400M: river |
|---|---|---|---|---|---|---|
| `3p-5bb` | 7.6% | 5.6% | 11% | 4% | 56% | 50% |
| `3p-short-deep` | 2.5% | 1.1% | 1% | 0% | 17% | 9% |
| `3p-unequal` | 3.9% | 1.8% | 1% | 0% | 26% | 12% |
| `4p-short-deep` | 9.5% | 8.4% | 10% | 7% | 43% | 42% |
| `6p-5bb` | 11.1% | 10.6% | 54% | 53% | 90% | 85% |
| `6p-short-deep` | 16.2% | 15.8% | 40% | 39% | 67% | 64% |
| `6p-unequal` | 16.0% | 15.4% | 39% | 38% | 64% | 61% |

This is the mechanism the study targeted, and the larger table barely moves it where it matters. At three players, river gaps roughly halve at the deep-mixed tables. At four and six players, every street moves by 1–5 points. 60% more entries bought about 3× more iterations before freezing (below), but the six-player postflop key space is far larger than either table. **The six-player postflop gap is not a capacity problem that a bigger table of this kind fixes**, and where coverage did improve (three players), play did not measurably improve.

## Models

| Model | Run | Seed | Entries | Frozen at iteration | Iterations at 10B nodes | Train time | Binary |
|---|---|---|---|---|---|---|---|
| `widecap` | 1 | 20261107910001 | 400.0M | 801,091 | 1,199,808 | 38 min | 22.57 GB |
| `widecap` | 2 | 20261107910002 | 400.0M | 787,426 | 1,205,061 | 39 min | 22.58 GB |
| `widecap` | 3 | 20261107910003 | 400.0M | 794,630 | 1,205,823 | 41 min | 22.58 GB |
| live `widemix` | #458 run 1 | — | 250.0M | 283,474 | — | 42 min | 14.13 GB |

`widecap` would cost 8.4 GB more memory than `widemix` on the client for no measured gain. The pins (checkpoint, average, mass receipt, binary) are in each run's `widecap-pins.json`.

## Qualification and checks

- **Qualification** ([receipt](qualification-receipt.json)) passed: native tests, #458's 100M `widemix` checkpoint `ca8f357b…` unchanged, and byte-identical 100M `widecap` checkpoints at 16 and 8 threads (`26f8a565…`).
- **Comparison pins:** the live `widemix` binary `702e10cf…` and mass receipt `afd951ff…` matched in every run.
- **Smoke:** a 100M `widecap` completed the full pipeline on every table.
- **Independent replay:** all 76 bank-0 traces of every run replayed through the engine and passed.
- **Training checkpoints** moved to the HDD after verification, as planned.

## Plumbing

- **Cost:** 10 h 49 min in all, inside the 10–12 hours planned. All-in equity for run 1 took 3 h 44 min, the longest stage.
- **Resources** (5-second samples): peak CPU package 85 °C, VRM 61 °C; at least 89 GB free on the NVMe and 138 GB on the HDD. No stop fired. Host-wide used memory peaked at 39.9 GB in the samples, well below the 86 GB projection; short training peaks may fall between samples, so this is not a sizing figure.
- **SSH:** the controlling Mac lost its connection from about 02:00 to 08:00 UTC while it slept. The run on bb128 was unaffected.

## Limitations

- One lineage per run; the three runs differ in training seed and deal roots, not in recipe.
- No 5-player table; 5-player hands follow the 4–6 group.
- Only one size was tried. A different key design or a postflop-focused sampler might close the six-player gap where a larger table does not; this study does not test that.
- All opponents are scripts or copies; no live hands were played.
