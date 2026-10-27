# Restricted fallbacks at untrained rows (protocol)

This protocol is committed before any evaluation. It is one evaluation of an existing model with no new training. Nothing is promoted, and no default or release changes.

## Why

In the first live session ([results](reports/openpoker-live-pilot/results.md)), 6 of 63 decisions had no trained row. There the policy draws uniformly from its whole menu, all-in included. Two of those draws, a turn shove and a flop raise, lost 2,137 chips and busted the bot.

Check-or-fold was already tested in the six-player loss diagnosis ([results](reports/nplayer-six-player-loss-diagnosis/results.md)), and it is not a candidate:
- it gained +4.7 BB/100 against tight-aggressive;
- it lost 67–582 against every weaker field, because random betting and calling win pots there.

This study tests two narrower changes. Both keep the random draw but remove the raises that cost the most when called.

## Arms

Both arms are #447's mixed-stack six-player 10B (`mix`, binary `64c693c4…`). It played every live decision. Both arms use the projected view and play the same deals.

| Arm | At a focal decision without a positive-mass row (missing or zero-mass) |
|---|---|
| 0, `uniform` | unchanged: uniform over the menu |
| 1, `no-all-in` | uniform over the menu without a raise to the whole stack |
| 1, `no-raise` | uniform over check or fold, and call |

- **Random number:** the candidate draws the same single number as `uniform` and maps it onto its own allowed actions. Later draws stay aligned.
- **Trained rows:** decisions with a positive-mass row are untouched.
- **Opponents:** opponents, including `mix` copies, keep the uniform fallback.

The menu is fixed by `min-pot-conditional-jam-v1`: check or fold, call, the minimum raise, a pot-size raise, and all-in. All-in appears only when it is at most twice the pot after a call. A minimum or pot raise that is the whole stack counts as all-in.

## Tables

Six players, focal `mix`, both candidates at every table:

| Table | Stacks (BB) |
|---|---|
| `100bb` | 100 at every seat |
| `50bb` | 50 at every seat |
| `unequal` | 100, 50, 150, 80, 100, 200 |
| `deep-outlier` | 100, 2,000, 100, 125, 150, 80; like the live table, one opponent far past the trained grid |

**Fields**, the first primary:
- `mixed`: two check-call, two pot-pressure and one tight-aggressive;
- `mix` copies, except at `deep-outlier`, because copies play natively and need every stack on the grid;
- `pot-pressure`, `tight-aggressive`, `check-call` and `random`.

**Deals:** 4 banks × 4,096 blocks per field. Each block is played at every cyclic seating. Roots are `20261028100000 + 1000·bank + case index`.

**Scoring:** all-in adjusted, over blocks.

The arena accepts stacks up to 2,500 BB, previously 250, for the `deep-outlier` table.

## Decision rules, fixed now

Each primary contrast is the candidate minus `uniform`, with a Bonferroni 95% interval over that candidate's four tables:
- **Candidate better:** lower bound above 0.
- **Uniform better:** upper bound below 0.
- **Otherwise no difference shown.**

**Harm flag:** any other field whose Bonferroni 95% interval over the table's other fields lies entirely below −10 BB/100.

**A candidate qualifies** if all three hold:
1. no table reads "uniform better";
2. no harm flag;
3. at least one table reads "candidate better".

**Outcome:**
- If both qualify, the one with the larger mean primary change over the four tables is chosen.
- If neither qualifies, the uniform fallback stays.
- A chosen candidate goes into the decision service in a follow-up PR, before any further live play.

**Descriptive:**
- each arm's share of focal decisions without a positive-mass row, by street;
- absolute results per arm;
- realized results beside adjusted ones.

## Limits

- **Miss rates:** the arena's fields reach untrained rows less often than the live table did, 1–4% against 9.5%. The study measures the candidates where misses occur in self-play and scripted play, not in every live line.
- **Thin stack:** a stack below 10 BB, like the live bust hand's 4 BB, is outside the tables.

## Qualification (the run stops on any failure)

1. **Inputs:** the `mix` binary and its mass receipt match their pins.
2. **Native tests:** the paired-arena host tests pass on bb128, single-threaded.
3. **Smoke:** #447's 100M smoke model runs every table at 64 blocks per field, on separate roots:
   - arena;
   - trace scan, including a check that no candidate arm ever plays an excluded raise at an untrained row;
   - independent replay;
   - all-in equity;
   - report.

## Rules

- **Host:** bb128. Stops: CPU 90 °C, VRM (Thermistor 15) 100 °C, below 10 GB free on the NVMe and below 20 GB free on the HDD.
- **Disk:** work under `/home/dberweger/openpoker-untrained-fallback-20261028/` on the NVMe. The `mix` binary is read in place from the routing study, with its pin checked.
- **Expected cost:** about 30 minutes of arena and about 1 hour of all-in equity.
- **Failures:**
  - A research failure is reported as is, with no retry or retuning.
  - A qualification failure stops the run.
  - Plumbing problems go in the PR.
