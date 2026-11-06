# Stack cap in the Open Poker client: checks

The client now caps every starting stack at the largest other seat's before routing. Chips beyond that can never be won or lost, so the capped hand is the same hand. A deeper seat's bets past its cap are cut to its capped all-in (a raise past it becomes an all-in raise or a call), and its turns after that all-in are dropped, as the capped game gives an all-in seat no turn. When the hero is the deep seat, a capped all-in goes to the server as a legal raise: nobody can match past the cap, so any raise at or above it plays the same hand.

This is a client change only. No model, route or default changes.

## Sandbox tests

- All 28 Open Poker tests pass. A new sandbox test plays four tables with a 2,000 BB stack (as opponent and as hero, heads-up and three-handed) against a 100 BB band route.
  - Every decision is in capped form, and hands route into the band.
  - The engine reproduces every capped decision: no fallbacks beyond the existing "possible all-in blind".
- The existing reconstruction test (five table shapes, one with a deeper stack) also has no new fallbacks.

## Deploy check on bb128

[`deploy-check.json`](deploy-check.json), all 8 live models with the routes merged in #455, from [`checks.sh`](checks.sh):

| | |
|---|---|
| Decisions | 5,770 policy, 7 fallback |
| Fallbacks | all 7 "possible all-in blind", the one allowed reason |
| Load | 367 s, peak memory 30.1 GB |
| Decision latency | p50 0.14 ms, p99 0.19 ms, max 0.87 ms |
| Verdict | **passed** |

A first version of the cap fell back whenever a deep seat had bet past its cap: 31 such fallbacks plus 8 "raise outside the offered range" when the hero was the deep seat. The version here plays both exactly.

The bb128 load took longer than #455's 261 s because the wide-stack study (#458) was training on all 16 threads at the same time.

## Live pilot journals, replayed

[`replay.json`](replay.json), from [`scripts/openpoker_cap_replay.py`](../../../scripts/openpoker_cap_replay.py): both sessions' server messages go through the client again, with three agents at every turn.

- **Replay check:** with the session's own routes and no cap, session 2's policy decisions by route and trained flag match the journal exactly (43 trained, 5 untrained). Session 1 differs as expected: its journal holds 3 fallbacks from the two client bugs fixed after session 1, and the replay runs the fixed client.
- **Effect, today's routes:** the cap changed **1 of 66 decisions**. In hand `c69df4e8`, a 2,252.5 BB stack was capped to 409.55 BB, and the hero's decision moved from an untrained row (a uniform draw: raise to 49.6 BB) to a trained one (raise to 1 BB, the minimum). The table stayed off the band, so the route didn't change.
- **What it means:** 66 decisions is far too few to estimate the cap's effect on untrained rows or results. The cap is exact, so it can only remove off-grid stack situations; how often it matters depends on how often deep stacks sit at our tables.

## Limits

- The cap doesn't help when two or more seats sit above 250 BB, or when our own stack is under 10 BB. The second case is #458's.
