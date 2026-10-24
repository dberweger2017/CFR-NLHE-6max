# Six-player capacity: implementation and engineering qualification

[PR419](https://github.com/dberweger2017/CFR-NLHE-6max/pull/419),
[proposal418](https://github.com/dberweger2017/CFR-NLHE-6max/issues/418),
[fixed protocol](../../nplayer-six-player-capacity.md).

The small exact-source qualification passes. **The 500M-key/10B experiment has
not started; no capacity strength result is available.** One fresh arm remains
proposed against the preserved PR417 250M/10B control, with fixed old 3B opponents.
No trainer, regret math, search, default or release change is included.

## Qualified behavior

Upstream `9b9204c8dccdda255b574cde48fb02d5c761d030` maps to independent execution snapshot
`2ccf21ac608d9729fecea80583ad3f9ee5f34b64`, with 884 tracked source/config
pins. [Compact receipts and costs](qualification.json) bind source, binaries,
configuration, model audits, replay and global proof hashes. Full maps and
original evidence remain on bb128 under
`/home/dberweger/nplayer-six-player-capacity-20261024`.

Local tests pass: 121 native library, 11 paired arena, 1 legacy arena and 32 focused
Python tests; one pre-existing K50 resource test is ignored in the unit suite.
On bb128, native tests/build and 24 focused Python tests pass, then all
**73 qualification stages** return 0. Main fixture: 384 initial hands
plus 384 byte-identical reproductions across eight fields; every initial hand
independently replayed. The separate self-comparison is exactly zero; legacy
three-player 20/100/200 BB traces match and replay.

The fixture also establishes fresh-arm construction; same-cap 16/1-thread and
save/resume equivalence; full-row checkpoint/export/binary audits; identical
serial/parallel and gzip/binary payloads; byte-identical ordinary traces against
the preserved PR417 arena; and unchanged action/RNG trajectories with shared
queries enabled or disabled. Privacy tests vary opponent cards and future cards
without changing the legal-observation fingerprint.

All **884 focal decision occurrences / 1,768 model queries** are retained,
including unchanged actions. The two queried models record 66/82 positive-mass
and 818/802 missing observations, respectively. No arena occurrence has zero mass;
forced-row unit fixtures separately verify zero-mass uniform fallback and its
distinction from missing and positive mass. Their legal menu,
acting-seat fingerprint, original mass status and exact float64 probability
vectors pass independent source/export checking. Both originating-arm strata
remain; no abstract-key deduplication or return-selected subset is used.
These tiny fixtures qualify engineering, not mature throughput or poker strength.
The current completed PR417 proof/report model metadata also agrees and all
protected control/peer paths remain readable. That review uses metadata/stat
pins, not a repeated full-model payload hash; native loads reverify pinned bytes.
The tiny native initial batch spends0.042s playing versus0.033s with diagnostics
off, and about5.1s preparing/loading in either case. Such short windows do not
qualify a mature speed ratio; the fixed quote retains its diagnostic allowance.

Complete qualification wall time: **7.12min**,
including controller/source-validation work. Measured stage wall sum: **3.56min**;
Stage CPU **1.54min**. Build+qualification sampled peak
**1.02GiB**, maxCPU 66°C /
Thermistor 15 58°C. Component commands and costs are retained.
The first build's native checks passed but its planner test compared macOS/Linux
normal-CDF last bits exactly. Build-v1 and failure remain preserved; publishing
planning probabilities to 12 decimals fixes portability. No qualification training
or main science ran in that failed build.

## Complete proposed allocation, not yet accepted

**3.16h central /6.32h reserved;
request 7h on bb128.** The 500M training/row-work/memory estimates remain extrapolations
from PR417, whose costs included owner cleanup. Three tables are resident for the
trained/mixed fields: 500M candidate + 250M control + 250M peer. Peer reload in the last
mixed field is included. The small fixture does not measure mature 500M loading.

| Component and assumption | Central min | Reserved min |
|:--|--:|--:|
| fresh0to10B active traversal;1.5x observed seconds | 45.7 | 91.3 |
| one 500M checkpoint save;2x10B250M save | 4.3 | 8.5 |
| fresh startup/hash residual;2x priorfresh | 1.1 | 2.3 |
| one 500M endpoint export/audit/convert/binaryaudit;2x perendpoint | 48.2 | 96.4 |
| three-model arena plus peer reload initial+repeat;2.5x prior job | 23.0 | 46.1 |
| initial independent replay;1.25x onejob | 7.4 | 14.8 |
| eight paired summaries;1.25x onecontrast | 2.6 | 5.3 |
| global proof/readout conservative wholepriorallowance | 12.4 | 24.8 |
| inline shared-query evidence/readout allowance; unmeasured | 15.0 | 30.0 |
| fresh build/source qualification allowance | 15.0 | 30.0 |
| compact reporting allowance | 15.0 | 30.0 |

The shared-query/readout 900s central allowance remains a planning scenario,
not a measured mature cost. The full result includes one 500M checkpoint, export,
full-row audits, binary conversion, all eight initial/repeated fields, every
initial replay, summaries and reporting. There is no automatic time stop,
sample extension, tuning or scientific retry.

Linear training/arena peaks are 41.3/
55.4GiB; plan 75 GiB, without an RSS guard. Only existing
CPU 90°C / Thermistor 15 100°C/missing-nonfinite thermal resource stops apply.
OwnerSTOP/mutex/correctness failures also terminate the attempt.

The total **120GiB new-storage scenario includes 25 GiB working room**. Estimated
model artifacts are 54.9GiB. Scaling tiny
fixture traces alone gives 11.88 GiB for initial+repeat, versus 10.37 GiB
without shared diagnostics; these are small-fixture scenarios, not bounds on
mature trajectories. Current 419 allocated bytes are 0.31 GiB, leaving
119.69GiB scenario growth against 99.59 GiB actual free: **20.10GiB
additional availability needed at this snapshot**. Existing protected inputs are
already resident. [Resource snapshot](resource-review.json).
No proposed admin reserve change, unverified 500 GB deletion, HDD staging or extra
cleanup gain is counted. Main admission must review fresh actual free space and
remaining growth; 120 GiB is not a live free-space floor or disk kill limit.

## Interpretation frozen before main

4,096 independent fresh deal blocks per field, 12 forward/reverse circular
seatings, 786,432 initial physical hands plus reproduction. Average seatings within
each block; they are not 12 independent observations. One eight-test one-sided
95% Student-t/Bonferroni family: trained-field lower>0, seven script/mixed lower>−5.
Same training seed and 10B node endpoint, not equal runtime; changed capacity can
alter freeze point and subsequent training visitation. Restricted opponent
orders and a single seed remain limitations.

The capacity-pair variance is unknown. Using the older PR417 trained SE 19.48 only
as a normal-reference scenario gives ~11% / ~53% / ~91% primary pass chances at true
+25 / +50 / +75 BB/100; neutral script safeguards can remain unresolved. This does
not promise a small-effect or all-gate verdict. Preserve prior adverse panels,
all new outcomes, coverage, probability differences and tails; no automatic
extension follows an inconclusive result. Shared-state support is descriptive,
not a causal attribution of payoff or proof of sufficient capacity.

Main configuration requires completed same-source qualification, immutable owner
approval of the exact quote/scope, and manual resource review. No approval receipt
or main directory exists. Raw traces/models/failed builds/source/proofs remain
protected on bb128; archival is owner-managed and no research-payload Drive
acceptance is claimed. PR419 remains draft pending the allocation decision.
