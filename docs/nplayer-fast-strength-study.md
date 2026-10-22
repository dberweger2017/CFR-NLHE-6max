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
never a strategy, seed, evaluation count or outcome. After selection, run a
fixed120-second fast-mode thermal soak on the excluded qualification seed
before any final training, under the same guards. Record actual nodes,
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
Reserve and commit evaluation roots and input/source manifests before final
training; pin new output model hashes after audits and before evaluation.
Cost qualification must supply a frozen execution quote.

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
orVRM>=85C, missing sensors, ownRSS>24GiB in qualification or80GiB in the full main worker family, availableRAM<8GiB, hostswapgrowth
>256MiB, or freeNVMe<50GB plus the remaining owned output reservation.
Qualification reserves10GB, maximum90min. Main execution reserves32GB and
has a seven-hour malfunction ceiling including qualification; this is a fixed
workload estimate, not work to fill. Measured fit can refuse main admission.
A resource/numerical/accounting/identity failure preserves all evidence and
stops dependent stages without automatic retry. No heavy work on M1/M4.
Research bundles/checkpoints/traces remain ignored and are eventually archived
through the research-cache policy. Retain every original/failure; no cleanup.

## Evaluation root reservation and parallel evaluation

Repository search on October18 found no use of20261018335101–106 before this
reservation. Seed1541 uses roots101/102 for equal-nodes/equal-time; seed1542
uses103/104; seed1543 uses105/106 (full prefix20261018335). Each paired lineup
shares its comparison root. Primary blocks remain8192 per lineup.

Training arms run sequentially to give each recipe its declared host allocation.
After every model audit passes, up to eight independent evaluation cases may
run concurrently. They use separate traces/processes and identical fixed RNG
streams; no outcome is read before the whole matrix is verified. A single
supervised process group owns the batch and enforces80GiB aggregate RSS,
including every native child and Python replay worker. This uses the machine's
RAM and cores during evaluation without changing the statistical sample count.
Qualification retains its24GiB limit. No concurrency with other study training.

## Disk-admission refinement before main work

The first main setup refused its initial disk admission at84.72GB free:
35GB planned growth plus the50GB floor required85GB. No admission receipt,
measurement directory, build child or final training existed. That source/root
and its failure are retained. The fresh setup reduces maximum owned growth to
32GB, keeping the50GB floor and original seven-hour deadline unchanged.
Measured pilot checkpoints are434.63MB at11.82M entries and475.16MB at12.81M.
A conservative planning projection of up to3.6B fast nodes per600s, roughly
58M entries,9 final checkpoint/export pairs,3GB traces and setup/soak files
is about28GB; the32GB cap retains headroom and is enforced continuously.
This is a fit estimate, not a guarantee; unexpected growth stops the study.
No scientific job was retried and no files were removed.

The next setup passed disk admission and built every native executable, but
its new environment used the host's Python3.13 with NumPy1.26.4. Installation
failed before any smoke/final training. Preserve that root too. The fresh
setup uses the existing managed CPython3.11.17 executable (the repository's
supported runtime), creates its own environment, and changes no experiment,
resource ceiling, evaluation count or original deadline. No other environment
is copied or modified.

The Python3.11 setup built and installed successfully, and its instrumented
3M endpoint matched qualification exactly. Export and the first independent
audit ran, but the supervisor mistook the audit's pretty-printed opening brace
for a complete JSONL event. The failed setup is retained before any final seed.
The corrected parser accepts only complete JSON objects as events and keeps
all other CLI output in the log. Required completion/identity gates remain.
A focused regression test covers that distinction; no scientific job is retried.

## Terminal outcome, October 18

The admitted v4 main run hit its thermal stop during the first final fast seed
at12:05:39UTC. Last progress was420,956,111 nodes/87.498 training seconds;
the last accepted resource sample showedCPU68C/VRM84.5C. The crossing sample
was not persisted, so its exact sensor and reading are unavailable. No final
strength evaluation ran. The study is terminal, with no automatic retry,
resource change or default adoption. Its timer is disabled; all roots and
shared inputs remain retained, with archival pending. See the
[terminal report](reports/nplayer-fast-strength/terminal.md) and compact receipt.

