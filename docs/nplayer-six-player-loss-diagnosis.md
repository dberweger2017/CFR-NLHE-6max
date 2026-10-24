# Six-player loss diagnosis against tight and aggressive opponents (protocol)

This protocol is committed before any analysis code runs on the saved hands. It is a diagnosis, not a strength study: no training, no new gates, no default or release change, and every earlier verdict (#413, #415, #417, #419, #423) stays as published.

## Why

The six-player 250M/10B control is very profitable against weak fields, but not against the two tough scripted fields:

| Field | #417 bank | #419 bank | #423 bank |
|---|---|---|---|
| Tight-aggressive | −16.39 | +6.11 | +30.30 |
| Pot-pressure | +1.25 | −33.88 | −26.33 |

BB/100, the same model each time; only the deals differ. The four-player model is clearly profitable against both fields (+25.5, +30.9), and the five-player model only against tight-aggressive.

The October 24 audits showed that the arena versions are not the cause. A 3×3 replay of every TAG bank through every arena version matched every action, state and reward, so the spread comes from the deals. Nobody has yet measured where the chips are lost. This diagnosis does that, and tests one cheap cause directly.

## Inputs

All inputs are saved hands from verified runs. Each file's SHA256 must match its run's recorded trace hash, and each published mean must be reproduced exactly from the rows before anything new is computed.

| Input | Run | Focal model | Trace arm |
|---|---|---|---|
| 6p bank 417 | #417 10B initial | six-player 10B, SHA256 `086938a8…c46178` | `b` |
| 6p bank 419 | #419 initial | the same 10B (control) | `a` |
| 6p bank 423 | #423 initial | the same 10B (control) | `a` |
| 4p | #413 initial | four-player 10B, SHA256 `f1e801a5…bdc68` | `b` |
| 5p | #415 initial | five-player 10B | `b` |

All eight fields are scanned for every input. Tight-aggressive and pot-pressure are the focus; the other six are context.

The statistical unit is the deal block: the mean of all seatings of one deal. Intervals are Student-t on block means, as in the original runs.

## Part A: accounting on the saved hands

1. **All-in adjustment (luck).** When the last action of a hand leaves two or more players in and fewer than five board cards, no decision remains and only the runout decides the pots.
   - For these hands, the adjusted result is each player's expected result over every possible runout of the unseen cards, enumerated exactly. The unseen cards exclude all hole cards and the visible board.
   - The calculation uses the recorded pots, eligibility and refunds and the engine's split rule, including odd chips.
   - **Check:** on the actual runout it must reproduce every recorded showdown result exactly, for every showdown hand.
   - **Reported:** realized and adjusted means per input and field, the luck component (realized minus adjusted), and Cochran's Q across the three six-player banks for both.
2. **Where the chips go.** Each input and field's result is split into additive parts that sum exactly to the published mean, both realized and adjusted, by:
   - **position:** BTN, SB, BB, then UTG to CO;
   - **preflop line:**
     - folded unopened;
     - folded to a raise;
     - folded after investing;
     - limped or checked pot;
     - single-raised pot as raiser or as caller;
     - 3-bet-or-more pot as last aggressor or as caller;
   - **how the hand ended:** folded on each street, won uncontested on each street, showdown after an all-in before the river, river showdown; for showdowns, won or lost;
   - **untrained exposure:** whether the focal player made a decision with no trained row in that hand, and on which street it first happened. A missing row and a zero-mass row both play the uniform fallback.
3. **Untrained spots.**
   - The share of focal decisions, by street, that are missing or zero-mass.
   - The action mix there: fold, check, call, minimum raise, other raise, all-in.
   - The chips the focal player put in at those decisions.
   - Hands with and without untrained exposure, as associations only.
4. **Playing style.** For the focal player and for one opponent seat:
   - **preflop:** VPIP, PFR, 3-bet rate when facing one raise, fold rate to a 3-bet;
   - **postflop:** fold rate to a bet by street, raise share of postflop decisions, all-in share;
   - **showdown:** WTSD and W$SD.
5. **Table size.** Every table above, for 4p, 5p and 6p (the three six-player banks pooled and separately), against the same fields.
6. **The TAG spread.** Per category, how much of the difference between the #417 and #423 banks each part accounts for, realized and adjusted.

The partitions are associations: a category with a negative contribution is not proof that a different action would have earned more.

## Part B: one counterfactual, the fallback

The arena gains an opt-in, focal-only option, `focal_untrained_fallback`, applied per arm:
- **uniform:** the default, unchanged behavior and bytes;
- **check-fold:** at a focal decision whose row is missing or zero-mass, the policy draws its random number exactly as before. If the uniform draw differs from the passive action, the action is replaced by check when check is legal, and by fold otherwise.

Keeping the draw keeps every later random number aligned, so the two arms play the same deals with the same random streams until the first replaced action.

**Run:** the six-player 10B in both arms, uniform and check-fold, on all three six-player banks and all eight fields.
- The original roots, schedules and opponents are used, so these are the same 4,096 deals per field and bank.
- **Check:** the uniform arm must reproduce the historical control's actors, actions, states and rewards hand for hand. If it doesn't, the run stops; that is a finding, not something to retry.
- **Reported:** per field and bank, plus the three banks pooled:
  - the paired change (check-fold minus uniform), realized and all-in adjusted, with Student-t intervals;
  - how many decisions were replaced and how many hands changed.

This is a diagnosis, not a candidate. No gate, default or model change follows from it. A clearly negative or positive result tells us how much the uniform fallback costs against each field; it doesn't say check-fold is the right fix.

## Cost and rules

- **Host:** bb128, CPU only, about 1–1.5 hours of compute in total:
  - Part A: one streaming scan of about 16 GB of saved hands, plus exact runout enumeration in Rust;
  - Part B: one 10B model load of about 2 minutes, then 24 paired cases of about 3 seconds each.
- **Disk:** working files go on the HDD under `/mnt/data2tb/nplayer-six-player-loss-diagnosis-20261025/`, since the NVMe is nearly full. Part B's regenerated traces take about 18 GB. Inputs are only read.
- **Stops:** CPU 90 °C or VRM (Thermistor 15) 100 °C; the run doesn't overlap another heavy job.
- **Failures:**
  - A failed reproduction check, a non-matching hash or a showdown the evaluator can't reproduce is a **finding**: it is recorded and the affected part stops, with no retry or tuning.
  - Plumbing (disk, host, lock) is reported in the PR, which then waits for the owner.
- **Evidence:** compact results and the scripts go in Git. Raw outputs stay on bb128; archiving is the vacuum cleaner's job.
