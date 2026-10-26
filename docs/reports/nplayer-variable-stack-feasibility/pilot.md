# Fixed variable-stack pilot: affordable mechanics, sparse postflop support

The owner-approved M4 pilot is complete. The single fresh lineage reached all
three fixed endpoints, and every export/binary audit, play reproduction and
independent replay passed. **This establishes bounded engineering feasibility;
it does not establish playing strength.** No further training was launched.

[Results and proofs](pilot-results.json) · [costs](pilot-costs.json) ·
[accepted admission](pilot-admission.json) · [provenance](pilot-provenance.json) ·
[all tuple summaries](pilot-tuples.csv) · [all common-panel cells](pilot-common-panel.csv) ·
[all learning cells](pilot-learning-cells.csv) · [played support](pilot-played-support.csv).

## Frozen scope and proof

Three players, 50/100 blinds, K50, production action menu, independent uniform
starting stacks from {20,50,100} BB and an independent uniform button. All 27
ordered tuples remain in every report. Seed 20261026441011, two workers,
10M-key whole-iteration freeze, fixed 5M→25M→100M nodes. The qualified native
source is `4f3a9183`; the frozen Python supervisor/source snapshot is `f76e42d0`.
The native Rust sources are identical across those snapshots. Configuration,
owner approval, executable, original qualification, Python, thermal helper and
K50 pins passed before and after execution. The postqualification executable-
hash timing caveat remains recorded in the original qualification report.

At each endpoint, every retained row passed float64 average-to-binary checking.
The fixed 81-hand played panel covered every tuple/button combination. All
**243 initial hands and 243 repeated hands** independently replayed against the
pinned engine; each endpoint's initial/repeat trace hashes matched. There were
563, 586 and 536 decisions in the three initial panels, respectively. Native
endpoint receipts originally said independent replay was pending; the outer
COMPLETE and six successful replay receipts close that barrier without rewriting
the historical native receipts. All seven guarded stages returned zero. Normal
and study locks were free at handoff.

## Growth and what continuation can change

| Target | Actual nodes | Retained rows | Active training | Common positive / zero / missing |
| --- | ---: | ---: | ---: | ---: |
| 5M | 5,001,133 | 2,876,747 | 1.69s | 873 / 108 / 2,093 |
| 25M | 25,004,642 | 10,003,912 | 7.08s added | 1,473 / 98 / 1,503 |
| 100M | 100,008,602 | 10,003,912 | 26.61s added | 1,541 / 30 / 1,503 |

The protective threshold froze membership at iteration 2,029, with 3,912 rows
of whole-iteration overshoot. The last recorded pre-freeze progress sample is
18,061,225 nodes and the first recorded frozen sample is 18,952,344 nodes. This
brackets the freeze; it does not locate its exact node count. Pre-cap growth
was still substantial: about 0.574 retained rows/node at 5M and 0.547 cumulative
rows/node at the last pre-freeze sample. Later flat membership is imposed by
the cap, not evidence of natural saturation.

On the same 3,074 common observations, missing counts remain exactly unchanged
from 25M to 100M. Positive mass rises by 68 as zero-mass rows acquire mass.
Continuation therefore improves support *within the retained membership* on
this panel, while being unable to admit its remaining missing keys.

The common panel was fixed before training: 324 synthetic hands, balancing
tuples/buttons and uniform-menu/check-call continuations. Its observations are
not a population-weighted sample. The representation counts stay 2,962
stack-owner keys versus 2,094 legacy live-order keys, with 559 legacy-key splits
and no stack-owner/exact-history merges observed on this panel. That warns
against assuming compact-table savings automatically transfer to this exact-chip
reference representation; it does not measure general abstraction quality.

## Street, tuple and learning findings

| Street, 100M fixed panel | Positive mass | Zero mass | Missing | Observations |
| --- | ---: | ---: | ---: | ---: |
| Preflop | 1,006 | 10 | 234 | 1,250 |
| Flop | 436 | 7 | 304 | 747 |
| Turn | 94 | 11 | 462 | 567 |
| River | 5 | 2 | 503 | 510 |

The river limitation is particularly clear: **98.63% of this panel's river
observations miss**, and only 0.98% have positive mass. This is not an estimate
of the frequency of river fallback in ordinary play. The separate 81-hand
self-play panels change their trajectories with the policy: positive-mass
lookups rise from 203/563 to 333/586 to 336/536, but those changing denominators
cannot isolate a support improvement on identical histories. Their settled
multi-pot counts are 2, 4 and 2; provisional contribution-layer exposure in the
common-panel CSV is a distinct measure.

All tuples were sampled. There are 269,136 cumulative training roots at 100M,
with 9,808–10,216 per ordered tuple. Actual button counts, every tuple's support
and all 972 endpoint/tuple/seat/street cells remain published; sparse and zero-
denominator cells are retained. Broadly balanced root exposure does not imply
balanced useful learning at later histories.

