# Inline river expectations: integration and small calibration pass

[PR393](https://github.com/dberweger2017/CFR-NLHE-6max/pull/393), proposal392.
The arena now evaluates expectations using its already loaded models and the
original captured search profile. The player, its chosen actions, fallback,
menus and model bytes stay unchanged. This removes duplicate model loading and
profile reconstruction from the expectation evaluator; it does not change search
or establish stronger play.

## Verification

Frozen source `dc58d5192ebae768a14ead940a05ff86220128af`; bb128 qualification
and calibration completed October22,2026. All120 optimized native library tests
and14 focused Python tests pass. The native fixtures check independent terminal
enumeration, shared immutable profile ownership, isolated sibling branches,
sticky off-tree fallback and rejection of progressed/mismatched root sessions.
Player callbacks accept only their own legal observations; hidden cards belong
to the privileged evaluator.

The fixed first4 original blocks across all six lineups produce288 initial
hands and288 fresh reproductions. Every initial hand independently replays,
matches its original PR388 hand bytes, and reproduces byte-for-byte. The12
encountered roots match PR391's original float64 expected values, profile hashes
and traversal work in both passes. No exclusions, incomplete roots, additional
solver advances, profile reconstructions or new deals.

These12 roots comprise three trained, one trained-pressure, seven call-pressure
and one random/TAG root. All installed; the small real-model panel contains no
quality fallback or pressure-only root. Native fixtures cover fallback, but
full384-root parity remains pending. Do not generalize this subset to all roots.

## Actual complete cost

| Component | Initial | Reproduction | Both |
|---|---:|---:|---:|
| Model and K50 loading |231.087s|231.157s|462.244s|
| Play and writing, including inline expectations |3.072s|3.035s|6.107s|
| Expectation-only work, included above |8.23ms|8.19ms|16.42ms|

Verification adds0.154s. Complete driver wall468.630s; supervised wall470.048s
(7m50s), childCPU476.225s. Two fresh model processes, ordinary host caches,
four arena workers and two shared read-only policies per process. Model loading
is98.6% of driver wall in this deliberately small batch; no global cache flush.
The expectation component is not a complete-pipeline speedup measurement.

Each pass visits5,737 continuation states, at most1,160 per arm against the
unchanged200,000 limit. Calibration sampled peak27.70GiB; CPU60°C,
Thermistor15 59.5°C; zero swap growth. Native build/tests separately take56.53s
supervised wall and reach CPU67°C. All four stages return0, no failure or retry.
RSS/thermal peaks are sampled rather than exact high-water counters.

## Next explicit allocation decision

The frozen full measurement is12 cases ×128 original six-permutation blocks:
9,216 initial hands plus9,216 fresh reproductions, all384 original expectation
roots, unchanged policies and200K per-arm limit. All initial hands independently
replay. No fresh strength hands or new variance fit.

The measured quote is662.60s (11m03s) centrally, with2,110.80s (35m11s) planning
reserve. It uses32× calibration play, two measured model starts, replay/proof,
and conservative reserves: twice loading, three times projected play or twice
the original full play cost, and at least600s verification. It is an allowance,
not an elapsed-time guard or guaranteed upper completion time. Full measurement
has **not started** and needs explicit owner acceptance of this quote.

After that measurement, compare variance × complete pipeline cost by lineup,
cold and amortized, against PR388 and the separate PR391 path. The original
trained-primary variance ratio0.414 suggests about2.4× sample efficiency before
overhead, with sparse-tail and one-focal-lineage uncertainty. Do not refit variance
on this cost calibration or compare its288-hand wall directly with the old full
panel's cost as a speedup. Preserve adverse panels and zero-intervention cases.

Use the measured full pipeline to price one fresh fixed peer-and-scripted study,
including adjustment families, margins, effect targets, counts and conditional
pass chances. The owner then chooses a fixed budget or defers search expansion.
No automatic strength campaign, training, menu change or further engineering.

## Reproduction and retention

The [protocol](../../river-arena-expectation.md) and versioned runner
`scripts.run_river_arena_expectation` freeze qualification, first4-block
calibration and separately admitted128-block measurement. Source, config,
binary, input hashes and protected dependencies are in [provenance.json](provenance.json).
Only a fresh measurement directory with an accepted unchanged quote/source is
admitted; do not rerun historical commands casually.

[Verification](calibration-verification.json) · [costs/resources/work](calibration-costs.json) ·
[component CSV](calibration-costs.csv) · [unaltered quote](full-measurement-quote.json).
Raw traces, sidecars, source bundle, binary, resources, test logs and local partial
debug-test evidence remain in their owned roots. bb128 originals:
`/home/dberweger/river-arena-expectation-20261022/`; local ignored evidence:
`planning/arena-expectation/`. Existing PR388/391 inputs, models, environments
and shared Git stores are read-only dependencies, not copied or cleaned.
Archive/Drive acceptance remains pending; no deletion or acceptance claim.
