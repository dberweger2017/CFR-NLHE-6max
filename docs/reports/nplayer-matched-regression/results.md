# Matched-state diagnosis: real action shifts, aggregate cause unresolved

The10B policies do change decisions on identical legal observations: on the
held-out sampled random+TAG states, betting/raising falls about4.1–4.3percentage
points in both lineages. The conditional panel finds **two clear local10B root
improvements and30 inconclusive states**, with no conclusively negative root
mixture. Some negative point estimates are substantial, but the declared
bounded intervals cross zero. This neither identifies the aggregate scripted
regression's cause nor proves that no value was lost.

Keep the independent peer gains from PR357 and the adverse scripted results as
separate evidence. Retain10B as a research candidate, not an adopted release
default. This diagnosis does not replace the fresh v0.6 acceptance protocol.

## Completion and fixed scope

[PR362](https://github.com/dberweger2017/CFR-NLHE-6max/pull/362),
[proposal360](https://github.com/dberweger2017/CFR-NLHE-6max/issues/360) and the
[frozen protocol](../../nplayer-matched-regression.md) use the two fresh PR357
lineages202610200601/02, each its own unchanged3B/10B averages and fixed
membership. Original PR355 remains discovery, not a third confirmation seed.

Root `bb128:/home/dberweger/nplayer-matched-regression-20261020/main-v1`
completed **October20,10:14:29UTC /12:14:29Madrid**. All20 stage return codes are0,
no failure file exists, and the global result is settled. Frozen runtime is
`b7214c13`, source bundleSHA256
`5d679438a2ee071dfbec01f58f4cd2e85c1b518729bb381b3600f42782d74d46`,
configSHA256 `f0124162899058163a3ac9b8edc8cac0f25e3b2caead7c25d2108494669fd58d`.
Global resultSHA256:
`63143278bd4d165da1a9c7306b0908ebf3e9ede6ba023d11363b56d13841f4a9`.
Later branch updates are integration/evidence, not changed runtime science.

The job queued85.12min behind PR361, then ran81.47min including qualification,
restoration, conversion/audits and verified storage. After the loader's exact
parity dependency passed, native qualification and a complete two-state
real-K50 synthetic-row fixture passed before the first scientific evaluation.
M1 qualification had68 native library tests, four Python tests and a release
build; the runtime repeats the five focused native test groups. No mature
scientific failure/retry, extra states or outcome-driven extension occurred.
The owner requested a preliminary read only after both scientific readouts had
settled; final checks preserve those results unchanged.

## Identical observations and descriptive shifts

Eight pinned archived initial traces supply393,216 source hands. The frozen
outcome-blind sampling rule retains **1,002 and968 states**, respectively.
All64 field/reach/street/split strata are populated; nine river strata have
16–30 observations rather than32. The maximum2,048-state budget is not filled
with replacements. These deliberately stratified samples are **not weighted
estimates of the opponents' naturally reached decision distribution**.

On every retained observation both models see the same acting player's own
cards, visible board and public action prefix. Reconstructed key/menu identity
passes. Held-out observations are separate from the discovery observations used
to select conditional tests. The following averages pool both reach policies
within the declared held-out strata; percentages are action probabilities,
not realized action counts or population frequencies.

| Lineage | Field | Held-out states |3B bet/raise %|10B bet/raise %|Change pp|
|---|---|---:|---:|---:|---:|
|601|random/random|247|31.52|31.10|−0.42|
|602|random/random|228|29.44|27.44|−2.00|
|601|random/TAG|256|31.58|27.43|−4.14|
|602|random/TAG|251|31.79|27.47|−4.32|

The random/TAG shift is mainly postflop: flop/turn/river betting/raising falls
about4.8–7.5pp in the two samples, while preflop rises about1.6–1.7pp. Changes
therefore do not amount to uniformly more passive play. Random/random changes
are smaller and vary by street. Position, visible made-hand/preflop features,
pot sizes and separate discovery/held-out groups are included in
[matched-groups.csv](matched-groups.csv) and [compact results](results.json).
They remain descriptive; subgroup sampling does not establish a causal EV loss.

Of all1,970 states,1,938 (98.38%) have positive original policy mass in both
models;26 are missing in both, five move zero→positive mass, and one stays
zero mass. Most action changes in this sample are therefore between represented,
positive-mass policies. This does not rule out important missing/zero-mass
effects elsewhere; one of the clear selected improvements is a zero→positive
case. Both original reach pools and all lookup categories remain reported.

## Conditional values and uncertainty

Sixteen maximum-disagreement discovery states per lineage give32 fixed selected
states. Each uses32 discovery worlds to select an alternative, then512 fresh
held-out worlds for all legal root actions and both fixed hero continuations.
Thus there are1,024 discovery and16,384 held-out worlds; all17,408 worlds are
reproduced exactly in memory. Reproduction and the two continuation evaluations
are not extra independent samples.

Known-script beliefs enumerate compatible TAG holdings using only observed
public-action likelihoods. Random-action likelihood cancels across holdings;
other private cards/runouts are freshly sampled without replacement. Archived
hidden holdings, future boards, decks and rewards never enter the belief or
policy input. Every branch settles with zero-sum accounting. Sampled showdown
share is a host-only, no-further-folding card proxy, not a continuation value or
an input to the policy. Table-composition labels include states where TAG has
already folded.

Primary results use the predeclared **two-sided empirical-Bernstein95% bounds,
Bonferroni family upper bound512**, conditional on the fixed observation and
discovery selection. Normal intervals/standard errors are auxiliary and do not
override a primary bound crossing zero. Units below are **BB per selected
decision**, not BB/100 or a full-policy win-rate difference.

| Selected state | Fixed continuation |10B root mixture minus3B, BB [primary interval]|
|---|---|---:|
|601 turn, `52e2299f`|3B|+32.05 [1.60,62.51]|
|601 turn, `52e2299f`|10B|+32.71 [2.16,63.26]|
|602 river, `b36c278e`|3B or10B|+78.94 [57.64,100.23]|

In the601 turn example (75BB pot, button),3B folds98.44%;10B folds30.82% and
puts65.37% on the all-in menu action. Both rows have positive mass. In the602
river example (183BB pot, small blind),3B's zero-mass uniform row folds50% and
calls50%;10B calls100% from a positive-mass row. The sampled showdown-share
proxies are47.27% and87.50%, respectively. In **both examples TAG is already
folded** and the remaining opponent is random; they are not evidence of a
specific improvement against a live TAG's bets. These are different states in
different lineages, not replications of one decision mechanism.

The remaining30 selected states have root-mixture bounds spanning zero under
both continuations. For example,601 river `9a1762c0` shifts from3B's100% largest
raise to10B's96.28% call probability; its10B-continuation root-change estimate
is−28.10BB, but the primary interval is[−67.68,11.48]. This is a useful missed
value hypothesis, **not an established loss**. Changing to the narrower normal
interval after seeing the result would change the declared analysis.

One selected alternative improves on the10B root mixture under both
continuations: in `52e2299f`, the discovery-selected all-in gives+15.91
[0.82,31.00]BB with3B continuation and+15.36 [0.35,30.37]BB with10B continuation.
The other31 selected alternatives do not establish a positive improvement;
some are exactly equivalent to the candidate action. This establishes one conditional local
opportunity under the specified scripted belief, not an approved policy patch.

[contrasts.csv](contrasts.csv) includes all64 state/continuation rows, both
primary contrasts, action probabilities, lookup status, position and card-share
proxy. Compact JSON retains all action values/contrasts, selected legal states,
TAG support/entropy/effective-holding diagnostics and exact output pins. No
selected adverse point estimate is dropped from the report.

## Interpretation for the next step

A stronger strategy can extract less from a particular weak opponent; equilibrium
play need not maximize exploitation. That possibility belongs alongside the
peer gains, rather than treating every scripted decline as a veto.
[Safe Opponent Exploitation](https://www.cs.cmu.edu/~sandholm/safeExploitation.ec12.pdf)
formalizes that distinction in two-player zero-sum games. However, improving a
three-player self-play policy is not proof of Nash convergence; the general
multiplayer CFR guarantee is absent, as the
[Pluribus paper](https://noambrown.github.io/papers/19-Science-Superhuman.pdf)
explains. This study measures neither exploitability nor distance to equilibrium.

The measured action shifts, two local improvements, one further conditional
opportunity and several unresolved missed-value hypotheses can coexist. They
do not establish how much of the aggregate random/random+TAG regression comes
from reduced value extraction versus avoiding costly mistakes. Targeting
maximum-disagreement states also cannot weight their contribution to total EV.
Keep the original adverse panels and3B comparators; do not retune the policy,
add samples, claim a search remedy or replace release gates from this result.

## Costs, preservation and reproduction

The two scientific native commands spend240.42/238.04s loading and240.52/238.15s
total internally; supervisor wall is241.74/238.75s. Their conditional-world
sections report0.070/0.087s including exact reproduction. This tiny targeted
panel is not a full arena/search latency forecast. Loading still dominates its
native execution. No new training runs in this PR.

Second-lineage conversion+audit totals21.62min; the first reuses the separately
audited PR361 binary derivatives through pinned new copies. Restores cost15.16min
and verified staging35.83min. All20 stages consume2495.82 child CPU seconds
(41.60CPU-min). Peak sampled worker-family RSS is27.66GiB; observed maximum
CPU59°C / Thermistor15 60°C. CPU90°C/Thermistor15 100°C and correctness stops
remain intact; no elapsed/RSS/disk/swap cutoff or machine setting changed.

Thirty new-owned staging records cover74,414,193,060 bytes. Accessible NVMe
paths point to verified copies under
`bb128:/mnt/data2tb/research-cloud/PR-362-nplayer-matched-regression/main-v1/`.
Original PR350/355/357/361 models/traces remain read-only and all source,
partials, raw matched/selected/world outputs and receipts are retained. There
is no deletion or cleanup. ZIP/Drive acceptance remains **pending**; future
`gdrive:PR-362-nplayer-matched-regression/` is not yet a verified restoration
source. Both owning roots and old dependencies remain protected.

Reproduce the report from retained `lineage-*/results.json`,
`native-result.json`, `extraction.json`, pinned manifests and compact aggregates,
plus `measurements/*/result.json` and `relocations.jsonl`; do not rerun science
to rebuild a table. [results.json](results.json) contains the completed
precomputed lineages and compact provenance/receipts; [costs.csv](costs.csv)
contains every stage. Single host, two fixed lineages, targeted states, known
scripts, finite belief samples and conservative family intervals limit the
conclusion. PR ready for owner review; no merge/default/release authorization.
