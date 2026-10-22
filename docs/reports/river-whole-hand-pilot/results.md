# Frozen river search: whole-hand cost and variance pilot

[PR388](https://github.com/dberweger2017/CFR-NLHE-6max/pull/388), closes proposal387.
**The integration qualifies and the pilot is affordable; playing-strength improvement remains unestablished.**
All 9,216 initial hand instances independently replay, all 9,216 fresh reproductions
match byte-for-byte, and both main stages return0. Search installs in 381/4,608
search-on hands (8.27%). Every nonzero exploratory return interval crosses zero.
There is no automatic larger campaign, training or default change.

## Fixed experiment and verification

The [protocol](../../river-whole-hand-pilot.md) was committed before implementation.
Frozen 100 BB 10B focal seed 2026101935003 plays six declared trained/scripted pairs;
trained peers use the same frozen10B seed 202610200601. Each arm has 128 independent
deal blocks per lineup, each containing all six seat permutations. The independent
variance unit is the paired six-permutation block. Reproduction is verification,
not additional statistical samples. Main roots are2026102138801–806; calibration
and qualification use disjoint reserved roots.

Only focal's legal acting-seat observation enters search. The privileged arena owns
cards/deck/settlement. Both arms share decks and logical-role action RNG streams;
verification requires the first changed action to be installed focal river search.
All paths identical between arms settle identically. The native core also checks
zero-sum accounting. Independent replay uses pokers commit
`5db20e3d5d6862b32a7402035c1340b622d3b005`.

Runtime source is `46caeceb88d24733f393f567c2b1e2fd6300cc4d`.
Main ran October21,21:48:51–22:00:59UTC (23:48–00:00Madrid).
Model SHA256s, source manifest/config/binary pins and original paths are in
[provenance](provenance.json). Later reporting helpers did not change the measured
runtime. No final hand was retried or added after observing outcomes.

Preflight: 111 native and 4 Python tests; 144 fixture hands plus144 byte-identical
fresh reproductions across1/2workers, independent replay and 12 ordinary-arena
search-off parity hands. Calibration1/2/4workers has identical strategic traces,
with the2worker traces independently replayed. Public cases 21/91 separately pass
idempotent zero-advance blueprint fallback for forced legal cap-excluded all-ins.
Those forced paths are controls, not observed poker decisions.

## Coverage and actual continuation

All rows below have768 hands per arm. Root is attempted once only when focal is
the first river actor, with exactly two non-all-in live players. Later first entry
and opponent-first roots remain blueprint-only by design.

| Opponent pair | Root attempts | Installed | Installed / hands | Changed hand paths | Reused search decisions | Off-tree hands |
|---|---:|---:|---:|---:|---:|---:|
| Trained / trained |74|73|9.51%|31|27|0|
| Trained / pressure |56|56|7.29%|27|28|0|
| Pressure / pressure |26|26|3.39%|7|17|0|
| Check-call / check-call |0|0|0%|0|0|0|
| Check-call / pressure |195|193|25.13%|69|0|0|
| Random / TAG |33|33|4.30%|18|25|1|
| **Total** |**384**|**381**|**8.27%**|**152**|**97**|**1**|

There are 1,906 hands with an actual river decision:1,407 begin two-live and 499
three-live. Focal has already folded in 629 of the two-live hands. Of the remaining
778 two-live focal-involved rivers, 384 have focal acting first and 394 are excluded
because the opponent acts first. Thus installation covers49.0% of these778 rivers,
or29.8% of all 1,277 focal-involved rivers. Automatic all-in runouts without a
river action are not counted as river-decision hands; no live all-in player appears
at the recorded first river decisions. These are lineup-specific pilot frequencies.

Check-call/check-call has 470 three-live rivers and 296 two-live rivers after focal
has folded. Its zero searches and identical arms do **not** establish a zero
population effect, zero future variance or a successful strength safeguard.

Three roots reach2,048 sweeps and fail the unchanged capped-game quality target:
trained hand183 (0.19666BB exploitability), check-call/pressure hands74 (0.10484BB)
and344 (0.11764BB). All use blueprint; one subsequent decision repeats that quality
fallback. Declared-game quality installation is381/384 (99.22%), not every-root
qualification. This is projected modeled-law quality, not a full-menu, exact-belief
or safe-resolving guarantee. Historical PR386 harms remain relevant.

Of99 subsequent focal decisions with a retained session,97 read the solved policy
with zero new solves. One reads the original quality fallback; one falls off-tree.
The observed omitted response is a raise to3,700 chips after
check→100→1,900, with two prior raises; it is neither all-in nor at the cap.
The controller plays blueprint thereafter. One event among381 installed hands
(0.26%) is insufficient to dismiss off-tree vulnerability; this pilot does not
replace saved cases 21/91 or measure adversarial full-menu quality.

The152 changed hand paths (3.30% of search-on hands) contain163 same-draw action
changes across focal decisions. [Seat coverage](seat-coverage.csv) preserves physical
seat results; aggregate rates are not a claim of seat-uniform coverage.

## Complete latency, throughput and resource costs

Root timing includes blueprint lookup, observation reconstruction, beliefs,
preparation, solving, quality screening and action selection. All 384 attempts,
including failed-quality fallbacks, are included.

| Opponent pair | Mean root seconds | Median | p95 | Maximum |
|---|---:|---:|---:|---:|
| Trained / trained |0.626|0.453|1.563|3.064|
| Trained / pressure |0.572|0.428|1.594|3.057|
| Pressure / pressure |0.536|0.410|1.284|1.287|
| Check-call / check-call |—|—|—|—|
| Check-call / pressure |0.533|0.426|1.316|3.094|
| Random / TAG |0.557|0.446|1.633|1.837|
| **All attempts** |**0.559**|**0.430**|**1.367**|**3.094**|

Overall p99 is3.057s. Retained reads average21.3μs (99 requests), including
fallback reads. Root work sums to214.55request-seconds, or46.6ms of root work per
search-on hand; that is summed worker work, not additional batch wall time.
Solve work is199.18s,93.1% of nonoverlapping instrumented native components.
Inclusive `native_before_serialization` is not added again. The median alone
understates both mean decision cost and tails.

| Cost | Initial | Fresh reproduction |
|---|---:|---:|
| Two shared model loads + K50 |234.91s|235.16s|
| Play + serialization/write/flush |125.55s|125.94s|
| Complete native batch |360.61s|361.26s|

Four measured workers share two read-only tables; models load once per batch,
not per lineup or worker. Calibration play/write1/2/4workers takes7.34/5.84/4.60s;
selection uses cost and exact parity only. This is not a general fourfold speedup.
Main measurement is726.20s, followed by2.02s readout: **728.23s/12.14min total**,
910.42childCPU-s/15.17CPU-min. Independent replay plus pairing/hash verification
inside measurement takes 2.88s; this cannot be interpreted as pure replay CPU time.
Model loading remains64.5% of main wall time despite amortization. No model
conversion, checkpoint save or training occurs; durable-fsync latency is not
separately measured from buffered trace writes.

Sampled family RSS peaks27.70GiB; minimum available RAM is94.97GiB.
CPU peaks65°C and Thermistor15 64°C; swap remains350.7MiB with zero growth.
Minimum free NVMe258.74GB and HDD530.87GB. Sampling every~2s can miss short peaks.
Main traces total66,068,928bytes plus3,463,735bytes of decision timing logs.
Successful qualification13.62min, calibration12.07min, public controls2.02min
and main12.14min total39.84min of stage wall time, excluding setup, failed
preflight, handoff gaps, analysis and archival.

The published main planning envelope was12.8–40.4min. Actual runtime is slightly
below its lower forecast, well below its admitted upper forecast. No counts,
settings or guards were changed to finish sooner. [Full accounting](costs.json),
[calibration and controls](calibration.json), [operational summary](operational.json).

## Exploratory returns and variance

The contrast is focal singleton search-on minus search-off, averaged across six
permutations per deal block, in BB/100. It is not a pooled individual-player score.
These unadjusted Student-t95% intervals describe this one-seed pilot, not a
predeclared strength acceptance gate.

| Opponent pair | Paired mean BB/100 | Exploratory95% interval | Block SD | Largest squared-block-contrast share |
|---|---:|---:|---:|---:|
| Trained / trained |+2.90|[−24.68,+30.48]|157.68|53.5%|
| Trained / pressure |+26.76|[−7.58,+61.10]|196.34|80.2%|
| Pressure / pressure |−13.67|[−39.49,+12.14]|147.59|99.6%|
| Check-call / check-call |0|No intervention; uninformative|0|—|
| Check-call / pressure |−25.91|[−68.47,+16.65]|243.32|20.0%|
| Random / TAG |+14.19|[−8.50,+36.89]|129.77|27.2%|

The concentration statistic uses each block's **uncentered squared contrast**,
not an additive decomposition of centered variance. Sparse changed hands and
large-pot tails make the variance estimate fragile. Neither positive mixed-field
means nor negative pressure means justify a strength verdict or post-hoc tuning.
The raw numeric zero-width interval for check-call remains in the machine readout
for reproducibility, explicitly labeled uninformative here and in the CSV.

## Conditional next-study cost, not launch authorization

Using only trained/trained's normal-model upper95% block SD179.78BB/100,
a one-sided0.05/3 primary family and nominal80% power at stipulated true effects:

| True effect scenario | Blocks per primary / lineage | All hand instances,3 lineages incl. reproduction | Conditional total hours |
|---|---:|---:|---:|
|1BB/100|285,029|20,522,088|109.7–327.9|
|2BB/100|71,258|5,130,576|27.7–82.6|
|5BB/100|11,402|820,944|4.8–14.0|

These extrapolate the measured trained-pair play/load/replay cost to three
unmeasured lineages. Upper forecasts use3×play,2×load/replay and≥600s replay
reserve. They exclude scripted safeguards, additional qualification and across-seed
variance calibration. A chi-square variance bound assumes normal blocks and
cannot bound unseen rare poker tails. These are sensitivity scenarios, **not a
ready-to-launch campaign quote or empirical pass chances**. Full code/arithmetic
is in [scenario metadata](future-cost-scenarios.json); the frozen readout also
retains per-lineup sample-size scenarios. We cannot promise a precise1–2BB gain
verdict from a short overnight campaign.

Next, qualify off-tree continuation in a separate small correctness-first task,
using saved omitted-response cases and consistent beliefs/retained hero policies.
Do not assume re-solving repairs the weakness. Before a larger strength study,
freeze its primary opponents, margins/families and effect target, obtain a new
budget, and address the fragile variance forecast. Keep the blueprint/menu and
exact audit oracle unchanged; runtime optimization remains secondary.

## Reproduction, failures and retention

From the measured source, the original guardian `qualify`, `calibrate`, `main`
commands and launch/config receipts are preserved in the owned root. Do not rerun
those campaign commands merely to inspect results. Existing `readout` consumes
verified files only. Operational tables can be reconstructed without playing:

```sh
PYTHONPATH=FROZEN_SOURCE python scripts/summarize_river_whole_hand_pilot.py \
  /home/dberweger/river-whole-hand-pilot-20261021-v2/main-v1 --out FRESH_OUTPUT
```

The reporting helper is a later evidence addition outside the frozen runtime;
its SHA256 is pinned in operational.json. Model inputs remain external read-only
PR367/361 derivatives, with exact hashes/paths in provenance. No originals,
other jobs, environments, fans or driver settings were changed or deleted.

The first qualification stopped before real fixture/final hands because a native
test detected non-idempotent repeated-query diagnostic metadata. The strategy was
unchanged; stable metadata was fixed, then a fresh owned attempt qualified. A new
clone's Git alternate/prerequisite setup failure before build/hands is retained.
Archival setup also found no `gh` executable on bb128 before copying; the current
PR state was instead read locally and transferred. After the immutable ZIP upload,
the deployed receipt tool rejected the `/research` symlink spelling. Receipt
recovery used the existing canonical HDD path, without reupload or changing the
deployed tool. These are preserved plumbing
findings, not hidden scientific retries.

Original roots (including failures) remain
`bb128:/home/dberweger/river-whole-hand-pilot-20261021{,-v2}/`.
[Archive receipt and both retrieval routes](archive.json) records current archival
acceptance. Protected model/K50/Git/environment dependencies stay outside the
archive and are retained. No archival receipt authorizes their deletion.
