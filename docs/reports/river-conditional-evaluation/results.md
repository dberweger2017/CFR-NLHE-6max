# River action-expectation qualification: fixtures and calibration pass

PR390, proposal389. October22,2026. Runtime source
`9998501a4a6794d7c682d39e4edb436b69e04d29`; evidence commits do not change it.

The native evaluator passes correctness fixtures and reconstructs all **13
predeclared calibration roots** exactly. Ten installed profiles complete all
positive-probability action branches within the fixed 200,000-state/arm/root
limit. The other three are the original quality fallbacks: identical on/off
blueprint policies cancel to zero, explicitly without enumerating absolute
returns. **Variance reduction and compute efficiency remain unmeasured.** The
full 384-root assessment and any fresh strength study have not started.

## What changed

The evaluator integrates future river actions against the actual trained or
scripted opponents, using integer-chip engine transitions and float64 sums.
It measures expected terminal return, a different quantity from full-menu
worst-case audits. Each policy sees only its own legal observation. The
privileged evaluator owns hidden cards and terminal settlement; those cards
do not enter search beliefs or policy inputs.

Each search profile must reproduce its original hash, work, installation or
fallback status and root probabilities. A branch-local retained session follows
the original solved strategy, then sticky blueprint fallback after an omitted
action, with zero solver advances. Full positive-support enumeration includes
opponent actions outside the search tree. Incomplete enumeration produces no
point value. The model, search recipe, menu and fallback are unchanged.

The frozen inventory contains every first eligible root, including unchanged
sampled actions: trained74, trained-pressure56, pressure26, call0,
call-pressure195 and random-tag33. Eventually aggregate at the original 128
six-permutation blocks per lineup, with zero contrast for noneligible hands.
Neither a root-only mean nor extra reproduction copies may inflate the sample.

## Evidence and measured cost

The independent small-fixture terminal-list oracle agrees within 1e-10BB,
covering folds, ties, unequal stacks/refunds and stochastic branches. Tests
reject malformed rows and partial values; a retained-session test checks branch
isolation and sticky off-tree fallback. A sampling-law fixture checks actual
script distributions at check and facing-bet observations.

Host qualification passes **116 native library tests, one native script-law
test and seven focused Python tests**. All five qualification stages return0;
qualification takes60.58s. The calibration stage also returns0, with no failure
or guard crossing. CI is a separate check, not implied by these host tests.

| Calibration component | Measured cost |
|---|---:|
| Load two frozen policies and K50 | 234.200s |
| Reconstruct and verify 13 original profiles | 14.073s |
| Enumerate 20 on/off installed-policy continuations | 0.01155s |
| Native batch, including output and other overhead | 248.338s |
| Supervised calibration stage | 250.169s wall /249.013s child CPU |
| Positive-support states visited | 9,652 |
| Largest single-arm traversal | 3,891 /200,000 states |
| Sampled worker-family peak RSS | 27.67GiB |
| CPU /Thermistor15 peaks during calibration | 58 /56.5°C |
| Swap growth | 0 |

Enumeration is inexpensive on these selected roots; loading dominates this
batch. This is not a population tail estimate or evidence of reduced return
variance. Calibration deliberately includes all three expensive quality misses,
so it is not frequency-representative. No root returns were retrieved or used
to select the method, sample or budget.

## Concrete next allocation: all saved roots and reproduction

The [published quote](calibration.json) is **1,300.47s (21.67min)** by mean
extrapolation, with a conservative **13,378.68s (3h42m59s)** planning reserve.
The reserve assigns both 200K-state arm limits to every installed root, the
maximum measured preparation cost to every root, worst measured seconds/state,
3× work and 2× loading reserves, and600s per pass. It is a planning allowance,
not a runtime guarantee, statistical confidence limit or automatic time stop.
No unmeasured concurrency or cache flush is assumed; two fresh processes load
models separately, with ordinary host caches.

The proposed action is exactly all384 roots, once plus one fresh reproduction,
using the qualified binary and the unchanged fixed limit. It would reconstruct
all original profiles, require complete coverage and reproduced values before
global readout, then compare sampled versus integrated **block variance times
total cost**, separately by lineup and cold/amortized cost. Include the measured
common-prefix generation/replay cost or a conservative allowance for a future
fresh pipeline. Preserve adverse panels, no-intervention zeros and tail
concentration. The fixed bootstrap, if used, is10,000 paired block resamples,
seed2026102239001.

The protocol requires an **explicit accepted measured quote before this larger
saved-data allocation**. No launch is admitted by this report. All-root execution,
two-pass verification and block-variance readout are now implemented separately
in `scripts/assess_river_conditional_evaluation.py`, but have not run on the
inventory. Four new assessment tests bring the local focused suite to11 passing
tests. These cover quote acceptance, changed profiles/float64 values, incomplete
or nonfinite values and paired bootstrap/no-intervention accounting.

The prepared launcher requires the exact published quote SHA256 and a planning
allowance at least as large as its reserve. It uses a separate, pinned assessment
checkout whose native files and critical helpers must match the qualified
source, and the existing qualified binary. The original runtime source/config,
qualification and calibration remain intact. Its own child process groups,
mutex and temperature checks remain active. A fresh strength study still needs
its own quote.

One incomplete required root prevents an efficiency verdict: no dropping it,
raising the limit, changing methods or extending until a favorable result.
Only temperature resource stops remain CPU90°C /Thermistor15100°C, with missing
or nonfinite required sensors terminal. Owner STOP and correctness/mutex
failures also stop owned work. No time/RSS/disk/swap kill guard is added.

## Interpretation

This establishes a working, inexpensive action-expectation prototype on the
cost-calibration subset. It does not establish a variance reduction, a shorter
strength-study budget, a search gain or safety against adversarial play.
Integrating river action randomness leaves dealt-card, prefix and training-seed
variation. Shared action streams and six-permutation covariance also mean a
per-hand noise reduction need not improve block variance. The saved pilot is
development evidence from one focal lineage, not fresh confirmation.

## Reproduction and retention

[Protocol](../../river-conditional-evaluation.md), [work-only root table](calibration.csv),
[inventory/quote and work metadata](calibration.json), [costs/resources](costs.json),
[source/config/binary/input pins](provenance.json). Raw inventory, values, logs
and source/build/environment dependencies remain on bb128 under
`/home/dberweger/river-conditional-evaluation-20261022`.

The completed original invocations are preserved as qualification-v1 and
calibration-v1; they must not be rerun in place. For authorized reproduction
into a separate fresh output, the pinned driver uses:

```sh
venv/bin/python -m scripts.run_river_conditional_evaluation qualify \
  --root ROOT --out ROOT/NEW_QUALIFICATION --source 9998501a4a6794d7c682d39e4edb436b69e04d29
venv/bin/python -m scripts.run_river_conditional_evaluation calibrate \
  --root ROOT --out ROOT/NEW_CALIBRATION --source 9998501a4a6794d7c682d39e4edb436b69e04d29
```

The calibration launcher additionally requires the original successful
qualification-v1 source/config/binary receipts. Commands document provenance,
not permission for another allocation. Original PR388 traces/models/K50 and
all Git/environment dependencies stay read-only and retained. Archive/Drive
acceptance is pending; no originals were removed and no other job changed.
