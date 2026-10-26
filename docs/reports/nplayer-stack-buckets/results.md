# Bucketed variable-stack keys: qualified mechanics, small support changes

PR444 completes the single frozen M4 pilot. The opt-in representation, all three
checkpoints and every correctness barrier pass. **It does not demonstrate a useful
compression gain on the fixed observations or establish playing strength.** At
100M, original-panel positive support is unchanged; held-out positive support
increases by 29/3,091 observations (0.94 percentage points). River support remains
very sparse. Keep both representations and all checkpoints; no mature training,
retuning, adoption or automatic continuation follows this result.

[Frozen protocol](../../nplayer-stack-buckets.md) · [complete results](results.json) ·
[all support cells](panel-cells.csv) · [learning cells](learning-cells.csv) ·
[final row audits](retained-rows.csv) · [tuple/button exposure](tuples.csv) ·
[played support](played-support.csv) · [collision audits](collisions.json) ·
[costs](costs.json) · [admission/review](admission-review.json) ·
[pins and restoration](provenance.json) · [agent handoff](AGENT_HANDOFF.md).

## What changed and what stayed fixed

Three players, 50/100 blinds, K50, production menu and independent uniform
20/50/100 BB initial stacks: all 27 ordered tuples remain in scope. The candidate
uses the same seed 20261026441011, recipe, two workers, 10M-key whole-iteration
freeze and 5M→25M→100M endpoints as PR441. The reference is queried from its
unchanged saved checkpoints/binaries; it is not retrained.

The new `stack-buckets` identity retains exact initial-stack ownership, public
seat/status, contribution ordering/equality, action-label/kind/all-in semantics
and the existing K50/live-order summary. Selected current amounts become declared
integer-ratio buckets. Actual legal raise targets are reconstructed from the
current observation rather than copied from another state. Original aggressor
identity is also retained, including a subsequently folded seat. This additional
context means the experiment is **not pure numerical coarsening** of StackOwner.
Changing the representation also changes policy-induced visitation. Neither
observed table-size differences nor support differences isolate one causal field.

The original 324-hand synthetic panel is unchanged (seed20261026441002); the
held-out 324-hand panel was fixed before training (seed20261026443002). Both
balance tuples/buttons and uniform-menu/check-call continuations. They contain
3,074 and 3,091 legal observations. These are deliberately constructed support
panels, not population-weighted coverage, payoff tests or independent strength
samples. There are no return intervals or acceptance claims in this study.

## Growth: the same protective cap still binds early

| Target | Actual nodes | Candidate rows | PR441 rows | Added training time |
| --- | ---: | ---: | ---: | ---: |
| 5M | 5,002,267 | 2,861,886 | 2,876,747 | 1.51s |
| 25M | 25,002,991 | 10,000,186 | 10,003,912 | 6.40s |
| 100M | 100,005,809 | 10,000,186 | 10,003,912 | 24.57s |

At 5M, the candidate retains 14,861 fewer rows (0.52%). This small difference
under changed trajectories is not a measured compression ratio on identical
visited states. Candidate membership freezes at iteration2,051 with 186 rows of
whole-iteration overshoot. Telemetry brackets freezing between 18,007,135 and
18,894,598 nodes. PR441's bracket was 18,061,225–18,952,344; they overlap.
Pre-cap candidate growth is still about 0.572 retained rows/node at5M and0.542
at the last unfrozen sample. Flat growth afterward is imposed by the cap, not
natural saturation. No change to that cap or extension was made.

## Identical-state support: modest gains and adverse cells retained

Cells below are **positive / zero-average-mass / missing** observations.

| Endpoint | Original reference | Original candidate | Held-out reference | Held-out candidate |
| --- | --- | --- | --- | --- |
| 5M | 873 /108 /2,093 | 880 /111 /2,083 | 878 /135 /2,078 | 885 /138 /2,068 |
| 25M | 1,473 /98 /1,503 | 1,481 /91 /1,502 | 1,502 /81 /1,508 | 1,517 /91 /1,483 |
| 100M | 1,541 /30 /1,503 | 1,541 /31 /1,502 | 1,549 /34 /1,508 | 1,578 /30 /1,483 |

