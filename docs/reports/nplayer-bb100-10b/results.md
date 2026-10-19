# Fixed 100 BB3B→10B: the primary gain clears zero; opponent tradeoffs remain

The unchanged unpruned 100 BB blueprint improves in its predeclared reciprocal
trained-policy comparison: **+28.40[+18.98,+37.81]BB/100**, primary95% interval.
More training helped this fixed-membership model on fresh held-out deals. It
also improves against fixed 3B+pot-pressure after adjustment across eight panels.
Returns fall against random and random+TAG; those adverse signals clear zero
pointwise but not after the declared family adjustment. Keep them visible.

Recommend the 10B checkpoint as the research candidate for independent-seed
confirmation, retaining3B and the adverse script panels. This one seed/host does
not qualify v0.6 or establish a universally stronger policy. There is no automatic
adoption, release, merge or further compute allocation.

## Completion and controls

The owner-authorized campaign ran October 19,20:08:19–21:21:05UTC
(22:08:19–23:21:05Madrid), **72.77minutes**. All five measured stages returned 0,
no failure, supervisor544891 exited. Both compute locks are free at closeout.
Both full 250,000,475-row audits pass, and all 18 cases pass exact reproduction
and independent engine replay: **884,736 initial plus884,736 reproduction hands**.
Reproductions add no statistical samples. No science was retried or changed.

The candidate reaches 10,000,009,599 nodes/756,434 iterations; its comparator is
PR350's3,000,011,203 nodes/212,132 iterations, seed 2026101935003. Preserve 100 BB,
K50, menu/schema, unpruned fast8 roots/seat,16 threads, fullfloat64 opponent-sampled
averaging, and exactly 250,000,475 retained keys. The membership hash is unchanged:
`a83858109eed965e73acd76787761d9353f2a66cccb482c0271173e3ff731425`.
The original cap was reached near2.09B; extra training updates retained states
and discards updates for new keys. It expands no retained membership.

Frozen controller`ecb08ada3caf85506f434bff51f05a9ff5c8b8ee` and native training
library`b9882e7e728847a58691995e64eabd4563ea0991` remain unchanged; later commits
are reports only. [Protocol](../../nplayer-bb100-10b-study.md),
[qualification](qualification.md), [launch](launch.md),
[completion/source/proofs/resources receipt](completion.json),
[compact verified readout](results.json).

## Strength and uncertainty

Each lineup uses 8,192 six-hand blocks, with all seat/identity permutations.
Confidence intervals use those blocks, not individual seats or reproductions.

The direct statistic is the **mean oriented singleton contrast**: half the
return difference between10B-vs-two3B and 3B-vs-two10B. Its two singleton means
are+31.54 and−25.26 BB/100. It is not pooled player return or a heads-up win rate.
The other rows subtract baseline from candidate singleton returns against the
same fixed opponent pair. Absolute means below are their respective lineups.

| Opponent configuration |3B mean|10B mean|Contrast|Pointwise95%|Family95% across8|
|---|---:|---:|---:|---|---|
| Reciprocal trained match | -25.26 | +31.54 | +28.40 | [+18.98, +37.81] | Primary95% |
| Two random | +365.44 | +332.01 | -33.43 | [-63.52, -3.35] | [-75.41, +8.55] |
| Two check-call | +261.24 | +232.88 | -28.37 | [-57.90, +1.17] | [-69.58, +12.85] |
| Two TAG | +46.42 | +49.31 | +2.89 | [-7.14, +12.92] | [-11.10, +16.88] |
| Two pot-pressure | +35.77 | +48.26 | +12.49 | [-0.75, +25.73] | [-5.99, +30.97] |
| Fixed3B + check-call | +161.87 | +190.64 | +28.77 | [+5.69, +51.85] | [-3.43, +60.97] |
| Fixed3B + pot-pressure | +9.65 | +38.83 | +29.18 | [+15.46, +42.91] | [+10.03, +48.33] |
| Check-call + pot-pressure | +126.30 | +149.89 | +23.59 | [+3.17, +44.00] | [-4.90, +52.07] |
| Random + TAG | +206.65 | +181.74 | -24.91 | [-43.53, -6.30] | [-50.89, +1.06] |

All values areBB/100. The direct row has its single predeclared primary95%
interval; the eight opponent contrasts also have Bonferroni family95% intervals.
Only fixed 3B+pot-pressure clears zero after that eight-panel adjustment.
Random and random+TAG have adverse pointwise intervals, with adjusted intervals
that cross zero. This does not prove safety or equivalence; no regression margin
was declared. No additional testing or sample extension follows these outcomes.
All eight candidate absolute means are positive; their intervals and every
physical-seat/button-relative-position result are retained in
[strength.csv](strength.csv), [seats and positions](seats-and-positions.csv).
The mixed trained opponent is this same seed's fixed 3B model, not an independent
training population. No external-opponent/generalization claim follows.

