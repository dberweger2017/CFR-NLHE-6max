# Compact information keys: correctness and bb128 benchmark

Owner-authorized proposal [#343](https://github.com/dberweger2017/CFR-NLHE-6max/issues/343).

Implements the design discussion in [#327](https://github.com/dberweger2017/CFR-NLHE-6max/issues/327).
Owner accepted implementing and benchmarking all three variants on October18:
“Perfect let’s do that now it’s important to do it as efficient as possible.”
The quoted compute allowance is approximately1–2 bb128 hours after implementation,
with a short cost pilot before the full comparison. No overnight run is launched
by this engineering benchmark.

## Why this comes before overnight training

The next intended research campaign builds stronger three-player **20 BB**
blueprints, using three fixed seeds and intermediate learning-curve checkpoints.
It will use fast mode, K50 and full-street averages, with a fixed final node
budget forecast to take roughly an overnight period. Exact targets, checkpoint
cadence and resource reservations must come from measured throughput, table
growth, save/export cost and sustained thermals, not the laptop's1.42–1.52x claim.
A new representation changes checkpoint keys, so existing v1 averages remain
protected reference models; they cannot simply be relabeled or resumed as v2.
Fresh v2 prefixes will establish a matched3B anchor before longer continuations.

The overnight campaign should expose TensorBoard progress: nodes, active and
wall-time throughput, memory, table growth, temperatures, saving and evaluation
overhead, plus per-seed BB/100 curves against random, check-call,
tight-aggressive and pot-pressure controls with uncertainty. Routine telemetry
can update every30–60s. A separate engineering cost check should qualify small
strength probes of a frozen in-memory average policy between complete training
iterations, comparing its decisions to the normal export/loader path. Recovery
checkpoints and monitoring probes need separate cadences. Every1B is a candidate,
not a fixed promise: the current~200s training per1B and~150–165s full saves near3B
would otherwise spend over40% of wall time saving alone. Target monitoring
slowdown below5%, with10% the proposed upper planning allowance, measured with
all resources and evidence processing included. This monitoring work follows
this PR; it is not silently included in its speed comparison.

Monitoring deals will be predeclared and reused for comparable curves. They
are development data, separate from fresh final confirmation deals. The final
checkpoint, seeds and evaluation size will be fixed before training; live curves
will not select a favorable seed or extend the campaign. Final evaluations
should include the current3B references, cross-seed/mixed-policy opponents and
the scripted panel, rotated seats, paired deals, uncertainty and full independent
replay/reproduction. Search, GPU solving and PR336/pruning are excluded.

This benchmark prevents spending that larger budget on a key representation
that changes information sets, loses old-model compatibility, gives no real
speedup on bb128, or incurs unacceptable memory/checkpoint costs.

## Three variants and compatibility

Compare the unchanged v1 encoding, compact+BLAKE2b-128 and compact+xxh3-128.
Keep v1 as the default and preserve its compressed checkpoint bytes. New schema
names explicitly select the encoder/hash across training, checkpoint resume,
export and policy loading. Unknown or mismatched schemas fail closed. The
compact encoding retains blinds and button-relative starting stacks explicitly,
including unequal-stack/button-rotation cases; it removes fields reconstructed
from the complete public action history. Card abstraction, menus, observations,
regret updates, sampling and averaging are unchanged. Hidden cards and seeds
never enter the observation encoder.

## Correctness before performance

- Native regression suite, existing v1 checkpoints/export fixtures and CLI checks.
- Adversarial legal-history tests: calls, short all-ins, folds, checks, repeated
  betting streets, maximum chip values, uneven stacks and every button position.
- Bidirectional v1-to-compact key mapping on legal playouts and training traversals.
- Full row equality after rekeying: actor/street/actions, visit counts, regret
  bits, average bits, total nodes, iterations and counters.
- Cross-thread determinism at1/2/4/8/16 and exact uninterrupted/resumed training.
- Export/loader probabilities and legal actions agree; old v1 fixtures stay exact.

## Workload and declared readout

bb128 only; one excluded benchmark seed2026101832701, three players20BB,
50/100 blinds, K50, full scope3 averages, fast mode/eight roots per seat,
16 threads. Run separate instrumented correctness work; dual encoding and
mapping must not contaminate measured training timings.

First qualify small fixtures and a100M-node cost pilot. Freeze a remaining-time
quote from actual pilot costs with table-growth allowance before main work.
The intended main comparison grows each encoding from fresh to1B and3B, with
saves, then independently resumes each3B snapshot three times for a200M-node
steady-state segment. Rotate the three arm orders across repeats. Each matching
endpoint has the same logical state; repeated resumes have identical bytes within
each schema. A separate audited traversal to3.2B supplies mappings for whole-row
comparisons of all endpoints. Admission requires this full work plus validation
to fit the original two-hour compute ceiling. If it does not, report the measured
quote and preserved pilot; do not silently reduce scientific checks or extend it.

Report active training nodes/s, speedup, CPU seconds, sampled RSS, table size,
load/save/hash time, compressed bytes and end-to-end wall time. Show every repeat
and the median; one seed/host and no cache flush limit inference. Storage timing
is identified by filesystem. Select only after correctness passes, with an
explicit practical assessment of extra xxh3 benefit versus BLAKE2b. No default,
release or overnight admission follows automatically.

## Resources and preservation

Acquire a new study mutex and the normal compute mutex nonblocking. All16 CPUs
are authorized; do not alter other jobs. Preserve existing CPU90C/Thermistor15
95C immediate stops, missing-sensor stop, admission below70/80C,80GiB entire
worker-family RSS,8GiB available RAM,256MiB swap-growth cap and48GiB per-process
address space. Two-hour malfunction ceiling from first compute launch, never
reset. No automatic retry of terminal scientific/resource failures.

Use a new owned root on `/mnt/data2tb` for source/builds/checkpoints/mappings;
retain at least50GB free on both owned filesystem and home NVMe. Reserve100GB
owned growth on the2TB disk; measure rather than assume disk overhead. No
cleanup, model movement, cache changes, fan/driver/OS changes, other machines,
new schedules or unrelated research. Inputs remain read-only. Retain every
failure, raw checkpoint, mapping, trace and source pin; compact reports only in
Git. Research-Cloud archival/acceptance remains pending until separately receipted.