## Owner-authorized second attempt, October 18

After reviewing the thermal evidence and the unavailable manual fan control,
the owner explicitly requested a new run with the recommended limits:
**CPU package stop90C; Thermistor15 stop95C**, both immediate hard stops.
This supersedes the no-retry instruction for this one fresh attempt only.
The v4 failure and all setup siblings remain terminal and preserved.

The new root is `bb128:/home/dberweger/nplayer-fast-strength-20261018-main-v5/`.
Retain the original qualification and selected16 threads; all native training,
seeds, node/time endpoints, gzip mode, model inputs, evaluation roots/counts,
verification barriers and statistical decisions stay unchanged. No final
evaluation ran in v4, so the reserved held-out roots have not been evaluated.
Restart the first seed from scratch; do not use its failed partial state.

The original18:31:32UTC deadline,32GB growth/50GB free floor,80GiB familyRSS,
8GiB availableRAM and256MiB swap-growth limits remain. Admission temperatures
remain below70C CPU/80C Thermistor15. Repeat the declared prerequisite smoke,
audits and120-training-second soak under the revised hard stops. No new
qualification scaling or additional experimental arms. A new failure stops
this attempt without automatic retry or further limit increases.

These are owner-selected operating limits, not verified MSI continuous thermal
ratings. Thermistor15 is strongly associated with the VRM/MOS channel; its
exact placement/calibration on MS-7C99 remains unverified. The original sensor
driver and BIOS fan control are unchanged. The unsigned alternative driver
could not load under Secure Boot and was rolled back; no boot change/reboot.

The supervisor now records the exact failing resource sample and names each
thermal sensor that crosses its limit. Generic storage/qualification defaults
remain80/85C; only the explicitly configured new main attempt uses90/95C.

## Completed second attempt, October 18

The frozen v5 attempt completed at14:42:31UTC/16:42:31Madrid, with all19
measured stage return codes0 and no failure. All12 final cases pass,
589824 final hands independently replay and589824 reproduction hands match
exactly before the settled readout. Both predeclared gates pass across all
three seeds: equal-node lower bounds exceed−5BB/100 and equal600s lower
bounds exceed0. See the [full result and limits](reports/nplayer-fast-strength/results.md),
[compact receipt](reports/nplayer-fast-strength/completion.json) and CSV tables.

Total v5 wall102.08min/childCPU9.16h. Fast600s produces2.910–3.004B nodes
versus0.610–0.621B production. MaxCPU74C/Thermistor94C, maximum familyRSS
59.86GiB during evaluation,6.25MiB maximum swap growth; all revised guards
and the original deadline pass. CPU/node efficiency and end-to-end saving
are separate questions: production writerpool1 versusfast16 and six versus
three checkpoint writes affect costs. No held-out roots/counts/endpoints were
changed; all setup failures and v4 thermal stop remain preserved above.

Recommendation: merge #335 as opt-in, retaining production default until the
owner decides adoption. No merge/default/release change is performed here.
Study monitoring is disabled on verified completion. PR335/340 remain open;
Research-Cloud archival is pending, all raw roots/shared inputs retained,
with no archive upload/acceptance or cleanup claimed.

## Owner-authorized merge, October 18

After reviewing the settled results, the owner requested merging #335 and
#340 and posting the results on #335. PR335 merged at15:15:57UTC as
`a846300ed94f297f5d62d0aecd4fc28963ce167f`; `--fast` remains opt-in and
production remains the default. The study branch is aligned with that merged
trainer before #340's final CI. Scientific source, results and checkpoints
remain frozen; no compute or new experiment is launched by this closeout.
[Results comment on #335](https://github.com/dberweger2017/CFR-NLHE-6max/pull/335#issuecomment-6251556909).
