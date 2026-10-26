# Finer live-order keys, and 10B against 50B head-to-head (protocol)

This protocol is committed before any training or evaluation. It covers two one-lineage experiments at six players and 100 BB. Nothing is promoted, and no default or release changes.

## Why

**Finer keys.** The [live-order key](nplayer-live-order-keys.md) merges spots so coarsely that its table holds 38.6M of 250M possible rows at 10B. Two pieces of detail it drops may matter strategically:
- **the hero's own seat** (button, blinds and so on) once others have folded;
- **the exact order of the current street's actions**, such as check-raise against bet-call.

The table has room to keep either.

**Head-to-head.** #439 found 30B and 50B score worse than 10B against the panel, but the panel doesn't measure exploitability. Playing the checkpoints against each other shows whether 50B is weaker, or only extracts less from weak fixed opponents.

## Key variants

Both variants have their own schema names and use the same seed, recipe and 10B nodes as #431's live-order model (seed 2026102361001):

| Option | Schema | Change from live-order |
|---|---|---|
| `--key-schema live-order-seat` | `nplayer-live-order-seat-summary-equity-k50-v1` | adds the hero's button-relative seat |
| `--key-schema live-order-street` | `nplayer-live-order-street-exact-equity-k50-v1` | replaces the current street's last raiser and action count with its exact actions: each actor's order among live players, action kind and raise-to amount |

Earlier streets, buckets, card classes and action labels are unchanged. Plain live-order keys are unchanged; the existing golden key test pins them.

## Qualification (the run stops on any failure)

1. **Plain live-order unchanged:** at seed 2026102361001, 16 threads and 100M nodes, the branch reproduces the pilot's live-order checkpoint `482a0f8f…`.
2. **Variants:** each gives byte-identical 100M-node checkpoints at 16 and 8 threads, different from plain live-order.
3. **Pipeline:** export, average-mass audit, binary conversion and verification pass for both 10B variants.
4. **Inputs:** #431's 10B (`75245fbb…`, binary `f894a59f…`) and #439's 50B (binary `1b5f8cf1…`) match their pins.

## Evaluation

**Variant screen:**
- **Design:** each variant's 10B against #431's 10B (control) as focal.
- **Fields:** the screens' eight fields; the trained fields use #417's 3B.
- **Deals:** one new set of four banks shared by both variants, roots `20261027100000 + 100·bank + field index`, 4,096 blocks × 12 seatings.
- **Scoring:** all-in adjusted.

**Decision rule, fixed now:**
- **Primary, per variant:** the trained-field change against #431's 10B. **Improved** if its lower bound clears 0 using a **Bonferroni 95% interval over the two variants** (97.5% each); otherwise **not shown**.
- **Harm flags, per variant:** Bonferroni 95% over the other seven fields. Pot-pressure is a named secondary, reported with its individual 95% interval.
- **Mechanism, descriptive:** table entries, missing share and regret updates per row, and learned-row coverage in play.
- **If both variants improve,** the one with the larger trained-field change is preferred for follow-up. Any adoption needs more seeds and its own protocol.

**Head-to-head, descriptive:**
- **Focals:** #431's 10B and #439's 50B (same lineage) on the same deals.
- **Fields:**
  - `vs-10b`: against five copies of the 10B;
  - `vs-50b`: against five copies of the 50B.
- **Deals:** roots `20261027200000 + 100·bank + field index`, 4 banks × 4,096 blocks × 12 seatings.
- **Reported:** the 50B-minus-10B change per field, all-in adjusted, with individual 95% intervals.
- **No gate:** it informs the node-budget question from #439 and adopts nothing.

## Rules

- **Host:** bb128. Stops: CPU 90 °C, VRM (Thermistor 15) 100 °C, below 20 GB free on the HDD, and below 10 GB free on the NVMe.
- **Disk:** work under `/mnt/data2tb/nplayer-live-order-variants-20261027/`. Inputs from #431 and #439 are read only.
- **If a variant's table reaches the 250M cap,** it freezes as configured and that is recorded.
- **Expected cost:** about 5 hours.
- **Failures:**
  - A research failure is reported as is, with no retry or retuning.
  - A qualification failure stops the run.
  - Plumbing problems go in the PR.
