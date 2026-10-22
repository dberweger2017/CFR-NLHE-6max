# Five/six-player 100 BB M4 feasibility — completed

Both fixed25M→50M pilots pass all declared correctness, full-row audit, replay and reproduction gates. The existing native workflow is affordable at these small capped tables for both sizes. This supports planning blueprint candidates, **not playing strength, adequate capacity or release acceptance**.

[PR408](https://github.com/dberweger2017/CFR-NLHE-6max/pull/408), [proposal407](https://github.com/dberweger2017/CFR-NLHE-6max/issues/407), [protocol](../../nplayer-five-six-feasibility.md), [unchanged results](results.json), [endpoints CSV](endpoints.csv), [street/coverage CSV](street-coverage.csv), [qualification](qualification.json), [prospective quote](quote.json), [resource/file proofs](proofs-and-resources.json), [retained progress](training-progress.json).

## Measured costs and growth

Combined main elapsed **359.46 seconds (5m59s)**; measured main stages total354.25s. Qualification/build elapsed **198.28 seconds (3m18s)**. Reporting/operator quote gaps are additional. Prospective combined quote24m11scentral/45m03sreserved included qualification and reporting within the one-hour planning allocation; it was deliberately conservative and not a runtime kill. The quote anchors whole cap-size tools to PR406 and separates fixed play/model startup from row work. Tiny qualification still includes1second stage polling; these are scenarios, not timing guarantees.

| Players | Nodes | Retained keys | Added traversal | Added-node rate | Save | Train wall | Export | Full-row audit |
|---|---|---|---|---|---|---|---|---|
| 5 | 25,000,508 | 14,753,432 | 3.84s | 6.52M/s | 5.70s | 13.42s | 15.40s | 18.49s |
| 5 | 50,007,287 | 20,006,770 | 3.99s | 6.27M/s | 7.51s | 26.69s | 21.55s | 24.61s |
| 6 | 25,010,759 | 15,520,261 | 4.19s | 5.97M/s | 5.83s | 14.42s | 16.46s | 19.53s |
| 6 | 50,015,901 | 20,002,527 | 4.26s | 5.87M/s | 7.38s | 27.77s | 20.52s | 24.64s |

- **5 players:** main stages175.52s; child CPU9.11minutes; sampled peak 3.04GiB. Freeze marker1829, crossing telemetry33,837,795–35,713,752nodes, cap overshoot6,770keys. Final river self-play misses7/8decisions; stored zero-average mass27.6%.
- **6 players:** main stages178.73s; child CPU9.34minutes; sampled peak 3.06GiB. Freeze marker1959, crossing telemetry31,442,336–33,214,235nodes, cap overshoot2,527keys. Final river self-play misses4/4decisions; stored zero-average mass24.8%.

All observed qualification/main thermal states are **nominal**; no observed swap growth, maximum system pressure1. The resource receipt gives available RAM/disk minima and peaks by size/phase. Samples are taken once per second, so peaks may be missed. CPU cost is summed child CPU, not wall time. Active traversal excludes checkpoint save; train wall also includes load/hash/process overhead. Short training windows and partially capped work do not establish mature-table steady throughput. Do not use these M4 rates as measured bb128 rates.

Final sampled training peak divided by retained keys is151.2bytes/key (five players) and150.1bytes/key (six). These include K50/allocator/save overhead and sampling; they are descriptive ratios, not physical record sizes or mature-memory bounds. Ordinary host caches and fixed five-then-six order are retained; no cache flush.

The20Mcap censors later retained growth, not natural saturation. Preserve pre-freeze aggregate entries and per-street training decisions/missing counts in progress; per-street distinct retained rows/visits are audited at endpoints. Those are different counters. The4/5/6 pilots use different seeds and fixed sequential order; cross-size differences are descriptive, not a controlled causal player-count effect.

## Correctness and coverage

Fourteen focused tests pass locally and on M4. Both builds pass 121 native library tests;256 independent engine fixtures cover five/six-player legal play, varied stacks, all-ins and side pots. Tiny100K/200KrealK50 checkpoints match bytes under1/10threads and fresh/resume paths, including capped membership. Qualification verifies180initial policy hands plus180byte-identical reproductions and independent replay.

Main audits every one of **70,282,990 export rows**, and240initial policy hands independently replay with240byte-identical reproductions. Each endpoint plays60hands, all five/six button positions, separate seeded policy instances and one shared read-only weight table. Full source/config/engine/binary/K50/checkpoint/export/trace bindings are retained. Final retained files are reread and their SHA256s match; both M4 research locks are free and source is clean.

The self-play samples are tiny and early, against identical models at every seat. Reached river missingness is descriptive, not general coverage or a trend between differently dealt checkpoints. Table-wide zero-average mass is not the played zero-mass fallback rate. The reused generic policy-play command counts played misses but **does not distinguish reached positive-mass from zero-mass rows**; per-street zero-average mass is also not separately instrumented. No such measurements, learning curve, payoff/interval, strength acceptance or release qualification are claimed.

## Next allocation and provenance

Together with PR406, this qualifies the small-table train/resume/export/play workflow for4–6players. Move toward an actual four-player candidate on bb128 after PR404 releases it, rather than extending these tiny M4 fixtures through further cost pilots. The [four-player campaign draft](../../nplayer-four-player-campaign-plan.md) declares a proposed fresh seed,3B/10Bendpoints, bounded250Mcapacity and a paired development design; a qualified four-player arena and complete measured/historical cost proposal still precede launch. Independent-seed release acceptance remains separate. Search and native algorithm changes remain deferred; PR404 is untouched.

Execution source **37cf758f6b8bb1d246a09863c3d5dd54f4f8361a**, source bundleSHA256f220108d5c41dc761bd060d0b1022992882738a1e406ca0fe8d501db6ec4ed44, main seeds2026102305001/2026102306001. All raw checkpoints/exports/traces/partials/proofs/source/builds remain under `/Users/dberweger/Local/nplayer-five-six-feasibility-20261023` on M4. Source uses shared Git objects from `~/Local/hu200-river-search`; protect that object store, read-only engine venv and K50 paths until owner-managed archival captures a standalone source. No other machine computes, no rerun/extension and no fan/OS/environment change. Cleanup/staging/Drive acceptance remain owner-managed pending; originals retained, no deletion or cloud acceptance claim. Later evidence commits do not replace the execution source.
