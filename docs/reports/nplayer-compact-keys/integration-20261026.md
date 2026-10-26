# PR344 integration and review closeout — October 26, 2026

PR344 is integrated with current main after the live-order schema, binary
inference, persistent arena and later training options landed. This closeout
finishes the opt-in engineering implementation. It does not run the refused
1B/3B benchmark, change a default or establish mature-table speed.

## Scope and distinction from live-order keys

| Schema | CLI option | Information and compatibility |
|---|---|---|
| Released history | `history` (default), alias `v1` | Existing byte format, button-relative owner, unchanged checkpoint/export bytes |
| Live-order | `live-order` | Existing coarse information abstraction and owner semantics; unchanged |
| Compact history / BLAKE2b | `compact-blake2b-v2` | Complete history information encoded more cheaply; distinct key bytes and schema |
| Compact history / xxh3 | `compact-xxh3-v2` | Same compact history payload, different explicit hash/schema |

Compact schemas implement the original complete-history representation, not a
compact version of live-order. PR431's gains and PR434's independent lineages
remain separate research. No compact default or speed benefit for live-order
has been demonstrated. All original pilot reports and the larger benchmark's
budget refusal remain unchanged.

## Conflict resolution

Current main's `KeySchema::History`/`LiveOrder` dispatch and `CashGame.schema`
remain authoritative. The two compact choices join that enum rather than
replacing the newer API. The diagnostic three-encoding API delegates to the same
decision builder as production lookups, removing duplicate encode/hash logic.
The key benchmark explicitly refuses live-order because its information sets
are not an exact re-encoding of the history arm.

The merge retains current pruning/admission/pressure options, binary loaders,
policy mass metadata, persistent arena/model caches, K50 cache reuse and optional
200 BB support. Legacy history-only arena headers remain unchanged. A mixed
encoding arena compares common game identity after removing only schema and its
encoding binding; each policy pin records its own schema/binding. The simpler
`nplayer_policy play` command retains its existing same-identity restriction.
No old source or research payload is edited.

## External review findings and resolution

### 1. Pin key bytes and legacy serialization

Golden tests pin all four formats for four legal observations: three-player
preflop, unequal-stack heads-up flop, six-player river and six-player turn at
the engine's 10^12-chip limit. Postflop card classes are explicit synthetic
labels, so these isolate encoding/framing rather than K50 bucket generation.
They cover all streets, betting/board transitions, rotated buttons, uneven
stacks and varint lengths. The existing randomized legal-history test retains
its observed bidirectional mapping across 2–6 players. Neither test constitutes
exhaustive game-state enumeration.

A small fixed history checkpoint and average export have pinned SHA256s:

- Checkpoint: `d59e809bf2528035acb36834e30b617e51089476f12d2b40bf2ce841de347885`.
- Average: `20e4ef9031f8dd124068240b3fcceb43aa7013bb54a78ae4bf1afb6c3d54c406`.

These pins and the history/live-order key golden values were separately checked
against a copy of main's original production source, with only test code added.
The comparison uses no K50 files, mature models or new poker evaluation.

### 2. Prove the xxh3 selection and remove duplicated code

Fixed xxh3 key digests differ from the BLAKE2b digests and fail if both paths are
accidentally changed to BLAKE2b. Production and diagnostic variants share
`decision_from_cards`; the benchmark mapping audit cannot silently exercise a
separate implementation. The dependency remains exactly `xxhash-rust=0.8.15`.

### 3. Fail closed on compact schema mislabeling without rejecting sparse tables

New compact identities require a `key_encoding` object containing the explicit
schema, `nplayer-passive-key-selftest-v1` probe version and a digest over fixed
preflop/abstract-postflop encoding probes at 2, 3 and 6 players. The loader
recomputes it using the selected encoder. Both expected compact binding digests
are golden-tested. Cash checkpoint, gzip-policy and binary-policy readers use
the shared validation path.

Changing only a compact header's schema to history, live-order or the other
compact hash is rejected even after re-pinning the file SHA. Unbound compact
prototype files are deliberately refused. History/live-order files without this
new field remain supported and byte-identical. Existing prototype files and
original readers stay preserved; no automatic rewrite, relabeling or migration
is performed.

The review suggested requiring known root rows. This implementation uses an
encoding self-test instead: a valid sparse or empty policy need not contain any
particular root. Tests cover both sparse and empty compact policies. The binding
is a format/implementation consistency check, not an authentication scheme or
a proof that arbitrary externally rewritten rows use the claimed encoding.
Removing/rebuilding metadata and re-pinning a deliberately altered file remains
outside the accidental single-field relabel guarantee; external artifact SHA
pins remain essential.

### 4. Document xxh3 byte order

The stored key is `xxh3_128(payload).to_le_bytes()`, seed zero. All 16 bytes are
used. This is the reverse of the conventional big-endian XXH128 digest display.
For an equivalent unsigned integer `h`, use `h.to_bytes(16, 'little').hex()`;
reverse canonical digest bytes before comparing to the stored hex. This
convention is preserved rather than silently changing the v2 key bytes.

### 5. Make coverage claims precise

The original 100M-node audit used three players at 20 BB. Its every-row results
remain evidence for that executed workload. Separate legal-history payload tests
cover other player counts/stacks using synthetic postflop labels. New golden
cases add the legal engine chip limit; a separate varint test reaches `u64::MAX`
for serialization arithmetic only. That is not a legal poker-stack claim.

## New correctness qualification

The integrated library adds a small preflop-only training fixture with actual
fold settlements and terminal truncation at the flop. It compares history and
both compact encodings, canonicalizing each retained row by the observed key
mapping. Across 1/2/4 threads, complete versus save/resume runs agree exactly in
nodes, iteration counts, visits, owner/street/menu, regret bits and average bits.
This is an estimator regression fixture, not Hold'em strength evidence.

Policy tests cover all four schema identities through gzip and binary
conversion/loading, preserving every probability bit and row identity. Compact
schema relabel tests cover both policy and checkpoint readers. Unknown formats,
unbound compact prototypes and corrupted bindings fail closed; valid legacy,
sparse and empty files remain supported.

The full native library and example compilation, benchmark self-tests and
relevant Python checks are run before publication. Final counts and CI status
are recorded in the PR body; the original pilot's counts are not relabeled as
new integration tests. All ordinary test outputs remain in the isolated local
checkout under ignored `planning/compact-finish/`; no research input, bb128 job,
M4 job, cache tool or archive policy is changed.

## Evidence and future work

Read [the original pilot](pilot.md), [unchanged pilot receipt](pilot-receipt.json)
and [historical protocol](../../nplayer-compact-key-benchmark.md) for the measured
4.97M/7.12M/7.85M nodes/s and 8–12% complete-workflow gains. One fixed-order small
pilot does not establish mature performance, speed with live-order keys, memory
benefit or an overnight campaign saving.

The original source/checkpoints/mappings/failures remain at the report's
protected bb128 path; this integration does not access or modify them. Original
cloud acceptance remains pending unless separately receipted. No new mature
benchmark, new seed, default, release or scientific continuation is authorized
by merging this PR. A later performance comparison should target a measured
current-runtime need and receive a separate budget.