At 100M, 6,188,917 of 10,003,912 retained rows have no traverser visit; 706,785
have at least two visits, and 2,769,450 have zero average mass. From 25M to 100M,
480,794 previously unvisited retained rows receive a traverser visit, while
zero-average-mass rows decline by 284,352. These quantities describe different
parts of the learner. They do not by themselves prove harmful admission waste,
convergence or playing benefit: opponent-only averaging has a separate purpose,
and final zero regrets can include cancellation.

Of the 2,962 predetermined watch keys, attempted positive-weight traverser
contributions reach 394 at 5M, 905 at 25M and 1,486 at 100M. At 100M, 1,027 have
repeated attempts; median nominal weight ESS among reached keys is 2.43.
**These are attempted root-aggregated updates, including discarded deltas after
freezing. They must not be described as 1,486 successfully learned retained
rows.** The ledger reports 41,745,959 declined root-key contributions at 100M;
these are not unique missing states. Native discarded-key counts differ because
they count merged iteration deltas rather than the observer's per-root deltas.

The nominal ESS is a weight-concentration diagnostic under adaptive policies,
not independent statistical sample size. Nonzero aggregate regrets, visits and
average mass are not interchangeable. Pathwise zero-target-reach and numerical-
underflow attribution remain explicitly unimplemented. Raw watch records,
including never-reached keys, are retained outside Git.

## Complete measured cost

The original quote extrapolated an entire tiny fixture into both training and
row-processing proxies: 19m59s central / 57m53s reserve, with a 60-minute owner
allocation. **Actual supervised pilot wall time was 141.45s (2m21s)**. This large
forecast error shows how conservative and immature the original proxy was; it
does not justify carrying this capped-table speed to a mature uncapped study.

| Measured component, summed across endpoints | Seconds |
| --- | ---: |
| Active training, including read-only observer | 35.38 |
| Checkpoint saves | 29.44 |
| Average exports, including checkpoint pinning | 19.67 |
| Binary conversion | 20.01 |
| Full-row binary verification, including binary pinning | 20.09 |
| Binary loads | 5.08 |
| Play, reproduction and endpoint diagnostics | 1.39 |
| Native guarded stage, including startup/guard overhead | 133.96 |
| Six guarded independent replay stages | 6.26 |
| Complete wrapper, including validation | 141.45 |

Components sit inside the native stage, and stages sit inside the wrapper;
do not sum all table rows. Active traversal is about 2.83M nodes/s across the
whole lineage; all three windows are short and capped after approximately 18M.
This is a measured bounded-work rate, not mature training capacity.

Guarded stage CPU totals 209.37s, including guard-helper children. Sampled peak
family RSS was 2,966,405,120 bytes (2.76 GiB). Minimum sampled available RAM was
5.76 GiB. All sampled thermals were nominal, pressure stayed 1, and swap stayed
1 MiB. Admission had 6.34 GiB available RAM and 22.69 GiB free disk. Minimum
sampled disk was approximately 20.22 GiB; the retained main tree is
2,559,581,416 bytes (2.384 GiB). No cleanup or staging was needed. Physical I/O
was not measured; ordinary OS caches were used, with no isolated/cold-cache claim.

Postscience once-only model/trace/receipt SHA256 pinning and compact readout took
1.04s wall / 1.01s CPU separately. The first metadata collector used the system
Python, which lacked `hashlib.file_digest`; it failed before payload hashing or
writing a bundle. That failed readout directory and failure record remain. A
corrected collector used the existing qualified Python, with no repeated
training, model play or scientific retry.

## Decision and bounded next step

Keep all three checkpoints and the exact-chip key as a qualified reference.
Do not promote the model or allocate mature variable-stack training from this
result. The main unresolved issue is representation/support, especially passive
later streets. One seed and a small capped table cannot separate abstraction,
visitation and capacity effects.

My recommended next engineering question is whether a deliberately specified
stack-aware abstraction can share useful states without losing public ownership,
folded contributions or legal-action interpretation. Start by checking its
collisions on the existing fixed observations; freeze and independently review
the candidate before any dependent training. Keep chance law, seed, recipe,
capacity, endpoints and common observations fixed if a single candidate is then
compared with this retained reference. No new depth, search or strength arm.

[Conditional next-allocation costing](next-allocation.json) prices that **single
100M candidate pilot only**, after implementation/review/fixtures: about 4m21s
central / 16m54s reserve, rounded to a proposed 20-minute M4 allocation, 8 GiB new
disk plus 4 GiB headroom, 5 GiB RAM plus 1 GiB headroom. It uses measured capped
pipeline costs with reserves, not a promise about an unimplemented key.
Engineering time is excluded. The representation is not yet selected, so this
is **not launch-ready or authorized**, and no next experiment has started.

## Retention

All ordinary sources, runtime/input pins, checkpoints, averages, binaries,
initial/repeated traces, watch data, resource samples, partial/error evidence
and original proofs remain on M4 under
`~/Local/nplayer-variable-stack-20261026/`. Restore/verification paths and hashes
are in [pilot provenance](pilot-provenance.json). Cleaner-owned later bb128
staging, ZIP packaging and Drive acceptance remain pending. No payload archival,
deletion, app/system changes, default change or bb128 science is claimed.
