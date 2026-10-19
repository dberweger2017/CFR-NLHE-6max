# Three-player pruning: training-time savings versus strength cost

[Proposal351](https://github.com/dberweger2017/CFR-NLHE-6max/issues/351).
**Owner authorized qualification and launch on October19 after the implementation
was returned for review: “Perfect do those things and start the run.”**
The release build and small K50 qualification precede the full study. The frozen
source is`66150f3b5089edc4c4dabf66c2a3a439d565953f`; later evidence commits do
not change its settings. Main run launched October19 at16:41:35UTC after qualification. The owner explicitly
authorized reviewing CI after launch; CI is not a compute-start gate.
[Launch receipt](reports/nplayer-pruning-strength/launch.json).
PR350's cancelled10B campaign remains cancelled; this is a separate experiment.

## Question

How much training time does PR336's optional pruning save, and what playing
strength change comes with that saving at three-player100BB? The purpose is
cheaper training, not an assumed strength upgrade. Measure both signs: pruning
may lose, preserve or improve measured strength. Do not label an unmeasured
change as degradation or demand that it becomes stronger at equal nodes.

The owner selected two sequential comparisons, reusing the existing unpruned3B
reference. There is no new unpruned campaign or parameter sweep.

## Fixed reference and timing

PR350 calibration seed`2026101935003`, actual3,000,011,203nodes and212132outer
iterations. At2,088,867,258nodes the table froze with250,000,475entries (an
iteration-boundary overshoot of the250M cap). Both full-average audits and
calibration replay/reproduction passed; no final strength claim exists.

| Historical reference cost | Measured value | Meaning |
|---|---:|---|
| Active traversal,0→3B |630.740595090997s =10m30.741s| Matched-time target |
| Training-stage wall, summed |3053.4585111550114s =50m53.459s| Two stages including loading/saves/exports/hash |
| Recorded training-stage childCPU |17682.897374s =4h54m42.897s| Includes serialization; not pure traversal CPU |
| Continuation train/save/export sampled peak |22.87GiB| Training command, not evaluator |
| Mature two-model evaluation sampled peak |66.03GiB| Separate evaluation command |

Active time is the sum of each completed `Trainer::step_fast` call. Its0→2B
prefix and resumed2B→3B suffix were measured separately and added. Checkpoint
I/O, reloads, hashing, probes, evaluation, audits, pauses and the stopped waiting
interval are excluded. The old50m53s wall figure has a different save/resume
cadence; it is not a valid direct end-to-end speedup denominator for this study.
[Original timing/proof receipt](reports/nplayer-bb100/continuation-admission-stop.json).

Read-only input root:
`bb128:/mnt/data2tb/research-cloud/PR-350-nplayer-bb100/bounded-20261019-v3/calibration-continuation/`.
Checkpoint`3000000000.gz`, SHA256
`ea0c7dca97ae627b08a39d4196cdd824d6e0767d85ca64c829eae5dcceb2da6b`.
Full-average`3000000000-average.gz`, SHA256
`c602c3727df28160a9807716d3c9211d988e420c33ed7b0c04c2fd899afef06b`.
The new study reads these immutable inputs; it never resumes them with pruning.

## Stage1: fresh pruning to3B

Use the same seed, three100BB stacks,50/100blinds, K50, full float64 averages,
fast8roots/seat,16threads,250M-entry freeze cap and uniform fallback. Fix one
setting before any study hand: `prune-bb=0.05`, `prune-after=200` **iterations**,
as in the contributor's existing pilot. The library retains its one-in20 full
iterations and existing regret/average semantics; this PR changes no regret math.

Train from scratch to the first complete iteration at/above3B visited nodes,
record its cumulative active time, and save the trainer/full average. Compare it
with the saved unpruned3B average on the fixed stage1 matrix below. Audit and
all-hand replay/reproduction must pass before displaying that comparison.

Nodes are not identical units of learning across arms: pruned actions remove
subtrees and change nodes per iteration. Record iterations, pruned actions,
entry growth/freeze point, discard counts and coverage. Pruning can freeze a
different key set from the reference; that is part of its algorithmic effect.
The candidate's own frozen membership must remain stable after its freeze.

## Stage2: continue the same model for the remaining training clock

Let`Tp` be the candidate's cumulative active traversal at3B and
`T0=630.740595090997s` the historical unpruned0→3B traversal.

- If`Tp<T0`, after the first verified strength comparison resume the exact
  pruned3B checkpoint and train for the remaining`T0−Tp` active seconds. The
  accumulated clock is restored from a checksum-bound sidecar; it never resets
  to zero. Save the first complete iteration at/above`T0`, then compare that
  average with the same unpruned3B reference on separate stage2deals.
- If`Tp>=T0`, save the equal-time checkpoint when crossing`T0` on the way to3B.
  Still finish3B and its first comparison. Then evaluate the earlier saved
  equal-time average; no negative-time continuation or duplicate training.

Only active training advances this clock. The final iteration's overshoot is
recorded and must be no larger than that iteration's measured duration. Save,
export, hash, audit, comparison and resume-loading costs are reported separately.
A sidecar binds the cumulative time, budget, node/iteration/pruned-action counts
to the exact checkpointSHA256; configuration and checksum mismatches refuse.

**Stage1payoffs never choose whether to continue.** Poor/inconclusive results
still proceed to the predeclared second comparison unless a correctness/resource
failure or owner stop occurs. No hyperparameter tuning, extra seeds or outcome-
based extension. The matching212132iteration landmark is timed when reached,
without another mandatory large checkpoint, to explain traversal savings.

## Fresh strength comparisons

Each stage has10lineups,8192independent six-hand deal blocks per lineup:

| Pair | Lineups per stage | Comparison |
|---|---:|---|
| Pruned singleton vs two unpruned; reverse orientation |2| Direct oriented strength contrast |
| Pruned and unpruned singleton vs two copies of each of four scripts |8| Paired changes against random/check-call/tight-aggressive/pot-pressure |

Each phase is491520hands plus491520exact reproduction hands; both phases total
**983040hands plus983040reproductions**. Every hand independently replays before
that phase's readout. Each paired lineup shares cards/action roots and rotates
all six seat permutations. Stage1roots20261019351101–105; stage2roots
20261019351201–20261019351205. Both are disjoint from PR350 calibration/probe/final roots.
The native evaluator holds at most two model tables and one K50 set; all20native
passes per phase must prove exactly two policy loads and resident bounds.
Eight independent replay workers run after native play, without policy tables.

Report pointwise95% Student-t intervals clustered by six-hand deal block, plus
Bonferroni95% intervals across the two direct contrasts and separately across
the eight scripted differences. Include per-seat/button-relative-position
returns and missing-information-set coverage. Direct strength is the mean of
the two oriented singleton contrasts, not pooled individual-player return.
Positive return change favors pruning; `strength_cost_bb100` reverses the sign
and interval so positive cost means degradation. Negative cost means a gain.

## Cost readout and decision

Report active seconds saved and speedup at3B, time to the reference iteration
count when reached, matched-time nodes/iterations, actual pruning activity,
checkpoint/export/load/audit/play/replay wall andCPU, sampled peak family RSS,
compressed bytes and complete study wall time. No end-to-end wall speedup is
claimed against a historical reference with different saves/resumes.

This is one host, one fixed seed and a historical timing reference. Thermal/
frequency/load variation and active-wall timer precision limit speed inference.
Pruning may barely activate or incur overhead; retain those results. Zero
pruning activity is not evidence that useful pruning was tested. The owner sees
both strength-versus-time points and chooses whether the tradeoff merits a
separately budgeted multi-seed long campaign. There is **no automatic pass,
pruning adoption, default change, release or long-run launch**. A positive
strength claim still needs its declared interval to clear zero; inconclusive
means inconclusive, not equivalence.

## Implementation, source and resources

`native/hu20-trainer/examples/nplayer_pruning_study.rs` implements the two
endpoints and exact clock-bound continuation. Existing checkpoint/export I/O is
shared with the unchanged-behavior bounded host, with a byte-identity regression.
`scripts/nplayer_pruning_strength.py` builds/configures explicitly, then supervises
the two stages, checks exports, reuses the bounded persistent replay evaluator,
and reports signed strength cost and timing. The old PR350 matrix/load defaults
are unchanged; the reusable batch accepts an explicit frozen matrix/load count.

To isolate pruning from storage changes, the `build` command pins the native
library/arena to PR350's source`b9882e7e728847a58691995e64eabd4563ea0991` and overlays
only the new harness/shared I/O. PR347/compact-key changes are not mixed into the
candidate. The independent controller source, original library files, native
executables and baseline modelSHA256s are pinned. New pruning-header support is
restricted to this study; the old bounded campaign still rejects pruning.

The owner's latest instruction supersedes the earlier resource-budget proposal:
**temperature is the only automatic resource stop**. CPU90°C/Thermistor15100°C
and loss of required temperature readings stop the run and preserve the exact
crossing sample. There is no runtime deadline, RSS/available-RAM threshold,
process-address-space cap, swap guard, disk floor or output-reservation guard.
The study code does not inspect disk capacity or swap use; the owner/agent will
check them manually while it runs. RSS and elapsed time are telemetry only.
The normal/study locks coordinate exclusive compute ownership without polling
or aborting for a busy slot. Manual STOP/signals and owned-child cleanup remain.
Numerical errors, invalid model identities, corrupt data or failed replay still
report a real failed experiment; they are not resource-budget stops.

The3B and630.741s targets are scientific endpoints defining the two comparisons,
not resource timeouts. The finite fixed matrix ends after its declared hands.
Estimates are informational and never create a kill threshold. No arbitrary
admission forecast gates or additional global deadline are introduced.
No fan/OS/other-job changes, M1/M4 science, schedules or automatic retries.

Freeze source/config/cost and record the launch and temperature-only policy
in a new per-PR root and RESULTS_INDEX before science. The owner-authorized
build and qualification use the isolated bb128 control root
`/home/dberweger/nplayer-pruning-strength-20261019`; the main configuration
is created only after qualification. No PR350 root is modified. The cancelled12h/100GiB PR350readmission patch
is separate, retained and undeployed. All old failures/checkpoints stay intact.
New raw models/traces belong in the indexed Research-Cloud per-PR root and eventual
Drive archive; only compact reports/receipts enter Git. No cleanup or upload
acceptance is claimed by this implementation PR.

## Explicit commands (owner approval recorded October19)

```sh
python3.11 -m scripts.nplayer_pruning_strength build /ABS/OWNED/build
python3.11 -m scripts.nplayer_pruning_strength configure /ABS/OWNED/study \
  --build-root /ABS/OWNED/build --tables /ABS/PINNED/K50 --python /ABS/MANAGED/python
# Qualification precedes launch; review CI separately. Configure never runs training.
python3.11 -m scripts.nplayer_pruning_strength run /ABS/OWNED/study
```
