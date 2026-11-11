# Suit canonicalization: correct symmetry, insufficient imitation gain

November 11, 2026. **Reject this recipe.** A one-shot Runpod pilot finds a small,
uncertain reduction in policy-imitation error and a clear CPU latency penalty.
Do not adopt it or allocate a larger training run on this evidence.

The owner authorized unattended execution within US$5. The
[protocol](../../suit-symmetry-pilot.md) was frozen before GPU execution in
`ccbf1b45`; telemetry handling was hardened in run source `317604a9`.
[Proposal #488](https://github.com/dberweger2017/CFR-NLHE-6max/issues/488)
records the design and authorization before the main run. There was one audit
and exactly six fits, with no tuning, extra seed or outcome-dependent retry.

## What was tested

The existing 612-feature policy encoder uses literal suit channels. We sort the
joint hole/board rank masks to give all 24 global suit renamings the same input.
Only the acting player's hole-card and public-board channels change; all other
features, labels and legal masks remain identical. The production encoder,
playing policies and regret calculation are untouched.

Targets are teacher-0 positive-mass tabular-policy labels from PR467, not sampled
Deep CFR regrets. The teacher's card abstraction uses the suit-invariant native
`class_key`; a frozen neural opponent profile need not be suit-invariant, so old
sampled regret targets would not justify this relabeling. This is an offline
policy-imitation test on existing mixed-field data, not a self-play or strength
test.

All eight source files match PR467's published SHA256 pins. Fixed selection gives
98,304 training and 12,288 test rows, balanced across 3–6 players and
flop/turn/river. The test contains 8,396 original hands. Source random-stream
roots differ across jobs and splits. No selected training/test canonical-input
orbits overlap; no test rows needed purging. [Data receipt](data.json).

Each of three fixed seeds fits raw and canonical inputs using identical initial
weights, batch-index streams, architecture and 1,000 optimization steps.
Initialization hashes match within each pair. No validation outcome selects a
checkpoint or recipe.

## Results

Lower TV-to-teacher error is better. The primary contrast is canonical minus raw,
averaged across the three fixed fits and then equally across original test hands.

| Fixed fit seed | Raw mean TV | Canonical mean TV | Difference | CPU latency ratio |
| --- | ---: | ---: | ---: | ---: |
| 20261111860011 | 0.35456 | 0.35221 | −0.00235 | 1.541× |
| 20261111860012 | 0.35588 | 0.35473 | −0.00115 | 1.696× |
| 20261111860013 | 0.35694 | 0.35446 | −0.00248 | 1.521× |

The pooled difference is **−0.001995**. Its one-sided 95% bootstrap lower/upper
bounds are **−0.004474 / +0.000505**, respectively (together these form a central
90% interval). These condition on the three fixed fits, not a population of
training seeds. They include zero and exclude the predeclared minimum useful
−0.005 gain at the lower-bound gate. The point also misses the −0.01 advancement
threshold. All three seed points are negative, but that alone does not pass.

No player-count or street subgroup has an established >0.01 TV regression under
the seven adjusted safeguards. The median latency ratio is **1.541×**, exceeding
the **1.25×** cap. Raw medians are 298–308 µs/decision; canonical medians are
459–511 µs. The measurement includes Python canonicalization, feature conversion,
network and legal softmax on the same CPU with two threads. This does not measure
an optimized native implementation, but the imitation-gain gate fails separately.
[Full result](results.json), [independent recomputation](verification.json).

The old imitation network does react to suit labels: on 3,072 held-out rows,
the mean per-row maximum TV change over 24 permutations is **0.03814**, p99
**0.13037**. Exact canonical inputs eliminate this representational asymmetry;
that did not translate into a sufficiently large imitation gain here.
[Audit](audit.json).

## Correctness, compute and retention

- Native `class_key` and hand evaluation agree under all 24 permutations on
  1,024 sampled cases per postflop street: **73,728 checks**. Python canonical
  keys match the same 3,072 native cases. The Runpod repeats the Python orbit/key
  check and confirms disjoint selected train/test orbits before fitting.
- Focused Python checks: **9 passed**. Native class-key regression: **1 passed**.
  Full repository run: **2,835 passed, 240 skipped**, with two tests initially
  failing because the temporary environment lacked `tensorboard`. After installing
  that declared dependency, the affected parametrized selection passes **3/3**.
  The full suite was not repeated. The 20-hand six-player game check and 30-hand
  moving-lineup session check also pass. This pilot does not change the native
  trainer or game behavior.
- Fresh Secure Cloud RTX 3090 (24 GB), EU-CZ-1, catalog/read-back **US$0.50/hour**.
  Image `runpod/pytorch:1.5.0-cu1281-torch280-ubuntu2404`, resolved from live
  template `hywnp7k0yl`; PyTorch `2.8.0+cu128`, NumPy `2.5.2`. Six GPU fits total
  **23.70 seconds**; supervised main run **40.33 seconds**. Sampled GPU peak:
  **60°C**, **1,098 MiB**. Training canonicalization: 0.69 seconds for 98,304 rows.
- Pod `nc1q3czuo6cw3k` and temporary 10-GB volume `mn484y0abl` were deleted after
  retrieval. Fresh MCP reads return 404 for both; account lists confirm absence.
  The unrelated pre-existing stopped pod was left untouched. The 55-minute stop
  watchdog was cancelled only after verified deletion.
- Total rental was under three minutes. **Estimated total below US$0.03**, using
  the catalog rate and published storage rates; hourly billing reads had not
  posted records at cleanup, so this is an estimate, not a settled invoice.
  [Compute/cleanup receipt](compute.json),
  [storage pricing](https://docs.runpod.io/pods/pricing).
- The output archive and all **26 output files** were SHA256-verified locally
  before teardown. All six fitted weights, row errors, selected inputs, original
  source files, resource samples and latency samples remain as ordinary ignored
  files under `results/suit-symmetry-pilot/` in this worktree. Small receipts are
  tracked; payloads are not. [Artifact manifest](artifacts.json).

This result closes this specific offline recipe. It neither proves suit symmetry
cannot help a different learner nor changes the six-player strength milestone.
No follow-up compute, deployment, model promotion or release follows automatically.
