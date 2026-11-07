# Wide-grid models for short stacks (protocol)

This protocol is committed before any training or evaluation. Nothing is promoted, and no default or release changes. A route change, if one qualifies, is a separate PR.

## Why

The first live session busted on two decisions without a trained row ([live pilot](reports/openpoker-live-pilot/results.md)). One came at 4 BB, below the 10–250 BB grid every live model trained on. Live-order keys hold each live stack's stack-to-pot bucket, so a short stack facing deep ones makes chip situations the grid never dealt. A model trained only at short tables would miss those too: when our stack is short, the others usually are not.

So the grid is widened, not replaced: the **wide grid** is #447's 13 depths plus 1, 2, 3, 4, 5, 6 and 8 BB, 20 depths in all, each seat drawn independently and uniformly. Short and deep seats then meet at one table during training.

## Models

Live-order 10B models with #431's recipe: fast mode, 16 threads, 8 roots per seat, 250M entries with whole-iteration freeze, average scope 3, K50 cards. The stack law is `wide-depth-grid-v1` (`iid-uniform-depth-grid-v1` over the 20 depths).

| Alias | Players | Plays through phantom folds at | Seeds (run 1, 2, 3) |
|---|---|---|---|
| `widemix` | 6 | 3–5 players | 20261106710001, …710002, …710003 |
| `huwide` | 2 | — | 20261106810001, …810002, …810003 |

Each model is exported, mass-audited, converted to binary and verified like #431's. The comparison models are today's live routes, read only, with pins checked:
- `humix` (2 players): binary `9d39dda9…`;
- `p3mix` (3 players off the band): binary `afddb595…`;
- `mix` (4–6 players off the band): binary `64c693c4…`.

## Code changes

- The trainer gains a second depth grid, `DepthGrid::Wide`, next to the live grid. The live grid's declaration, draws and identities are unchanged, so existing models load as before.
- The paired-arena host accepts table stacks from 1 BB; it accepted 10 BB and up.

## Qualification (the run stops on any failure)

1. **Native tests:** the library tests and the paired-arena host tests pass on bb128.
2. **Fixed training unchanged:** at 100M nodes the six-player live-order checkpoint is still `482a0f8f…`.
3. **Live grid unchanged:** the 100M five-player live-grid mixture is still `0448ff91…`, byte for byte, as in #453.
4. **Wide-grid determinism:** two 100M six-player wide-grid runs, at 16 and 8 threads, write byte-identical checkpoints.
5. **Comparison pins:** every comparison model's binary and mass receipt match their pins.
6. **Smoke:** 100M wide models complete the full pipeline on every table at 64 blocks per field on separate roots: arena, trace scan, independent replay, all-in equity and report.

## Evaluation

- **Tables:** every table has a seat under 10 BB. They are in the client's capped form: no seat holds more than the largest other seat, since chips beyond that can never be won or lost.

| Table | Players | Stacks (BB) | Arm 0 | Arm 1 | Fields; the first is primary |
|---|---|---|---|---|---|
| `2p-3bb`, `2p-5bb`, `2p-8bb` | 2 | 3·3, 5·5, 8·8 | `humix` | `huwide` | `wide-copies` (`huwide`), `pot-pressure`, `tight-aggressive`, `check-call`, `random` |
| `3p-5bb`, `3p-short-deep`, `3p-unequal` | 3 | 5·5·5; 4·100·100; 8·40·100 | `p3mix` | `widemix` | `mixed`, then the four scripts |
| `4p-short-deep` | 4 | 5·100·100·100 | `mix` | `widemix` | the same |
| `6p-5bb`, `6p-short-deep`, `6p-unequal` | 6 | 5 each; 3·100·100·100·100·100; 8·100·50·100·150·100 | `mix` | `widemix` | `mixed`, the four scripts, `wide-copies` (`widemix`) |

- **Fields:** `mixed` and the four scripts are as in the earlier studies; copies fill every other seat.
- **Amendment, November 6, before any main training or results:** the smoke run stopped at its first arena because model opponents play natively and must hold the table's stacks and player count. Copies of `humix`, `p3mix` and `mix` can't sit at a table with a seat under 10 BB, and `widemix` can't sit at 3 or 4 players. The `current` and `current-copies` fields are dropped, `wide-copies` stays only heads-up and at six players, and heads-up's primary field becomes `wide-copies`, as the earlier heads-up depth tables used the strongest model's copies. Nothing else changes.
- **Views:** both focals use the projected view.
- **Contrast:** arm 1 minus arm 0, all-in adjusted, over blocks.
- **Deals:**
  - run 1: 4 banks × 4,096 blocks per field, roots `20261106100000 + 1000·bank + case index`;
  - runs 2 and 3: 1 bank × 4,096 blocks, roots offset by 100,000 per run;
  - each block is played at every cyclic seating.

## Decision rules, fixed now

**Per table, run 1:** a Bonferroni 95% interval over the ten tables.
- **Wide better:** lower bound above 0.
- **Current better:** upper bound below 0.
- **Otherwise no difference shown.**
- **Harm flag:** any other field whose Bonferroni 95% interval over the table's other fields lies entirely below −10 BB/100.

**Replication:** runs 2 and 3 replicate a table when their primary point estimates are both above 0.

**Route, per group** (heads-up; 3 players; 4–6 players, decided by the 4p and 6p tables): the wide model plays hands where some dealt seat holds under 10 BB after capping, only if, in that group:
- no table reads "current better";
- at least one table reads "wide better" and replicates;
- no table has a harm flag.

Otherwise the current route stays. 5-player hands follow the 4–6 group's verdict without a table of their own; that is a stated limitation.

**Descriptive:** each arm's share of decisions without a positive-mass row, by street (the live bust's mechanism); absolute results per arm; realized beside adjusted results; entries and table freeze; seat-depth draw counts; binary sizes; per-run results.

## Rules

- **Host:** bb128, all 16 threads. Stops: CPU 90 °C, VRM (Thermistor 15) 100 °C, below 10 GB free on the NVMe and below 20 GB free on the HDD. The VRM paste was retested on November 6: 10 minutes of 16-thread stress-ng peaked at 83 °C package and 58 °C VRM.
- **Disk:** work under `/home/dberweger/openpoker-wide-stacks-20261106/` on the NVMe (342 GB free at launch). The comparison models are read in place.
- **Expected cost:** six trainings of about 30–40 minutes plus about 15–30 minutes of export, audit and conversion each; about 1 hour of arena for run 1 and 15 minutes for each later run; all-in equity of a few hours, likely more than earlier studies since short stacks go all-in often. About 9–12 hours in all.
- **Failures:** a research failure is reported as is, with no retry or retuning. A qualification failure stops the run. Plumbing problems go in the PR.
