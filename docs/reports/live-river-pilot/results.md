# Legal river decision engineering pilot

[PR375](https://github.com/dberweger2017/CFR-NLHE-6max/pull/375),
[issue374](https://github.com/dberweger2017/CFR-NLHE-6max/issues/374), follows the
[prepared prototype](../native-river-prototype/results.md). This is a fixed-state
engineering qualification, with no played arena, training, adoption or release
change. The [protocol](../../live-river-pilot.md) declares the six roots and work
levels. A later strength campaign requires an accepted separate quote.

## Numerical discrepancy review

The first divergent strategy is at sweep 2, case 2/node 9, holding 3h6d. A rational
oracle over the integer-chip fixture proves its first-sweep regrets are exactly
`[0, 0]`. Native computes those zeros; Python's dense products leave
`[6.938893903907228e-18, -1.3877787807814457e-17]` BB. Regret matching therefore
plays `[0.5, 0.5]` in native and `[1, 0]` in Python. The normalization at zero
amplifies rounding into a different later learning trajectory.

Sixteen identical-profile checks agree on regret deltas within 1.78e-15 BB.
A separately selected scalar native terminal kernel also changes the learned
trajectory while retaining identical-profile values and best-response quality.
At 64 sweeps, exploitability is 0.51854749 BB in Python, 0.57553373 for sorted-linear
native and 0.51579272 for scalar native. At 256 sweeps the corresponding values
are 0.18953886,0.17177268 and 0.17924151 BB. Scalar arithmetic does not guarantee
bitwise reproduction of a NumPy/BLAS reduction order either.

This identifies a concrete rounding mechanism, supported by an exact oracle and
controlled evaluations. It does not make the original symmetric quality screen
pass: its two misses and overall 34/36 result remain preserved. No epsilon floor,
rounding of regrets, policy-matrix equality requirement, threshold relaxation or
extra original endpoint has been introduced. Future fixed-work configurations
must report the quality of their actual returned strategies.

## Live boundary and belief law

The new persistent worker accepts only public history, public board and stacks,
legal bounds and the acting seat's own holding. The Python adapter takes an
immutable `Observation`; the native side independently reconstructs and checks
its public actions, payments, player snapshot and legal bounds. Previous actions
must match the exact blueprint menu. Other hidden cards, a deck and a seed are
not accepted input fields. The own holding selects the strategy row; it does not
change the public root law.

Every seat's observed-action likelihood is computed over all 1,081 board-compatible
holdings, using previous street observations and the frozen blueprint. Folded-seat
actions are included. There is no likelihood floor. The model's actual uniform
fallback for missing/zero-mass keys is preserved and counted separately from
positive-mass rows. Zero modeled reach and unsupported histories are explicit
unsupported results.

Under that declared three-seat product-action model, folded cards are integrated
out with exact single-card/pair removal sums. Exact active marginals are then
projected into a product-compatible two-seat law. The projection's total-variation
distance from the original active joint is reported per root. This approximation
changes correlations: it is not a true unrestricted posterior, an opponent model
learned from these games, or a safe resolving certificate.

The live tree uses the existing N-player cash rules and full production
`min-pot-conditional-jam-v1` menu, with no two-raise cap. Its current supported
allocation is at most 4,096 public nodes and 2,000,000 strategy cells. The pilot retains
rejections at those limits. Its synthetic roots are not a frequency-weighted
sample of real hands; the two long minimum-raise, near-all-in roots are support
controls. They must not be used to estimate an eligible-river frequency.


## Measured complete decisions

Frozen measured implementation: `bc1bb630f64918483b23928b843bf2ce82dfa244`.
The [compact results](results.json) bind code hashes, the frozen model binary,
request fingerprint and every endpoint. Ordinary shared-host file-cache state
was used, without flushing. The existing release download/upload continued.

The six-case pilot finishes in **331.54 seconds**, including one **260.91-second
model+K50 load**. The model contains 250,000,475 rows and passes the frozen v0.6
SHA256 pin. That one first-use load is not a cold-cache or loader-speed comparison;
concurrent HDD traffic and ordinary cache state affect it. The persistent process
loads once for the entire panel. Sampled entire-family peak is **14.81 GiB**;
native-child high-water is 14.57 GiB. Stage wall/CPU is 331.69/211.70 seconds.
Maximum sampled CPU 64 C / Thermistor 15 at 55.5 C; every stage returns 0 and no thermal,
numerical or supervisor failure occurs. The supervisor exits and releases its lock.

| Case | Pot BB | Nodes | Sweeps | Complete ms | Ranges ms | Solve ms | Exploitability BB |
|---|---:|---:|---:|---:|---:|---:|---:|
|0|2.00|unsupported|—|21.08|—|—|—|
|1|2.50|unsupported|—|22.15|—|—|—|
|2|67.50|801|16|547.58|22.20|459.44|4.303420|
|2|67.50|801|64|1921.35|22.00|1833.02|0.330986|
|2|67.50|801|256|7449.52|21.92|7360.17|0.035129|
|3|187.50|unsupported|—|23.27|—|—|—|
|4|198.50|9|16|101.14|93.48|4.44|0.328044|
|4|198.50|9|64|113.92|92.96|17.89|0.021467|
|4|198.50|9|256|169.16|94.17|71.61|0.001470|
|5|196.50|21|16|108.99|94.20|10.86|0.304854|
|5|196.50|21|64|141.04|92.15|44.87|0.021557|
|5|196.50|21|256|275.58|92.60|178.64|0.002093|

Medians use three fixed repetitions; there is no p95 or concurrent-request
throughput estimate. Complete time starts at the immutable observation and ends
after validating the returned legal action distribution. It includes range
construction, all tree/solver work, quality diagnostics, JSON and transport;
model/K50 loading is separate. No human-facing policy or retained-profile play
adapter is installed. The first request for each root is retained in the raw
samples; no warm-up observation is silently discarded.

Case 2 is a 67.5 BB pot with 66.5 BB remaining for both active seats. Its exact
production-menu tree has 801 nodes: 64 sweeps spend 1.833 s solving out of 1.921 s complete,
with 22.0 ms constructing/projecting ranges. Higher work reduces stipulated
subgame exploitability from 4.30342 BB at 16 sweeps to 0.330986 at 64 and 0.035129 at256.
The 1024-sweep reference is reported below; it is still a finite-work reference,
not an equilibrium certificate.

Cases 4/5 are near-all-in support controls with 1/2 BB remaining, long minimum-raise
histories and 9/21 nodes. Their 93 ms range cost largely reflects those long histories;
their 64-sweep solves take 17.9/44.9 ms. They are not evidence of typical complete
100 BB decision latency. There is no universal15 ms result.

Case 0 (2BB pot) exceeds 4,096 nodes. Case 1 (2.5BB pot) exceeds the inherited
2,000,000 strategy-cell support limit. These are implementation allocation
rejections, not proofs the games cannot be solved. Case 3 (187.5BB pot) has zero
modeled reach for its own holding and is explicitly rejected; no likelihood floor
or invented belief makes it pass. Root support3/6 is descriptive for this synthetic
panel, not an estimate that half of real river decisions would be supported.

## Belief and quality limits

- Case 2: projection TV=0.065241;1024-sweep exploitability=0.00338696BB.
- Case4: projection TV=0.040531;1024-sweep exploitability=0.00010486BB.
- Case5: projection TV=0.080750;1024-sweep exploitability=0.00030783BB.

All three returned 1024-sweep profiles are independently reevaluated by the native
scalar terminal kernel: value/BR quality agrees within 1e-9 BB. The earlier prepared
qualification separately compares against the dense Python evaluator. This
pilot does not independently certify every legal belief or full production tree.
Projection distances of 4.05–8.07% are material approximation diagnostics, not
whole-game value bounds or a justification for ignoring the folded seat.

All 7,567 enumerated decision/holding lookups in case 2 find positive-mass rows.
Across cases 4/5,78,804/109,181 lookups are missing (72.18%), with 3,031 zero-mass
lookups and27,346 positive-mass lookups. These are unweighted candidate-lookup
counts, not reach-weighted policy coverage. The controls' large fallback share
is another reason not to extrapolate their costs/quality to typical play.

## Strength-study quote: conditional, not launch-ready

The measured 801-node root gives the following **serial solving-path** costs,
including the measured diagnostics/transport. These totals exclude startup,
whole-hand simulation, independent hand replay and any unsupported-state fallback.
Reproduction doubles the specified initial decision calls:

| Work |1,000 initial calls + reproduction|100,000 initial calls + reproduction|
|---|---:|---:|
|16sweeps|0.30h|30.42h|
|64sweeps|1.07h|106.74h|
|256sweeps|4.14h|413.86h|

For example, three lineages each making 1,000 initial calls at 64 sweeps cost about
**3.20serial hours including reproduction**, before the excluded work. This is
a cost scenario, not a scientifically justified sample count. There is no
measured speedup from concurrent requests to divide these numbers by 16.

**Recommendation: do not launch a broad strength campaign yet.** First profile
and reduce the solve work on the actual larger trees, decide how to support the
rejected allocation sizes, and qualify policy-consistent retained-profile reuse.
The measured belief projection and zero-reach behavior also require review.
A separately approved small whole-hand cost/variance pilot must then measure
actual eligible-call frequency, replay costs and paired-return variance before
fixing confirmation counts, adjustment families, margins or pass chances.
The fixed-state pilot cannot estimate any of those quantities. No arena,
additional seed, training or automatic continuation was started.

## Verification, provenance and retention

81 native library tests and 18 focused Python tests pass on the measured code;
full game/session checks (20 six-player hands/30 session hands) pass. The final source, including the added rational-oracle regression, passes all
19 focused Python tests in 2.26 seconds (`ffb21e97`). The measured native/adapter
file hashes still match the final tree exactly; no model pilot is rerun.
Source/model/native binary hashes, exact stage costs and maximum temperatures are
in the linked JSON receipts. The model and K50 inputs are existing read-only
PR367/qualification assets; none was copied, changed or removed. This is one
Intel i7-10700KF host, one sequential solver and BLAS thread, one blueprint seed,
three repeated work-level measurements and a shared release-transfer workload.

All originals remain under
`bb128:/home/dberweger/live-river-pilot-20261020/`. `qualification-v1` is the only
frozen-model pilot. The initial setup's missing shell Cargo path and shallow-bundle
prerequisite refusal occurred before any model pilot; setup logs/bundles remain.
One later added oracle test was initially executed against the older frozen
module and failed import; its standalone rational proof passed, and the final
source tests are recorded separately. No successful/failed science was restarted.
Research archive/Drive acceptance remains pending; no release or research payload
was uploaded by this PR, and no original, partial or unrelated input was deleted.


The [retention receipt](retention.json) records 50 owned files with local
SHA256 copy/ZIP-member readback at `/mnt/data2tb/research-cloud/PR-375-live-river-pilot`.
Archive SHA256: `6ba0de79aa8f33e0ac5f15c98a57e19f44efa267edb3348e942c2b55bfd535ea`.
No research upload competes with the active release. Drive acceptance is pending;
local at-rest and NVMe originals remain the available retrieval paths.
