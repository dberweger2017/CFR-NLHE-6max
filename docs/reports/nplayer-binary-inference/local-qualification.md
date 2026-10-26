# Exact binary inference — local qualification and mature quote

[PR359](https://github.com/dberweger2017/CFR-NLHE-6max/pull/359),
[proposal358](https://github.com/dberweger2017/CFR-NLHE-6max/issues/358),
[format and commands](../../nplayer-binary-inference.md).

The optional reader passes local exactness/integrity checks. The final generated
100,000-row fixture loads **3.16× faster** by median native elapsed time.
Binary search has a cost: the lookup-plus-digest probe takes **1.62× as long**.
Keep this as an engineering candidate pending mature complete-job qualification;
there is no mature performance, strength, release or default-adoption claim.

## Measured small fixture

One macOS arm64 laptop, release binary, deterministic keys/probabilities,
2–6 action rows, 380,000 float64 values. Conversion and a complete row audit
precede six fresh child processes in fixed ABABAB order. Ordinary filesystem
cache; first recorded loads are already cache-touched, not cold-cache claims.
No global cache flush or selection among repeated timings.

| Format | Median validated load s | Median process wall s | Median child CPU s | Max process RSS MiB |
|---|---:|---:|---:|---:|
| gzip-json | 0.129664 | 0.134643 | 0.133402 | 12.812 |
| binary | 0.041093 | 0.044051 | 0.043019 | 10.172 |

All load timings include file SHA256 plus complete parse/semantic validation.
Process wall/CPU also cover startup, output and table destruction; native load
stops when the validated table becomes available. RSS is Unix wait4 per-child
peak, not model-only memory, and this small table cannot forecast mature density.
[All six observations](loads.csv), [compact receipt](local-qualification.json).

Conversion: 0.5117s process wall / 0.2211s CPU;
full-row audit: 0.1952s wall / 0.1928s CPU.
These one-time costs are separate from load speedup. Both full row bits and the
133,120 lookup-plus-digest results match, including 2,048 explicit missing probes.
Probe times: JSON 0.014615s, binary 0.023656s;
SHA256 work is included, so these are not isolated lookup latency estimates.

Logical file bytes: gzip 5,440,945, binary 6,241,020
(binary 1.147×).
Filesystem allocated bytes (st_blocks×512): gzip 6,000,640,
binary 6,242,304; filesystem allocation does
not establish unique physical device ownership. Every measured load has zero
major faults; minor faults and per-process accounting remain in the receipt.

One separately instrumented legacy load reports verification 0.016173s,
streaming/decompression 0.046986s,
parse/validate/allocation 0.053642s,
index insertion 0.002593s, total 0.134255s.
Per-row clocks change timing; this observation is excluded from load medians.
Conversion, audit and process pins plus execution-source hashes are in the receipt.

## Correctness and review

- All 63 native library tests pass. After the final streaming/publication changes,
  all four binary test groups pass again; all four mass-helper integration tests
  and three Python CLI/benchmark tests pass. Four release policy/arena examples build.
- Full-row bit parity across current/average/scoped-average and 2–6 players;
  signed zero, non-binary fractions, empty tables and missing fallbacks remain exact.
- 72 seeded legal trajectories in a unit test match every decision, transition and
  settlement, with both stored and missing states. Their explicit toy card
  assignments are a unit fixture, **not real K50 qualification**.
- Corrupt prefix/header/payload, truncation, lengths, offsets, duplicate keys,
  bad owner/street/actions, nonfinite values, dtype/endian/schema/menu changes
  and wrong source/receipt pins refuse. Semantic corruptions are also tested
  with recomputed internal and outer hashes. Existing outputs never overwrite.
- Audited mass tags preserve zero/positive/unknown distinctions; diagnostics bind
  the embedded tags to the exact receipt. A normalized uniform row alone does
  not imply zero original mass.
- Primary-agent source review checked streaming memory, checked arithmetic,
  offsets, atomic no-replace publication and unchanged policy sampling. It is
  not independent review approval. No trainer/game/observation/regret math changes.

CI full-suite results are separate; local qualification runs the affected tests,
not the entire Python dependency stack. The new CLI is built by the existing CI
native step before Python tests. Real K50 first-action and mature complete-job
performance remain unmeasured.

Earlier local-v1/v2/v3 fixture runs are retained development measurements, not
additional samples pooled with this final source. Source/binary/fixture pins in
the receipt identify this final run. Raw fixtures and child logs remain ignored
under `results/nplayer-binary-inference-20261020-local-v4/`; no model enters Git.

## Proposed mature bb128 quote — not launched

Use exactly seed202610200601's PR357 3B/10B average policies, each 250,001,069 rows,
with their pinned mass receipts. PR357's indexed policy SHA256s are
`9890286b1cb5d4cf71380d7cd07c6d220ac98e7b05cc6165837cd60b426bbf78`
and `fbb0b16f8459376519c9ea81c2c2d33b8c08d36efeb8cc2ca9d148eaf08b8843`.
Copy into fresh owned NVMe paths after verifying the read-only PR357 sources.

1. Freeze source/binary/input pins and a small real-K50 parity qualification.
2. Convert both policies once, including audited mass; report conversion separately.
   Perform complete linear row/key/probability/mass audits against the originals.
3. Three sequential loads **per policy per format** (12 loads), in fixed alternating
   order, ordinary warm cache, no cache eviction. Record the earlier first-use
   conversion/audit context honestly. One separate profiled legacy load;
   fixed real-K50 startup first-action probes per format/policy.
4. Run the unchanged first fresh lineage's 18-case matrix with both formats,
   including its reproduction and independent replay. Same roots/counts/order,
   8 arena workers, two resident models. Only trace-header artifact pins may
   differ; all hand/action/payoff/lookup rows must match exactly. Within each
   format, reproduction files must match byte-for-byte. No strength selection.
5. Report complete wall, conversion, validated load, first action, play/replay,
   CPU, faults, process/family RSS, allocated/logical bytes and temperatures.
   Require ≥2× median warm-load speedup per model and lower complete-job wall;
   record a negative result without extending the experiment.

**Forecast: 90–150 minutes wall, roughly 2–3 child CPU-hours**, including build,
read-only input restoration, two conversions/full audits, 12 load samples and
both complete jobs. This uses the historical ~240–300s mature load cost plus
conservative binary/conversion/I/O allowances, not a linear extrapolation from
100k rows. Readers/conversion are sequential and mostly single-threaded; only
play uses 8 workers. Expected peak RSS is below the prior two-model ~66GiB
sampled peak; allow ~80GiB in the planning estimate, not a new arbitrary stop.

Read-only October20 host check: 16 logical CPUs, 135GB physical RAM reported by
/proc/meminfo, ~132GB available, NVMe **60.95GB free**, HDD **932.81GB free**
(decimal GB; RAM rounded from KiB). A bound of 80bytes/row gives at most 40.01GB
for both derivatives. Source gzip copies total 11.84GB, audited zero-key inputs
~2.37GB. PR357 retained 6.30GB for this completed 18-case comparison, so
both formats need ~12.61GB for initial/reproduction evidence. Allow **about
68–70GB total new files**, including receipts/build, at the conservative
maximum binary row width.
The converter needs no duplicate value spool; publication's temporary hard link
shares the same file blocks. The conservative total exceeds current NVMe free
space. Acceptance must include a storage arrangement for only new PR359
outputs: propose verified staging of completed comparison evidence to the
2TB cache, keeping accessible paths, and sequential phase/case staging if
needed after exact derivative sizes are known. Existing source models remain
untouched. No staging/cleanup has started; recheck exact sizes and free space
before launch, and return with a revised quote if safe working space is still
unavailable. No heavy live work is planned on the HDD.

Use the owner's CPU90°C / Thermistor15 100°C thermal stops; inspect disk, RAM and
swap manually. Correctness, accounting, hashes, owner stop and thermal failures
remain terminal; preserve partials with no automatic scientific retry. No new
training, machine, time extension, global cache flush, cleanup, default change
or merge. Fresh owned results will eventually use
`PR-359-nplayer-binary-inference` under the research-cache policy; archival and
Drive acceptance remain pending. Existing PR350/355/357 inputs remain unchanged.

**The agreed protocol requires owner acceptance of this mature compute quote
before launch.** The PR remains draft pending that qualification.
