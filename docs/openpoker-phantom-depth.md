# Phantom folds and stack depth for Open Poker tables (protocol)

This protocol is committed before any training or evaluation. It covers two one-lineage experiments that decide how a bot routes hands at [Open Poker](https://docs.openpoker.ai/) tables. Nothing is promoted, and no default or release changes.

## Why

Open Poker deals 2–6 players per hand at 6-max tables, with buy-ins from 50 to 250 BB and stacks that drift. Our blueprints are trained for one player count and one equal stack depth. Two questions decide how many blueprints the bot needs.

**Player count.** A hand dealt to N players is the six-player game after 6−N phantom early positions fold preflop: blinds, pot, positions and action order are identical. If #431's six-player live-order 10B plays 3–5-handed tables this way about as well as a dedicated model, the bot needs only the six-player model and the existing heads-up model. Heads-up is different (the button posts the small blind and acts last after the flop) and is not tested.

**Stack depth.** Live-order keys don't read initial stacks: the pot and each live stack enter only as buckets, from real chips. A 100 BB model can therefore play any depth without translation, but it was trained only on 100 BB situations. A 50 BB model shows what that costs, and whether a shorter-depth blueprint is worth routing to.

## The projected view

`multi_view::project` gives a model its own frame of a table it wasn't trained at:
- **Phantom seats:** fewer players than the model's table. Phantom seats sit at the first positions after the big blind, hold the model's stack and fold preflop before any real action. Three or more real players only.
- **Configuration:** the model's own, so lookups accept it; every live stack, bet and contribution stays the table's real chips.
- **Exactness:** a unit test plays random legal hands at 3–6 players and checks that each projected observation equals a real six-player hand's observation after the phantom folds. A second test checks that live-order keys are unchanged when only the configured initial stacks change, while history keys differ.
- **Scope:** live-order schemas only, focal arms only. Opponents always play their native view.

The paired arena gains three opt-in case fields: `focal_views` (`native` or `projected` per arm), 3-player tables and `stacks_bb` (one stack per seat, 10–250 BB; the cyclic schedule moves every identity through every stack).

## Training

Four live-order 10B models with #431's recipe: seed 2026102361001, fast mode, 16 threads, 8 roots per seat, 250M entries with whole-iteration freeze, average scope 3, K50 cards:

| Alias | Players | Stack |
|---|---|---|
| `p3`, `p4`, `p5` | 3, 4, 5 | 100 BB |
| `six50` | 6 | 50 BB |

`six` is #431's six-player 100 BB 10B (binary `f894a59f…`). Each new model is exported, mass-audited, converted to binary and verified like #431's.

## Qualification (the run stops on any failure)

1. **Training unchanged:** at seed 2026102361001, 16 threads and 100M nodes, the branch reproduces the live-order pilot's checkpoint `482a0f8f…`.
2. **Native tests:** the projection tests and the paired-arena host tests pass on bb128.
3. **Inputs:** `six`'s binary and mass receipt match their pins.
4. **Smoke:** 100M-node versions of all four models complete the full pipeline on every table at 64 blocks per field: arena, trace scan, independent replay, all-in equity and report. Smoke outputs are kept apart and never enter the results.

## Evaluation

**Deals:** 4 banks × 4,096 blocks per field, each block played at every cyclic seating (N hands); roots `20261027300000 + 1000·bank + case index`. Both arms play the same deals. Scoring is all-in adjusted, over blocks.

**Phantom study** (100 BB; arm 0 = dedicated `pN`, native; arm 1 = `six`, projected):

| Table | Fields (N−1 opponents) |
|---|---|
| 3, 4 and 5 players | `dedicated` (copies of `pN`, primary), `random`, `check-call`, `tight-aggressive`, `pot-pressure`, `mixed` |

`mixed` is check-call + pot-pressure at 3 players, plus tight-aggressive at 4 and random at 5.

**Depth study** (six players; arm 0 = `six`, arm 1 = `six50`; each projected where it wasn't trained):

| Table | Stacks | Fields (5 opponents) |
|---|---|---|
| `50bb` | 50 BB each | `trained` (copies of `six50`, primary), the four scripts, `mixed` |
| `100bb` | 100 BB each | `trained` (copies of `six`, primary), the four scripts, `mixed` |
| `unequal` | 100, 50, 150, 75, 100, 200 BB | `mixed` (primary), the four scripts |

Six-player `mixed` is two check-call, two pot-pressure and one tight-aggressive.

## Decision rules, fixed now

**Phantom, per table size:** the primary is `six` (projected) minus `pN` on `dedicated`, with a **Bonferroni 95% interval over the three sizes**. The non-inferiority margin is **10 BB/100**.
- **Phantom adequate:** lower bound above −10.
- **Dedicated needed:** upper bound below −10.
- **Otherwise inconclusive:** the router uses the dedicated model at that size.
- **Harm flag:** any other field whose Bonferroni 95% interval over the five other fields lies entirely below −10.

The router uses phantom folds at a size only if it is adequate and has no harm flag.

**Depth, per table:** the primary is `six50` minus `six`, with a Bonferroni 95% interval over the three tables.
- **50 BB model better:** lower bound above 0.
- **100 BB model better:** upper bound below 0.
- **Otherwise no difference shown.**

A 50 BB route is recommended only if the `50bb` table shows "50 BB model better". Other fields are reported with Bonferroni 95% intervals over their table's other fields.

**Descriptive:** each arm's share of decisions without a positive-mass row, by street; absolute results per arm; realized results beside adjusted ones.

## Rules

- **Host:** bb128. Stops: CPU 90 °C, VRM (Thermistor 15) 100 °C, below 20 GB free on the HDD and below 10 GB free on the NVMe.
- **Disk:** work under `/mnt/data2tb/openpoker-phantom-depth-20261027/`. #431's inputs are read only.
- **Expected cost:** about 7 hours: four trainings of 20–40 minutes each, about 3 hours of arena and scans, and about 2 hours of all-in equity.
- **Failures:**
  - A research failure is reported as is, with no retry or retuning.
  - A qualification failure stops the run.
  - Plumbing problems go in the PR.
