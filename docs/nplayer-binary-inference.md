# Exact binary inference loading

[Proposal #358](https://github.com/dberweger2017/CFR-NLHE-6max/issues/358).
Owner approved implementation and small local qualification on October20.
PR357 measured 2656.51 seconds loading versus 5.72 seconds playing in its cyclic
panel, including reproduction. Existing evaluators already retain two models.
This work targets parsing, decompression, allocations and resident representation.

## Scope and acceptance

Add an optional versioned binary derivative of an unchanged policy export.
Preserve float64 bits, sorted keys, owner/street/action identity, averaging scope,
uniform missing behavior and original average-mass tags when supplied. Bind
source policy/checkpoint SHA256, game/key/menu/card identity, dtype, byte order,
counts, offsets and payload hash. Reject corrupt/truncated/mismatched inputs.
No trainer recipe, released model, default, key schema or policy change.

Start with eager validation and a compact sorted row index plus contiguous
probabilities. No memory mapping or lazy verification is needed for this first
implementation. Binary search can cost more per lookup; measure complete play,
not just startup. Keep the existing gzip export/reader supported.

## Qualification and proposed mature benchmark

Instrument file verification and decompression/parsing/index construction before
conversion. Qualify every stored row bitwise and seeded action/trajectory parity,
including missing and zero-mass rows; test metadata/payload corruption and source
binding. Run a reproducible small local load/lookup benchmark, with conversion
reported separately and no global cache flush.

The mature bb128 benchmark is **not launched** by this PR. Before launch, provide
the owner a runtime/CPU/memory/storage quote using the local measurements and the
historical mature load cost. Proposed fixed comparison: same two mature PR357
policies, three loads per format in alternating order under ordinary warm-cache
conditions, honest first-use observations, full-row parity and the same18-lineup
job including reproduction. Record conversion, time to first action, complete
validation/load and play costs, page faults, RSS, physical/logical bytes and
whole-job wall. Target at least2× median mature warm-load improvement and a clear
whole-job gain with identical trajectories. This is a target, not a measured claim.
Existing PR350/355/357 inputs remain read-only. No new training, large evaluation,
other-host work, schedules, cleanup or automatic merge/default adoption.

## Implementation and format v1

[Draft PR359](https://github.com/dberweger2017/CFR-NLHE-6max/pull/359) adds
`nplayer_inference`; existing native policy consumers detect its magic through
`PolicyTable::load`. Choosing a pinned derivative is explicit. Existing gzip
JSON, checkpoints, trainers and model choices retain their current behavior.

The derivative is portable little-endian data, decoded without unsafe casts or
new dependencies. An eager loader verifies the outer file SHA256, header and
payload hashes, then every record and distribution before returning. There is
no mapped file, deferred validation or lazy page work hidden after load. A
sorted index and a contiguous `Vec<f64>` replace individual row allocations and
the hash table. Lookups use binary search, so startup/memory gains can trade off
against lookup latency; the mature complete-job comparison must measure both.

| Region | Content |
|---|---|
| 128-byte prefix | Magic `NPLBIN01`; u64 header length, row/value counts, row/value offsets and total length; header/payload SHA256; eight reserved zero bytes. |
| JSON header (at most 64 KiB) | `nplayer-policy-binary-v1`, unchanged original policy header, source export SHA256, float64, little endian, 32-byte record size, optional audited mass identity. |
| Sorted 32-byte records | 16-byte key; u64 probability start; u8 owner, street, action mask and mass tag; four reserved zero bytes. |
| Probability values | Contiguous original IEEE754 float64 bits, in the original legal-action order. |

Mass tags are unknown/zero/positive, never inferred from whether a normalized
row is uniform. With `--mass`, conversion binds the exact checkpoint-audited
receipt and zero-key SHA256, checks sorted membership, uniform zero rows,
counts and the full keyset. The reader validates all embedded tags and counts;
diagnostics bind the supplied pinned receipt without re-reading the zero-key
list. Without audited mass data, represented rows keep unknown original mass.
Missing lookups continue to use the existing uniform fallback.

Conversion streams the validated source once into separate record/value regions
of one temporary file, with independent file cursors. It does not construct a
second mature table or duplicate the values into a spool. Source SHA256 is
checked before and after reading. Publication uses a same-directory hard link
with no replacement; an existing output or any corrupt/mismatched input fails.
Successful publication removes only its own temporary link. Failed partials
remain for diagnosis. Verification then compares every sorted key, metadata,
float bit and mass tag in a linear full-row audit against the pinned source.

## Commands

Build from the checkout and use fresh ignored outputs:

```sh
cargo build --release --locked --manifest-path native/hu20-trainer/Cargo.toml --example nplayer_inference
native/hu20-trainer/target/release/examples/nplayer_inference convert SOURCE.gz SOURCE_SHA NEW.bin --mass MASS/receipt.json RECEIPT_SHA
native/hu20-trainer/target/release/examples/nplayer_inference verify SOURCE.gz SOURCE_SHA NEW.bin BINARY_SHA --mass MASS/receipt.json RECEIPT_SHA
native/hu20-trainer/target/release/examples/nplayer_inference load NEW.bin BINARY_SHA
native/hu20-trainer/target/release/examples/nplayer_inference load SOURCE.gz SOURCE_SHA --profile
python3.11 -m scripts.benchmark_nplayer_inference --binary native/hu20-trainer/target/release/examples/nplayer_inference --out results/FRESH_FIXTURE_RUN --rows 100000
```

Omit `--mass` from both conversion and full verification for an export without
mass metadata. The load command accepts either format and always validates all
rows. Fine profile counters are opt-in and are not used in load medians: clocks
partition legacy verification, streaming/decompression, parse/validate/allocation
and index insertion, with other work left in total elapsed time. `probe POLICY
SHA KEYS_JSON ROUNDS` reports lookup plus digest time for identical keys; this
is not an isolated lookup microbenchmark or a legal first-action timing.
`first-action K50 POLICY SHA` separately includes policy verification/load, real
pinned K50 initialization and one legal preflop choice at a fixed deck/button/
action seed. It is a startup probe, not a latency distribution across streets.

[Local qualification and mature quote](reports/nplayer-binary-inference/local-qualification.md)
record measured limits. Real K50 play, mature performance, first legal action and
the 18-lineup complete-job comparison remain pending owner acceptance of the
compute quote. No mature result or default adoption follows from local fixtures.
