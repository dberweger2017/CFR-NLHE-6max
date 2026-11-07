# Covering short multiway tables: protocol

Committed before training. Follows [#461's capacity study](openpoker-wide-capacity.md).

## Question

Can `widemix`, the model the Open Poker client uses whenever a seat holds under 10 BB at 3–6 players, get trained rows for the postflop decisions it now lacks at short six-player tables, and does it play better there for it?

## Why

At #458's short six-player tables, the live `widemix` has no positive-mass row for 39–54% of its flop decisions and 61–90% of its river decisions ([#461 results](reports/openpoker-wide-capacity/results.md)). A 400M-entry table barely changed that (1–5 points at four and six players), so table size isn't the lever. Two others are left, and either could be the binding one:

- **Key fragmentation (lever K).** Live-order keys hold the sorted stack-to-pot bucket of every live seat. The wide grid draws each seat's depth independently, so at six players the same strategic spot splits across many stack multisets, and the table freezes at about a quarter of training. Fewer distinct keys would let the table keep learning.
- **Deal distribution (lever S).** Under the wide grid, a six-player deal has every seat under 10 BB with probability (7/20)^6 ≈ 0.18%. States like a six-way limped flop with every stack-to-pot ratio under 1 almost never occur in training, whatever the key. In training only about 10% of river decisions lack a row, against 85–90% at `6p-5bb` in play.

## Candidates

- **K: effective-stack keys** (`--key-schema live-order-effective`). Live-order keys, except that the sorted list of every live stack's stack-to-pot bucket is replaced by three fields: the hero's own bucket, the bucket of the effective stack (the hero's stack or the deepest live opponent's, whichever is smaller), and the number of live opponents with less than the hero. All stacks are taken at the street's start and bucketed against the pot then, with the live-order edges. At six live seats this cuts the stack part from 924 sorted combinations to at most 168, and unlike the sorted list it says which stack is the hero's. Everything else in the key is unchanged.
- **S: short-heavy deals** (`--stack-law short-wide-mixture-v1`). Each deal is drawn from one of two components with probability 1/2 each: every seat from the wide grid's depths under 10 BB (1, 2, 3, 4, 5, 6, 8 BB), or every seat from the whole wide grid as now. The support is the wide grid's, so the client's projection and routes are unchanged. All-short six-player deals go from 0.18% to about 50%.
- **KS:** both.

The code changes are limited to these: a new key schema beside the live-order variants, a new stack law beside the depth grids, the mixture identity accepting either live-order schema, and `nplayer_train` passing the schema through. The existing schemas and laws, their keys and their draws are unchanged, which qualification checks by hash.

## Stage A: coverage screen (no strength claim)

- **Models:** four six-player models at **4B nodes**, all with #458's recipe otherwise (wide-depth support, 250M-entry cap with freezing, roots per seat 8): control `ctrl` (live-order, wide grid), `eff` (K), `short` (S), `effshort` (KS). Seeds `2026110892000` followed by 1, 2, 3, 4. At 4B nodes the control's table has already frozen (the live `widemix` froze at about 2.4B).
- **Arena:** each candidate against `ctrl` at #461's seven short tables, with #461's fields (`mixed`, the four scripts and, at six players, copies of the live `widemix`). One bank of 512 blocks per field; all three arenas use the same roots, `20261108100000 + case index`, so `ctrl` plays identical deals in each.
- **Metric:** a model's untrained share is the fraction of its decisions without a positive-mass row. The screen metric is the **pooled postflop untrained share at the three six-player tables**, over all fields: flop, turn and river decisions together.
- **Rule, fixed now:** a candidate advances if its metric is at least **10 points** below `ctrl`'s and it is below `ctrl`'s postflop share at each of the three six-player tables. Of those that qualify, the one with the lowest metric advances; within 1 point, the simpler one is preferred, in the order `eff`, `short`, `effshort`. If none qualifies, the study stops there and Stage B doesn't run.
- **Also reported:** entries and freeze iteration, training-time missing shares by street, untrained shares by table and street for the 3- and 4-player tables, binary sizes.

The screen measures coverage only. Its chip results are not reported as a comparison: one bank of 512 blocks without all-in adjustment can't support one.

## Stage B: strength (only if a candidate advances)

- **Model:** `cand`, the advancing candidate's recipe at **10B nodes**, three seeds: `2026110893000` followed by the run number.
- **Comparison:** the live `widemix` (#458 run 1, binary `702e10cf…`, mass receipt `afd951ff…`), read only, both pins checked.
- **Evaluation:** exactly #461's: the same seven tables in capped form, arm 0 the live `widemix` and arm 1 `cand` through the projected view, the same fields with `mixed` primary, all-in adjusted, every block at every cyclic seating. Run 1 uses 4 banks × 4,096 blocks with roots `20261108200000 + 1000·bank + case index`; runs 2 and 3 use 1 bank each, roots offset by 100,000 per run.
- **Decision rules:** #461's, renamed. Per table in run 1, a Bonferroni 95% interval over the seven tables: **candidate better** if the lower bound is above 0, **widemix better** if the upper bound is below 0, otherwise no difference shown. A harm flag is any other field whose Bonferroni 95% interval over the table's other fields lies entirely below −10 BB/100. Runs 2 and 3 replicate a table when both their primary point estimates are above 0.
- **Route, per group** (3 players; 4–6 players, decided by the 4p and 6p tables): `cand` would replace `widemix` on the short route only if no table reads "widemix better", at least one reads "candidate better" and replicates, and no table has a harm flag. A route change is its own PR with a deploy check and needs the owner's go.
- **Descriptive:** untrained shares by table and street for both arms, absolute and realized results, entries and freeze iteration, binary sizes, and the `tight-aggressive` field at `6p-5bb`, where #458's wide models lose about 10 BB/100.

## Qualification (the run stops on any failure)

1. **Native tests:** the library tests and the paired-arena host tests pass on bb128.
2. **Unchanged code:** at 100M nodes, #458's `widemix` recipe still writes #458's qualification checkpoint `ca8f357b…`.
3. **Determinism:** two 100M `effshort` runs, at 16 and 8 threads, write byte-identical checkpoints. `effshort` exercises both new paths.
4. **Comparison pins:** the live `widemix` binary and mass receipt match.
5. **Smoke:** 100M `eff` and `short` models complete the screen's pipeline, and Stage B's on every table at 64 blocks per field, on separate roots.

## Rules

- **Host:** bb128, all 16 threads, one job at a time. The owner gave this run an exclusive lock on bb128.
- **Stops:** thermal, CPU 90 °C or VRM (Thermistor 15) 100 °C; plumbing, below 10 GB free on the NVMe, 20 GB on the HDD or 4 GB of available memory.
- **Disk:** about 105 GB is free on the NVMe at launch, too little for seven 250M-entry models. So every model's training checkpoint moves to the HDD after verification, as in #461. The screen models' averages are removed as soon as their binaries verify, since nothing reads them after that. Once Stage A's decision is written, the screen models' binaries and checkpoints are removed too. They are reproducible from their pinned seeds and this source, which qualification 3 checks for the new paths. Their pins and reports stay.
- **Expected cost:** Stage A about 3 hours: four 4B trainings of about 17 minutes, plus export, audit and conversion, plus three small arenas without all-in equity. Stage B about 11 hours, as #461. About 14–15 hours in all.
- **Failures:** a research failure is reported as is, with no retry or retuning. A qualification failure stops the run. Plumbing problems go in the PR.
