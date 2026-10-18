# Three-player blueprint promotion: verified results

**The fast model family passes both predeclared gates.** All three same-seed
comparisons improve on the production1B references; all three cyclic cross-seed
comparisons clear the −5 BB/100 noninferiority margin. Recommend using all three
fast averages as the next v0.6 blueprint candidates, retaining production1B as a
comparison baseline. Search validation and any default or release change remain
separate decisions.

[PR342](https://github.com/dberweger2017/CFR-NLHE-6max/pull/342) implements
owner-authorized [proposal #341](https://github.com/dberweger2017/CFR-NLHE-6max/issues/341).
[Protocol](../../nplayer-blueprint-promotion.md); [input pins](../../nplayer-blueprint-promotion-inputs.json).

## Strength comparison

| Comparison | Fast seed | Production seed | Oriented singleton contrast, BB/100 [95% interval] |
|---|---:|---:|---:|
| Same seed | 1541 | 1541 | +5.92 [+2.55, +9.30] |
| Same seed | 1542 | 1542 | +5.38 [+1.96, +8.80] |
| Same seed | 1543 | 1543 | +4.35 [+0.87, +7.83] |
| Cross seed | 1541 | 1542 | +3.02 [−0.42, +6.45] |
| Cross seed | 1542 | 1543 | +5.18 [+1.71, +8.65] |
| Cross seed | 1543 | 1541 | +5.58 [+2.22, +8.94] |

Every primary lower bound exceeds zero. Every secondary lower bound exceeds −5.
The 1541-versus1542 cross-seed comparison is inconclusive for improvement;
passing its noninferiority gate does not establish a gain. No seed was selected,
no extra hands were added and no failed gate was replaced with a pooled result.

The statistic is the mean over paired independent six-hand blocks of
(fast-singleton BB/100 minus production-singleton BB/100)/2, **not pooled
individual-player return**. Each comparison has 8192 blocks per orientation.
Intervals are nominal two-sided 95% Student-t intervals conditional on these
six fixed model instances; they do not estimate training-seed population variance.
The joint claim uses predeclared conjunctive gates, not simultaneous intervals
or best-seed selection.

## Model family, seats and coverage

Fast seeds1541/42/43 use PR340's 600-active-second endpoints at
2,949,726,632 / 3,003,671,483 / 2,910,499,919 nodes, representing
44,661,934 / 44,216,070 / 44,406,527 keys. Production references are the
previously audited PR292 1B-node averages. No new training or export occurred.
Exact policy and parent-checkpoint hashes are in the pinned inputs.

Both singleton roles' per-seat and button/small-blind/big-blind intervals are
in [seats-and-positions.csv](seats-and-positions.csv). Descriptively, the mean
oriented contrast is positive at every relative position in all six comparisons;
this is not an additional simultaneous significance claim.

Encounter-weighted represented-key coverage across the final lineups:

| Street | Fast | Production |
|---|---:|---:|
| Preflop | 100.000% | 99.999% |
| Flop | 99.999% | 99.991% |
| Turn | 99.984% | 99.963% |
| River | 99.972% | 99.912% |

Counts and each identity/street are in [coverage.csv](coverage.csv). These are
coverage rates on encountered decisions, not estimates of all possible states.
Policies encounter different histories; this association does not explain the
strength gain causally or measure visit density.

## Verification and compute

All 12 cases passed native play, exact reproduction and independent replay with
pinned pokers commit `5db20e3d5d6862b32a7402035c1340b622d3b005` before global
readout: **589,824 final hands plus 589,824 reproduction hands**. Excluded
qualification used another 144 final and 144 reproduction hands. Every measured
stage returned0; no failure, retry or guard stop. All six policy hashes and the
arena binary matched; the binary enforces the original three K50 table hashes.

Focused local validation:16 tests and5 subtests pass;2 optional native-arena
checks skipped because the M1 checkout has no compiled arena. The pinned bb128
arena was exercised by every smoke and final lineup. Staged repository artifact
and whitespace checks also pass.

Frozen orchestration: `d6cb8ebdb9384142b78d8ee93fa609b9dbe6b133`.
Arena source: `8f6fb76dade872b6ab282f1a0a4f6f3abee7dbfa`.
Launch October18 **16:38:01 UTC**, complete **16:50:09 UTC**.

| Stage | Wall | Child CPU | Sampled family peak RSS |
|---|---:|---:|---:|
| Qualification, full-model loading and smoke | 5.52 min | 32.34 min | 56.21 GiB |
| Final play, reproduction and replay | 6.10 min | 35.67 min | 56.22 GiB |
| Verified readout | 0.50 min | 0.50 min | 0.11 GiB |
| Total including controller overhead | **12.13 min** | **1.142 hours** | **56.22 GiB** |

Six independent workers had affinity across CPUs0–15, with single-thread
BLAS/OMP. The final stage averaged 5.85 logical CPUs of child work; this is a
six-worker evaluation measurement. Model loading dominates: median first-pass
load69.40s, play3.11s and independent replay9.50s per lineup. Timings are
descriptive on one host, not a controlled scalability comparison.

Maximum CPU package **69°C**, Thermistor15 **81.5°C**, swap growth **2.75 MiB**;
minimum available RAM **65.47 GiB**, free NVMe **55.70 GB**. Output growth was
about **2.99 GB**, below the fixed5GB budget and above the50GB free floor.
RSS samples are500ms apart and may miss short peaks. No training, model/table
copy, fan, driver, OS, cache or cleanup changes. The existing venv was read-only:
Python3.11.17, NumPy1.26.4, SciPy1.17.1; replay receipts pin the engine Git commit.
[Stage costs](stage-costs.csv), [case costs and trace hashes](case-costs.csv).

## Limits and next step

Three fixed seeds on one host, three-player20BB/K50/menuv1 only. Cyclic secondary
opponents are two copies of another seed's policy, not mixed opponents or a
broad population. Training procedure and accumulated nodes both change, so this
compares blueprint families rather than isolating either cause. It establishes
neither six-player strength, exploitability, search strength nor a v0.6 release.

The next useful implementation is the bounded three-player search pilot in
PR334, using this family as candidates and keeping the old baseline. No
additional training or search experiment is launched by this result.

## Reproduction and retained evidence

Check out the frozen source and verify [input SHA256s](../../nplayer-blueprint-promotion-inputs.json),
restoring from the PR292/PR340 indexed provenance if needed. The launch receipt
pins all673 deployed source/config files. The source archive contains `scripts/`,
`src/`, this protocol/input JSON and its focused test. Controller command:
`python -m scripts.nplayer_blueprint_promotion run ROOT`. Do not restart science
or run the controller over its existing root.

For read-only result reanalysis on bb128, from the frozen source use:

```sh
python -c 'from pathlib import Path; from scripts.nplayer_blueprint_promotion import read; print(read(Path("ROOT")))'
```

Replace ROOT with `/home/dberweger/nplayer-blueprint-promotion-20261018` and use
the input-pinned PR340 venv Python. The reader checks every trace digest and the
complete global barrier before computing intervals; it plays no additional hands.
The settled results already exist at `ROOT/results.json`.

[Strength CSV](strength.csv), [role/seat/position intervals](seats-and-positions.csv),
[coverage](coverage.csv), [complete compact receipt](completion.json).
Raw traces, excluded smoke, source and logs remain on bb128 at that root.
Research-Cloud archival is pending; no upload acceptance or deletion is claimed.
PR292 and PR340 model roots remain protected dependencies. Compact retrieval:
SSH reads only results, manifest/launch/admission/freeze, stage/case/replay receipts
and resource aggregates; no raw model or hand trace was copied locally.
