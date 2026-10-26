# Overnight three-player 20 BB blueprints: verified results

All three fixed seeds reached 30B nodes and passed export/every-row audit.
The final study completed October 19 at **08:44:04 UTC / 10:44:04 Madrid**.
All 36 lineups passed independent replay and exact reproduction before readout:
**1,769,472 final hands plus 1,769,472 reproduction hands**.

The result is mixed. Two same-seed comparisons improve; seed1541 is inconclusive,
so the predeclared all-three improvement gate **fails**. All three cyclic
cross-seed comparisons pass the −5 BB/100 safeguard and have positive intervals.
All three models regress against random opponents, and seed1542 also regresses
against check-call under the declared twelve-comparison adjustment. Retain the
30B models as research candidates; do not promote the family as uniformly
stronger or infer that another tenfold training increase is the best next use
of compute. No model selection, extra hands, default change or release follows.

[PR346](https://github.com/dberweger2017/CFR-NLHE-6max/pull/346) ·
[Proposal345](https://github.com/dberweger2017/CFR-NLHE-6max/issues/345) ·
[Frozen protocol](../../nplayer-overnight-blueprint.md) ·
[Compact completion receipt](completion.json).

## Peer-policy comparisons

| Comparison | Final seed → anchor seed | BB/100 [nominal 95% interval] |
|---|---|---|
| Same | 1541 → 1541 | +1.66 [-1.54, +4.86] |
| Same | 1542 → 1542 | +5.89 [+2.88, +8.91] |
| Same | 1543 → 1543 | +4.59 [+1.46, +7.72] |
| Cross | 1541 → 1542 | +5.57 [+2.41, +8.73] |
| Cross | 1542 → 1543 | +4.41 [+1.31, +7.51] |
| Cross | 1543 → 1541 | +5.43 [+2.37, +8.49] |

Each comparison has 8192 paired independent six-hand blocks in each singleton
orientation. The statistic is the mean of (30B-singleton return minus
anchor-singleton return)/2, **not pooled player return**. Consistent improvement
requires each same-seed lower95 bound >0; the cyclic safeguard requires each
cross-seed lower95 >−5. A failed gate can be inconclusive; seed1541 is not a
proven loss. Nominal intervals are conditional on these fixed model instances,
not simultaneous intervals or estimates of training-seed population variance.

The ~3B anchors are PR340's 600-active-second fast averages. Cyclic opponents
are two copies of another seed's anchor, not mixed trained/scripted populations.
No PR336 pruning, compact-key schema or search was used.

## Scripted opponents

Each final and anchor policy plays as singleton against two identical bots on
matched deals. Changes below are **full singleton-return differences**, without
the peer contrast's division by two. Intervals use the predeclared Bonferroni
adjustment over all twelve comparisons (family 95%).

| Seed | Opponent pair | 30B − anchor, BB/100 [family 95% interval] |
|---:|---|---|
| 1541 | random | -21.46 [-32.01, -10.91] |
| 1541 | check-call | -12.65 [-27.36, +2.07] |
| 1541 | tight-aggressive | -2.89 [-6.46, +0.69] |
| 1541 | pot-pressure | +2.06 [-3.55, +7.66] |
| 1542 | random | -23.53 [-34.31, -12.75] |
| 1542 | check-call | -17.81 [-32.36, -3.27] |
| 1542 | tight-aggressive | +1.11 [-2.48, +4.71] |
| 1542 | pot-pressure | -2.40 [-7.85, +3.06] |
| 1543 | random | -27.77 [-38.37, -17.16] |
| 1543 | check-call | -6.65 [-21.21, +7.90] |
| 1543 | tight-aggressive | +1.54 [-2.16, +5.24] |
| 1543 | pot-pressure | -1.07 [-6.46, +4.32] |

All twelve 30B singleton means remain positive: random **+82.82 to +99.00**,
check-call **+156.30 to +162.86**, tight-aggressive **+33.87 to +38.77**, and
pot-pressure **+23.83 to +28.75** BB/100. These are descriptive absolute means;
this table reports uncertainty for the paired change, not absolute-return
intervals. The remaining adjusted differences cross zero. Peer-policy gains
and reduced exploitation of some scripts can coexist; these observations do
not establish the strategic cause or imply any release qualification.

## Training, memory and costs

| Seed | Nodes | Table entries | Retained-lineage active training | M nodes/s | Train / save peak GiB | Final save |
|---:|---:|---:|---:|---:|---:|---:|
| 1541 | 30,000,002,144 | 109,378,727 | 97.31 min | 4.63 | 9.81 / 10.40 | 373.0 s |
| 1542 | 30,000,001,659 | 108,248,711 | 92.70 min | 4.85 | 9.72 / 10.29 | 369.0 s |
| 1543 | 30,000,005,834 | 111,013,468 | 101.98 min | 4.43 | 9.91 / 10.49 | 397.6 s |

Active training excludes checkpoint I/O, loading, monitoring, exports and audits.
It combines only segments in the retained lineage from each ~3B anchor; it
excludes recomputed work after guard stops. Full model/checkpoint hashes, paths,
iterations and timings are in [models-and-training.csv](models-and-training.csv).
Every table stays below the150M cap; discarded keys/visits are zero. All three
full-average audits pass across **328,640,906 rows**.

The final continuation took **152.31 minutes wall / 18.36 child CPU-hours**:
91.13min third-seed training-stage wall, 5.69min export, 12.15min audit,
37.12min final play/reproduction/replay and 1.52min readout, plus input checks
and preservation/controller overhead. Completed first/second models were reused
without retraining, re-export or repeated audit. Model loading dominated final
play: first-pass median **98.56s** per lineup, maximum157.79s. Four evaluation
workers; training uses all16 logical CPUs with fixed8 roots/seat.

The overall observed campaign spans **13h24m56s**, October18 19:19:08 through
October19 08:44:04UTC, including owner-response/overnight pauses. Recorded
successful stages total **54.75 child CPU-hours**. Exact whole-campaign CPU time
is unavailable because the two failed training stages did not write final CPU
receipts;54.75h is a lower bound, not a complete bill. The last periodic events
show at least **9.68B recomputed nodes /34.37 active minutes** after the two
stops. Do not present retained-lineage speed as total end-to-end efficiency.

Training peaks at9.91GiB and saving10.49GiB. Final evaluation peaks at
**63.99GiB family RSS**, with at least33.74GiB available RAM. Maximum recorded
CPU74°C/Thermistor15 95°C includes the original95°C crossing; the final
continuation peaks atCPU73°C/Thermistor94°C. No final-continuation guard stop.
Sampled RSS is based on roughly500ms samples and can miss short peaks.

Host swap rises to **23.09GiB during evaluation**, while available RAM remains
above33.74GiB. Swap is telemetry only as explicitly authorized. These host-wide
samples do not identify which process/tmpfs pages were swapped or establish
that swap was cost-free. Earlier traces lack absolute-swap telemetry; their
CSV cells are empty, rather than falsely claiming zero usage. Physical NVMe
free space stays at least55.48GB; HDD at least1.154TB in the final continuation.

## Coverage and seats

Represented-key coverage among encountered policy decisions, counting only the
first play pass and excluding scripted-policy slots:

| Street | 30B | ~3B anchor |
|---|---:|---:|
| Preflop | 100.0000% | 99.9996% |
| Flop | 99.9993% | 99.9932% |
| Turn | 99.9951% | 99.9665% |
| River | 99.9602% | 99.1835% |

Coverage improves descriptively, particularly on the river, while scripted
returns sometimes regress. Encountered histories differ, so this is not causal
attribution or proof that coverage determines strength. Mean peer contrasts
are positive at BTN/SB/BB in all six comparisons; no additional significance
claim follows. [Role/seat/position intervals](seats-and-positions.csv),
[case/identity/street counts](coverage.csv), [all18 contrasts](strength.csv).

## Retained failures and limitations

- The original95°C guard stopped the first seed before20B on October18
  20:46:30UTC. Its10B checkpoint was retained; the proposed20B handoff never
  activated. The owner explicitly authorized recovery from10B at100°C.
- The first recovery setup refused before a native child because of an incorrect
  zero-swap assumption. Corrected recovery completed two seeds, then stopped
  seed1543 near12.20B at01:34:58UTC on256.54MiB **absolute** host swap. Only
  about122.25MiB was new, and82.37GiB RAM remained available. This overly
  conservative guard/accounting choice caused the interruption.
- The owner removed the swap stop and explicitly authorized one remaining-work
  allocation. It launched06:11:45UTC with an unchanged4h cap, retained prior
  failures and source, reused completed models and finished before10:11:45UTC.
  No automatic retry, outcome-based extension, checkpoint selection or reduced
  final matrix occurred. Historical source/deadlines remain recorded.

One host, three fixed seeds, 20BB/K50/menuv1 only. No mixed-population robustness,
six-player strength, exploitability, search or release conclusion. Live scripted
curves reused development roots and were not used for final selection; final
roots were fresh and frozen. Thermal and swap policy changes affect cost and
recovery history; they do not change the native algorithm or final deal matrix.
The original and recovery reports remain part of this record, not overwritten.

## Provenance, reanalysis and storage

Frozen native source `4cd199a5fef18b24cac188617d767b3f49a422de`, binarySHA256
`54d2bc7b727737fdd5e92aecc4464583ea3c374a92e3f9b0f8485e64ba652d84`.
Separate deployed controller hashes are in the completion receipt's active
metadata. Later Git integration/report commits were not deployed to the study.
The precomputed settled result was retrieved byte-for-byte and checked against
SHA256 `e47b9e07bae8a6ad1f898a8c4175ffb070807dc1f1dac716e713566ab912a695`.
[Exact result bytes](source-results.json), [compact receipts](completion.json),
[stage timing/resource aggregates](stage-costs.csv). Every case's replay receipt,
trace digest and selected model identity is retained. These are existing proof
receipts; no new full-trace audit or model download is claimed at this handoff.

Recreate tables from the compact receipts into a fresh ignored directory:

```sh
python docs/reports/nplayer-overnight/summarize_completion.py \
  docs/reports/nplayer-overnight/completion.json \
  docs/reports/nplayer-overnight/source-results.json \
  --out results/overnight-reanalysis-FRESH
```

The summarizer verifies exact result bytes, all36 case/replay identities and
counts, all18 nominal/adjusted intervals, paired means, declared gates and all
three model audit/checkpoint identities. It does not train, play or reopen raw
hand traces. The readout had already hash-checked both traces and independently
replayed all hands before settling the result.

Raw evidence and models remain onbb128 under the original and recovery roots:
`/tmp/nplayer-overnight-20261018`, `...-20261018-resume100-v2`, and
`/tmp/nplayer-overnight-20261019-finish-noswap`. Hash-verified preservation copies
remain under `/mnt/data2tb/research-cloud/PR-346-nplayer-overnight-blueprint/`,
with matching continuation subdirectories. Final traces were written directly
to the final continuation's `evaluation/` cache directory. Source/qualification,
TensorBoard logs, all failures/checkpoints/exports and PR340 shared inputs remain
protected. Only compact metadata was retrieved to this Mac's ignored results.

PR346 remains open; Research-Cloud ZIP/upload acceptance is **pending**. No
archive or cleanup was started at this handoff, and no Drive restoration is
claimed. Existing source-root and cache paths, hashes and input retrieval pins
are indexed in RESULTS_INDEX. Preserve originals until authorized closeout.
