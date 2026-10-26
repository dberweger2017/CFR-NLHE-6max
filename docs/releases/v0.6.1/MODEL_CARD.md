# v0.6.1 model card

These three separately qualified 200 BB blueprints are the fixed 10B endpoints
of [PR404](https://github.com/dberweger2017/CFR-NLHE-6max/pull/404), merged as
`bbb71f408db6b1964541e22978628f8c60105313` after five successful checks.
The three 3B comparators remain research evidence; they are not release candidates.
No seed is selected by score and no default is replaced.

| Seed | Actual nodes | Retained rows | Exact binary bytes |
|---|---:|---:|---:|
| 2026102240001 | 10,000,017,024 | 250,002,537 | 14,304,919,746 |
| 2026102261001 | 10,000,003,556 | 250,000,924 | 14,307,166,826 |
| 2026102261002 | 10,000,009,688 | 250,001,937 | 14,306,896,906 |

Float64 little-endian `nplayer-policy-binary-v1`, all-street opponent-sampled
linearly weighted averages, no continuation/search. Original average-mass tags,
checkpoint/export/keyset hashes, game/menu/schema and K50 pins are retained in
[the exact manifest](MODEL_MANIFEST.json). All six checkpoint/export and all six
binary full-row audits passed; reuse those receipts instead of reconverting or
repeating mathematical audits for release packaging.

## Acceptance scope

The [prospective protocol](../../nplayer-bb200-model-campaign.md) froze counts,
roots, fields, endpoints and a single family of 30 one-sided simultaneous 95%
Student-t/Bonferroni lower bounds before confirming hands. All pass:

- 24 scripted-profit bounds >0: each seed against random/random, check-call/check-call,
  TAG/TAG, pressure/pressure, own-3B+call, own-3B+pressure, call+pressure, random+TAG.
  The weakest lower bound is +30.43 BB/100 (seed 61002, pressure/pressure).
- Three own-3B improvement bounds >0: +69.06, +56.94, +67.63 BB/100 in seed order.
  The statistic is half the paired reciprocal singleton-return difference.
- Three cyclic bounds >−5: +59.87, +58.57, +52.54. Each 10B and own 3B play the same
  other-lineage **3B** pair, without halving; this is not a 10B-vs-10B tournament.

10,543,104 initial hands use independent six-seat-permutation deal blocks;
10,543,104 reproductions add no independent information. All initial hands
independently replay and all reproductions match bytes. No extra hands or
strength screening are needed. [Complete results and uncertainty](../../reports/nplayer-bb200-model-campaign/results.md).

## Remaining coverage and evidence limits

Membership freezes near the 250M threshold after a whole iteration and is exact
within each 3B→10B lineage. More training cannot insert missing keys. Stored
zero-average-mass rows are 26.20%, 26.23%, 26.16%; reached check-call river misses
are 17.09%, 16.86%, 16.75%. Found zero-mass river lookups are 0.01%, 0.03%, 0.04%.
These are distinct descriptive quantities, not a controlled coverage improvement
estimate. Missing/zero-mass lookups keep the qualified uniform legal-menu fallback.
The UI's represented-key indicator does not imply positive original mass.

One host, three seeds, one abstraction/menu and capped memberships. Tail-concentration
diagnostics were not emitted by the frozen readout; no outliers were removed.
PR357's adverse/inconclusive relative 100 BB scripted panels remain evidence;
absolute profit here does not erase them. No 200 BB script-relative 3B→10B
regression gate was declared. No equilibrium, universal strength, human or
external-opponent claim, or search adoption follows.

## Provenance and availability

Frozen scientific source `f11edfe5227882980f57925ab0ca93b3a2f790a7`.
Original result SHA256 `6909662e4b2372c13981467723759ba5a37ffde7daa3899514e8d52c72c969b8`;
committed readout SHA256 `3784cd2d4b5b3d79a5461510bf206577aaff0927708ac407a6a4c1008d06e26d`.
The original and committed JSON parse identically; their byte formatting differs.
Research root: `bb128:/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1`.
The manifest retains exact paths and hashes of all six checkpoints, exports,
binaries and mass receipts. Release source is bound separately when assets are built.

No release assets or Drive acceptance are claimed by this preparation. The owner’s
vacuum-cleaner owns research staging/archival; its receipts control archive status.
Released models will use GitHub split assets with existing pinned v0.5.3 K50
assets. Drive is not a mandatory release dependency.
