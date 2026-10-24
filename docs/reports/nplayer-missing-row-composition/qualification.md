# Missing-positive-row composition: engineering qualified, mature quote pending approval

[PR423](https://github.com/dberweger2017/CFR-NLHE-6max/pull/423),
[proposal422](https://github.com/dberweger2017/CFR-NLHE-6max/issues/422),
[protocol](../../nplayer-missing-row-composition.md).

The opt-in arena player and one-use campaign controller are implemented.
**M4 qualification passes all 28 stages in 88.95 seconds:** 121 native library,
15 paired native and 23 focused Python tests; 384 initial hands independently
replay and reproduce exactly. **No mature-model arena has started**, no new
training or exports, and no strength result is available. The owner selected
the experiment; the separately priced mature allocation below is not accepted yet.

## Exact selection rule

1. If the key exists in the 250M/10B base, use its existing float64 vector,
   including its zero-mass uniform fallback. Do not consult the donor.
2. Otherwise, use the 500M/10B donor vector only when its original average mass
   is positive. A uniform vector can still be learned; vector shape is no proxy
   for mass.
3. Otherwise, use the existing uniform fallback over the legal menu.

The two tables remain immutable and separate. A composed alias holds references,
not a materialized union or a second copy. Three physical tables are resident in
trained/mixed fields: base250M/10B, donor500M/10B and fixed peer250M/3B.
No extra model loads per seat. Each seat retains an independent action RNG;
the composed sampler uses the original one-draw/accumulation/rounding sequence.
A change after a donor lookup can alter later histories; preserving base rows
is not a claim that complete trajectories remain unchanged.

Schema/menu/card/game/full-average scope must agree. Source/mass receipts bind
all physical files; a virtual policy digest binds the composition rule and both
source pins. Composition is opt-in focal-only; ordinary manifests remain byte
compatible with the pre-composition arena. No released/default player changes.

## Qualification evidence

Native forced rows cover all nine presence/mass combinations, zero-base precedence
with positive donor, positive-mass uniform donor, unknown mass, wrong row identity,
nonuniform zero fallback and incompatible schema/average scope. The independent
Python oracle reads the existing small audited exports/zero-key receipts, compares
exact float64 bits for **all 428 composed decisions**, and verifies selection,
row identity and legal menus. Six decisions actually use donor rows in the tiny
arena; forced tests cover branches not reached naturally, including zero mass.
These frequencies are engineering fixtures, not mature usage estimates.

Across all eight fixture fields, initial/repeat and serial traces agree exactly;
diagnostics on/off leaves ordinary payload/action RNG unchanged. Identity
composition (base as its own donor) matches the plain base hand payload exactly.
Composed-versus-itself traces are byte-identical with exact-zero contrast.
The ordinary base/donor case matches the preserved pre-composition arena bytes.
Every initial hand independently replays; opponent fields, seating and deal
blocks reconcile. A copied tag intentionally corrupted after execution is refused
by the independent oracle. No protected source is modified.

Peak sampled family **1.11 GiB**, thermals always nominal,
stage CPU **219.00s**. Twelve existing fixture binary/export/mass
files total4,268,484bytes; no new model export or training was performed.
Both successful qualification-v1 and final qualification-v2 are preserved.
Final source **`c8b257e635e042ae2742268be2fc095e9d46ab15`**, 1,403 source/config pins;
raw qualification result **`c488e06f8382297f311e41bc564b2ef72df929517d773297b234d86a1e17eff3`**.
[Compact source/binary/proof/cost receipt](qualification.json).

## Complete arena-only allocation to accept

**58.87min central /117.74min reserve;
propose 2h15m (8,100s) on bb128**, including target-host exact-source build/small
qualification, all initial/repeated games, independent replay, selection accounting,
global readout and report. These are planning scenarios, not elapsed-time stops
or completion guarantees. No training/save/export/conversion cost is included.

| Component | Central min | Reserved min |
|:--|--:|--:|
| bb128 exact-source build/tests and same small qualification allowance | 10.00 | 20.00 |
| initial plus reproduction arena, measured PR419 whole stages | 21.59 | 43.18 |
| all initial independent replay, measured PR419 | 6.09 | 12.17 |
| eight paired summaries, measured PR419 | 2.25 | 4.50 |
| all composed-decision accounting, conservatively retain PR419 shared-proof cost | 3.77 | 7.53 |
| global input/trace pin checks, absolute/tail readout, measured PR419 allowance | 5.18 | 10.36 |
| compact report and reconciliation allowance | 10.00 | 20.00 |

The mature components use **same-host PR419 measurements**, not M4 speed
extrapolation. Its two arena stages total21.59min, including **20.08min reported
model loads** and45.85s play. Those nested load/play numbers are not added again.
Retain the measured shared-proof cost as a conservative selector-accounting
allowance; this new pipeline has not yet been benchmarked with mature tables.
Linux build/small qualification and reporting are explicit allowances. Ordinary
host caches and the independently owned HDD backup may affect actual costs;
no global cache flush, isolation claim or measured speedup is made.

No new mature model artifact is produced. Plan **24 GiB NEW storage**, comprising
16GiB trace allowance,2GiB source/build/proofs/reports and6GiB working allowance;
this is not a live free-space floor. Manual snapshot at2026-10-24T15:11:52.467297+00:00 finds
**32.32GiB NVMe free**, so the current scenario fits with
8.32GiB beyond its included working allowance.
No filesystem reserve or proposed cleanup gain is counted. Three-table sampled
peak in PR419 was54.05GiB; plan75GiB memory, without an RSS cutoff. Current
MemAvailable122.76GiB, CPU34°C /
Thermistor15 29.5°C. Recheck resources before launch;
no reservation or mature root exists at this snapshot.

## Counts, prospective rules and precision

Propose **4,096 fresh independent deal blocks per field**, eight unchanged PR417
fields,12balanced forward/reverse circular seatings and control/composed arms:
786,432initial hands plus equal byte-identical reproduction. Initial hands all
independently replay; average the12seatings within each deal block for uncertainty.
Fresh roots20261024750001–8 are distinct from prior studies and qualification
roots20261024759901–8. Trained opponents remain the fixed250M/3B peer; never replace
them with the composed player. Retain all paths, fallbacks, unchanged actions,
position/lookup/source counts, tails and adverse results.

One family of eight one-sided95% Student-t/Bonferroni lower bounds, df4095:
trained lower>0, seven script/mixed lowers>−5BB/100. Passing all gates plus a useful
gain supports considering independent confirmation; it never authorizes adoption.
No gain or unresolved/adverse safeguards means no promotion and a separate concrete
visitation/history decision. No extra hands, tuning or automatic science retries.

**Composition-pair variance is unmeasured.** The table below illustrates the
precision at this count if trained-field SE is the same as PR419's full-replacement
comparison, half as large, or one quarter as large. Approximate pass probabilities
use a normal power approximation with the predeclared t critical value; they are
not measured powers or bounds.

| SE factor vs PR419 | Assumed SE BB/100 | Ordinary95% half-width | True+5 pass | True+10 pass | True+25 pass |
|:--|--:|--:|--:|--:|--:|
| 1.00 | 19.87 | ±38.96 | 1.2% | 2.3% | 10.7% |
| 0.50 | 9.94 | ±19.48 | 2.3% | 6.8% | 50.7% |
| 0.25 | 4.97 | ±9.74 | 6.8% | 31.4% | 99.4% |

Even the quarter-SE scenario does not promise a small-gain verdict. Neutral
scripted effects can also fail the−5 safeguard when imprecisely estimated;
passing all eight is more demanding than one primary test. The complete
[quote/scenarios](quote.json) retain all fields' prior eligibility counts.
On the old PR419 histories, missing-base/positive-donor opportunities range
0.51–4.03% of focal decisions (trained2.41%). Those are **different policies'
histories**, not predicted usage, return or variance for the composed player.
Rare large pots can dominate despite low activation frequency. No automatic
extension follows an inconclusive result.

The player still falls back uniformly on every observation missing in both
models; it cannot directly fill the44,274 shared check-call river observations
that both missed in PR419. Earlier donor choices may change which histories are
reached. Added rows may be weak or incoherent with the smaller model's earlier
strategy; qualification establishes the selector, not strength or equilibrium.

## Remaining launch gate and preservation

The [research-proposal rule](../../../CONTRIBUTING.md#research-proposals) requires
acceptance of this concrete allocation before main. The owner receipt must bind
the exact scope and quote SHA; no receipt was invented here. The prepared configure
entry point also requires completed same-source M4 and **bb128 small qualification**,
unchanged model/mass/K50/runtime pins and manual resource review. Target-host
qualification is budgeted and still unstarted; the mature arena cannot bypass it.
Normal/study locks are nonblocking. Only the existing CPU90°C /Thermistor15 100°C /
missing-nonfinite thermal resource stops apply; ownerSTOP/mutex/correctness also
terminate. No time/RSS/disk/swap cutoff is added. Partial evidence remains incomplete,
never a smaller acceptance run. Both finite M4 qualifications finished, no timer,
observer, mature model play or other-machine experiment was created.

Ordinary source, fixtures, failures/partials if any and proof/results remain at
`m4:/Users/dberweger/Local/nplayer-missing-row-composition-20261024/` and ignored
M1`planning/missing-row-composition/`. Existing417/419/shared dependencies remain
protected. The cleaner later creates complete relative-path ZIP archive sets on
bb128 HDD and uploads them to the matching Drive PR folder with verified receipts;
research-payload Drive acceptance is pending. No research deletion, pre-ZIP or
loose payload upload is performed here.
