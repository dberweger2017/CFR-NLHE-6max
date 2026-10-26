# Full inline expectation measurement: integration qualifies

[PR394](https://github.com/dberweger2017/CFR-NLHE-6max/pull/394), proposal392;
follows merged PR393. **All384 original roots pass, and inline expectations
remove the measured duplicated work. This completes evaluation engineering;
it does not establish stronger poker play.** No further science starts here.

## Scope and verification

The [accepted allocation](measurement-admission.md) ran on bb128 October22,
02:52:52–03:04:52UTC. Frozen source `dc58d5192ebae768a14ead940a05ff86220128af`,
binary `aaa1308888998f6013d88c21c556dd802617143f79504ad51d5b52b9157bb886`.
Four workers share two read-only original10B models. Same six lineups,128
six-permutation blocks per lineup,12 on/off cases,9,216 initial hands plus9,216
fresh reproductions. These are existing deals, not fresh strength samples.

Both passes match all384 PR391 original float64 expected values, profile hashes,
completeness and traversal work, with no exclusions or extra solves/profile
reconstructions. Each pass has381 fully enumerated roots and three original
quality fallbacks cancelling identical blueprint policies. Maximum arm work
is3,891 states against the unchanged200,000 limit; each pass visits223,018 states.

All9,216 initial hands independently replay and match original PR388 hand bytes;
fresh reproduction matches byte-for-byte. No changed action/RNG path, fallback,
menu, model, hidden-information boundary, new deal, retry or outcome extension.
The single main stage returns0, no failure. Prior qualification120 native and14
focused Python tests remains valid. [Full proof and work](measurement-results.json).

## Complete measured cost

| Pipeline, same saved panel including reproduction | Wall | Child CPU |
|---|---:|---:|
| PR388 sampled-only play/replay/readout |728.23s|910.42s|
| PR388 plus separate PR391 expectations |1,627.97s|1,808.65s|
| **Inline arena expectations, PR394** |**720.26s**|**901.42s**|

The integrated workflow is2.260× faster than the old separate workflow. Its1.1%
wall difference from sampled-only is ordinary one-job variation, not evidence
that expectation evaluation speeds up play. It achieves essentially the old
sampled-only batch cost while also producing the qualified expectations.

Two model/K50 starts total465.81s; play/writing including expectations251.20s;
independent replay/parity verification2.20s. Driver719.54s, supervised720.26s
(12m00s). Expectation-only work totals0.634s inside play/write, not in addition.
No second model load or profile reconstruction for the evaluator. Ordinary host
caches, fresh process per pass; no global cache flush or durability-fsync claim.

Sampled RSS27.70GiB, CPU65°C/Thermistor15 63°C, zero swap growth. Minimum free
NVMe257.53GB/HDD530.77GB; all originals retained. Two-second samples can miss
short peaks. The run fits the accepted35m11s planning reserve; the11m03s central
estimate was optimistic by58s. No target, resource setting or deadline changed.

## Efficiency: reuse the original variance, do not refit it

The on/off expectation values equal PR391's, so that study's means, variance,
adverse panels and uncertainty stay unchanged. The table replaces only cost.
Each ratio uses the common whole-panel measured cost, not per-lineup wall time.
Lower variance × cost is better;1.0 is sampled-only cost per equivalent variance.

| Lineup | Original variance ratio | New cold wall ratio | New amortized wall ratio |
|---|---:|---:|---:|
| Trained / trained |0.414|0.409|0.408|
| Trained / pressure |0.050|0.050|0.049|
| Pressure / pressure |0.028|0.028|0.028|
| Check-call / check-call |Undefined|Undefined|Undefined|
| Check-call / pressure |0.453|0.448|0.446|
| Random / TAG |0.059|0.058|0.058|

The trained primary gains approximately2.44× measured cost efficiency relative
to sampled evaluation, and not an order of magnitude. Cold cost multiplier is
0.989; amortized multiplier0.986 after subtracting model/K50 starts from each
workflow. The separate evaluator's previous trained-primary ratios were0.925
cold/1.104 amortized. [Per-lineup CSV](measurement-lineups.csv).

This is one focal lineage on saved development deals. One block still supplies
80.5% of primary residual centered squared variation. The original variance-ratio
bootstrap interval is[0.123,0.631], not protection against unseen tails or other
training seeds. Pressure has61 undefined zero-denominator bootstrap resamples;
its finite interval conditions on9,939 defined replicates. Check-call has no
intervention here; zero sample variance is not a passed population safeguard.

Preserve the original conditional means, including trained+8.33, pressure−0.43
and check-call/pressure−14.81BB/100, alongside their uncertainty. This accounting
does not turn exploratory means into strength or equilibrium claims.

## Decision: a fixed campaign or deferral

[One concrete strength proposal](strength-study-proposal.md) specifies three
frozen lineages, a+5BB/100 primary design effect, proposed−5BB/100 non-inferiority
margin, separate primary/safeguard families, fresh fixed deal counts and
conditional power/cost. Those numbers are proposals for owner review, not
previously accepted margins or a launch authorization.

At nominal80% joint power under the stated normal model, the full design costs
26.16h centrally/76.99h reserved, within a proposed80h planning allocation.
Check-call/pressure dominates both sample size and cost. If its previous adverse
effect repeats, that safeguard should fail; the nominal80% design assumes zero
safeguard loss and is not the empirical probability of acceptance.

**Recommendation:** close engineering and make the budget decision explicitly.
Do not sell this tight-safeguard confirmation as an overnight run. Given the
adverse panel and uncertain tails, deferring the broad campaign is reasonable
unless the owner accepts both this cost and the chance of a failed/inconclusive
result. No further optimization or search expansion is proposed as an automatic
alternative. A smaller stipulated primary effect costs more, not less.

## Reproduction and evidence

[Pins/admission](measurement-provenance.json) links unchanged source/config/input
identity. [Measurement results](measurement-results.json) contains the original
compact proof, stages, costs and resource/work summaries. The offline reporting
helper reads compact receipts and existing PR388/391 summaries only:

```sh
python3.11 -m scripts.summarize_river_arena_expectation RETRIEVED_RECEIPT_JSON --out FRESH_OUTPUT
```

It never plays hands or refits outcome variance. Models, raw traces and sidecars
remain off Git. All original qualification/calibration/full outputs, build/test
logs, source bundle and local debug partials are retained; protected external
models/K50/environments/Git stores are referenced only. The [accepted archive](archive.json)
covers266 local files, main ZIP6,635,240bytes and closeout ZIP9,995bytes. Local
SHA256/member readback and deployed-tool Drive MD5/size acceptance passed; no
remote SHA256/member readback is claimed. Fast cache is
`/research/PR-394-river-arena-expectation/`; Drive fallback and ZIP/member hashes
are in the receipt. The offline helper's exact input is
`closeout/measurement-retrieval.json`. KEEP and every original remain. No deletion
or environment change.
