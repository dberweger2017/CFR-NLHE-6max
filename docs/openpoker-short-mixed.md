# Mixed-stack models for 3, 4 and 5 players (protocol)

This protocol is committed before any training or evaluation. It is one experiment, one lineage per model. Nothing is promoted, and no default or release changes.

## Why

At 3–5 dealt players, the router currently plays ([routing results](reports/openpoker-routing/results.md)):
- **inside the [89.4, 136.9] BB band:** #445's dedicated 100 BB `pN`;
- **elsewhere:** #447's six-player mixed-stack `mix` through phantom early-position folds.

At 100 BB, `pN` beats `mix` by 21–26 BB/100, so the player count matters. Away from 100 BB, `mix` beats `pN` by 30–81, so mixed-stack training matters. A model trained for N players at mixed stacks might keep both advantages. In heads-up, where no phantom folds are possible, `humix` beat the fixed model by 108–155 off-depth and was level at 100 BB ([heads-up results](reports/openpoker-heads-up/results.md)).

## Models

Three live-order 10B models, with #431's recipe:
- seed 2026102361001;
- fast mode, 16 threads, 8 roots per seat;
- 250M entries with whole-iteration freeze;
- average scope 3, K50 cards.

| Alias | Players | Stacks |
|---|---|---|
| `p3mix`, `p4mix`, `p5mix` | 3, 4, 5 | `iid-uniform-depth-grid-v1`: each seat drawn from #447's 10–250 BB grid |

Each model is exported, mass-audited, converted to binary and verified like #431's. The comparison models are read only, with pins checked:
- `p3`, `p4`, `p5`: binaries `1a607613…`, `66ec2f87…`, `bdc5ab50…`;
- `mix`: binary `64c693c4…`.

## Qualification (the run stops on any failure)

1. **Six-player training unchanged:** at 100M nodes the live-order checkpoint is still `482a0f8f…`.
2. **Mixture determinism:** two 100M-node five-player mixture runs, at 16 and at 8 threads, write byte-identical checkpoints.
3. **Native tests:** the library tests and the paired-arena host tests pass on bb128.
4. **Smoke:** 100M-node versions of all three models, with the earlier studies' smoke `pN` and `mix`, complete the full pipeline on every table, at 64 blocks per field and on separate roots:
   - arena;
   - trace scan;
   - independent replay;
   - all-in equity;
   - report.

## Evaluation

- **Deals:** 4 banks × 4,096 blocks per field. Each block is played at every cyclic seating.
- **Roots:** `20261028200000 + 1000·bank + case index`.
- **Views:** both focals use the projected view.
- **Contrast:** every contrast is `pNmix` minus the current route's model.
- **Scoring:** all-in adjusted, over blocks.

| Table (each N) | Study | Stacks (BB) | Arm 0 | Fields; the first is primary |
|---|---|---|---|---|
| `Np-100bb` | home | 100 each | `pN` | `dedicated` (`pN` copies), `mixed`, `pot-pressure`, `mixed-copies` (`pNmix`) |
| `Np-50bb`, `Np-20bb`, `Np-200bb` | depth | that depth at every seat | `mix` | `mixed`, `pot-pressure`, `tight-aggressive`, `mixed-copies` |
| `Np-unequal` | depth | 3: 150, 40, 100 · 4: 65, 150, 100, 30 · 5: 100, 50, 200, 30, 125 | `mix` | the same |

`mixed` is as in the earlier studies.

## Decision rules, fixed now

**Home, non-inferiority:** a Bonferroni 95% interval over the three home tables; the margin is **10 BB/100**.
- **Mixed adequate at 100 BB:** lower bound above −10.
- **Mixed loses at 100 BB:** upper bound below −10.
- **Otherwise inconclusive.**
- **Harm flag:** any other home field whose Bonferroni 95% interval over the table's other fields lies entirely below −10.

**Depth, per table:** a Bonferroni 95% interval over the twelve depth tables.
- **Dedicated mixed better:** lower bound above 0.
- **Six-player mixed better:** upper bound below 0.
- **Otherwise no difference shown.**

**Route, per N:**
- **Off the band:** `pNmix` replaces `mix` if no depth table at N reads "six-player mixed better" and at least one reads "dedicated mixed better". Otherwise `mix` stays.
- **In the band:** `pNmix` also replaces `pN`, so it plays every N-handed hand, only if both hold:
  - it took the off-band route;
  - `Np-100bb` reads "mixed adequate at 100 BB" with no harm flag.

  Otherwise `pN` stays in the band.
- **Adverse finding:** a depth table that reads "six-player mixed better" is reported as one.

**Descriptive:**
- each arm's share of decisions without a positive-mass row, by street;
- absolute results per arm;
- realized results beside adjusted ones;
- entries and table freeze;
- seat-depth draw counts;
- binary sizes.

## Rules

- **Host:** bb128. Stops: CPU 90 °C, VRM (Thermistor 15) 100 °C, below 10 GB free on the NVMe and below 20 GB free on the HDD.
- **Order:** the run starts after the untrained-fallback study (#452) finishes, so the two don't share the CPU.
- **Disk:** work under `/home/dberweger/openpoker-short-mixed-20261028/` on the NVMe. The comparison models are read in place.
- **Expected cost:**
  - three trainings of about 30–40 minutes each, plus about 15 minutes each of export, audit and conversion;
  - about 30 minutes of arena;
  - about 2–3 hours of all-in equity;
  - plus smoke and qualification.
- **Failures:**
  - A research failure is reported as is, with no retry or retuning.
  - A qualification failure stops the run.
  - Plumbing problems go in the PR.
