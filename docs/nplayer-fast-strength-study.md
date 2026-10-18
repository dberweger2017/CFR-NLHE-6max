# PR335: bb128 fast-mode qualification and strength comparison

Owner-authorized October18 after the PR339 comparison. Extends proposal #337
with a direct equal-training-time comparison. PR335 head b9923248 is applied
onto main06b1e7a5 in an isolated branch. PR336/pruning remains excluded.
No merge, default or release change is authorized by these measurements.

## Fixed preliminary qualification

Review sampling, snapshot/update order, checkpoint resume and the default path.
Build main and candidate release binaries with the same locked toolchain.
Run candidate native library tests. On the real pinned K50 tables, require
main/candidate production checkpoints to match at10M nodes and require fast
checkpoints to match across1/2/4/8/16 threads at3M nodes. Verify fast resume
across thread counts, and reject mismatched recipe/roots. Qualification seed
2026101833500 is excluded from every final strength comparison.

For a more representative scaling measurement, train one fresh fast100M pilot
(eight roots per seat), then independently resume that exact checkpoint to120M
at1/2/4/8/16 threads in forward then reverse order. Compare all ten endpoint
hashes; choose the thread count with the lowest median training time. Ties
within3% choose fewer threads. Pilot results select only runtime configuration,
never a strategy, seed, evaluation count or outcome. Record actual nodes,
iterations, training/save/load/CPU/wall times, process RSS, thermals, fans,
swap, free disk and background archive activity. No final playing results
are inspected during cost qualification.

## Final training and comparisons

Three training seeds2026101541/42/43 and the exact Phase2 three-player20BB
settings:2000-chip stacks,50/100 blinds,K50,menuv1,linear CFR,scope3,
150M-entry ceiling with no freezing. Fast mode uses eight roots per seat;
production uses its original stream recipe. All checkpoints use compatible
gzip. The production reference1B models are the archived, hash-pinned PR292
models. Fast models start fresh; production checkpoints cannot switch mode.

For each seed, train fast from scratch until BOTH the1B-node endpoint and a
600-second cumulative training-clock endpoint have been saved. Save each when
first crossed at a complete iteration; exclude table loading/checkpoint I/O
from the training clock. Train one fresh candidate-build production model
for600 training seconds. This produces an equal-node comparison against the
existing1B reference and an equal-time comparison between the two fresh600s
models. Report end-to-end preparation/save/export/audit costs separately.
No extra milestones, tuning, seeds or outcome-driven extensions.

Each comparison uses both lineups: fast singleton vs two production copies,
and production singleton vs two fast copies. Six seat permutations per block,
8192 independent blocks per lineup. Paired lineups share block deals and
fixed domain-separated action streams; policies see only legal observations.
12 contrasts total:589824 final hands plus589824 reproduction hands.
Replay every final hand in the pinned engine and exactly reproduce every trace
before any result readout. Independently audit every exported probability row.
Reserve and commit evaluation roots and exact model/input/source manifests
before final training; cost qualification must supply a frozen execution quote.

For each seed/comparison, form the paired block statistic
(fast-singleton BB/100 minus production-singleton BB/100)/2. Report the mean
and two-sided95% Student-t interval over independent block statistics.
Equal-node evidence clears the proposal's5BB/100 noninferiority margin only
if every seed's lower bound exceeds-5. Equal-time consistent improvement
requires every seed's lower bound above0. Otherwise report failed/inconclusive
as applicable; no interval narrowing by extra hands. Neither passing result
automatically changes defaults. Report both lineups, per-seat results,
coverage and actual compute costs; no Nash/exploitability claim.

## Admission, coexistence and limits

Owner explicitly permits this compute now and confirms #301 will not start
scientific work. Its archival coordinator may retain the legacy exclusive
mutex. Do not signal, edit, remove its locks or change that process. Acquire
our own /tmp/cfr-pr335-compute.lock nonblocking. Prefer the legacy mutex too;
if held, admit only when its holder is the known #301 archive coordinator,
record its identity and the owner's override. It remains untouched. Log this
coexistence: shared archival I/O can affect timing. Unknown/scientific holder
refuses admission. No other research job may be started by this study.

All16 logical CPUs may be used (eight physical cores); scaling determines the
main training pool size. Parent control uses negligible CPU. No OS/firmware
or cooling changes. AdmissionCPU<70C/VRM<80C; immediate own-group stopCPU>=80C
orVRM>=85C, missing sensors, ownRSS>24GiB, availableRAM<8GiB, hostswapgrowth
>256MiB, or freeNVMe<50GB plus the remaining owned output reservation.
Qualification reserves10GB, maximum90min. Main execution reserves35GB and
has a seven-hour malfunction ceiling including qualification; this is a fixed
workload estimate, not work to fill. Measured fit can refuse main admission.
A resource/numerical/accounting/identity failure preserves all evidence and
stops dependent stages without automatic retry. No heavy work on M1/M4.
Research bundles/checkpoints/traces remain ignored and are eventually archived
through the research-cache policy. Retain every original/failure; no cleanup.
