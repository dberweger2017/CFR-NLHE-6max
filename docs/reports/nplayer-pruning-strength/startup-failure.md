# PR352: completed training, evaluation interpreter failure

The original attempt stopped2026-10-19 at17:22:33UTC before evaluation played
any hands. Both trained snapshots and full-average exports are preserved.
The3B checkpoint passed hash/recipe verification and its independent audit
passed250,000,119rows. No playing-strength result exists.
[Failure and completed-stage evidence](startup-failure.json).

Frozen source`66150f3b5089edc4c4dabf66c2a3a439d565953f`, supervisor517163,
root`bb128:/home/dberweger/nplayer-pruning-strength-20261019/study-v1`.
The failure occurs at the import of the pinned poker engine, before the batch
creates its evaluation directory or starts the native arena. The root and
stage failure receipts remain intact. No thermal stop or guard breach caused
the failure. The supervisor has exited and released its compute locks.

## Completed evidence

-3B:3,000,010,865nodes,212514iterations,631.8955200200134active seconds,
 32,499skipped actions. Historical unpruned3B:630.740595090997seconds.
 The difference is1.154925seconds,0.1831%; no replicated timing claim.
-Equal-time snapshot:2,994,344,973nodes,212096iterations,
 630.7424571240145active seconds. Its overshoot is0.001862seconds, within
 the final iteration's0.003026seconds.
-Native training/export command returned0,2011.21674481s wall,
 13869.018818s child CPU. Model verification and3B audit returned0.
-Evaluation returned1 at startup in0.086s. Zero play/reproduction hands;
 neither final statistical readout has run.

The JSON evidence pins both checkpoint/policy pairs and retains the completed
audit's model lineage. The raw checkpoint/average files are dependencies for
any evaluation-only recovery; do not retrain or discard them.

## Cause and correction

The configuration CLI called`Path.resolve()` on the supplied virtual-environment
Python executable. That followed its symlink to the underlying managed CPython
binary. Invoking the base binary uses its base package environment, which lacks
`pokers` and SciPy. Qualification invoked the virtual-environment executable
directly, so it did not exercise this production configuration boundary.

The correction preserves an absolute executable path without resolving its
symlink. Configuration now probes that exact interpreter for the pinned poker
engine and SciPy statistics before creating a study root, records the environment,
and rechecks it before launching science. No packages, shared environment,
native binary, model or regret/sampling rule were changed.

Three regressions cover the CLI symlink, the exact probe executable, and missing
dependencies refusing before a study root is created. All17 focused tests pass
on bb128, including the Linux child-process test. A separate real-environment
probe confirms the qualified executable retains its venv prefix and pinned
engine commit; the resolved base executable fails dependency import.
[Linux qualification receipt](environment-fix.json).

The fix qualification is isolated at
`bb128:/home/dberweger/nplayer-pruning-strength-20261019/environment-fix-qualification-v1/`.
It contains source/test hashes, tests.log and receipt.json; no study hands or
training ran there. The original frozen deployed source and failed configuration
have not been edited.

## Recovery boundary

No automatic retry or replacement run has started. An evaluation-only continuation
can reuse the two checksum-bound endpoints, preserve the successful3B audit,
and execute the unchanged two held-out matrices without repeating training.
It must record its new source/interpreter identity and link the original failure,
keeping that original root unchanged. No strength outcomes were available to
select a different model, root, sample count or evaluation method.

All raw evidence remains on bb128. Research-Cloud archival and Drive upload
acceptance are pending; no cleanup or upload coverage is claimed.
