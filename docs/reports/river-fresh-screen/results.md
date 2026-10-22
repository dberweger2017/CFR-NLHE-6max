# Fresh frozen river screen: both panels inconclusive

[PR396](https://github.com/dberweger2017/CFR-NLHE-6max/pull/396), proposal395.
**The earlier check-call/pressure disadvantage does not recur as a negative
fresh point estimate. Trained-peer improvement is also unestablished.** Both
simultaneous intervals cross zero and−5BB/100. No predeclared unacceptable-harm
flag fires; neither benefit nor−5 non-inferiority is established. No hands added.

## Frozen study and interpretation

The [protocol](../../river-fresh-screen.md) preceded implementation and fresh
outcomes. Same100BB10B focal003/peer601, same native player/menu/work/quality/
retained fallback,4workers,200K expectation states/arm/root. Roots
2026102239601/02 are fresh, independent of PR388/391/394. Exactly1,024 independent
deal blocks per lineup, six seat permutations, paired on/off arms:24,576 initial
hand instances and24,576 reproduced instances. Reproduction adds no samples.

The reported statistic is mean oriented focal singleton search-on minus off
expected return over whole-hand deal blocks, inBB/100. Every eligible root and
unchanged sampled action is included; no-root paths contribute zero. Hidden
cards enter only the privileged evaluator, never player methods. Expectations
average future river actions against the actual fixed opponents at dealt cards;
they do not establish correct opponent beliefs or safe resolving.

| Opponent pair | Expected contrast BB/100 | Pointwise95% interval | Two-panel family95% interval | Sampled contrast |
|---|---:|---:|---:|---:|
| Trained / trained |−1.11|[−5.65,+3.43]|[−6.30,+4.08]|+7.39|
| Check-call / pot-pressure |+2.50|[−5.79,+10.79]|[−6.98,+11.99]|−0.99|

These are Student-t block intervals; the simultaneous column uses the frozen
two-sided Bonferroni family of two means. Sparse heavy tails still limit their
accuracy. The protocol's clear-harm flag requires the family upper bound below
−5; an adverse-direction flag requires the upper bound below0. Neither fires.
The peer-promising flag requires its family lower bound above0; it also does
not fire. Failure to flag harm is not evidence that harm is excluded.

The old saved-deal expectation means were+8.33 against peers and−14.81 against
check-call/pressure. Preserve those results: opposite fresh point estimates do
not prove the old signal false or a beneficial player change. We changed no
player. The much smaller old128-block sample and its concentrated tails allow
substantial sampling variation. Do not pool development deals into this fresh
screen or select the more favorable sampled estimator.

## Variance and tails

| Lineup | Fresh expected block SD | Fresh sampled SD | Expected/sample variance | Largest centered-square share | Largest3 / largest5 |
|---|---:|---:|---:|---:|---:|
| Trained / trained |74.03|158.58|0.218|18.06%|39.93% /47.34%|
| Check-call / pressure |135.18|180.95|0.558|8.19%|20.50% /28.27%|

The corresponding development expected SDs were101.40/163.73 and variance ratios
0.414/0.453. Fresh peer variance reduction is greater; scripted reduction is
smaller. The implied sample efficiencies are4.59× and1.79× in this fresh sample,
not universal cost/speed guarantees. All on/off sampling and solving still runs;
complete cost below includes those components. This study has no sampled-only
fresh cost-control run. Fresh pointwise half-widths4.54/8.29 are below the old
conservative7/11 planning estimates; unseen tails and other lineages remain.

The table lists exactly the predeclared three largest positive and three largest
negative **expected block** contrasts per lineup. Block scores areBB/100 over a
six-hand average, not thousands of BB lost in one hand. Root deltas below areBB
for one fixed deal/permutation. They are not independent extra samples.

| Lineup / block | Block contrast BB/100 | Centered variation share | Largest recorded root delta BB |
|---|---:|---:|---:|
| Peers829 |+540.66|5.24%|+35.99|
| Peers512 |+481.61|4.16%|+20.12|
| Peers841 |+426.27|3.26%|+25.58|
| Peers400 |−1,007.37|18.06%|−30.22|
| Peers666 |−966.79|16.63%|−48.01|
| Peers838 |−391.42|2.72%|−11.74|
| Call/pressure0 |+1,193.69|7.59%|+61.97|
| Call/pressure727 |+942.20|4.72%|+34.15|
| Call/pressure966 |+868.35|4.01%|+50.43|
| Call/pressure242 |−1,234.83|8.19%|−39.83|
| Call/pressure637 |−687.28|2.55%|−40.67|
| Call/pressure207 |−652.71|2.30%|−38.73|

[All selected examples](results.json) retain up to three roots per block with
public board, own holding, on/off mixes, chosen actions and root IDs.
[Both centered and uncentered shares](tails.csv) are retained. The examples are
descriptive; they do not establish a causal repair or justify tuning mid-study.

Peer examples show both effects. In block829's44BB pot, search checks96.1%
versus14.5% for blueprint, with+35.99BB conditional gain. Block512 replaces a
97.8%-pot-bet blueprint with68.7% minimum bets/31.3% checks, gaining20.12BB in
one permutation. Block841 increases pot betting from9.6% to97.8%, gaining25.58BB.
Thus the positive tail is not uniformly more passive.

The peer losses include block400's42BB pot: search checks99.7% versus37.5%,
with−30.22BB in each of two permutations sharing this deck. Block666's30BB pot
checks77.9% versus2.4%, losing48.01BB conditionally. Block838 has very similar
root mixes but−11.74BB per affected permutation; the expected contrast includes
the whole continuation, so root probabilities alone cannot explain it.

Against call/pressure, block0's67.5BB pot switches from98.5% large betting to
92.9% checking and gains61.97BB. Block727 likewise checks98.4% versus3.6% in
one36BB pot, gaining34.15BB, while another permutation bets larger more often
and gains22.38BB. Block966 increases a78BB raise-to from18.9% to91.0%, gaining50.43BB.

The adverse call/pressure tails are mixed too. Block242's81BB pot reduces a
68.5%-large-bet blueprint to55.3% minimum betting/43.5% checking, losing39.83BB;
another permutation loses34.26BB. Block637 favors1BB betting88.0% instead of
the blueprint's64.4% large-bet component, losing40.67BB. Conversely, block207
increases54BB betting from27.1% to99.2% and loses38.73BB. These fixed-deal
contrasts show neither uniformly lost value extraction nor uniformly beneficial
mistake avoidance. We did not evaluate a tuned alternative or claim those were
knowable mistakes under the player's legal beliefs.

## Coverage, quality and fallback

Each lineup has6,144 search-on hands. Peers attempt582 roots/install581 (9.46%
of hands); call/pressure attempts/installs1,483 (24.14%). These are the strict
first-actor/two-live/non-all-in eligibility conditions, not all rivers. Aggregate
installation16.80% reflects the selected two-lineup mix and is not a universal
search frequency. All2,065 roots reproduce exact values/profiles/work in both
passes, no exclusion/incomplete evaluation or additional solves/reconstructions.

The one peer quality failure is root`trained/5953/0011`,54nodes,2,048sweeps,
maximum best-response gain0.18360BB exceeding the unchanged0.1BB cap. It plays
blueprint and cancels identical expectations; no extra convergence is added.
All1,483 scripted roots pass. Projected-game quality does not imply full-menu
or exact-belief safety.

Peers have213 subsequent retained-session decisions and two first off-tree
events: hand1011 reaches an omitted raise-to26BB after check→1→13.5BB, neither
all-in nor cap-limited; hand3735 reaches a95BB all-in after1→13→49BB with three
prior raises and the cap reached. Both use the frozen sticky blueprint fallback.
Call/pressure has no recorded subsequent session/off-tree event. These small
frequencies do not remove adversarial vulnerabilities. [Exact metadata](diagnostics.json).
Neither off-tree hand belongs to the preselected largest peer tail blocks;
these events do not explain those selected losses.

Peer root latency: median0.444s/p951.544s/p993.031s/max3.132s;
call/pressure0.431/0.970/1.816/3.116s. These are player root timings; complete
batch time also includes inline expectation, writes, loads and replay. Physical
seat root counts are177/203/202 for peers,493/503/487 for call/pressure.
Only7/13,032 and59/16,751 recorded blueprint lookups respectively report not
found. Existing ledgers do not separate positive from zero mass, so no new
lookup classifier is inferred. [Full counts/seat/timing data](results.json).

## Complete cost and verification

All five stages return0. Known-deal qualification96 initial plus96 reproduced
hands matches original PR388/391 traces/profiles/values.19 focused Python tests
and environment checks pass.73 native files and the qualified binary are
unchanged from the prior120-native-test qualification. All24,576 fresh initial
hands independently replay;24,576 reproductions match byte-for-byte, with all
2,065 root value/profile/work records reproduced. Native zero-sum accounting
and paired first-intervention checks pass. No technical/scientific retry.

| Cost | Seconds |
|---|---:|
| Model/K50 loads, fresh initial+repeat |465.25|
| Fresh play/write including expectations |1,186.99|
| Inline expectation-only work, included above |2.61|
| Fresh independent replay/parity proof |11.20|
| Fresh screening plus readout, supervised |1,668.46 (27m48s)|
| Known-deal qualification |472.11|
| All five stages |2,144.61 (35m45s)|

All stages use3,222.34 childCPU-s (53m42s); screen/readout2,741.77s. Fresh
driver1,664.47s differs slightly from supervising stage wall. First/repeat native
batches829.35/823.65s, each sharing two loaded policies across4workers.
Expectation work visits837,205states/pass, max3,661/arm versus200K limit.
No model conversion, save, training or separately measured durable-fsync cost.

Fresh sampled peak27.70GiB, CPU67°C/Thermistor15 66°C, zero swap growth;
minimum NVMe257.01GB/HDD530.68GB free. Two-second samples can miss short peaks.
Stages began04:01:54UTC; the final readout sample is04:37:39UTC/06:37:39Madrid
October22, with completion about two seconds later. The complete
runtime fits both58min central and2h planning allowance; coding/report/archive
time is separate from those stage costs. [Costs/resources](costs.json).

## Decision and bounded follow-up

This screen neither establishes benefit nor fires its clear-unacceptable-harm
rule. The fresh scripted point estimate does not justify carrying the old
negative mean forward as a settled weakness, and the fresh peer result does not
justify assuming improvement. Retain both as uncertainty, with the tail evidence.

[One fixed follow-up proposal](followup-proposal.md) uses all three existing
lineages,2,048 fresh peer blocks and4,096 call/pressure blocks per lineage,
442,368 initial/reproduction instances total. It costs4.01h centrally/10.72h
reserved, within a proposed12h allocation. This tests a narrower peer/single-
safeguard question, with no80h-design joint-power, broad-script or release claim.
It could still be inconclusive for modest effects; counts never extend for a
positive interval. Owner approval is required before any follow-up hands.

Recommendation: review this bounded cross-lineage proposal or defer the frozen
candidate. Do not tune menus, training, resolving or the player based on selected
tails. No automatic larger study or further evaluation optimization.

## Reproduction, provenance and preservation

Frozen runtime6145e4d4, source-v2 bundle/config/binary/model pins are in
[provenance](provenance.json). The [unaltered precomputed readout](results.json),
[lineups](lineups.csv), [tails](tails.csv), [costs](costs.json) and
[follow-up arithmetic](followup-proposal.json) are compact; raw models/traces
stay off Git. Offline summary helper:

```sh
python3.11 -m scripts.summarize_river_fresh_screen RETRIEVED_RECEIPT_JSON --out FRESH_OUTPUT
```

All raw qualification/screen outputs, source bundles, logs and setup versions
remain in `bb128:/home/dberweger/river-fresh-screen-20261022/`. Setup emitted a
nonfatal nested-Git-alternate warning; identities and every stage passed. V2's
cost-only admission change preceded any qualification/fresh hands. No external
model/K50/environment/Git store changed or copied; no cleanup. [Archive acceptance](archive.json)
passes:17,691,383-byte ZIP,130 payload members plus manifest,132 covered local
files. Local SHA256/member readback and deployed-tool Drive MD5/size acceptance;
no remote SHA256/member audit claimed. Fast cache
`/research/PR-396-river-fresh-screen/`, Drive fallback and exact restoration paths
in the receipt. All scientific/qualification/raw/source/binary/retrieval evidence
is covered. KEEP, originals and partials remain; zero deletion.
