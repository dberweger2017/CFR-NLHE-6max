# Live-order n-player keys and their six-player pilot (protocol)

This protocol is committed before the pilot runs. The pilot is a feasibility step: it measures how the key table fills, and checks that the pipeline handles a second key schema. It makes no strength claim. A strength screen, if the pilot clears its gate, gets its own protocol before training.

## Why

[#430](reports/nplayer-traverser-admission/results.md) found the six-player table is too small for the key space self-play explores. Rows average 2–4 regret updates over a 10B run, and 66.7% of training decisions find no row.

The history key records every public action with its amounts, so histories that differ only in who folded earlier, or in an earlier street's exact sequence, never share a row. [Saved traces](reports/nplayer-key-collapse/) of #430's control show how far coarser keys would merge played decisions. Only seat-order summaries merge meaningfully: 2.3–2.9× postflop, 28× preflop.

## The key

`nplayer_train --key-schema live-order` selects `nplayer-live-order-summary-equity-k50-v1`. A decision's key is:
- **The table:** the number of players, live players and all-in players, the hero's order among live players counted from the button, and the street.
- **Earlier streets:**
  - the pot at the street's start, in big-blind buckets with edges 2, 4, 8, 16, 32, 64, 128;
  - each live player's stack-to-pot ratio at the street's start, in buckets with edges ½, 1, 2, 4, 8, 16, as a sorted list;
  - each street's raise count, capped at 3;
  - the previous street's last raiser, by order among live players.
- **The current street:** its capped raise count, last raiser by order among live players, number of actions, and the price to call (call over pot after calling, edges 0.1, 0.2, 0.3, 0.4).
- **Unchanged from the history key:** the current street's card class and the menu's action labels. Amounts don't enter the key; the menu is still built from the exact observation.

Every feature comes from the acting seat's public observation. A row's owner is the hero's order among live players, so merged decisions share owner, street and action labels.

Released models and the default keep the history schema. Policy tables carry their schema and key every lookup with it. Tools that compare rows under one key refuse mixed or non-history schemas.

## Pilot

- **Host:** bb128, 16 threads, the #417 recipe: seed 2026102361001, fast mode, 8 roots per seat, 250M entries with whole-iteration freeze, average scope 3.
- **Training:** 2B nodes with `--key-schema live-order`. No history run is needed: #417's 10B telemetry records the same recipe and seed every 100 iterations.

**Qualification (the pilot stops on any failure):**
1. **Legacy parity:** without the option, the branch trainer and a `main` build produce byte-identical 100M-node checkpoints.
2. **Determinism:** with the option, 16 and 8 threads produce byte-identical 100M-node checkpoints, which differ from the legacy one.
3. **Pipeline:** export, average-mass audit, binary conversion and verification of the 2B checkpoint pass.
4. **Mixed-schema arena:** a paired smoke of 64 blocks × 12 seatings against pot-pressure, #417's 10B against the live-order 2B as focal, completes and its traces pass the replay scan. The live-order arm records positive-mass lookups.

**Gate for a 10B strength screen, fixed now:** #417's table held 112.0M entries at 200M nodes and 209.8M at 400M, and froze with 250.0M entries at iteration 23,678, before 600M nodes. Proceed if the live-order table holds at most **125M entries at 600M nodes**, half of #417's. Otherwise stop: the key doesn't merge enough in training, and the result is recorded.

**Also reported (descriptive):** entries, missing-decision share and discarded-update share against nodes for both keys, the freeze iteration if reached, and regret updates per row by street at 2B.

## Rules

- **Stops:** CPU 90 °C, VRM (Thermistor 15) 100 °C, and below 10 GB free on the NVMe.
- **Disk:** working files under `/home/dberweger/nplayer-live-order-pilot-20261026/`.
- **Expected cost:** under an hour.
- **Failures:** a qualification failure stops the pilot. Plumbing problems go in the PR.
