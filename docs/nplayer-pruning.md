# N-player regret-based pruning

`nplayer_train --fast --prune-bb B --prune-after N` skips the subtrees of traverser actions whose regret shows a large average loss. It is opt-in and needs fast mode ([nplayer-fast-mode.md](nplayer-fast-mode.md)); without the flags training is unchanged.

## What is skipped, and when

In iteration `t`, at a node where the **traverser** acts:

- **When:** only if `t > N`, and not in a full iteration. About one iteration in 20 is full, chosen by a hash of the seed and `t`, so every action is periodically explored again.
- **Which actions:** action `a` is skipped when both
  1. its current probability is exactly zero: regret matching gives zero to every action with non-positive cumulative regret whenever some action has positive regret; and
  2. its stored cumulative regret `R(a)` is below `-B * K * t(t+1)/2`, with `K` roots per seat. Regrets accumulate with linear weights, `sum of s * r_s` over iterations `s <= t`, and each iteration adds the regrets of all `K` roots of a seat, so this says that `a` has lost more than `B` big blinds per root and iteration on average, weighted the same way.

  Both are read from the table snapshot of the iteration start, which every traversal of the iteration reads.
- **Never skipped:** opponent nodes, terminal nodes, and any action with positive probability. If every action has non-positive regret, regret matching plays uniformly, so no action has zero probability and nothing is skipped.

## Effect of a skip, exactly

At the node with value `v = sum_b pi(b) v(b)`:

1. **Not visited:** the subtree below `a`. Its nodes get no regret, average or visit update in this iteration, and its opponent draws are not made.
2. **Not updated:** `a`'s own regret. Unpruned it would receive `t * (v(a) - v)`; pruned it keeps its value.
3. **Unchanged, exactly:** `v`, because `pi(a) = 0` removes `v(a)` from the sum. So every other action's regret update at this node, `t * (v(b) - v)`, is the same value, and so is the value returned to the parent and every update above it. The node's visit count still increases.
4. **Unchanged:** every opponent-sampled average update outside skipped subtrees. In fast mode a draw depends only on the node's path, so skipping a subtree changes no draw elsewhere.

So pruning changes which regrets and averages are updated (items 1 and 2), never the values passed up the tree (item 3). Pluribus prunes the same way but updates its average strategy in a separate pass; here the opponent-sampled average updates inside a skipped subtree are skipped too. A variant that still walked skipped subtrees for their averages gave the same small-game results (independent review: Kuhn 0.0124 against 0.0122, Leduc 1.730 against 1.752 at equal iterations).

## Why the limit grows with `t(t+1)/2`

A limit of `-B * t` would compare a quantity that grows like `t^2` with one that grows like `t`: eventually any action with a slightly negative average would be pruned, and in games with mixed equilibria near-zero actions would be frozen between full iterations. On 3-player Kuhn that version left the average strategy almost six times as exploitable after 10,000 iterations (mean largest best-response gain 0.057 against 0.0099 unpruned, eight seeds). Without the factor `K`, `B` would mean a loss of `B / K` per root, so pruning would grow more aggressive with more roots per seat. With the averaged limit:

| 3 players, mean largest gain over 8 seeds, 2 roots per seat | Unpruned | Pruned, equal iterations | Pruned, equal nodes |
|---|---:|---:|---:|
| Kuhn, 10,000 iterations, `B = 0.05`, `N = 500` | 0.00986 | 0.00967 | 0.01063 |
| Leduc, 1,000 iterations, `B = 0.05`, `N = 100` | 1.403 | 1.478 | 1.239 |

At equal nodes, the comparison that matters for training, pruning is within noise of unpruned training on Kuhn and better on Leduc. These are small-game sanity checks, not a strength result.

## Checkpoints

The header records `"pruning": {"bb", "after", "pruned_actions"}`. A checkpoint with pruning resumes only with the same `--prune-bb` and `--prune-after`; pruning in a checkpoint without fast sampling is refused.

## Checks

- `pruning_that_never_triggers_changes_no_row`: with an unreachable limit, checkpoint rows are byte-identical to unpruned training.
- `pruning_keeps_node_values_and_the_other_updates_bit_identical`: on traversals of a trained Leduc table with and without pruning (same draws, fork depths 0 and 4, limit 0 and the largest limit), the traverser's value is bit-identical, every skip saves at least one node, and at the root pruned actions receive no update and every other action exactly the same one.
- `all_negative_regrets_prune_nothing`.
- `the_pruned_count_is_one_per_skipped_action`.
- `the_pruning_schedule_waits_for_after_and_keeps_full_iterations`: no limit up to `N`; full iterations exactly where the hash says, about one in 20; the limit is `B` per root under the linear weights.
- `pruning_is_identical_for_every_thread_count_and_resumes_exactly`, including refusal of pruning outside fast mode.
- `pruning_converges_like_unpruned_fast_mode`: the table above; pruning at equal nodes must stay within 25% of unpruned.
