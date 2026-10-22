# Bounded integration: expectation evaluation from the live arena profile

Owner requested this final evaluation-engineering task on October22,2026 after
PR391. Keep the released v0.6 models, menus, search recipe, fallback and played
strategy frozen. Qualify a cheaper evaluator, not stronger poker play. No
training, earlier-street expansion, off-tree resolving, loader optimization,
new deals or automatic strength campaign.

## Implementation and correctness

At each eligible original search root, let the privileged arena capture a
read-only evaluation view of the profile already solved by WholeHandPolicy.
The view shares immutable profile/model bytes and copies session progress.
Evaluation has no action RNG and cannot advance a solver or mutate the live
session. Player methods continue accepting only acting-seat Observation;
Hand/deck/other holdings stay in the evaluator. Avoid a second model load,
profile reconstruction, copied profile payload or process per root.

Evaluate both actual on/off policies with the existing chance-free float64
walker, unchanged200,000-state/arm/root limit, full positive support and existing
script likelihoods. Preserve branch-local sticky blueprint fallback. Original
quality-fallback roots cancel identical policies explicitly; incomplete values
never become estimates. Include unchanged sampled actions and every root.
Write expectation values/timings separately, keeping sampled replay bytes
unchanged. Default/legacy arena mode without expectations remains supported.

Qualify isolated branch state, zero solver/RNG advances, original profile/row
identity, full expected-value/work equality against frozen PR391 and exhaustive
small fixtures. Require original privileged traces to reproduce exactly at the
same block count, independently replay, and match original PR388 hands. New
measurement source/binary pins are distinct from the frozen reference pins.

## Fixed engineering measurement

Reuse only PR388's six existing main roots and two frozen policies, focal003
and peer601. Initial cost qualification uses the first4 original six-permutation
blocks per lineup,12 on/off cases,4 workers,288 initial hands plus one fresh
288-hand reproduction. No new roots or result-based selection. Compare every
encountered eligible root with its PR391 reference, including unchanged actions;
small fixtures cover isolated/quality/off-tree fallback paths as well.
Report complete model load, play/write including inline expectation, proof and
replay, CPU and sampled RSS/temperatures. Separate expectation-only component
cost from total batch cost; a sub-millisecond component is not a pipeline quote.

Small fixtures/build/tests and this bounded cost qualification are within the
requested engineering task. Publish a measured quote before the larger full
128-block assessment, which needs explicit acceptance rather than borrowing
PR391's budget. If admitted: fixed12 cases ×128 blocks ×6 permutations,9,216
initial hands and one fresh9,216-hand reproduction, all384 original expectation
roots matching PR391, all initial hands independently replayed. No extra
variance fit, fresh strength hands, outcome extension or scientific retry.

All owned measurements acquire the normal compute mutex plus their own mutex.
Only automatic resource stops: CPU90°C /Thermistor15100°C or required missing/
nonfinite sensors. Owner STOP, numerical/information/accounting/parity/replay
failures stop owned children. No elapsed/RSS/disk/swap cutoff; manually inspect
resources. No other-machine compute, fan/driver/environment changes, other jobs,
cleanup, schedules, subagents or deletion. Existing inputs/roots stay read-only.
Use fresh owned source/build/output and retain every failure/partial.

## Final decision

Compare observed variance × measured full pipeline cost with PR388 and the
standalone PR391 path, cold and amortized, separately by lineup. Retain adverse
means, no-intervention panels, uncertainty and sparse-tail concentration. The
primary's observed variance ratio0.414 implies at best about2.4× sample efficiency
before evaluation overhead in this development sample, with substantial tail/
training-seed uncertainty; no order-of-magnitude primary shortcut is assumed.

Use measured work to price a separate fresh, fixed peer-and-scripted strength
comparison, specifying lineups, counts, adjustment families, margins, effect
size and pass chances before playing. Keep sample-count and cost assumptions
explicit; models/seeds not measured here require reserve/calibration. The owner
then chooses a fixed-budget study or defers search expansion. No further
engineering task or strength campaign starts automatically.

Raw traces/models/profiles stay off Git. Publish compact evidence and a report;
stage intended files before the repository artifact checker. Preserve originals
and protected inputs/dependencies. Archive only owned evidence under the
storage policy, and claim acceptance only after a verified receipt.
