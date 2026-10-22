# Four-player100BB M4 feasibility — completed

The fixed25M→50M pilot completes with all stages/proofs passing and **no strength readout**. The current four-player recipe is affordable on this M4 at the measured small-table scale. This is allocation evidence toward v0.7, not a release, learning or playing-strength result.

[PR406](https://github.com/dberweger2017/CFR-NLHE-6max/pull/406), [protocol](../../nplayer-four-player-feasibility.md), [unchanged main results](results.json), [qualification](qualification.json), [resource/proof summary](resource-summary.json), [endpoints CSV](endpoints.csv), [street/coverage CSV](street-coverage.csv), [prospective quote](quote.json).

## Cost and table growth

Main elapsed wall time is **171.42seconds (2m51s)**; the table below separates process costs from control/hash gaps. Qualification/build stages total95.89seconds; qualification controller elapsed about97.88seconds. From qualification launch to main completion, including the operator quote/admission gap, elapsed is about5m50s. Analysis/reporting is additional. The reserved34-minute quote was deliberately conservative: it scaled whole small-tool costs, including fixed K50 loads and1second polling overhead, to the cap and applied2×reserve; these fixed costs do not actually scale linearly with rows.

| Nodes | Retained keys | Added-node throughput | Active training | Save | Train process wall | Train sampled peak | Export | Full-row audit |
|---|---|---|---|---|---|---|---|---|
| 25,010,502 | 13,691,524 | 7.07M/s | 3.54s | 5.38s | 12.39s | 2.33GiB | 14.37s | 17.45s |
| 50,020,943 | 20,007,998 | 6.58M/s | 3.80s | 7.69s | 26.72s | 2.86GiB | 21.62s | 24.61s |

Measured main stages total **2.82minutes**, plus **1.60minutes** qualification/build stages. Main child CPU cost is **8.84CPU-minutes**. Complete main sampled family peak **3.21GiB**; all observed thermal states **nominal**, maximum system pressure level **1**, observed swap growth **0.00MiB**. Available RAM minimum **5.72GiB**, disk minimum **87.76GiB**. Memory/pressure/swap/disk are observations, not runtime kill thresholds. Timing separates active traversal from checkpoint save and load/hash/other process overhead. Stage polling adds up to about1second per process and inflates tiny fixture cost estimates.

Membership froze at iteration1,933; recorded telemetry brackets the crossing between37,032,026 and38,990,087nodes. The final20,007,998rows overshoot the20Mthreshold by7,998 because freezing occurs after a whole iteration. [Freeze/file-size/lock-release receipt](freeze-and-release.json). Retained growth after freezing is censored; this is not natural saturation. Marginal retained-key/node rates are **0.5474** then **0.2526**. Peak-RSS/key includes K50 mappings, allocator and save buffers; it is not a physical record-size measurement. Active training windows are only3.54/3.80seconds and the second interval includes capped work; do not treat these as steady mature-table rates. A matched three-player control is absent, so historical comparisons cannot isolate player count from hardware/table-size effects. M4 timings are not measured bb128 forecasts.

## Correctness and coverage

Six focused controller tests and121native library tests pass.128independent engine rules fixtures cover four-player legal play and varied stacks/all-ins/side pots. Tiny realK50 checkpoints match byte-for-byte for1/10threads and fresh/resumed paths, with fixed membership. Qualification exports audit all rows;72initial self-play hands reproduce and independently replay. Main exports audit every retained row at both endpoints, with128initial self-play hands plus128byte-identical reproductions and independent replay, one shared read-only table/four policy instances and all four button positions. All initial and repeated hands are retained; no exclusions or payoff-based selection.

Street CSV reports retained keys/visits and source training missingness separately from reached self-play missingness. The latter comes from only64hands per endpoint against the same model in all seats and is descriptive. River self-play misses are5/9decisions at25M and12/18at50M. Those tiny, differently dealt panels cannot establish a coverage trend; they emphasize that this early capped model is not qualified for strength or deployment. Table-wide zero-average-mass row shares are **30.0%** and **29.8%**; these are not played-decision fallback rates. Per-street zero-average mass is not separately counted by this auditor.

## Interpretation and next allocation

This pilot supports preparing a separately priced four-player bb128 campaign. It does not justify silently scaling these rates to mature capped tables or starting long training. Use the observed uncapped growth/bytes, model load/save/export/audit costs and intended coverage/capacity to price that next campaign explicitly. Keep PR404's three-player200BB strength acceptance independent; no work or result from this pilot substitutes for it.

Source **6637a70e28a7349067f7ea8291c72264b0986c92**, one fresh main seed2026102240601, fixed25M/50M/current100BBK50unprunedfast10/eightroots/fullfloat64averages/parallelgzip/20Mthreshold. Original config/source/build/K50/engine/model/trace/proof hashes are retained on M4 under `/Users/dberweger/Local/nplayer-four-player-feasibility-20261022`. The source checkout uses shared Git objects from the existing `~/Local/hu200-river-search` root; that object-store dependency, the read-only engine venv and K50 paths must remain protected until owner-managed archival records a standalone source snapshot. Both research locks are verified released and the main process has exited. All outputs/partials/source/qualification remain, no scientific retry/extra endpoint/tuning/default/release change. No other machine or job was used or modified. Archive/staging/Drive acceptance is owner-managed and pending; no deletion or cloud-acceptance claim.
