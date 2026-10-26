# River search when the hero acts second

Opt-in engineering change; no default, player, model or release change, and no strength claim.

## What changes

River search (PR373 to PR398) begins only at the hero's first river decision when the hero is
the **first** river actor. With `search_second_to_act`, it also begins at the hero's first river
decision after the opponent's single first river action (check or bet), still heads-up, neither
player all-in, one contested pot.

- **Root:** the subgame still starts at the first river decision (equal contributions, the same
  terminal ledger). The opponent's first action there is **fixed to its blueprint row** for every
  holding, so the opponent's range after that action follows the same blueprint likelihoods as
  every earlier street. River actions never enter the belief prior.
- **Played row:** the hero's average row at the child for the action actually taken.
- **Quality:** only the hero's played subtree is judged. The opponent's root and every branch it
  ruled out are settled (`Solver::set_settled`): best responses keep the profile there instead of
  deviating, in quality and in best-response values alike. Unsettled fixed nodes, such as the
  constraints of prepared requests, are still deviated from exactly as before.
- **Target:** best-response gains are weighted by reaching each node. The quality target is
  multiplied by the probability of the observed action under the solver's projected product
  law, conditioned on compatible hero/opponent holdings. This uses the entire modeled hero
  range and includes card removal, rather than just the opponent's marginal action share.
  Thus the played subtree keeps the same conditional per-decision target (at a 10% share, a
  ten times smaller target). The base target still uses the pot at the river start, so after
  an opponent bet it is stricter than a first-to-act root at the larger pot would get, until
  the 0.1 BB cap binds. This does not remove the existing folded-law projection approximation.
- **Fallbacks:** a root that misses the target, a zero-reach own holding, an unsupported tree or an
  observed opponent action with zero modeled likelihood plays the blueprint at the hero's decision.
  In particular, an action possible across the opponent's range but impossible against the hero's
  actual cards falls back before solving; globally positive likelihood alone is insufficient.
- **Continuation:** retained rows replay the opponent's first action before later actions;
  off-tree handling is unchanged.
- **Scope:** projected-product beliefs and `solve` only. Exact backends, `classify`,
  `belief-control`, `diagnose`, omitted-raise evaluation, retained audits, profile export and
  restore, and harm and full-menu diagnostics refuse second-to-act roots. An opponent all-in first
  action is refused (eligibility already excludes it).

## How to enable

Arena manifest case field `"search_second_to_act": true` (requires `"search": true`). Absent or
false keeps first-to-act search only and the trace header unchanged; a true value adds
`"search_second_to_act": true` to the trace header. Library callers pass `second_to_act` to
`WholeHandPolicy::new` and `eligibility`.

## Checks

- First-to-act results unchanged: on 299 eligible first-to-act roots from self-play, every
  `river_live` result (strategy, stopping checkpoint, quality, checkpoint gains) equals main's.
- Second-to-act roots: the same hands add 280 eligible roots. All 280 solve; under the scaled
  target (median 0.032 BB, minimum 0.003 BB) 278 meet it and 2 fall back to the blueprint. Solve
  time per root: median 0.22 s, 90th percentile 0.75 s, maximum 3.16 s.
- Unit tests: second-to-act roots keep the river start and the opponent action and never put river
  actions in the prior; a hero river action and an opponent all-in first action are refused;
  settled nodes are kept by quality and best-response values while plain fixed constraints are
  unchanged; eligibility with and without the switch; the declared solve errors fall back; and,
  through the retained session with a fixture model, the opponent root is fixed and the hero row
  comes from the taken child, in-solve quality equals the quality recomputed with an independently
  built settled set and the target scales with the share, an opponent action the blueprint never
  takes falls back, an unconverged root falls back at the hero's decision,
  continuation replays the opponent action, and audits, exports and omitted evaluation refuse the
  root. Copies that leave the root unfixed, read the wrong child, skip the prefix replay, fall back
  at the river start, drop the target scaling, skip the settling, settle only the opponent's root,
  also settle nodes inside the played subtree, drop the all-in refusal, or drop the zero-likelihood
  guard or its fallback each fail at least one of these tests.
- Paired arena (360 hands each against peers and against check-call/pot-pressure): every on/off
  action difference occurs at an installed focal river search, and retained continuations served
  later decisions. This ran on an earlier prototype of this change (environment switch, before the
  quality and fallback hardening), not on the final code.

All of the above used a small laptop-trained three-player 100 BB model (110M nodes), not the frozen
10B models; they show the mechanism and its accounting, not strength.

The measurements above precede the blocker-aware support/target correction. New regression
fixtures independently enumerate compatible pair masses (1/3 and 2/3 versus a marginal1/2),
check no-overlap and constant-probability controls, and construct an opponent that bets only
with cards blocked by the actual hero. That retained-session fixture must return the exact
blueprint probabilities at the hero's decision, with no installed profile. Existing quality
tests also independently sum compatible pairs when checking the scaled target. No new arena
or mature-model speed/strength measurement is claimed for the correction.

## Suggested evaluation

A paired comparison of first-to-act search against first- and second-to-act search on the
existing three-lineage harness, with predeclared blocks and margins as in PR398. On the
self-play sample above, the switch nearly doubles the eligible roots (299 to 579 in 3,000 hands);
against peers in a 360-hand arena it raised installed roots from 18 to 42.
