# Exact binary inference loading

[Proposal #358](https://github.com/dberweger2017/CFR-NLHE-6max/issues/358).
Owner approved implementation and small local qualification on October20.
PR357 measured 2656.51 seconds loading versus 5.72 seconds playing in its cyclic
panel, including reproduction. Existing evaluators already retain two models.
This work targets parsing, decompression, allocations and resident representation.

## Scope and acceptance

Add an optional versioned binary derivative of an unchanged policy export.
Preserve float64 bits, sorted keys, owner/street/action identity, averaging scope,
uniform missing behavior and original average-mass tags when supplied. Bind
source policy/checkpoint SHA256, game/key/menu/card identity, dtype, byte order,
counts, offsets and payload hash. Reject corrupt/truncated/mismatched inputs.
No trainer recipe, released model, default, key schema or policy change.

Start with eager validation and a compact sorted row index plus contiguous
probabilities. No memory mapping or lazy verification is needed for this first
implementation. Binary search can cost more per lookup; measure complete play,
not just startup. Keep the existing gzip export/reader supported.

## Qualification and proposed mature benchmark

Instrument file verification and decompression/parsing/index construction before
conversion. Qualify every stored row bitwise and seeded action/trajectory parity,
including missing and zero-mass rows; test metadata/payload corruption and source
binding. Run a reproducible small local load/lookup benchmark, with conversion
reported separately and no global cache flush.

The mature bb128 benchmark is **not launched** by this PR. Before launch, provide
the owner a runtime/CPU/memory/storage quote using the local measurements and the
historical mature load cost. Proposed fixed comparison: same two mature PR357
policies, three loads per format in alternating order under ordinary warm-cache
conditions, honest first-use observations, full-row parity and the same18-lineup
job including reproduction. Record conversion, time to first action, complete
validation/load and play costs, page faults, RSS, physical/logical bytes and
whole-job wall. Target at least2× median mature warm-load improvement and a clear
whole-job gain with identical trajectories. This is a target, not a measured claim.
Existing PR350/355/357 inputs remain read-only. No new training, large evaluation,
other-host work, schedules, cleanup or automatic merge/default adoption.
