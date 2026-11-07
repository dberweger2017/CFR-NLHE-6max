# A larger wide-depth model for short multiway tables: protocol

Committed before training. Follows [#458's wide-stack study](openpoker-wide-stacks.md).

## Question

Does a 400M-entry `widemix` play better than the live 250M one at short 3–6-player tables?

## Why

#458 moved hands with a seat under 10 BB to the wide-depth models ([results](reports/openpoker-wide-stacks/results.md)). `huwide` has a trained row for essentially every heads-up decision. `widemix` does not:
- Its table hit the 250M-entry cap and froze at about 283k of 1.21M iterations, in all three runs.
- At short multiway tables it still has no trained row for many postflop decisions: 56% of river decisions at `3p-5bb`, 90% at `6p-5bb` and 64–67% at the deep-mixed six-player tables.

A larger table freezes later and keeps more postflop keys. Training at 250M peaked at 54 GB on bb128. 400M should peak at about 86 GB, inside its 125 GB with room to spare, and convert to a binary of about 23 GB.

## Models

- **`widecap`:** #458's `widemix` recipe exactly (live-order keys, `wide-depth-grid-v1`, 6 players, 10B nodes, roots per seat 8, freeze at cap), with `--max-entries 400000000` instead of 250M. **Three seeds:** `2026110791000` followed by the run number.
- **Each model** is exported, mass-audited, converted to binary and verified as in #458. After verification, the training checkpoint moves to the HDD under its pinned hash, because the NVMe can't hold three of them.
- **Comparison:** the live `widemix`, #458 run 1, binary `702e10cf…`, mass receipt `afd951ff…`. It is read only, with both pins checked.

No code changes beyond the study script, [`openpoker_wide_capacity.py`](../scripts/openpoker_wide_capacity.py), which reuses #458's tables and the phantom/depth harness.

## Qualification (the run stops on any failure)

1. **Native tests:** the library tests and the paired-arena host tests pass on bb128.
2. **Unchanged code:** at 100M nodes and the 250M cap, the wide grid still writes #458's qualification checkpoint, `ca8f357b…`.
3. **Determinism at 400M:** two 100M `widecap` runs, at 16 and 8 threads, write byte-identical checkpoints.
4. **Comparison pins:** the live `widemix` binary and mass receipt match.
5. **Smoke:** a 100M `widecap` completes the full pipeline on every table at 64 blocks per field, on separate roots: arena, trace scan, independent replay, all-in equity and report.

## Evaluation

- **Tables:** #458's seven multiway tables, all in the client's capped form:
  - 3 players: `3p-5bb` (5·5·5), `3p-short-deep` (4·100·100), `3p-unequal` (8·40·100);
  - 4 players: `4p-short-deep` (5·100·100·100);
  - 6 players: `6p-5bb` (5 each), `6p-short-deep` (3·100·100·100·100·100), `6p-unequal` (8·100·50·100·150·100).
- **Arms:** arm 0 is the live `widemix` and arm 1 is `widecap`, both through the projected view.
- **Fields:**
  - `mixed`, which is primary;
  - `pot-pressure`, `tight-aggressive`, `check-call` and `random`;
  - at six players only, `live-copies`: copies of the live `widemix`. At 3 and 4 players no model holds the player count natively.
- **Contrast:** arm 1 minus arm 0, all-in adjusted, over blocks.
- **Deals:**
  - run 1: 4 banks × 4,096 blocks per field, roots `20261107100000 + 1000·bank + case index`;
  - runs 2 and 3: 1 bank × 4,096 blocks each, with roots offset by 100,000 per run;
  - every block is played at every cyclic seating.

## Decision rules, fixed now

**Per table, run 1:** a Bonferroni 95% interval over the seven tables.
- **400M better:** lower bound above 0.
- **250M better:** upper bound below 0.
- **Otherwise no difference shown.**
- **Harm flag:** any other field whose Bonferroni 95% interval over the table's other fields lies entirely below −10 BB/100.

**Replication:** runs 2 and 3 replicate a table when their primary point estimates are both above 0.

**Route, per group:** the 3-player group, and the 4–6-player group (decided by the 4p and 6p tables). In a group, `widecap` replaces `widemix` on the short route only if:
- no table reads "250M better";
- at least one table reads "400M better" and replicates;
- no table has a harm flag;
- a deploy check with `widecap` in place passes on bb128.

Otherwise the live `widemix` stays. 5-player hands follow the 4–6-player group.

**Descriptive:**
- each arm's share of decisions without a positive-mass row, by street, which is the mechanism this study targets;
- absolute results per arm;
- realized results beside adjusted ones;
- entries and the iteration at which the table froze;
- binary sizes;
- peak memory;
- per-run results.

## Rules

- **Host:** bb128, all 16 threads, one job at a time; every stage needs all 16 threads.
- **Stops:**
  - thermal: CPU 90 °C, VRM (Thermistor 15) 100 °C;
  - plumbing: below 10 GB free on the NVMe, 20 GB free on the HDD, or 4 GB of available memory.
- **Disk:**
  - work goes under `/home/dberweger/openpoker-wide-capacity-20261107/` on the NVMe (212 GB free at launch);
  - checkpoints go under `/mnt/data2tb/openpoker-wide-capacity-20261107/` (188 GB free).
- **Expected cost:**
  - three trainings of about 45–60 minutes, plus about 30–45 minutes each for export, audit and conversion;
  - about 4 hours of arena and all-in equity for run 1, and about 1 hour for each later run;
  - about 10–12 hours in all.
- **Failures:** a research failure is reported as is, with no retry or retuning. A qualification failure stops the run. Plumbing problems go in the PR.
