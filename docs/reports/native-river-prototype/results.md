# Prepared native river prototype: values agree, full-range solving is 31–36× faster

[PR373](https://github.com/dberweger2017/CFR-NLHE-6max/pull/373), issue372,
implements the owner-approved first deliverable. All twelve prepared cases
complete in **72.48 seconds** on bb128. Numerical correctness passes; the
preserved fixed-work quality-agreement screen is **34/36**, so the overall JSON
status is **`quality-threshold-not-met`**. This is a standalone review candidate,
not an adopted live search or a poker-strength result.

## Measurements

Six public river roots each use 8 and 1,081 hypothetical holdings per seat,
16/64/256 sweeps and three native repetitions. Roots come from three-seat hands
with two active players, unequal stacks near 100 BB, different public boards and
pots of 2.00/3.00/11.90/12.90/61.41/141.61 BB. The existing Python reference compiles
9/39/45-node prepared trees with a **two-raise cap**. These are not qualification
of the complete N-player production menu or every possible 100 BB river tree.

For the six full-range cases, each row below spans the per-case timing medians:

| Sweeps | Native solve ms, range | Prepared compact roundtrip ms, range | Median solver speedup |
|---|---:|---:|---:|
| 16 | 4.62–23.65 | 8.85–29.99 | 32.34× |
| 64 | 18.29–90.31 | 22.46–98.77 | 33.02× |
| 256 | 72.33–364.19 | 76.69–366.45 | 33.77× |

Every full-range endpoint passes the unchanged 5% quality screen: **18/18**.
Individual solver speedups versus the dense Python reference range 30.89–36.11×.
The native child high-water RSS is **43.00 MiB** over the benchmark; that excludes
the Python dense reference, mature blueprint weights and future range inference.
The scalar/Python terminal-vector maximum absolute error is **1.63e-13 BB**.

Compact roundtrip includes preparing the supplied tree/ranges, JSON input/output,
solving, best-response diagnostics and returning a selected average action row.
It excludes constructing ranges from legal observation history, loading a model,
live tree building and full-hand execution. Full debug-profile roundtrips are
recorded separately in [all 36 measurements](measurements.csv). There is no
universal 15 ms claim: full-range 16-sweep roundtrips already range8.85–29.99 ms,
and higher solution quality costs additional sweeps.

## Correctness and quality are separate results

All cases pass independent hand-rank/tie ordering, every terminal's dense value
comparison in both orientations, one uniform first-sweep accumulator comparison,
and two-sweep gradients/own-reach averages under identical supplied nonuniform
profiles. Each native and Python learned average is independently evaluated by
the other implementation's value/best-response calculation. Native repeats
produce identical mathematical outputs. **75 native library tests and 58 focused
Python tests pass**; the new tests include blockers, identical holdings, zero
mass, invalid input, persistent transport recovery, fixed policies, numerical
failure without partial publication, independent engine settlement with odd
folded dead money, and a nearly blocked chance-law regression.

The strict screen is `max(1e-7 BB, 5% of reference exploitability)` at each declared
endpoint. Two small 8-holding checkpoints of case 2 miss it:

| Sweeps | Python exploitability BB | Native exploitability BB | Native−Python BB | Interpretation |
|---|---:|---:|---:|---|
|64|0.51854749|0.57553373|+0.05698624|10.99% worse at this fixed work|
|256|0.18953886|0.17177268|−0.01776618|9.37% better; also outside symmetric agreement|

The remaining 16 small-range endpoints and all 18 full-range endpoints agree
within the screen. Smaller is better here. No endpoint or threshold was changed
to obtain agreement; the original finite grid finishes and retains both flags.
Tiny initial regret differences can change subsequent CFR strategies. Identical
supplied-profile values/gradients still agree. This supports a rounding-sensitive
trajectory explanation, not a guarantee that every untested discrepancy is benign.
The small-range differences need review before choosing integration acceptance
criteria. Exploitability here applies only to the stipulated two-player prepared
game, not the original three-player game or an unknown opponent range.

## Implementation and limits

The Rust module uses the existing hand evaluator, float64 state, sorted rank
prefixes, per-card removal sums and identical-holding correction. Traversal
buffers are reused; both traversers use one frozen profile before publishing
regrets, and averages use actual own reach and linear iteration weights. A
strict prepared-input JSON boundary and persistent process remain off the live
play path. The existing trainer, Python reference and release models are unchanged.

The supported chance law is explicitly normalized product weights conditioned
on disjoint cards. The Python exporter checks the actual joint matrix and refuses
other correlations. It does not infer a true folded-player posterior. Normalizing
chance mass and locating identical holdings still use allocation-free quadratic
preparation. Leaf evaluation is linear in ordinary cases. Compatible chance mass
below 1e-4 explicitly selects a scalar fallback to avoid cancellation; that mode
has no linear-cost promise. Every timing case used `sorted-linear`.

This is one Intel i7-10700KF/Linux host, rustc 1.99.0/LLVM 23.1.1, optimized build,
one solver thread and one BLAS thread. The release upload ran concurrently.
Native medians use three warm process repetitions, the Python solve one timing
per endpoint. There is no isolated-host, cold-start or p95 tail, M4-native-versus-this
solver, safe-resolving or playing-strength claim. Independent review and a later
range/decision adapter are needed before a strength study is quoted.

## Reproduction and retained development failures

Measured clean source: **`7e905da4be0c640e6518f2b68eaf330104e81788`**. The
[compact JSON](results.json) pins every relevant source file, native binary,
engine identity, request fingerprint and timing/quality result. All recorded
source hashes match that commit; subsequent changes are report/documentation only.
Results SHA256: `27846c3e24fa17807ca7d4fd30fd1c705a98ddebb75a01a09a32d9873bffd1cc`.
[Test and retained-file proof](verification.json).

```sh
cargo build --release --locked --manifest-path native/hu20-trainer/Cargo.toml --example river_prepared
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python -m scripts.benchmark_native_river --out results/FRESH_NATIVE_RIVER
python docs/reports/native-river-prototype/summarize.py \
  results/FRESH_NATIVE_RIVER/results.json results/FRESH_NATIVE_RIVER/summary
```

The benchmark requires Python 3.11, NumPy and the pinned engine. It loads no
blueprint. It returns measurement completion separately from the JSON quality
screen; callers must inspect `status`, not treat a completed process as adoption.

All originals remain under `bb128:/home/dberweger/native-river-prototype-20261020/`.
The final result is `qualification-v4/results.json`; exact test outputs are
`native-final-tests.log` and `python-final-tests.log`. `qualification-v1` and`v2`
stopped on overly strict second-sweep accumulator equality; `v3` stopped on the
case 2/64 quality discrepancy now preserved in the complete v4 grid. Neither value
correctness tolerances nor the 5% quality screen were relaxed. Earlier smoke runs,
source bundles, binaries and the targeted case 2 diagnosis are retained. An initial
broader legacy test collection required unavailable Torch; the focused environment
was created separately, with no changes to old environments. Full CI supplies
its normal dependencies. No weights, training or strength matches ran.

A verified at-rest copy of compact evidence, test outputs, source bundles and the
native binary is retained in the 2 TB cache at
`/mnt/data2tb/research-cloud/PR-373-native-river-prototype/`. Its manifest is pinned
in verification.json. Research ZIP/Drive acceptance remains pending; the release
upload is separate, and no original or partial was deleted.
