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
- **Quality:** best responses no longer deviate at fixed nodes, so the target measures the
  remaining game only. With no fixed node (first-to-act roots) the computation is unchanged.
- **Continuation:** retained rows replay the opponent's first action before later actions;
  off-tree handling and blueprint fallbacks are unchanged.
- **Scope:** projected-product beliefs and `solve` only; exact backends, `classify`,
  `belief-control` and `diagnose` refuse second-to-act roots.

## How to enable

Arena manifest case field `"search_second_to_act": true` (requires `"search": true`). Absent or
false keeps first-to-act search only and the trace header unchanged; a true value adds
`"search_second_to_act": true` to the trace header. Library callers pass `second_to_act` to
`WholeHandPolicy::new` and `eligibility`.

## Checks

- First-to-act results unchanged: on 299 eligible first-to-act roots from self-play, every
  `river_live` result (strategy, stopping checkpoint, quality, checkpoint gains) equals main's.
- Second-to-act roots: 280 of 280 from the same hands solve and meet the quality target.
- Unit tests: second-to-act roots keep the river start and the opponent action and never put river
  actions in the prior; a hero river action is refused; quality does not deviate at a fixed node
  (fails with the previous best response); eligibility with and without the switch.
- Paired arena (360 hands each against peers and against check-call/pot-pressure): every on/off
  action difference occurs at an installed focal river search, and retained continuations served
  later decisions. This ran on the prototype of this change, which had the same solver code but an
  environment switch instead of the manifest field.

All of the above used a small laptop-trained three-player 100 BB model (110M nodes), not the frozen
10B models; they show the mechanism and its accounting, not strength.

## Suggested evaluation

A paired comparison of first-to-act search against first- and second-to-act search on the
existing three-lineage harness, with predeclared blocks and margins as in PR398. On the
self-play sample above, the switch nearly doubles the eligible roots (299 to 579 in 3,000 hands);
against peers in a 360-hand arena it raised installed roots from 18 to 42.