## Why do returns fall against random and check-call?

The 10B model still earns **+332.01 BB/100 against two random opponents** and
**+232.88 against two check-call opponents**, versus +365.44 and +261.24 for 3B.
Those absolute profits coexist with the primary trained-policy improvement.
The random decline has a negative pointwise interval; the check-call decline
does not. Neither clears zero after the eight-panel adjustment. A change in
opponent-specific performance is a useful diagnostic, even when its magnitude
remains uncertain; it does not by itself explain the primary gain.

### Measured behavior in the complete script traces

At the owner's request, a post-hoc audit streamed all four original pure-script
traces: 49,152 hands per model/opponent, **196,608 existing hands in total**.
It counts only the blueprint identity's actions after mapping identities to
physical seats. Script actions and exact reproductions are excluded. The trace
SHA256s match the original replay proofs, and the rewards reconcile to the
verified absolute means. No new hands were played or selected. The other model's
quoted sample counts have no reproducible selector; the complete counts below
replace them. Rates are descriptive, with no new significance test.

| Blueprint behavior | Random: 3B→10B | Check-call: 3B→10B |
|---|---:|---:|
| Checks / legal check opportunities | 56.44%→61.57% | 57.77%→65.71% |
| Bets or raises / legal raise opportunities | 30.18%→27.34% | 36.45%→31.73% |
| Turn checks / legal check opportunities | 50.31%→56.26% | 54.74%→62.40% |
| River checks / legal check opportunities | 47.82%→52.87% | 45.86%→55.94% |
| Blueprint all-in bets/raises, count | 3,085→2,222 | 946→672 |
| Mean gross pot award, conditional on positive net hand (BB) | 77.83→70.49 | 43.57→33.26 |

The observed shift is toward more checking, fewer bets/raises and smaller
conditional winning awards, particularly against check-call. Raw checks rise
9,582→10,788 against random and 57,364→68,326 against check-call; bets/raises
fall 27,524→25,327 and 48,130→43,398 respectively. Decision totals also change
(93,789→94,708 and 132,062→136,756), so raw counts alone would confound action
choice with how many decisions the policies reach. Opportunity denominators
help, but still compare different reached states and hand distributions.

Bet sizing changes less than betting frequency. Mean raise increment divided
by the pot after calling falls 0.578→0.572 against random and 0.575→0.534 against
check-call; medians stay 0.40 and one-third respectively. Here `raise` includes
bets, and the increment is raise-to minus the outstanding wager. The gross
award is net reward plus contributions minus refunds, measured only on hands
with positive net reward; it is not the full table pot or an unconditional
measure of value extraction. Positive-net hand counts fall 9,424→8,756 against
random but rise 10,320→10,922 against check-call. A lower conditional award does
not alone establish missed value bets.

**The proposed explanation that 10B folds more to random preflop jams is not
supported by these traces.** When another live opponent was already all-in
and a preflop call was required, observed fold frequency falls from
374/1,154 (32.41%) to 236/849 (27.80%). Overall folding when facing a bet against
random rises slightly, 49.40%→50.47%; those different denominators cannot be
substituted for the preflop all-in comparison. Neither comparison controls for
the changed cards and histories reaching it, or measures whether a fold is good.

### Interpretation and remaining uncertainty

The native check-call script checks whenever legal and otherwise calls; it
never initiates a bet or raise. Random samples the fixed legal-action menu.
Less betting into check-call is therefore a plausible contributor to lower
returns, consistent with the smaller winning awards and existing pot-band
analysis. We have not measured hand strength, equity, missed value, bluff quality
or counterfactual action values. Betting every hand into a calling station is
not an appropriate remedy: a bluff with no fold equity can simply lose more.

