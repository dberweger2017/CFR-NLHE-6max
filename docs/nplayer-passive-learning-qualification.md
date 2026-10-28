# One target-policy exploration qualification

Research proposal [456](https://github.com/dberweger2017/CFR-NLHE-6max/issues/456).

The owner requests a PR, correctness review and a measured allocation before the
main qualification. This protocol authorizes no mature training, arena, live
session, deployment/default change or automatic extension. Existing models and
the PR455 router stay unchanged. Main compute acceptance remains pending.

## Question and one intervention

Can a small explicit exploration component in the **target training policy**
produce repeated, retained positive learning on passive histories, rather than
merely visiting histories whose importance weights remain zero?

PR425's behavior-only passive sampler did not qualify that remedy under an older
warmed four-player policy. It is not evidence that every current mixed-stack key
is unreachable. This task tests a different, declared training law from its first
iteration, not a continuation of the old warmed sampler or a missing-prefix reset.

One candidate only: epsilon=0.02, uniform over the current legal menu. Base
regret-matching strategy pi becomes sigma=(1-epsilon)pi+epsilon*uniform. The
control has epsilon=0. Both draw opponents from their own sigma, so q=sigma;
there is no off-policy sigma/q correction to remove this actual exploration.
No parameter sweep, pruning, pressure mixture, key/menu/card change or additional
admission intervention is bundled into the comparison.

This changes the strategy class. It is not claimed to preserve the unconstrained
CFR objective, solve equilibrium or yield stronger play. Independent math review
must settle the precise regret and average updates before dependent training.
Expected value at a traverser node is sum(sigma[a]*v[a]); the intended local
perturbed-action regret is (1-epsilon)*(v[a]-sum(pi[b]*v[b])). Simply replacing
pi by sigma in the old regret baseline is not this perturbed-action game.
Opponent-sampled averages record sigma, retaining the production averaging
estimator's scope and limitations. Hidden cards/payoffs remain evaluator-owned;
policy probabilities use only legal acting-seat observations.

## Bounded workload and measurements

Prospective small feasibility scope: three players, current live-order K50 keys,
production menu, independent uniform 13-depth 10–250 BB initial-stack law. It
matches the current mixed-stack recipe's game, not its mature table or seed
uncertainty. Fresh matched root seed20261028456011, eight roots/seat/sweep,
linear weights, two workers, whole-sweep cap2,000,000 rows, endpoints128/512
sweeps. Counts are matched sweeps/root contexts; traversal-node counts may differ.
Control and candidate start empty. A separate-process reproduction repeats the
same fixed work; it is proof, not another experimental seed.

Before training, freeze watch keys from512 independently generated legal passive
hands, seed20261028456002, with the same chance law and uniform button. Preserve
every turn/river observation/key including never-hit keys; freeze all family and
street denominators. No choice based on losing hands or favorable outcomes.
P0/P1/P2 public-history families follow PR425. Report complete root inventory,
watch reach, update magnitudes, positive regret and average evidence separately,
root-grouped raw/linear coefficient moments and nominal ESS, retained versus
attempted/discarded updates, and zero-update slots at admission/freeze/end.
Signed regret/payoff ESS is invalid. Grouping is per independently seeded root;
correlated branches never become separate independent samples. Adaptive-policy
ESS is a concentration diagnostic, not a statistical confidence interval.

The repeated-learning proxy follows PR425: each key needs nonzero regret and
positive-average evidence from at least four distinct roots for each kind, with
grouped coefficient ESS>=4 each. Include all zero/never-hit denominators. A
prospective continuation signal requires at least five more such retained watch
keys than the control and at least five in total, without increasing the share
of fully zero-update admitted slots by more than five percentage points. This
is an explicit research heuristic, not a strength or adoption gate. Missing the
proxy is retained as a negative/inconclusive result; no hands/sweeps are added.
Mathematically nonzero but negligible weights are not silently called useful;
publish their magnitudes and concentration alongside the proxy.

Final logical row values/visits, table identity, watch/cell ledgers and row
digests must reproduce exactly. Freeze timing and whole-sweep overshoot are
reported; flat membership after a protective cap is not natural saturation.
This small fresh task cannot establish mature support or deployment quality.

## Correctness, cost and stops

Keep implementation research-only where possible: reuse game/keys/table merge
and compare epsilon=0 against unchanged production traversal. Fixtures exhaust
tiny two/three/four-player games, comparing expected values, all regret vectors
and all average vectors to an independent perturbed-game oracle. Require zero
epsilon parity, legal information boundaries, finite probabilities/updates,
thread/reproduction parity and source/input/executable identity checks. No
dependent training before independent review clears unresolved math questions.

Local fixtures and a separate tiny cost calibration precede a published complete
quote. M4 is the proposed main host, subject to fresh AC, nonblocking compute
mutex, measured RAM/disk admission and explicit allocation acceptance. No mature
model is loaded, exported or copied. The earlier30–60minute estimate is a
provisional planning scenario, not accepted compute or reserved storage. Publish
build/qualification, traversal, observer/merge, reproduction, hashing/readout,
wall/CPU, sampled memory, thermal and retained-byte costs separately.

The new controller fails closed on missing/nonfinite temperature or thermal-state
readings, owner STOP, correctness/config changes and declared resource exhaustion.
It owns and terminates its entire child process group, including multiprocessing
workers. No elapsed-time stop substitutes for the fixed scientific workload.
All failures and partials remain; no scientific retries or automatic tuning.
Historical published run guards/proofs are preserved as historical evidence.

Ordinary working/final files stay in a new ignored owned tree; no model/raw
ledger payload enters Git. Cleaner owns later stable ZIP/cache/Drive archival.
No cleanup, credential access, other jobs, host configuration or schedules change.
