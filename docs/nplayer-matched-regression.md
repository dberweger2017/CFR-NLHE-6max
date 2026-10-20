# Matched-state diagnosis of the random/random+TAG regression

Proposal360; owner authorized October20 as a separate PR alongside the mature
loader validation. That benchmark owns bb128 until it releases the compute
mutex. M1 is free for small local development/qualification for30–60min; no mature
models or large study run there. No new training, defaults, search or automatic
merge.

## Question and fixed inputs

Did the3B→10B change forfeit profitable value or avoid costly actions against
random/random+TAG? Both mechanisms can coexist. Use both independent PR357
lineages202610200601/02 and their unchanged fixed-membership3B/10B averages.
Discovery PR355 is context, not another independent confirmation. Preserve the
adverse scripted evidence; aggregate checking rates do not establish a cause.

Extract only acting hero's own cards, visible board, complete public action
prefix, position and script identities from verified archived traces. Never
pass opponent holes, original deck, future board, payoffs or chosen outcomes to
the matched-state/policy/belief input. Reject unknown input fields. Independent
reconstruction must recover the archived key/menu exactly.

## Matched-state panel

Sample one permutation and one hero decision per archived six-hand block with
fixed hashes (decision ordinal0–15 selected before seeing the hand, omitted
if unreached, so future decision counts cannot affect selection), then retain32
discovery and32 held-out observations per
field/reached-policy/street stratum. Split by whole block, not duplicate hand;
use outcome-blind deterministic priority sampling. Report every populated and
missing stratum, both original reach distributions, position, menu and original
mass statuses. Probe both exact policies on each identical observation. Action
probability/sizing/total-variation changes are descriptive, not causal.

## Legal-belief counterfactual panel

Choose the largest-disagreement discovery observation per
field/reached-policy/street stratum, ties fixed by state ID: at most16 per fresh
seed,32 total. This conditional panel deliberately targets changed decisions;
its returns are not a population win-rate or attribution of the whole headline
regression. Keep held-out observations for descriptive confirmation.

For random/random+TAG there is at most one TAG opponent. Enumerate every
compatible unordered TAG holding and weight by the likelihood of that script's
observed actions. Random's action probabilities depend only on the public menu
and cancel from the holding posterior. Sample other private holdings and future
cards uniformly without replacement after removal of visible cards and the
sampled TAG holding. The script likelihood integrates action RNG; archived
hidden holdings/runouts are never reused. Report posterior support, entropy/
effective holding count and normalization. This is a known-script belief model,
not a learned/general opponent range.

Use32 independent discovery belief worlds to select one legal menu action,
then512 fresh held-out worlds for evaluation. Evaluate all legal root actions
under common hidden worlds and action streams, with both fixed3B and fixed10B
hero continuations. Opponents keep their exact scripts and receive only their
own legal observations. Compare3B/10B root mixtures and the selected alternative
within each continuation (values are BB per decision, not BB/100). Repeat all32+512 worlds in memory for exact
reproduction without reloading models; repeated worlds are not extra samples.
Keep discovery and held-out RNG roots distinct.

Record visible made-hand features and conditional showdown share against
current live contenders on fresh belief runouts (no-further-folding proxy, not
strategy value). Never feed those sampled hidden values to a policy.

Report paired Monte Carlo estimates/standard errors and predeclared family
intervals for the fixed selected-state panel (Bonferroni upper family512,
two-sided empirical Bernstein bounds across512 independent worlds, with
normal intervals auxiliary; Monte Carlo uncertainty conditional on observations,
not a full-policy strength interval), plus each action value and its
probability shift. A reduction in betting only indicates missed value if its
alternative has higher conditional value; it can instead avoid negative value.
Different continuation results indicate dependence on downstream strategy. No
claim of multiplayer equilibrium, universal strength or a search remedy follows.

## Execution and limits

Qualify likelihoods against the existing script sampler, visible-input privacy,
posterior support/normalization, legal reconstruction, branching/accounting,
randomness separation and deterministic reproduction on small local fixtures.
Use a small measured calibration before the fixed mature panel. Two models
resident at a time; lineages sequential. Stage only new owned completed outputs
with verified copies/accessible paths. Preserve earlier PR inputs and all
failure/partial/raw evidence. CPU90°C/Thermistor15 100°C thermal stops and
correctness/owner stop; inspect disk/RAM/swap manually. No competing measured
bb128 load job, automatic retry or outcome-driven extension. Full costs and any
unsupported/insufficient states must be reported. Raw evidence stays outside Git;
Research-Cloud archival remains pending until verified receipt.

## Bounded conditional uncertainty

Primary intervals rescale [Maurer–Pontil2009, theorem4](https://www.learningtheory.org/colt2009/papers/012.pdf)
and union-bound both tails over at most512 contrasts. With n=512, sample variance
s², known range width R and L=ln(4×512/0.05), the half-width is
sqrt(2s²L/n)+7RL/[3(n−1)]. Each hero return lies in[−100,200]BB, so a linear
action contrast with coefficients c has width R=300Σ|c|. Root-mixture and
selected-action widths use their actual fixed coefficients; identical actions
have zero width. Selection uses independent discovery worlds. These bounds
can remain wide after a small panel; normal/SE estimates are descriptive and
do not override the bounded decision interval. No outcome-driven extra worlds.