A self-play recipe does not directly optimize exploitation of these scripts.
An opponent-specific tradeoff is plausible, but **Nash convergence, optimal pot
control and increased unexploitable strength are not established**. CFR's usual
average-policy Nash convergence guarantee applies to two-player zero-sum games;
it does not generally extend to this three-player setting. No exploitability
certificate was measured here. [Brown and Sandholm, 2019](https://noambrown.github.io/papers/19-Science-Superhuman.pdf).

The earlier [20 BB 30B study](../nplayer-overnight/results.md) also has negative
point changes against random on all three seeds (−21.46, −23.53, −27.77 BB/100)
and check-call (−12.65, −17.81, −6.65). All random declines clear that study's
family intervals; only one check-call decline does. The repeated direction is
interesting across depths and recipes, but it is not an exact replication or
proof of a shared mechanism. Here the defensible strength claim remains the
predeclared single-seed primary gain and the adjusted trained/pressure result,
alongside the adverse and inconclusive panels, rather than universal superiority.

These results also **do not prove that search will recover the script losses**.
Local subgame refinement and exploiting a known opponent are different tasks;
search does not automatically adapt to a calling station. Pluribus itself used
a fixed strategy without adapting to observed opponent tendencies, despite its
search component. [Original paper](https://noambrown.github.io/papers/19-Science-Superhuman.pdf).
No search arm or complete-decision latency was tested here; a sub-15 ms target
remains unverified. Retain the script panels in any prospective paired search
evaluation. Separately testing missed value bets would require legal-information
counterfactuals on fresh held-out states, not a claim inferred from action counts.

Full per-street counts, opportunity denominators, award definitions and trace
pins are in [script-behavior.json](script-behavior.json), generated by
[script_behavior.py](script_behavior.py). This descriptive audit took 13.81 s
on one pinned core after the main study completed; its cost is additional to
the campaign timings below. It changes no frozen result or decision rule.

## What the lookup measurements explain

Both raw checkpoints bind their sidecars to exact policy/checkpoint hashes and
full key-set hashes. Original positive mass, zero mass and missing are distinct;
normalized uniform probabilities alone never establish zero mass. Qualification
proved instrumentation leaves probabilities and action RNG consumption intact.

| Measurement |3B|10B|
|---|---:|---:|
| Retained entries |250,000,475|250,000,475|
| Original zero-average-mass rows |79,729,265(31.89%)|68,541,567(27.42%)|
| Pooled singleton decision probes |897,814|919,397|
| Own positive-mass lookup |99.3565%|99.4539%|
| Own zero-mass lookup |0.0457%|0.0111%|
| Own missing lookup |0.5978%|0.5350%|

**11,187,698 retained rows gain positive average mass.** Across both reached
singleton-state corpora, matched probes record 1,402 zero→positive decisions
(227 on baseline trajectories,1,175 on candidate trajectories). There are no
matched missing/present disagreements or positive→zero transitions. Repeated
probes are decisions, not counts of distinct converted keys.

The table-wide zero-row fraction greatly overstates exposure to zero-mass
fallback in this opponent panel. Most reached decisions use positive-mass rows.
That label does not imply sufficient visits, correct action probabilities or an
optimal decision. Gain cannot be causally assigned to mass conversion from
these summaries. Missing frequencies can change because trajectories change,
despite identical key membership.

| Own lookup street |3B missing|10B missing|3B zero mass|10B zero mass|
|---|---:|---:|---:|---:|
|preflop|0.0305%|0.0459%|0.0027%|0.0004%|
|flop|0.1712%|0.1383%|0.0230%|0.0051%|
|turn|0.6151%|0.5006%|0.0845%|0.0229%|
|river|3.5696%|3.0648%|0.2079%|0.0464%|

Pooling is descriptive and depends on this panel's opponent mix. These are
singleton actions under each acting policy; both policies are separately probed
on every matched observation. Full per-identity/street/position counts are in
[lookup.csv](lookup.csv), [positions](lookup-by-position.csv),
[matched transitions](matched-transitions.csv). The audit's training missing/visit
counters in[results.json](results.json) are different lifetime-training quantities.

## Paths, pots and future river scope

[Paths](paths.csv) contains every aggregate preflop/position/outcome class, its
hand frequency, conditional mean, contribution to the full lineup mean, and
replay root/hand/block/permutation/trace SHA256. Path and pot-band partitions
reconcile to the precomputed absolute means. [Strata](strata.csv) also preserves
reached-street and final-pot-band summaries. These are descriptive partitions,
not paired counterfactual action evaluations or uncertainty-adjusted path tests.

For the random panel, the≥50BBpot band contributes369.60 BB/100 for 10B versus
392.13 for3B:−22.53 of the overall−33.43difference. Its count falls 13,916→13,074.
For random+TAG, that band's contribution falls 234.79→219.77. The policies reach
different pot/hand sets, so this does not identify a wrong action. High-frequency
blind folds also necessarily contribute losses; sorting by lost money alone
cannot diagnose a decision error. Inspect recurring paths with legal-information
counterfactuals before changing the policy.

The counter finds two-live-player river decisions in 73,014/442,368baseline
hands(16.51%) and 77,911/442,368candidate hands(17.61%). Opponent dependence is
large: candidate frequency is0%against two check-call,7.18%against two random,
and 49.41%against check-call+pot-pressure. The counter requires a river action
and two nonfolded players; it is not a count of nontrivial solver opportunities
and can include all-in response decisions. [Every lineup](river-frequency.csv).
Do not use the pooled percentage as a universal search budget.

## Actual costs

| Cost |Measured value|
|---|---:|
| Root wall, including initial input checks |72.77 min|
| Additional7B active traversal |25.04 min;4.66Mnodes/s|
| Native continuation job including load/save/export |38.42 min|
| Checkpoint save |146.29 s|
| Average export |86.32 s|
| Baseline/candidate full audits |398.32/425.09 s|
| Evaluation stage, including verification/replay |766.29 s|
| Recorded native two-policy loading |502.13 s|
| Recorded native play, all initial+repeat cases |22.50 s|
| Independent replay wall |41.49 s|
| Global readout |120.90 s|
| Sum measured stage child CPU |7.29 CPU-hours|
| Sampled training phase RSS |22.39 GiB|
| Sampled continuation job peak RSS(save) |23.36 GiB|
| Sampled evaluation/overall peak RSS |66.03 GiB|
| Maximum sampled CPU/Thermistor 15 |74°C/91.5°C|

CPU sum excludes unsupervised parent input checks, and sampled RSS/temperatures
can miss between-sample peaks. No thermal stop occurred. Temperature-only
resource stops remained90°C/100°C/missing readings; disk/swap were manual.
About38.4 GB free NVMe remained at closeout; both compute mutexes are free.

The native evaluation wall is624.39 s:502.13 s recorded policy load,22.50 s play,
and 99.76 s additional native preparation/overhead. Evaluation-stage input hash
verification totals100.32 s and is separate. Do not equate play time with total
job latency. Active traversal is34.4%of total campaign wall, so faster loading,
serialization and verification may matter substantially for future campaigns.
That is a performance observation, not authorization for another experiment.

Checkpoint bytes grow9.712→11.009 GB and average bytes5.600→6.230 GB despite
unchanged membership. [Exact model paths/sizes/hashes](completion.json) and
[model hashes in the verified readout](results.json) preserve retrieval identity.

## Reproduce and retain

Only compact settled results/proofs/resources metadata were retrieved into
ignored`results/pr355-final-20261019T2125/compact/`. All retrieved source files
match their remote recorded SHA256 s. Raw source result is 925,548 bytes, SHA256
`41cffb0c7b131358b7b3906bb540cb12116f22da5200dcb0b99edc1612e83bd3`.
The committed44KBreadout is derived from it; all aggregates have complete CSVs.
To regenerate these tables without any training or evaluation:

```sh
python3.11 docs/reports/nplayer-bb100-10b/summarize.py FRESH_COMPACT_SOURCE FRESH_OUTPUT
```

The source directory needs results/metadata, the original evaluation manifest
and proofs, and the 18 compact case summaries/replay proofs indexed in
[completion.json](completion.json). Retrieve only those files from
`bb128:/home/dberweger/nplayer-bb100-10b-20261019/main-v1/` into a fresh ignored
working directory with SSH/rsync, preserving relative paths; verify the recorded
hashes before using them. Never relaunch the existing root. The summarizer
rechecks hashes, barriers, all eighteen case identities/counts, exact-reproduction
attestations, diagnostic totals, membership, and path/pot return reconciliation.
It does not repeat independent engine play or reread remote model bytes.

The owner-requested descriptive script audit is retained separately at
`bb128:/home/dberweger/nplayer-bb100-10b-20261019/posthoc-script-behavior-v1/script-behavior.json`.
Its SHA256 is `4b18f51bd4a68704df415ae8a1fbdfee40d59f7b60f72945d44251a118f69807`;
the committed copy has identical bytes. It records the four exact source trace
paths, sizes, modification times and SHA256s. Retrieve that compact file with
`scp bb128:EXACT_REMOTE_FILE FRESH_IGNORED_DIRECTORY/` and verify the hash.
To reproduce on bb128 with the existing raw traces and both compute locks free,
run the committed helper with the completed main root and a fresh sibling output:

```sh
python3.11 script_behavior.py /home/dberweger/nplayer-bb100-10b-20261019/main-v1 FRESH_POSTHOC_OUTPUT
```

This streams existing hands and verifies their original trace/replay hashes and
absolute means. It acquires both mutexes nonblocking, pins itself to one core,
and refuses an existing output directory. Do not retry an active main campaign.

Native logs, checkpoints/averages, mass sidecars, all 6.31GBof raw hand traces,
source/builds, initial Cargo/PATH setup failure and qualification fixtures remain
on bb128. Current PR355 is open: no move/archive/delete of its raw root or shared
PR350/352/353 inputs is performed. Cache/Drive namespace is
`PR-355-nplayer-bb100-10b`; archival and Drive acceptance remain pending.
The separate owner-authorized relocation of completed PR339/340/342 evidence
remains indexed in[its receipt](../../artifacts/nvme-relocation-20261019.md).

SSH status checks briefly failed because local Tailscale was stopped. Restoring
the existing session with its saved routing preference recovered access; this
was not a host/scientific stop, reboot, result selection or retry. Initial local
report-generation schema mismatch left a partial ignored output; it was fixed
and the complete summarization ran in a new output directory, without rerunning
science or changing source outcomes. No new experiment, timer or merge follows.
