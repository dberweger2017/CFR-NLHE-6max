# Four-player v0.7: corrected release proposal, revision 3

**Proposal only; mature training and release evaluation remain paused.** The
short [estimator qualification](../../nplayer-warm-estimator-qualification.md)
comes first. Its findings can inform a separate science hypothesis, not launch
a training campaign. Four-player release keeps the existing recipe unchanged.

The [machine-readable protocol](release-protocol.json),
[component quote](release-pricing.json) and
[counts and conditional power](counts-and-power.csv) supersede revision 2.
They restore the agreed **−5 BB/100** cyclic peer margin and **all 24 seatings
for the three mixed fields**. Homogeneous fields and peer comparisons use
eight balanced forward/reverse rotations. Three-player and six-player variance
is not used to size this four-player proposal.

## Acceptance and estimands

Retain PR413's seed `2026102341001` and both checkpoints. Price two independent
seeds `2026102570001/2`, each 0→3B→10B, with the current unpruned K50 recipe,
250M threshold and fixed membership within each continuation. No redundant
3B focal arms are evaluated in scripted profit panels.

All **27 tests** must clear their threshold: 21 absolute-profit tests (seven
scripted/mixed fields × three 10B models), three own-lineage reciprocal tests
and three cyclic fixed-opponent tests. The independent statistical unit is a
deal block after averaging its declared seatings. Reproduction adds no samples.

The reciprocal statistic is
`0.5 × [R(10B_i vs three 3B_i) − R(3B_i vs three 10B_i)]`, with lower bound
strictly above zero. Retain it for continuity with #404's release comparison:
it compares oriented singleton performance across ancestor/successor fields.
**Both the focal and its opponents change.** It is a distinct estimand from a
focal-only improvement against fixed opponents, and proves neither general
superiority nor progress toward equilibrium.

The cyclic statistic changes only the focal checkpoint:
`R(10B_i vs three 3B_next) − R(3B_i vs the SAME three 3B_next)`. No halving;
its lower bound must exceed **−5 BB/100**. The cycle is existing→fresh1→fresh2→existing.

Predeclare **16 fresh banks per test**. Every test must pass BOTH its pooled
block Student-t lower bound and its 16-bank-mean Student-t lower bound, each
at one-sided alpha `0.05/27`. Report the smaller lower bound and every bank.
This fixed rule exposes bank variation without selecting favorable banks or
changing intervals after outcomes. It still relies on distributional assumptions
and cannot certify coverage against rare tails absent from the sample.

## Counts, precision and cost

Counts below apply **to each lineage**. Mixed fields use 24 seatings; other
rows use eight. Profit panels have one focal arm; peer panels have two.

| Gate | Blocks | Seatings |
|---|---:|---:|
| Random profit | 16,384 | 8 |
| Check-call profit | 81,920 | 8 |
| TAG profit | 98,304 | 8 |
| Pressure profit | 180,224 | 8 |
| Check-call/pressure profit | 32,768 | 24 |
| Random/TAG profit | 32,768 | 24 |
| Trained/check-call/pressure profit | 49,152 | 24 |
| Own reciprocal improvement | 98,304 | 8 |
| Cyclic fixed-peer noninferiority | 2,064,384 | 8 |

Total: **121,110,528 initial hands**, plus the same number regenerated into a
hash-only reproduction sink. Every initial hand is independently replayed.
The corrected cyclic count is nearly four times revision 2's count. Mixed-field
variance and bytes are recomputed from the original full 24-seating blocks.

Sizing targets a conservative lower bound of 80% per-gate pass probability
under the listed effect scenarios and **1.5× measured four-player SD**, using
noncentral-t calculations. The CSV also reports 1× and 2× SD scenarios. Peer
SD is an explicitly **unmeasured proxy** from PR413's paired trained-field
contrast; no reciprocal-halving variance discount is assumed. These are
conditional scenarios, not guarantees of joint passage or reproducibility
across training seeds. The first lineage's observed profit is not assumed to
recur. An unresolved test means the family is not qualified; no automatic extension.

The all-NVMe scenario is **23.1 hours central / 45.7 hours reserved**, including
two fresh training lineages, saves, exports, full-row audits, conversions,
model/K50 loads, both arena passes, independent initial replay, readouts and
reporting. Replay and analysis remain substantial costs even when raw repeat
traces are not stored. The quote assumes eight arena workers as in PR413;
it does not claim that writing fewer copies accelerates traversal.

## Storage and release ledger

The all-NVMe scenario needs **850.9 GiB new NVMe**. A conditional bank-at-a-time
staging scenario needs **161.9 GiB new NVMe plus 700.9 GiB new HDD**. Serial
copy and independent readback at provisional 80/64 MiB/s add 3.7 hours centrally
or 7.5 hours reserved: **26.8 / 53.2 hours total** for that option. It is not
admitted or assumed; paths must stay accessible and existing protected inputs
remain retained. No cleanup, compression or deletion gain is credited. Later
ZIP packaging/upload and release publication need separate allocations.

The last read-only snapshot (October 24, 22:31:54 UTC) had **19.0 GiB NVMe** and
**92.6 GiB HDD** free. It reserves nothing. Neither release storage scenario fits;
the all-NVMe scenario also exceeds the device's entire **443.2 GiB filesystem**.
It cannot become feasible through cleanup on that device alone. Staging needs
real additional HDD headroom and owner/cleaner coordination before admission.

**Deliberately defer the exact per-key release-training watch ledger.** Its
checkpoint byte parity and overhead are not qualified. Ordinary growth,
freeze/discard/visit telemetry and played missing/zero-mass/positive-mass lookup
diagnostics remain mandatory. Without an admission ledger, historical missing
keys cannot be classified as never visited versus discarded at freeze. Shadow
qualification does not fill that historical gap. Including a release ledger
later requires parity/overhead qualification and a revised source/budget.

Single-focal generation and the release hash-only writer still require tiny
byte-parity and replay qualification before main. Hash-only reproduction must
regenerate every hand with unchanged RNG behavior, compare ordered block/full
stream digests and lengths, and retain the full first mismatch block. This PR's
smaller diagnostic sink is separate; it byte-compares emitted diagnostic files.

## Reproduction of the quote

`python -m scripts.price_four_player_release` uses the committed
[pricing inputs](pricing-inputs.json) and the existing SciPy runtime. It is scalar
planning arithmetic: no model load or poker run. [Provenance](provenance.json)
records all 16 historical trace hashes, read-only scan cost and input/source
pins. The 24-seating summaries reconstruct before eight-seating estimates are
used; all source trace SHA256s match PR413's original report. The supporting
saved-data scan source is [here](../../../scripts/scan_four_player_seating_variance.py).

Before a release allocation: settle these estimands and conditional precision,
obtain feasible measured storage, qualify the exact implementation and get an
explicit complete budget. No acceptance threshold is relaxed to make it fit.
