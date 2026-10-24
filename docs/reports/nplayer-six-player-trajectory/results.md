# Six-player trajectory: first changes concentrate preflop at supported rows

[PR421](https://github.com/dberweger2017/CFR-NLHE-6max/pull/421),
[proposal420](https://github.com/dberweger2017/CFR-NLHE-6max/issues/420),
[fixed protocol](../../nplayer-six-player-trajectory.md).

**Completed October 24 at 15:34:54 Madrid (13:34:54UTC).** All 24 original input
hashes, 16 panels and 786,432 paired comparisons pass; both complete analyses produce
the same bytes. **87.93%** of first sampled-action changes in 3B→10B and **82.75%**
in 10B→15B start preflop. **99.969% /99.980%** start at positive-mass rows in both
checkpoints. This localizes observed strategy changes; it does not measure their
causal action value or prove that later missing states are harmless.

## All 16 panels

Each panel retains 4,096 independent deal blocks × 12 seatings, including unchanged
hands and zero contrasts. Mean/SE use the deal block, not 49,152 independent hands.
They exactly reconcile with the already verified PR417 summaries. These are
previously inspected outcomes, **not a fresh strength study or new gate family**.
The original PR417 adjusted 40-test decisions remain unchanged.

BB/100; preflop/later contributions are additive whole-hand return partitions
by the first changed sampled action. Percent preflop is among changed hands.

| Contrast | Field | Existing delta | Block SE | Hands changed | First change preflop | Preflop contribution | Later contribution |
|:--|:--|--:|--:|--:|--:|--:|--:|
| 10b-15b | call-pressure | -20.32 | 14.43 | 14.85% | 84.50% | -25.33 | +5.01 |
| 10b-15b | check-call | -16.87 | 21.42 | 13.40% | 94.50% | -17.55 | +0.68 |
| 10b-15b | pot-pressure | -12.87 | 8.63 | 12.95% | 78.18% | -11.98 | -0.90 |
| 10b-15b | random | +18.74 | 16.18 | 11.53% | 97.99% | +18.32 | +0.43 |
| 10b-15b | random-tight | -16.14 | 8.49 | 15.03% | 73.67% | -6.85 | -9.30 |
| 10b-15b | tight-aggressive | +8.72 | 5.51 | 12.05% | 76.28% | +5.69 | +3.02 |
| 10b-15b | trained | -2.19 | 12.87 | 13.92% | 80.54% | +1.31 | -3.50 |
| 10b-15b | trained-call-pressure | +33.05 | 15.31 | 16.11% | 79.37% | +37.57 | -4.52 |
| 3b-10b | call-pressure | +35.31 | 21.71 | 30.04% | 88.38% | +38.00 | -2.68 |
| 3b-10b | check-call | +3.40 | 29.89 | 26.11% | 93.45% | +6.68 | -3.28 |
| 3b-10b | pot-pressure | +79.89 | 14.84 | 27.55% | 85.59% | +72.27 | +7.61 |
| 3b-10b | random | -5.99 | 26.42 | 27.71% | 98.30% | -5.53 | -0.46 |
| 3b-10b | random-tight | -5.39 | 13.09 | 31.09% | 82.68% | -4.47 | -0.92 |
| 3b-10b | tight-aggressive | +21.19 | 9.88 | 25.07% | 83.00% | +20.24 | +0.95 |
| 3b-10b | trained | +46.19 | 19.48 | 31.09% | 87.29% | +34.52 | +11.67 |
| 3b-10b | trained-call-pressure | +49.05 | 23.16 | 32.44% | 85.65% | +44.01 | +5.04 |

Across the eight fields,3B→10B changes 113,599 of 393,216 paired hands; 99,885 first
changes are preflop and 113,564 are positive→positive.10B→15B changes 53,987 hands;
44,675 first changes are preflop and 53,976 are positive→positive. Every unchanged
path has zero return difference. The few zero→positive changes remain included.
Identical uniform fallback at both checkpoints cannot itself produce the first
different sampled action under the matched RNG; the qualification tests enforce
that invariant. It does not imply unsupported continuations have no value effect.

## What the decomposition says

For 3B→10B against the trained field, ** +34.52 of +46.19** is associated with
preflop-first-divergent paths. First call→fold and raise→fold groups contribute
+16.11 and +14.84; other groups offset and add to these. Against pressure,
call→fold and raise→fold groups contribute +32.11 and +37.34 of the +79.89 total.
Against random, however, the same two groups contribute −29.24 and −9.59;
fold→call(+21.56) and raise→call(+15.12) offset much of that, leaving −5.99.
Thus an aggregate fold/check rate cannot settle the exploitation tradeoff.

For 10B→15B, the mixed trained/call/pressure field's +33.05 is associated with
preflop-first-divergent paths(+37.57), offset by later paths(−4.52).
The trained field remains −2.19 overall: preflop +1.31, later −3.50. This does not
rescue the earlier inconclusive marginal-training result. Likewise the
check-call panel's −16.87is mostly associated with preflop-first paths(−17.55).

These categories partition **whole-hand returns**, not local counterfactual
utilities. After the first changed action, all later actions/histories can differ;
selection into a group is policy-dependent. A call→fold group with a positive
contribution does not establish that folding was optimal on those observations.
Do not infer Nash convergence, opponent adaptation, universal superiority or
recoverable thin value from this accounting.

Missing continuations still occur after supported first changes. In trained
3B→10B changed hands, 9,060 have no later focal missing lookup in either arm;
1,572 only in 10B, 3,334 only in 3B, 1,317 in both. The10B→15B mixed-trained field has
609 neither /1,087 only15B /2,211 only10B /4,013 both. Those are different reached
histories, not a controlled support intervention. They cannot attribute terminal
return differences to missing keys. [All partitions](partitions.csv) include
street, lookup pair, action pair, raise-size direction, position and later exposure.

Matched-prefix unchanged actions and all reached actions use separate counters
in [compact results](results.json). Reached action frequencies have different
post-divergence denominators; first changed sampled action does not reveal the
first difference between probability distributions. No mature policies were loaded.

## Actual cost and proof

The finite job waits for PR419's source-I/O clearance from 12:18:46 to 13:27:33 UTC:
**68m47s**, separately recorded,0.050 child CPU seconds and no normal M4 compute
mutex held. It uses one kernel pidfd exit event, no periodic polling or timer.
Only after PR419 completes does it acquire the ordinary M4mutex and read source data.

| Component | Wall s | Child CPU s | Recorded child peak RSS |
|:--|--:|--:|--:|
| M4 transfer | 238.30 | 55.56 | 213.77MiB |
| Independent destination SHA readback | 2.92 | Not separately measured | Not separately measured |
| First full scan | 98.36 | 98.36 | 21.16MiB |
| Repeat full scan | 101.44 | 101.43 | 21.20MiB |

**Active operation 7m21.02s**, versus 13.6 min central /32 min reserve /45 min accepted.
That includes copy, destination hashes, both scans and final equality/reference
barriers; publication work is separate and not silently counted as zero.
M4child CPU total 255.40s includes transfer and the tiny dependency wait, but not
unmeasured parent/hash CPU. The bb128sender independently records 238.09s wall,
32.88s CPU and 18.26MiB peak RSS; its time overlaps the transfer row and is not added
to active wall. Source block input 15,607,808 (512-byte units), no block output.
One capped 32MiB/s stream transfers 7,989,712,885 bytes over confirmed Ethernet;
source metadata remains unchanged. Two scans each read 10,641,416,174 bytes because
the 10B files participate in both contrasts. No new poker hands, model loads or
training occur. Native PR417 replay proofs are provenance; this is not a second
engine replay. Scan-derived SHA/count/mean/SE/lookup/group reconciliation is new.

Qualified scanner source`ed5ac7804c97e12a6bd50f3aaa133703c637e55e`, existing M4
Python 3.11.14, ordinary mutex plus own study mutex. Config
`d022f932a9aac337e6dae5e83537dfd07d912834b8f94998fb23b5015ec8d398`;
inventory`dcdbda4b1b8ff93529b080df3d9721f0fb569409c05c61d2a6a76bc78bf5da8b`;
raw deterministic result`f4a408f1c2ddc9d4af9d4d080eace57d4d184d6c649b6522a5811996644a2267`.
Both output digests match and all 24 destination hashes agree with recorded replay
proofs. The original PR417 result remains
`361e40b70f195d578592d1155738340917d753fdd2cbd3866236adee3bd3e5c1`.
[Panel CSV](panels.csv), [complete compact proof/cost/partition summary](results.json).

## Decision and preservation

This supports focusing a future concrete mechanism test on **supported preflop
strategy changes and their later support**, rather than assuming river fallback
alone explains the training trajectory. It does not select a policy change or
authorize new samples, action-value evaluation, capacity, training, search or
release work. PR419 separately measures capacity on fresh deals. Retain all four
PR417 checkpoints and the original adjusted-strength conclusions.

Ordinary inputs/source/results/failures/proofs remain at
`m4:/Users/dberweger/Local/cfr-six-player-trajectory-diagnosis-20261024/`;
original traces remain at
`bb128:/home/dberweger/nplayer-six-player-candidate-20261023/main-v1/`.
No model/repeat trace transfer, raw JSONL in Git, deletion or research-payload
Drive acceptance is claimed. The owner cleaner later packages completed stable
evidence on bb128 HDD as verified ZIP sets with relative paths, complete manifests
and retrieval instructions. The initial engineering packaging failure is retained.
Both finite controllers have exited; no timer, observer or scientific retry remains.
