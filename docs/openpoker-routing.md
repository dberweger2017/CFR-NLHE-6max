# Depth band and short-handed routes for Open Poker tables (protocol)

This protocol is committed before any evaluation. It is one evaluation of existing models with no new training. Nothing is promoted, and no default or release changes.

## Why

The bot plays whatever stacks it has. Two earlier results bear on routing:
- **A fixed-depth model loses about 50 BB/100 away from its training depth** ([phantom/depth results](reports/openpoker-phantom-depth/results.md)).
- **#447's mixed-stack model wins by 32–82 BB/100 away from 100 BB, but loses 14.6 at exactly 100 BB**, interval [−22.2, −7.0] ([mixed-stack results](reports/openpoker-mixed-stacks/results.md)).

The router should therefore use the 100 BB model only in a band around 100 BB, and `mix` elsewhere. This study fixes that band at six players. It also decides, at 3–5 players, whether to use the dedicated 100 BB `pN` or `mix` through phantom folds.

## Models

All models are live-order 10B. None are retrained, and all are read only.

| Alias | Players | Training depth | Source |
|---|---|---|---|
| `six` | 6 | 100 BB | #431, binary `f894a59f…` |
| `mix` | 6 | 10–250 BB grid | #447, binary `64c693c4…` |
| `p3`, `p4`, `p5` | 3, 4, 5 | 100 BB | #445, binaries `1a607613…`, `66ec2f87…`, `bdc5ab50…` |

## Evaluation

- **Deals:** 4 banks × 4,096 blocks per field. Each block is played at every cyclic seating.
- **Roots:** `20261027700000 + 1000·bank + case index`, disjoint from the earlier studies.
- **Arms:** arm 0 is the fixed model, arm 1 is `mix`, and both focals use the projected view. Both arms play the same deals.
- **Scoring:** all-in adjusted, over blocks.

**Band study** (six players; `six` vs `mix`):

| Table | Stacks (BB) | Fields (5 opponents) |
|---|---|---|
| `65bb`, `80bb`, `125bb`, `150bb` | that depth at every seat | `mixed` (primary), `mix` copies, `pot-pressure`, `tight-aggressive` |
| `near-100` | 80, 100, 125, 100, 80, 125 | the same |

**Short study** (N = 3, 4, 5; `pN` vs `mix`, which goes through phantom folds):

| Table | Stacks (BB) | Fields (N − 1 opponents) |
|---|---|---|
| `Np-100bb` | 100 each | `dedicated` (`pN` copies, primary), `mixed`, `pot-pressure` |
| `Np-50bb` | 50 each | `mixed` (primary), `pot-pressure`, `tight-aggressive` |
| `Np-unequal` | 3: 150, 40, 100 · 4: 65, 150, 100, 30 · 5: 100, 50, 200, 30, 125 | the same |

`mixed` is as in the earlier studies. Mixture fields play natively, so they sit only at six-player tables.

## Decision rules, fixed now

Each primary contrast is `mix` minus the fixed model, with a Bonferroni 95% interval: over the five band tables, or over the nine short tables.
- **Mixed better:** lower bound above 0.
- **Fixed better:** upper bound below 0.
- **Otherwise no difference shown.**

Under the same sign rule, #447's `100bb` primary reads "fixed better".

**Six-handed band.** The band starts at {100} and grows outward one tested depth at a time:
- 80, then 65, while each reads "fixed better";
- 125, then 150, likewise.

Each edge of the band is the geometric midpoint between its outermost included depth and the next tested depth. If only 100 is included, the band is [89.4, 111.8] BB.

**Router rule.** A six-handed hand uses `six` only if every dealt seat's starting stack lies inside the band; every other hand uses `mix`.

**Near-100 check.** If the band contains every `near-100` stack and `near-100` reads "mixed better", the router uses `mix` at unequal tables. The band then applies only when all dealt stacks are within 10% of each other.

**Short-handed, per N:**
- If `Np-100bb` reads "fixed better", N-handed hands use `pN` inside the six-handed band and `mix` elsewhere. Otherwise every N-handed hand uses `mix`.
- If `Np-50bb` or `Np-unequal` reads "fixed better", it is reported as an adverse finding for that size, and that size's off-band route goes to a follow-up.

Other fields are reported with Bonferroni 95% intervals over their table's other fields.

**Descriptive:**
- each arm's share of decisions without a positive-mass row, by street;
- absolute results per arm;
- realized results beside adjusted ones.

Heads-up is out of scope; a separate study covers it.

## Qualification (the run stops on any failure)

1. **Inputs:** every model's binary and mass receipt match their pins.
2. **Native tests:** the paired-arena host tests pass on bb128.
3. **Smoke:** the 100M smoke models of the earlier studies run every table at 64 blocks per field, on separate roots:
   - arena;
   - trace scan;
   - independent replay;
   - all-in equity;
   - report.

## Rules

- **Host:** bb128. Stops: CPU 90 °C, VRM (Thermistor 15) 100 °C, below 20 GB free on the HDD and below 10 GB free on the NVMe.
- **Disk:** work under `/mnt/data2tb/openpoker-routing-20261027/`. Models are decompressed copies whose pins are checked.
- **Expected cost:** about 30 minutes of arena and about 3 hours of all-in equity.
- **Failures:**
  - A research failure is reported as is, with no retry or retuning.
  - A qualification failure stops the run.
  - Plumbing problems go in the PR.
