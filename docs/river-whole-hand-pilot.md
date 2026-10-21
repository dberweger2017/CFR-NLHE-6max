# Frozen river search: whole-hand cost and variance pilot

Owner approved implementing this plan and running its qualified, separately
quoted pilot on October21,2026. This is engineering/cost calibration, not a
confirmatory strength study. No training, menu tuning, exact-runtime optimization,
off-tree re-solving, defaults or release change.

## Frozen intervention and legal scope

Use PR386's `pot-jam-cap3-root-min-responses-v1`, projected-product beliefs,
DCFR(1.5,0,2), checkpoints8/16/32/64/128/256/512/1024/2048 and stop at
min(1%pot,0.1BB). Only focal policy differs between search-on and search-off.
Focal is the frozen100BB10B seed2026101935003, binary SHA256
`d835f61f4a5407bd47e8f8a5da849ef82c16ad21fce32f15dce72d5997275189`.
The fixed trained peer is seed20261020060110B, existing binary SHA256
`23599816cf632a51cace45f25d70ed4918fe5e75875c33136d8629052a8a2a70`.
Pin source, binaries, full input metadata and K50 before measurement.

Begin at most one search per hand, only when focal acts at the FIRST river
decision, exactly two players remain active, neither all-in and the current
single-contested-pot contract is supported. If another player acts first, or
three-way play later becomes heads-up, stay blueprint-only; count these cases.
Only the acting seat's legal observation enters the policy/search boundary.
Hidden cards/deck, seeds and future outcomes are privileged arena data only.
Beliefs retain the existing blueprint-modeled law, including folded actions;
they are not the actual scripted opponents' posterior.

Retain the solved strategy through on-tree actions with no new solves. Preserve
blueprint fallback for unsupported/zero-reach/quality-miss roots and, after the
first omitted action, for the rest of the river. Unexpected numerical, legal,
identity or accounting failures are terminal, not ordinary fallbacks. A capped
all-in is reported as both off-tree and stack/cap-boundary where applicable.

## Fixed lineups, pairing and counts

Focal singleton versus these two fixed opponents, in this order:

1. peer/peer;
2. peer/pot-pressure;
3. pot-pressure/pot-pressure;
4. check-call/check-call;
5. check-call/pot-pressure;
6. random/tight-aggressive.

Each lineup gets128 independent duplicate-deal blocks, each with all SIX seat
permutations, for search-off and search-on. Total9,216 initial hand instances,
plus9,216 fresh reproductions. The independent variance unit is a paired
six-permutation block, not individual hands or reproduction copies. Couple deck
and logical-role action RNGs across arms, using the existing native arena law;
an action change must first occur at focal's eligible river action.

Reserve final roots2026102138801–806, fixture roots2026102138891–896 and
calibration roots2026102138871–876; check uniqueness against current protocols
before final play. Qualification/calibration never enter pilot estimates.
One focal lineage suffices for this cost pilot; no three-seed strength claim.
No outcome-based stopping, configuration selection, added hands or retries.

## Qualification, calibration and launch admission

First qualify the native whole-hand adapter with small fixtures and realK50:
search-off parity to the existing arena; acting-observation isolation; stable
sampling; root eligibility; retained rows; expected fallback causes; session
release/hand isolation; malformed/mutated input rejection; fresh reproduction;
and independent engine replay. Include saved cases21/91 and capped all-ins.

Load read-only models/K50 once per batch and share the existing arena tables.
Measure small1/2/4-worker calibration before selecting the highest measured
useful concurrency with identical outputs; no unmeasured speedup assumption.
Calibration has four blocks/lineup/arm at each concurrency, excluding startup
reuse effects from per-hand cost but reporting them separately. Build/test time,
model loads, play/solves, logs, reproduction and independent replay enter the
whole-job quote. Preserve sparse-call/rare-tail uncertainty and use mean work,
not median decision latency. Publish the quote HERE and in the PR before main.

The owner accepted a provisional1–3h bb128 pilot. Main admission requires
qualification passed, immutable inputs/source, both compute mutexes, and the
published conservative upper quote at most3h. Otherwise stop at the quote.
This is an admission forecast, not an elapsed kill timer. Resource stops remain
CPU90°C/Thermistor15100°C or missing/nonfinite required sensors; owner STOP and
correctness failures stop only this study's process groups. No RSS/disk/swap
cutoff; inspect disk/RAM/swap manually. No other jobs, environments, fans,
drivers, original inputs or schedules are changed. No scientific retry.

## Outputs and interpretation

Before global readout require all fixed cases complete, fresh reproduction
matches every strategic field, every initial hand independently replays and
source/input/count/zero-sum/pairing proofs pass. Timings and process handles
are excluded only from deterministic comparison, never from cost reporting.

Report first-river composition and eligible/attempted/installed search rates
per hand, calls/hand, retained reuse, same-draw action changes, fallback causes,
off-tree frequency/first action and cap/all-in status. Give mean/p50/p95/p99/max
decision latency, total hand/batch latency, loads, solve/replay/reproduction/I/O
wall and CPU, sampled family RSS, temperatures, manual free disk/RAM/swap and
artifact bytes. Denominators include all hands and every fallback.

For each lineup report paired block returns, SD/SE and exploratory intervals,
plus variance sensitivity and tail concentration. Pilot means are not strength
gates or tuning evidence. Sparse search or unstable variance means inconclusive,
not permission to top up. Quote a future separately frozen three-lineage study
from measured search frequency, mean total cost and conservative variance;
report requested-effect/margin scenarios rather than a guaranteed pass chance.
No automatic confirmation follows. PR317's eventual HU200 findings inform that
later design; its absence does not establish transfer to this three-player game.

Keep models/traces/profiles/logs off Git. Preserve all new outputs/failures and
source/control pins in the owned root; original PR350/355/357/367/380/382/384/386
inputs and Git dependencies stay read-only. Archive only owned new evidence
through the deployed cache workflow after checking PR/dependency state; no
deletion or Drive acceptance claim before a verified receipt.
