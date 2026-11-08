# The network at every decision: results

This is a run of [the protocol](../../neural-policy-everywhere.md), committed before any implementation run or arena hand. Its one amendment, the Gate D trained field, was made before any run. It ran on bb128 on commit `45752b8a` with the [controller](run.sh) and [guard](guarded.sh), on November 8 from 12:42 to 19:55 UTC ([stage log](stages.json)).

The three step-2 networks were used exactly as trained, with no retraining or tuning. Run *k* uses network *k*.

Data files:
- **Per run** ([`run1/`](run1), [`run2/`](run2), [`run3/`](run3)): `results.json` (every field, interval, absolute result per arm and untrained share), `fields.csv`, the model catalog and the independent replay receipt.
- **The decision:** [`decision.json`](decision.json).
- **Agreement:** [`run1/agreement.json`](run1/agreement.json), computed after the run by [`agreement.py`](agreement.py) (see below).
- **Smoke:** [`smoke/`](smoke).
- **Qualification:** [`qualification/`](qualification).
- **Binary hashes:** [`binaries.sha256`](binaries.sha256).
- **Resource samples:** [`resources.csv`](resources.csv), with columns time, CPU °C, VRM °C, used MB, free NVMe GB and free HDD GB.

All values are BB/100, all-in adjusted, arm 1 minus arm 0, over blocks.
- **Arm 1** plays the network at every focal decision.
- **Arm 0, Gate S:** the live client (`widemix` through the projected view, with the `net1` fallback, as #470 routes it).
- **Arm 0, Gate D:** `six`, #431's live-order 10B, in the native view.

Run 1 is 4 banks × 4,096 blocks per field; runs 2 and 3 are 1 bank each.

## Verdict under the prespecified rules

| Gate | Condition | Result |
|---|---|---|
| **S** (seven short tables) | no table reads "table better" | **fails:** `6p-5bb` reads "table better" in run 1 |
| | at least one "network better" that replicates | holds: `3p-5bb` (+2.4, then +1.3 and +3.8) |
| | no harm flag | holds |
| **D** (6 players, 100 BB) | run 1's lower bound on `trained` above −10 | **fails:** −37.2 |
| | runs 2 and 3 above −10 | **fail:** −27.4 and −27.9 |
| | no harm flag (check-call exempt) | holds |

**Both gates fail.** Under the protocol's table of outcomes, the tables stay on every route. The intervals below are step 5's baseline: the gap a network has to close before it can replace a table. This study changes no route or default.

## Gate S: primary contrasts (`mixed` field)

| Table | Run 1 | Run 1 decision interval | Run 1 verdict | Run 2 | Run 3 |
|---|---|---|---|---|---|
| `3p-5bb` | +2.4 | [+0.6, +4.2] | network better | +1.3 | +3.8 |
| `3p-short-deep` | +4.4 | [−6.0, +14.8] | no difference shown | +0.6 | −1.5 |
| `3p-unequal` | −5.4 | [−11.8, +1.0] | no difference shown | −3.4 | −5.4 |
| `4p-short-deep` | −2.6 | [−13.5, +8.4] | no difference shown | −0.9 | −7.9 |
| **`6p-5bb`** | **−1.6** | **[−2.6, −0.5]** | **table better** | +0.7 | +0.3 |
| `6p-short-deep` | −7.5 | [−26.3, +11.2] | no difference shown | −13.2 | +26.5 |
| `6p-unequal` | +2.3 | [−14.2, +18.8] | no difference shown | −14.2 | +4.6 |

Decision intervals are Bonferroni 95% over the seven tables.

- **`6p-5bb` alone fails Gate S,** and only by a small margin. Its upper bound is −0.5, and runs 2 and 3 read +0.7 and +0.3. The rule uses run 1, so it stands. Even so, a network that ties the table at 5 BB isn't the replacement the gate looks for.
- **`3p-5bb` is the one clean win:** about +2.5 BB/100, replicated.
- **`3p-unequal` leans negative in all three runs** (−5.4, −3.4, −5.4), but no single run shows a difference.
- **The deep six-player tables are noisy.** Their one-bank intervals are 70–75 BB/100 wide, and the runs disagree in sign.
- **Realized results agree with the adjusted ones** within about 5 BB/100 in run 1, except at `6p-short-deep`: −13.9 realized against −7.5 adjusted.

**Absolute, run 1, all-in adjusted, against `mixed`:**

| Table | Live client | Network everywhere |
|---|---|---|
| `3p-5bb` | +22.3 | +24.7 |
| `3p-short-deep` | +58.6 | +63.0 |
| `3p-unequal` | +74.1 | +68.7 |
| `4p-short-deep` | +86.4 | +83.8 |
| `6p-5bb` | +25.0 | +23.5 |
| `6p-short-deep` | +142.3 | +134.8 |
| `6p-unequal` | +145.8 | +148.0 |

## Gate S: other fields

No table has a harm flag in run 1. Run 1's lowest other-field decision bound is −19.2 (`check-call` at `3p-short-deep`). The lowest point estimate, −8.6, is in the same place, so the bound reflects width rather than a loss.

| Field | Pattern across the three runs |
|---|---|
| `pot-pressure` | −5.3 to +8.0; run 1's `3p-5bb` (−1.1) and `6p-5bb` (−0.8) intervals lie below 0, but above the −10 margin |
| `tight-aggressive` | −7.9 to +4.1; mostly within ±3 |
| `check-call` | +13.5 [+3.0, +24.0] and +22.9 at `4p-short-deep` (runs 1–2), −2.1 in run 3; elsewhere −23 to +10, with wide intervals |
| `random` | −38 to +30, with wide intervals |
| `live-copies` (6p) | −5.9 to +0.9; run 1's three are −0.4, +0.9 and −2.8 |

**`check-call` at the deep six-player tables,** step 3's open question:

| Table | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| `6p-short-deep` | +0.8 [−7.5, +9.2] | −0.0 [−28.3, +28.3] | −23.1 [−52.5, +6.3] |
| `6p-unequal` | −5.5 [−13.3, +2.2] | −8.8 [−33.9, +16.2] | −16.2 [−43.9, +11.5] |

Run 1 shows no difference at either table, and the one-bank runs lean negative inside wide intervals. It's still unresolved.

## Gate D: 100 BB six-handed

| Field | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| **`trained`** (primary) | **−29.4 [−37.2, −21.6]** | **−27.4 [−43.8, −11.0]** | **−27.9 [−43.6, −12.2]** |
| `pot-pressure` | −6.2 [−15.9, +3.5] | −13.0 [−32.7, +6.8] | −16.7 [−35.2, +1.9] |
| `tight-aggressive` | −1.5 [−8.3, +5.3] | −10.2 [−24.0, +3.6] | −6.7 [−21.1, +7.7] |
| `check-call` (exempt) | +40.9 [−8.1, +89.8] | −13.8 [−108.6, +81.0] | +32.0 [−69.8, +133.8] |
| `random` | +46.2 [+18.9, +73.6] | +48.7 [−5.9, +103.2] | +38.4 [−15.2, +92.0] |
| `mixed` | −8.6 [−37.8, +20.7] | −12.2 [−69.2, +44.9] | −15.8 [−73.6, +42.0] |

The primary interval is the two-sided 95% interval, so its lower bound is the protocol's one-sided 97.5% bound. Other fields carry Bonferroni 95% intervals over the five of them.

- **The network is clearly worse than `six` at 100 BB.** That holds on all three network seeds, by 27–29 BB/100.
- **In absolute terms, against the trained field:** `six` makes +2.3 and the network −27.2. Realized: −0.7 and −27.3.
- **It's worse against the solid fields too:** `pot-pressure` in all three runs, and `tight-aggressive` in all three.
- **It does better against `random`,** in all three runs. That's the profile of a policy that's looser than its opponent's equilibrium, with an edge only against a field that punishes nothing.

## Agreement: where and how much the arms differ

Arm 0 plays a positive-mass row wherever it has one, and arm 1 plays the network there instead. That's where the arms differ. The table below gives that share of focal decisions, and the network's total variation (TV) from the row at those decisions.

Measured on run 1's arm 1 traces, all four banks, for the primary field. The full table, by table, field and street, is in [`run1/agreement.json`](run1/agreement.json).

| Table | Differ: all | TV: preflop | TV: flop | TV: turn | TV: river |
|---|---|---|---|---|---|
| `3p-5bb` | 97% | 0.039 | 0.34 | 0.30 | 0.34 |
| `3p-short-deep` | 99% | 0.031 | 0.22 | 0.22 | 0.22 |
| `3p-unequal` | 99% | 0.018 | 0.23 | 0.23 | 0.24 |
| `4p-short-deep` | 99% | 0.020 | 0.20 | 0.20 | 0.20 |
| `6p-5bb` | 88% | 0.059 | 0.34 | 0.25 | 0.13 |
| `6p-short-deep` | 87% | 0.059 | 0.26 | 0.28 | 0.28 |
| `6p-unequal` | 87% | 0.060 | 0.27 | 0.28 | 0.28 |
| **`6p-100bb` (`trained`)** | 100% | **0.194** | 0.29 | 0.29 | 0.28 |

- **At the short tables the network matches the table closely preflop.** TV there is under 0.07 against every scripted and copy field, and up to 0.17 against `random`. Postflop it differs by mostly 0.15–0.34.
- **At 100 BB it differs preflop too: TV 0.19–0.32 across the fields.** The networks imitate `widemix`, which trained on the wide depth grid, not `six`'s equal 100 BB stacks.
- This is descriptive, not a decomposition of the chip loss. Still, a preflop gap of this size against `six`, whose preflop rows are learned at almost every decision, fits Gate D's loss. The protocol's limitations said as much: a miss here says little about a network trained at 100 BB.
- **The traces only record the row where arm 1 played,** so these shares are along arm 1's path. The agreement script was written after the run. It reads the traces as they are and changes no result.

## Qualification and checks

**Qualification** ([receipt](qualification/receipt.json)) passed:
- native library tests (189) and paired-arena host tests (19), including the new `network-all` and live-copy tests, plus 22 Python tests ([log](qualification/native-tests.log));
- with the new code, #469's 38-case smoke manifest reproduced its 76 traces byte for byte ([comparison](qualification/repro-compare.txt));
- service and arena agree on the network fallback ([receipt](qualification/fallback-parity.json));
- the `widemix`, `six` and peer 10B binaries, their mass receipts and the network pins match.

**Further checks:**
- **Smoke:** run 1's network completed the full pipeline on every table at 64 blocks per field.
- **Trace checks:** every arm 1 decision carries a network distribution, and every action played is legal with positive probability there. There are 0 violations in all 616 receipts, across the three runs and the smoke.
- **Independent replay:** all 88 bank-0 traces of each run (1,712,128 hands per run) replayed through the engine and passed.

## Plumbing

- **Cost:** 7 h 13 min in all, under the 8–10 hours planned.
  - **Run 1's all-in equity** took 4 h 8 min, the longest stage.
  - **An arena bank,** with its scan, took 8–9 min for all 16 cases, both arms, at 16 threads.
  - **Forward-pass cost:** not timed separately here. Step 3 measured 1.8 ms per decision on the f64 path this study uses; #471's f32 path is about 50× faster on the same network.
- **Resources** (5-second samples):
  - peak CPU package 89 °C, in two samples, 1 °C under the stop; VRM peaked at 61 °C;
  - at least 41 GB free on the NVMe and 135 GB on the HDD;
  - host-wide used memory peaked at 17.2 GB.

  No stop fired, and the GPU wasn't used.
- **Not in the controller:** the protocol's agreement statistics weren't computed by the controller. They were computed afterwards from the traces, as described above.
- **No failures or retries.**

## Limitations

- **The networks imitate `widemix`,** so Gate D tests generalization from wide-grid rows to equal-stack 100 BB play. It doesn't test a network trained at 100 BB.
- **One recipe, three seeds.** The runs differ in network seed and deal roots, not architecture or training.
- **There's no 2-player or 5-player table.**
- **The opponents are scripts and copies,** with no live hands. The 6p tables' `live-copies` field is the closest to a real field.
- **Runs 2 and 3 are one bank each,** so their deep-table intervals are wide.
