# Deep CFR pilot: results

This is a run of [the pilot protocol](../../neural-deep-cfr.md), committed before the run. It ran on bb128 from commit `b59bc2c1` with the [controller](run.sh) and [guard](guarded.sh), from November 8, 20:22 UTC, to November 9, 12:13 UTC ([stage log](stages.jsonl)).

**The run did not complete as planned.**
- Iteration 310 of 400 stopped on the traversal node limit.
- The final strategy network (20,000 steps at iteration 400) was never trained.
- The owner chose to evaluate the **iteration-300 checkpoint** (4,000 steps) with the planned evaluation, as a declared deviation (see "What happened").

Read every number below with that in mind. This is one seed and one bank, so it is a pilot read, not a gate.

## Reading under the prespecified rule

| Condition | Result |
|---|---|
| No table reads "start better" | **holds:** none of the eight |
| At least one table reads "Deep CFR better" | **holds:** four tables |

Under the protocol this reads **promising**, with four caveats:
- **The checkpoint deviation** described above.
- **Four secondary harm flags at the 3–4-player short tables.**
- **The biggest gains come against passive fields.**
- **The recipe can't currently run to completion.**

The protocol's next step is a three-seed run with step 4's gates. It can't run as is: traversals are deterministic, so a resumed or repeated run reaches the same node limit at iteration 310. Changing how traversal handles very long hands needs a new protocol.

## Primary contrasts