From25M to100M, candidate membership is fixed: 60 original and61 held-out
observations move from zero mass into the positive-mass total. Missing counts
cannot improve in that interval. Against the reference at100M, the original
positive total is unchanged; the held-out increase is29. Across the union,
positive support is3,119/6,165 versus3,090/6,165, a0.47-point difference.
This is descriptive support, not a statistical or playing-strength success.

| Street,100M | Original reference positive/missing | Original candidate positive/missing | Held-out reference positive/missing | Held-out candidate positive/missing |
| --- | --- | --- | --- | --- |
| Preflop | 1,006 /234 | 1,006 /232 | 1,021 /224 | 1,032 /213 |
| Flop | 436 /304 | 444 /299 | 453 /292 | 470 /279 |
| Turn | 94 /462 | 86 /468 | 69 /483 | 72 /481 |
| River | 5 /503 | 5 /503 | 6 /509 | 4 /510 |

The original turn loses eight positive observations; the held-out river loses
two. Original river misses remain503/510 (98.63%); held-out river misses are
510/516 (98.84%). Of324 tuple/physical-seat/street cells per panel at100M,
positive counts improve/decline/stay equal in31/34/259 original cells and
44/19/261 held-out cells. Every zero/sparse/adverse cell is included in the
3,888-row support CSV; no tuple or street is dropped.

The separately played81-hand panels have candidate missing/zero/positive counts
339/20/204,215/18/337 and221/9/354. Their trajectories and denominators change,
so they cannot replace identical-state comparisons. Settled multi-pot hands are
2,4,4. Provisional contribution-layer and all-in exposure on the fixed panels
are separately retained in the support CSV; they are not the same measure.

## Collision and learning diagnostics

The original panel has2,962 distinct keys under **both** candidate and reference;
the held-out panel has2,981 under each; their union has5,717 under each.
There are **zero observed groups merging distinct StackOwner reference keys**
in all three audits. Thus these observations do not demonstrate the proposed
compression mechanism. A legal unit fixture does exercise an intended200-versus-
201 raise-target merge, but a constructed fixture is not evidence of frequent
use in this panel or during training. Protected public contracts pass throughout;
all observed numerical/legal-target variants would be retained if groups existed.
Compatibility still does not prove equal payoffs or strategic equivalence.

All27 tuples receive training roots: cumulative271,200 at100M, ranging
9,894–10,298 per tuple. Button counts remain in the tuple CSV. Balanced root
sampling does not imply balanced useful learning at later histories.

| Predetermined watch keys | 5M | 25M | 100M |
| --- | ---: | ---: | ---: |
| Attempted positive-weight traverser reach | 399 | 904 | 1,507 |
| Retained nonzero-regret aggregate reach | 399 | 871 | 1,231 |
| Repeated retained traverser contributions | 123 | 523 | 990 |
| Keys with declined contributions | 0 | 33 | 276 |
| Never attempted | 2,563 | 2,058 | 1,455 |

The watch denominator remains2,962 because this panel has no candidate/reference
merges. At100M,1,507 attempted reached keys must **not** be called1,507 learned
retained rows:276 have declined contributions, leaving1,231 with retained
nonzero root aggregates. Attempted repeated reach is1,071; median nominal
weight ESS among attempted reached keys is2.43. PR441's1,486 reached/1,027
repeated counts were attempted-only diagnostics; a direct retained-learning
comparison is unavailable from that old observer and is not invented here.

The candidate observer records18,450,677 attempted nonzero-regret root-key
aggregates but5,172,650 retained ones, plus41,215,696 declined root-key
contributions. Declines are not unique absent rows; native merged-iteration
discard counters use another aggregation unit. Of10,000,186 retained rows,
6,172,377 have no traverser visit,748,272 have at least two visits and2,768,362
have zero average mass. Final zero regrets can include cancellation; opponent-
only averaging is not zero target reach. All972 learning cells and12 final
street-row audits remain published. Weight ESS is a concentration proxy under
adaptive policies, not independent statistical sample size. Pathwise zero reach
and numerical-underflow attribution remain explicitly deferred.

## Correctness, independent review and preserved failures

Qualified source is `8425ecbd36b40cb51b26d3ba771fccc8aefba587`; the exact executable
was pinned **before** dependent fixtures, SHA256
`0fef03fc6ab6f65f0c92b858df3b0b63320f1dbef007231dac8525d47c1013b3`.
All898 source/runtime files, K50, Python, thermal helper, reference payloads,
qualification and review/owner receipts validate before and after the pilot.
Independent review cleared information boundaries and then separately checked
raw qualification bindings and final arithmetic/proofs. Reviewer made no edits
or scientific runs.

