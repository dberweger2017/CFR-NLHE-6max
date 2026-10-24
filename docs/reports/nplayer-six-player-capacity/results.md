# Six-player capacity: better support, no established strength benefit

[PR419](https://github.com/dberweger2017/CFR-NLHE-6max/pull/419), [proposal418](https://github.com/dberweger2017/CFR-NLHE-6max/issues/418), [frozen protocol](../../nplayer-six-player-capacity.md).

**Completed October 24 at 15:27 Madrid (13:27UTC), in2h08m52s. All 40 stages pass.**
The fresh 500M-key arm reaches10,000,018,757nodes with 500,004,559 retained keys.
Its larger table improves support on identical played observations, but the
trained-field contrast is **+5.26BB/100 [−33.70,+44.22]** and **0/8 declared
gates pass**. The call-pressure panel is adverse: **−65.44 [−111.97,−18.91]**.
Do not promote 500M on this evidence. Keep the 250M/10B comparator and all models;
no extra hands, nodes, tuning, replication, search or release adoption follows.

## What was compared

One fresh six-player 100 BB arm, same seed 2026102361001, unchanged unpruned K50/v1
recipe, 16 training threads/eight roots/full float64 average, 500M whole-iteration
membership threshold, from scratch to 10B. Control remains PR417's250M/10B;
all trained opponents remain its250M/3B. Same seed does not hold trajectories
fixed after cap-dependent strategies diverge. This tests the capacity threshold
at matched nodes, including its freeze/visitation effects; it is not equal CPU,
equal wall time, an isolated membership-only effect, or another training seed.

Eight fields × 4,096 fresh independent deal blocks × 12 balanced forward/reverse
seatings × two arms: **786,432 initial hands plus byte-identical reproduction**.
Every initial hand independently replays. Mean the 12 seatings within each block;
neither seatings nor reproduction inflate the sample count. All observations,
unchanged actions, missing/zero rows and adverse outcomes remain included.

## All strength results

BB/100. Delta is500M minus250M. Ordinary two-sided 95% intervals are descriptive;
the predeclared decision uses one eight-test one-sided 95% Student-t/Bonferroni
family, df 4095. Trained lower must exceed 0; the seven safeguards must exceed −5.

| Field | 250M absolute | 500M absolute | Paired delta [ordinary95%] | Family lower | Required > | Pass |
|:--|--:|--:|:--|--:|--:|:--|
| trained | +63.30 | +68.56 | +5.26 [-33.70, +44.22] | -44.39 | +0 | No |
| random | +356.04 | +321.89 | -34.15 [-91.05, +22.75] | -106.67 | -5 | No |
| check-call | +251.67 | +249.43 | -2.24 [-74.33, +69.86] | -94.12 | -5 | No |
| tight-aggressive | +6.11 | +8.77 | +2.65 [-12.21, +17.51] | -16.29 | -5 | No |
| pot-pressure | -33.88 | -15.10 | +18.77 [-7.26, +44.81] | -14.41 | -5 | No |
| call-pressure | +132.59 | +67.16 | -65.44 [-111.97, -18.91] | -124.74 | -5 | No |
| random-tight | +125.57 | +109.72 | -15.85 [-38.47, +6.76] | -44.68 | -5 | No |
| trained-call-pressure | +63.91 | +79.02 | +15.12 [-33.42, +63.65] | -46.75 | -5 | No |

No trained gain is established. An unpassed safeguard does not prove a loss,
and wide intervals do not establish equivalence. Call-pressure's ordinary
interval is wholly negative, a concrete adverse signal; the prospective family
defined lower-bound pass gates, not a new post-hoc harm/selection rule.
Both models still profit absolutely there (132.59 versus 67.16), so relative
regression is distinct from losing overall. Pressure's favorable point delta
also does not establish profitability or a repeatable capacity benefit.

Ten extreme blocks contribute 4.79–20.26% of squared block variation across
fields (trained 8.02%, call-pressure 5.28%). All remain in the estimates.
Per-seat/position results, full tails and on-policy lookup counts are retained
in [compact results](results.json); [strength CSV](strength.csv) includes all gates.
One lineage and two circular opponent orders limit generalization. Prior
PR417/415/413/357 adverse results remain evidence; this does not overwrite them.

## Support on the same observations

Every focal legal observation from both arms is queried against both capacities,
without consuming RNG or changing actions. Each occurrence has equal weight;
the pooled multiset, originating-arm strata, positive/zero/missing counts and
float64 distribution differences are preserved. This is distinct from on-policy
counts, whose visited histories differ. [All streets and counts](shared-coverage.csv).

| River field | Shared observations | 250M missing | 500M missing |
|:--|--:|--:|--:|
| trained | 4,888 | 30.11% | 20.19% |
| random | 617 | 86.55% | 80.88% |
| check-call | 44,274 | 100.00% | 100.00% |
| tight-aggressive | 3,500 | 15.37% | 8.17% |
| pot-pressure | 4,241 | 20.44% | 11.41% |
| call-pressure | 29,515 | 99.83% | 99.70% |
| random-tight | 6,468 | 28.01% | 16.19% |
| trained-call-pressure | 19,771 | 92.76% | 84.24% |

The trained-field river improves 30.11%→20.19% missing, and TAG 15.37%→8.17%.
But **all 44,274 check-call river observations are missing for both**, while
call-pressure remains 99.83%→99.70% missing. Doubling capacity is not a universal
coverage repair for this recipe. Larger retained support coexists with mixed
returns; these counts do not identify the payoff cause of a changed action.

The 500M table has 375,466,874 positive-mass rows and 124,537,685 zero-mass rows
(24.91% zero mass), versus 191,147,053 positive and 58,854,501 zero at 250M(23.54%).
Stored zero mass is not the rate of uniform fallback in played decisions.
Retained visits per key are lower at 500M on every street (for example preflop
1.42 vs 2.01, river 1.60 vs 2.00), although absolute retained visits and support rise.
This illustrates the fixed-node coverage/update-density tradeoff; it does not
prove that visit density caused any return difference.

Membership freezes at iteration 49,319. The first already-frozen telemetry sample
is 1,098,785,908 nodes /500,004,559 entries; this is a sampled witness, not an exact
freeze-node claim. Whole-iteration overshoot 4,559 is expected. Final discarded-key
and visit counters remain in the receipt; growth after freeze is censored.

## Actual complete cost

| Component | Wall min | Process CPU min |
|:--|--:|--:|
| training including save | 38.17 | 482.43 |
| export | 13.91 | 52.37 |
| row audit | 13.50 | 91.09 |
| binary conversion | 10.73 | 10.73 |
| binary audit | 10.46 | 10.47 |
| arena initial and repeat | 21.59 | 25.41 |
| independent replay | 6.09 | 5.79 |
| paired summaries | 2.25 | 2.18 |
| shared observation proofs | 3.77 | 3.62 |
| global readout | 5.18 | 5.11 |

Measured stages total 125.63 min;
complete controller wall 128.87 min includes 3.23 min
of setup/source checks and other controller work. Stage CPU totals
11.49 core-hours. Native active traversal is 32.28 min
and checkpoint save 4.75 min, subsets of the 38.17 min training stage. Arena loads
total **20.08min**, versus **45.85s** reported play across
initial+repeat; remaining arena wall includes startup, hashes and writing.
These nested numbers must not be added again to the component totals.

Peak sampled training family 40.63 GiB; complete workflow 54.05 GiB(three-model
arena). Maximum CPU 76°C /Thermistor15 93.5°C; no thermal stop or correctness
failure. Swap used rises from 451.1 MiB to 550.4 MiB; no swap cutoff exists.
Main retained allocated bytes 72,224,677,888 (67.26 GiB); checkpoint 18.72 GB,
average 11.16 GB, binary 28.31 GB. Last NVMe free 32.33 GiB. The 120 GiB NEW scenario
included 25 GiB working room and was not a live free-space floor. No proposed
cleanup/reserve gain is counted.

Observed wall time is **not isolated**: the separately authorized closed-PR317
HDD-only backup/receipt worker overlaps (nice19/ioniceidle,3MiB/s network,
no NVMe payload I/O). The transfer runs 12:01:31–12:02:50UTC; subsequent HDD receipt/member checks
and a large metadata scan overlap the science, then continue afterward. The
backup child later exits1 with MemoryError at its own 8 GiB virtual cap; this is
a separate archival failure, not a scientific failure or missing PR419 proof.
Whole-child CPU 301.21 s includes post-science work; concurrent-only CPU/physical
I/O and exact peak RSS are unavailable. A prior bounded sample observes 7.34 GiB
RSS. [Exact receipt provenance and limitations](backup-cost-context.json).
Do not infer causal slowdown or subtract wall windows as CPU time. PR421's source transfer
starts only after this main ends, so it does not overlap this campaign.

## Provenance, preservation and decision

Frozen source`2ccf21ac608d9729fecea80583ad3f9ee5f34b64`,884 source/config pins,
implementation`9b9204c8dccdda255b574cde48fb02d5c761d030`.
Config`2fff4245900b851bedb2625cdf6a2d274e3500e525b39d83291d369374ca1801`;
raw result`c12ec77d688db05cbdcb1ce64c603d1914169a3cb4ce992e2748e7710057684a`.
All 40RC0, replay/reproduction/model/catalog/shared-inventory checks pass before
global readout. [Compact proof/model/cost provenance](results.json) binds the
retrieved files and every field's recorded proof hashes. Qualification failures,
partials, source, environment pins and original/derived evidence remain retained.

This is a bounded development result, not release acceptance. **Keep250M/10B
as the working control; the500M arm has not earned promotion.** Combine the
remaining field-dependent support gaps with the separately descriptive PR421
trajectory diagnosis before choosing a concrete history/visitation intervention.
No follow-up experiment is authorized by this report.

Ordinary evidence remains at
`bb128:/home/dberweger/nplayer-six-player-capacity-20261024/`.
The cleaner owns later completed-evidence ZIP packaging, archive-set manifests
and verified upload to the matching Drive PR folder. Research-payload Drive
acceptance is **pending**, no deletion or pre-ZIP/upload is performed here.
Originals and all protected PR417/shared dependencies remain readable.
