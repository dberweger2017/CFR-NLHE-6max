# Mixed-stack training for Open Poker tables (protocol)

This protocol is committed before any training or evaluation. It is one experiment, one lineage. Nothing is promoted, and no default or release changes.

## Why

At [Open Poker](https://docs.openpoker.ai/), buy-ins run from 50 to 250 BB and stacks drift with every hand. The bot doesn't leave and rejoin to reset its depth, so one model has to play every depth at once, including tables where every seat's stack is different.

Live-order keys never read initial stacks. A model trained at 100 BB can therefore play any table through the projected view ([phantom/depth protocol](openpoker-phantom-depth.md)), but every row it learned comes from 100 BB situations. In mixed-stack training, every root draws each seat's depth independently, so the same rows are learned from the chip situations that real tables produce.

## The stack law

`iid-uniform-depth-grid-v1`, declared in the checkpoint identity (`stack_distribution`):
- **Depth:** each seat independently draws a depth, uniformly from the 13-point grid 10, 15, 20, 30, 40, 50, 65, 80, 100, 125, 150, 200, 250 BB (about evenly spaced in log depth).
- **Button:** drawn uniformly, as in fixed-stack training.
- **Scope:** live-order schema, 3–6 players, 50/100 blinds. The trainer option is `--stack-law live-depth-grid-v1`, and it refuses `--stacks`, `--stack-bb` and other blinds or schemas.
- **Consumers:**
  - Fixed-only consumers refuse a mixture policy.
  - A mixture policy plays natively at any table whose stacks are all grid depths.
  - Its projected view keeps every real seat's chips and gives phantom seats 100 BB.
- **Unchanged:** fixed-stack identities, keys, training and checkpoint bytes.

## Training

One live-order 10B model, `mix`, with #431's recipe:
- seed 2026102361001;
- fast mode, 16 threads, 8 roots per seat;
- 250M entries with whole-iteration freeze;
- average scope 3, K50 cards;
- six players under the stack law.

It is exported, mass-audited, converted to binary and verified like #431's.

The comparison models are already trained:
- `six`: #431's 100 BB 10B, binary `f894a59f…`.
- `six50`: the phantom/depth study's 50 BB 10B, used only as a field.

## Qualification (the run stops on any failure)

1. **Fixed training unchanged:** at seed 2026102361001, 16 threads and 100M nodes, the fixed-stack 100 BB live-order checkpoint is still `482a0f8f…`.
2. **Mixture determinism:** two 100M-node mixture runs, at 16 and at 8 threads, write byte-identical checkpoints.
3. **Native tests:** the library tests pass on bb128. These include the strict stack-law identity, seeded grid draws and the projection tests.
4. **Inputs:** `six` and `six50` match their pins.
5. **Smoke:** a 100M-node `mix` completes the full pipeline on every table, at 64 blocks per field and on separate roots:
   - arena;
   - trace scan;
   - independent replay;
   - all-in equity;
   - report.

## Evaluation

**Deals:**
- 4 banks × 4,096 blocks per field;
- each block is played at every cyclic seating;
- roots are `20261027600000 + 1000·bank + case index`, disjoint from the phantom/depth study's.
- Both arms play the same deals and both focals use the projected view: arm 0 = `six`, arm 1 = `mix`.
- Scoring is all-in adjusted, over blocks.

| Table | Study | Stacks (BB) | Fields; the first is primary |
|---|---|---|---|
| `100bb` | home | 100 each | `trained` (5 × `six`), `mix`, four scripts, `mixed` |
| `50bb` | depth | 50 each | `trained` (5 × `six50`), `mix`, four scripts, `mixed` |
| `20bb` | depth | 20 each | `mixed`, `mix`, four scripts |
| `200bb` | depth | 200 each | `mixed`, `mix`, four scripts |
| `unequal-a` | depth | 100, 50, 150, 80, 100, 200 | `mixed`, `mix`, four scripts |
| `unequal-b` | depth | 250, 30, 100, 15, 200, 65 | `mixed`, `mix`, four scripts |
| `unequal-4p` | depth | 200, 50, 100, 30 | `mixed`, four scripts |

- **Fields:**
  - The scripts are `random`, `check-call`, `tight-aggressive` and `pot-pressure`.
  - Six-player `mixed` is two check-call, two pot-pressure and one tight-aggressive. Four-player `mixed` is check-call, pot-pressure and tight-aggressive.
  - The `mix` field (5 copies of `mix`, native) sits only at six-player tables whose stacks are all grid depths.
- **Stacks:** the cyclic schedule moves every identity through every stack.

## Decision rules, fixed now

Every primary is `mix` minus `six` on the table's primary field.

**Home (`100bb`), non-inferiority:** a 95% interval; the margin is **10 BB/100**.
- **Mixed adequate at 100 BB:** lower bound above −10.
- **Mixed loses at 100 BB:** upper bound below −10.
- **Otherwise inconclusive.**
- **Harm flag:** any other field whose Bonferroni 95% interval over the table's other fields lies entirely below −10.

**Depth, per table:** a Bonferroni 95% interval over the six depth tables.
- **Mixed better:** lower bound above 0.
- **Fixed better:** upper bound below 0.
- **Otherwise no difference shown.**

**Recommendation for the Open Poker route**, which is a recommendation only: route `mix` instead of `six` if all four hold:
1. `100bb` reads "mixed adequate at 100 BB";
2. `100bb` has no harm flag;
3. no depth table reads "fixed better";
4. at least one depth table reads "mixed better".

Otherwise keep `six` and report why.

**Descriptive:**
- each arm's share of decisions without a positive-mass row, by street;
- absolute results per arm;
- realized results beside adjusted ones;
- the run's seat-depth draw counts.

## Rules

- **Host:** bb128. Stops: CPU 90 °C, VRM (Thermistor 15) 100 °C, below 20 GB free on the HDD and below 10 GB free on the NVMe.
- **Disk:** work under `/mnt/data2tb/openpoker-mixed-stacks-20261027/`. #431's and the phantom/depth study's models are read only.
- **Expected cost:**
  - about 30 minutes of training;
  - about 20 minutes of arena;
  - about 2 hours of all-in equity;
  - plus smoke and qualification.
- **Failures:**
  - A research failure is reported as is, with no retry or retuning.
  - A qualification failure stops the run.
  - Plumbing problems go in the PR.
