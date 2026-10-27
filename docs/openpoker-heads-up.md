# Heads-up routes for Open Poker tables (protocol)

This protocol is committed before any training or evaluation. It is one experiment, one lineage per model. Nothing is promoted, and no default or release changes.

## Why

Open Poker deals heads-up hands, and the bot has no route for them:
- **Phantom folds don't reach heads-up:** the button posts the small blind and acts first preflop and last afterwards.
- **The released HU100 models can't be loaded:** they use the legacy trainer format, which the n-player decision service doesn't load.

Six-handed, a fixed-depth model loses about 50 BB/100 away from its depth, and a mixed-stack model recovers most of that. This study trains both kinds of model for two players and compares them on the same tables as #447.

## Models

Two live-order 10B models, with #431's recipe:
- seed 2026102361001;
- fast mode, 16 threads, 8 roots per seat;
- 250M entries with whole-iteration freeze;
- average scope 3, K50 cards.

| Alias | Players | Stacks |
|---|---|---|
| `hu100` | 2 | 100 BB each |
| `humix` | 2 | `iid-uniform-depth-grid-v1`: each seat drawn from 10–250 BB (#447's grid) |

The stack law now accepts 2–6 players, and the paired arena and its scanners accept heads-up schedules. Each model is exported, mass-audited, converted to binary and verified like #431's.

## Qualification (the run stops on any failure)

1. **Six-player training unchanged:** at 100M nodes the live-order checkpoint is still `482a0f8f…`.
2. **Heads-up mixture determinism:** two 100M-node runs, at 16 and at 8 threads, write byte-identical checkpoints.
3. **Native tests:** the library tests and the paired-arena host tests pass on bb128.
4. **Smoke:** 100M-node versions of both models complete the full pipeline on every table, at 64 blocks per field and on separate roots:
   - arena;
   - trace scan;
   - independent replay;
   - all-in equity;
   - report.

## Evaluation

- **Deals:** 4 banks × 4,096 blocks per field. Each block is played at both seatings.
- **Roots:** `20261027800000 + 1000·bank + case index`.
- **Arms:** arm 0 is `hu100`, arm 1 is `humix`, and both focals use the projected view.
- **Scoring:** all-in adjusted, over blocks.

| Table | Study | Stacks (BB) | Fields; the first is primary |
|---|---|---|---|
| `100bb` | home | 100, 100 | `trained` (`hu100`), `humix`, four scripts |
| `50bb`, `20bb`, `200bb` | depth | that depth at both seats | `trained` (`humix`), four scripts |
| `unequal-a` | depth | 150, 40 | the same |
| `unequal-b` | depth | 250, 100 | the same |

- **Primary field:** at each table, the opponent trained for that table. Fixed models play natively only at their own depth, so off 100 BB that opponent is `humix`.
- **Scripts:** `pot-pressure`, `tight-aggressive`, `check-call` and `random`.

## Decision rules, fixed now

These are the same as #447's ([mixed-stack protocol](openpoker-mixed-stacks.md)). Every primary is `humix` minus `hu100`.

**Home (`100bb`), non-inferiority:** a 95% interval; the margin is **10 BB/100**.
- **Mixed adequate at 100 BB:** lower bound above −10.
- **Mixed loses at 100 BB:** upper bound below −10.
- **Otherwise inconclusive.**
- **Harm flag:** any other field whose Bonferroni 95% interval over the table's other fields lies entirely below −10.

**Depth, per table:** a Bonferroni 95% interval over the five depth tables.
- **Mixed better:** lower bound above 0.
- **Fixed better:** upper bound below 0.
- **Otherwise no difference shown.**

**Route:**
- **`humix` for every heads-up hand,** if all four hold:
  1. `100bb` reads "mixed adequate at 100 BB";
  2. `100bb` has no harm flag;
  3. no depth table reads "fixed better";
  4. at least one depth table reads "mixed better".
- **Otherwise, a band:** `hu100` inside the six-handed depth band from the routing study (`openpoker-routing.md`), and `humix` elsewhere. This applies only if no depth table reads "fixed better". If one does, it is reported as an adverse finding and the heads-up route goes to a follow-up.

**Descriptive:**
- each arm's share of decisions without a positive-mass row, by street;
- absolute results per arm;
- realized results beside adjusted ones;
- entries and table freeze;
- seat-depth draw counts;
- binary sizes.

## Rules

- **Host:** bb128. Stops: CPU 90 °C, VRM (Thermistor 15) 100 °C, below 20 GB free on the HDD and below 10 GB free on the NVMe.
- **Disk:** work under `/mnt/data2tb/openpoker-heads-up-20261027/`.
- **Expected cost:**
  - two trainings of about 30–40 minutes each;
  - about 20 minutes of arena;
  - about 1.5 hours of all-in equity;
  - plus smoke and qualification.
- **Failures:**
  - A research failure is reported as is, with no retry or retuning.
  - A qualification failure stops the run.
  - Plumbing problems go in the PR.