Legacy StackOwner qualification checkpoint/average/binary/traces remain
byte-identical to PR441. Both fixed history/live-order checkpoints and averages
also retain their historical bytes. Candidate thread/resume/observer parity,
hidden-world invariance, physical rotations, strict schema/identity refusal and
collision fixtures pass. Four new key tests, strict mixture-identity tests,
six independent Python guard tests and all-example compilation pass; an earlier
local full-library run passed164 tests before the additional identity test.
Current CI independently checks the final branch.

All22,862,258 candidate endpoint rows pass full float64 average/binary checking.
Reference mass tags come from the original checkpoint; binary probabilities
match that checkpoint bitwise on both panels and union. All972 original
reference support cells reproduce PR441 exactly. At each candidate endpoint,
81 initial hands and81 repeated hands independently replay against the pinned
engine: **243 initial+243 repeat**, six successful replay commands, identical
trace hashes and seven outer stagesRC0. The native receipt deliberately remains
`native-complete-proof-pending`; the immutable outer COMPLETE closes that
historical proof barrier. Both research locks were verified available afterward.

Two preparation issues remain preserved. An unused protocol-only source archive
was caught before execution when the host PR head lagged the local committed
head. Qualification-v1 then stopped at an all-examples compile check because the
old exact-history benchmark lacked the new enum refusal; no training fixture or
pilot ran in that failed qualification. The benchmark was fixed to reject coarse
schemas, reviewed, and qualification-v2 ran from a new snapshot. No successful
pilot training was retried and no failed evidence was overwritten.

## Complete cost and preservation

The published remaining-pilot quote was4m28s central/12m14s reserve, within the
conditionally accepted20-minute M4 plan. Admission provided7.64GiB available RAM
and17.17GiB disk against6GiB RAM/12GiB disk requirements. Main actual wall is
**141.82s (2m22s)**; measured stages use201.80 CPU seconds. This is a tiny capped
pilot, not a mature throughput forecast or an isolated runtime comparison.

| Main component, summed across endpoints | Seconds |
| --- | ---: |
| Active training including observer | 32.48 |
| Checkpoint saves | 30.12 |
| Average exports including checkpoint pins | 19.75 |
| Binary conversion | 20.54 |
| Full-row binary audits including pins | 19.85 |
| Binary loads | 4.95 |
| Play/reproduction/panels/endpoint readout | 1.80 |
| Native guarded stage including startup/guard overhead | 132.82 |
| Six guarded independent replays | 6.29 |
| Complete wrapper including validation | 141.82 |

Qualification-v2 is96.00s including25.57s of read-only three-endpoint reference
audit, reused rather than repeated. The preserved compile-failed qualification
cost20.75s, including7.18s in the failed build stage. These three supervised
wrappers total258.57s; local implementation/testing, preparation transfer and
final reporting/readback are additional and not mislabeled as that total.

Main sampled family RSS peaks at**2.82GiB**; minimum available RAM is6.64GiB,
minimum sampled free disk14.65GiB, all thermal samples nominal and pressure1.
Swap existed before launch: main sampled range1.392–1.401GB, without growth.
The earlier qualification preparations span a change from1MiB to1.443GB swap;
there is no across-preparation no-swap-growth or causal attribution claim.
Thermal-state sampling is not a degrees-C measurement; sampled RSS is not an
exact allocator peak. Main retains2,560,296,556bytes (2.384GiB). The whole owned
tree at readback is6,135,668,222bytes (5.714GiB), including builds/source/failures.

Ordinary evidence stays under M4
`/Users/dberweger/Local/nplayer-stack-buckets-20261026/`, with PR441 inputs
unchanged. Provenance records model/trace/config/source hashes and immutable
readback-bundle pins. No bb128 access, ZIP upload, cleanup or deletion occurred.
Cleaner-owned later archive/cache/Drive acceptance remains pending; no Drive
coverage is claimed. This result favors reviewing the remaining sources of key
fragmentation before any separately proposed mature experiment, rather than
assuming this particular bucketing design solved support.
