# Prepared-input native river prototype

Owner-approved first deliverable, tracked in issue #372. This standalone CPU
prototype evaluates complete-board, two-seat public betting trees under an
explicit **product-compatible** private range law. It does not construct beliefs
from a blueprint or act in a live hand. Its inputs are hypothetical ranges and
prepared terminal ledgers, never an actual opponent hand or hidden deal.

The implementation will use float64, sorted linear leaf evaluation with card
removal and identical-holding correction, simultaneous linearly weighted CFR,
actual-own-reach averaging, and information-set best-response quality. Existing
Python `RiverGame`/`RiverCFR` remain the reference and are unchanged. Native values,
not exact long-run policy matrices, are the numerical agreement criterion.

Qualification covers small scalar/dense fixtures and fixed river cases, both
seat orientations, ties/blockers/zero mass, invalid inputs, full-sweep staging,
determinism and fixed-work quality/latency curves. Preparation, solving, quality
measurement and process roundtrip are reported separately. Prepared-input speed
is not legal observation-to-action latency; no 15 ms achievement is presumed.

A small bb128 build/test/benchmark may run beside the release upload with two
build jobs and one benchmark thread. It reads no large models or old research
payloads. Shared-host timings are labeled. M1 remains free of heavy compute.
The existing publication process, guards, inputs, environments and jobs remain
unchanged. This work schedules no automatic task and launches no strength study.

Later deliverables separately qualify range construction (including folded-seat
history and range approximations), policy-consistent reuse, native live decision
integration, and fresh paired three-lineage strength. Ordinary local CFR is not a
safe resolving certificate, and subgame exploitability is not whole-game strength.

## Numerical and finite-work quality checks

Leaf values, gradients and averages are compared under **identical supplied
profiles**. One uniform first sweep checks ordinary CFR publication. Later
learned profiles are not required to match: even a second sweep can amplify
rounding of a nearly zero regret. Both implementations evaluate the exact same
native and Python strategies independently before comparing their learned
fixed-work quality curves.

The fixed grid is twelve cases (six public roots, each with 8 and 1,081 holdings
per seat), at 16/64/256 sweeps. Three repetitions check deterministic native
mathematical outputs. The comparison screen remains `max(1e-7 BB, 5% of the
reference exploitability)` at every endpoint. A miss is retained as
`quality-threshold-not-met`; the original grid completes without increasing
sweeps or relaxing the screen. Value/gradient/average/BR disagreement is a
terminal numerical failure. The report separates those two outcomes.

The chance normalizer and identical-holding map currently use allocation-free
quadratic preparation; **leaf evaluation** uses sorted linear passes and
reusable traversal buffers. When compatible chance mass is below `1e-4`, an
explicit scalar fallback avoids cancellation in blocker inclusion-exclusion.
Its result labels that mode; no linear-cost claim applies to that fallback.
Full and compact JSON roundtrips are timed separately. Compact requests return
selected average action distributions without every debug accumulator matrix.
All these times still exclude blueprint belief construction and live adaptation.