Deep CFR (iteration 300) minus start (step 2's network), both playing every focal decision. All-in adjusted BB/100, 1 bank × 4,096 blocks per field. Decision intervals are Bonferroni 95% over the tables of each group (seven short tables; one deep table).

| Table | Primary field | Change | Decision interval | Verdict |
|---|---|---|---|---|
| `3p-5bb` | mixed | +5.2 | [−0.1, +10.5] | no difference shown |
| `3p-short-deep` | mixed | −4.7 | [−27.9, +18.5] | no difference shown |
| `3p-unequal` | mixed | −10.8 | [−25.8, +4.3] | no difference shown |
| `4p-short-deep` | mixed | −4.0 | [−28.5, +20.5] | no difference shown |
| `6p-5bb` | mixed | +6.9 | [+2.9, +10.8] | **Deep CFR better** |
| `6p-short-deep` | mixed | +42.9 | [+1.3, +84.5] | **Deep CFR better** |
| `6p-unequal` | mixed | +55.3 | [+16.9, +93.7] | **Deep CFR better** |
| `6p-100bb` | trained (#434's peer 10B) | +15.9 | [+1.3, +30.5] | **Deep CFR better** |

Every table and field: [`eval/fields.csv`](eval/fields.csv) and [`eval/results.json`](eval/results.json).

## Secondary fields and harm flags

Harm means a secondary field's Bonferroni upper bound lies below −10, as in step 4.

| Table | Field | Change | Decision interval |
|---|---|---|---|
| `3p-short-deep` | check-call | −48.3 | [−66.4, −30.2] |
| `3p-short-deep` | random | −48.6 | [−80.9, −16.3] |
| `3p-unequal` | random | −28.8 | [−45.3, −12.4] |
| `4p-short-deep` | random | −73.9 | [−108.9, −38.8] |

There are no harm flags at the six-player tables. Elsewhere, against TAG and pot-pressure the changes are mostly small and mostly negative at three and four players. For example, `3p-unequal` against tight-aggressive is −8.4, with a nominal interval of [−12.9, −3.9].

**The big gains are against check-call:**

| Table | Change against check-call |
|---|---|
| `6p-short-deep` | +269 |
| `6p-unequal` | +283 |
| `6p-100bb` | +415 |
| `4p-short-deep` | +86 |

But at `3p-short-deep` the change against check-call is −48. The primary `mixed` field includes check-call seats, so part of the six-player deep primary gain likely comes from playing better against passive opponents. Against the trained field at `6p-100bb`, the one primary field without scripted players, the gain is +15.9.

At `6p-5bb`, against the live copies of the client, the change is −1.8 (nominal [−3.0, −0.5]). That's not a harm flag, but it's adverse.

## How the network plays differently

Shares of focal decisions in the evaluation traces, start → Deep CFR ([`action-mix.json`](action-mix.json); counts summed over fields).

| | Start | Deep CFR |
|---|---|---|
| Postflop checks, every table | 33–41% | 43–48% |
| Postflop pot-size raises, deep tables | 17–22% | 16–17% |
| Postflop min-raises, deep tables | 26–28% | 22–24% |
| Preflop all-ins, `3p-5bb` | 25% | 17% |
| Preflop all-ins, `6p-5bb` | 19% | 14% |
| Preflop calls, 5 BB and three-player tables | 11–15% | 19–24% |

The 6p 100 BB preflop mix barely moves: fold 64 → 66%, call 14 → 14%.

**The Deep CFR network is more passive postflop and calls more preflop at the short tables.**

## What happened

### 1. Iteration 310 hit the traversal node limit

`deep_cfr::NODE_LIMIT` caps one traversal at 50 million nodes so that a runaway tree can't hang the machine. In iteration 310, one of the 20,000 traversals reached it after about 28 minutes. The traversal had started at 01:48:25 UTC and failed at 02:16:28 UTC with `traversal node limit`, and the controller stopped as designed.

External sampling explores all six labels at each of the traverser's decisions, so a traversal's size grows about sixfold with every decision the traverser makes in a hand. The tree had been growing as the strategy moved away from the table:

| Iterations | Mean nodes per traversal | Median seconds traversing | Slowest |
|---|---|---|---|
| 101–125 | 133 | 19 | 29 |
| 126–175 | 167 | 23 | 527 (it150, 822 nodes per traversal) |
| 176–225 | 190 | 28 | 42 |
| 226–275 | 258 | 41 | 233 (it264) |
| 276–309 | 306 | 47 | 100 |

The most likely cause is long re-raising sequences at deep stacks, which give the traverser many decisions in one hand. The failing hand wasn't identified: its root follows from (seed, 310, index), but traversal 310's partial file wasn't analysed.

Per iteration ([`iterations.csv`](iterations.csv)): nodes, samples, traverser value, the time of each stage, the record hashes, the reservoir counters, and every advantage network's loss and hashes.

### 2. The reservoirs were moved to RAM after iteration 122 (plumbing)

Once the strategy reservoir filled at iteration 119, adding samples meant writing to random positions on the HDD. Each add took 965–1,133 seconds instead of 10–14.

After iteration 122 the controller was stopped, and both reservoirs were copied to `/dev/shm`, with a byte-for-byte check against the HDD. The original HDD directory was kept, and the controller was relaunched ([log](move-buffers.log)). Adds then took 6–9 seconds.

This changed no computation: the reservoir files are the same bytes, read and written by the same code.

### 3. The RAM reservoirs were deleted after the stop (plumbing)

When the stopped controller's login session ended, systemd-logind removed the user's `/dev/shm` files, which it does for users without linger. This happened at 02:16:40 UTC, 12 seconds after the stop.

That's why the final strategy network can't be trained now. The HDD copy holds the reservoirs only as they were after iteration 122.

Traversals are deterministic and every advantage network is kept, so the reservoirs could be rebuilt by replaying iterations 123–309. That isn't needed for this report.

### 4. Deviation: evaluating the iteration-300 checkpoint

The owner chose to evaluate `strategy300-s4000`. This is the strategy network the controller fitted at iteration 300:
- 4,000 steps from step 2's seed-1 weights, on the strategy reservoir at iteration 300;
- the planned final network was 20,000 steps at iteration 400.

It was evaluated with the controller's unchanged `evaluation` stage, run through [`eval300.sh`](eval300.sh) on November 9 from 11:00 to 12:13 UTC. That covers the planned tables, fields and roots, plus the scan, the replay, the all-in equity and the report.

## Training

| | |
|---|---|
| Deep CFR iterations completed | 101–309 (209 of 300) |
| Traversals | 4.18 million (889.7 million nodes) |
| Advantage reservoir after it309 | full at 30 million; 165.8 million rows offered |
| Strategy reservoir after it309 | full at 30 million; 396.6 million rows offered |
| Warm start | export 9 min; pretraining 4.7 min; warm buffers 2 min |

**Losses:**
- **Advantage network:** the pretraining fit on the table's regrets ended at a loss of 51.7.
- **Per iteration:** the final loss rose from 87 at iteration 101 to 1,368 at iteration 300 and 1,515 at iteration 309. The training loss is weighted by iteration and fitted to sampled regrets whose spread grows as the strategy moves, so its level isn't comparable across iterations.
- **Strategy networks:** cross-entropy 0.59, 0.65, 0.66 and 0.66 at checkpoints 150, 200, 250 and 300 ([`networks.json`](networks.json)).

**The evaluated network:** `strategy300-s4000.npnet`, SHA-256 `6da3db39…3c14`, 8.8 MB, weights `340a62ac…3947`. Its start is `net1` (`5e276263…b5`).

## Qualification and checks

- **Qualification passed** before any iteration ([`qualification/`](qualification)):
  - native library tests with the K50 tables, paired-arena host tests and the Python tests;
  - the GPU check and the pins;
  - f32 against f64 parity on step 2's network;
  - identical traversal records at 16 and 7 threads.
- **Smoke passed** ([`smoke/`](smoke)).
- **Evaluation integrity:** 88 trace receipts, all hash-matched, with 0 fallback violations ([`receipts.csv`](receipts.csv)). All 88 bank-0 traces replay independently (1,712,128 hands; [`eval/replay-b0.json`](eval/replay-b0.json)).
- **Resources** ([`resources.csv`](resources.csv): time, CPU °C, VRM °C, GPU °C, used MB, free NVMe GB, free HDD GB):
  - peaks: CPU 85 °C, VRM 60 °C, GPU 55 °C;
  - minimums: 36 GB free on the NVMe and 69 GB free on the HDD;
  - no guard stop.

## Compared with step 4 (descriptive)

Step 4 ran the same tables and fields on different roots. At `6p-100bb` against the trained field:
- **Step 4:** network everywhere (`net1`) was about 28 BB/100 behind `six`.
- **Here,** in absolute terms against the trained field:
  - start (`net1`) is −36.6 BB/100;
  - the iteration-300 network is −20.7.

So self-play closed roughly half of step 4's gap at 100 BB. The arms and roots differ, so this isn't a paired estimate against `six`.

## Limitations

- One seed, one bank, and an early checkpoint with a short strategy fit.
- Primary gains at the deep six-player tables lean on passive fields. Harm flags at the 3–4-player short tables show the network losing ground there to random and check-call play.
- The recipe stops at iteration 310 under the node limit. Any rerun needs a protocol that bounds or samples long traversals.
- Warm-start regrets are approximate (see the protocol).
- No live hands. Live play needs the owner's go.
