# The network fallback on the short route: deploy check

This adopts [step 3's result](../neural-policy-fallback/results.md) in the Open Poker client. Both route groups passed there under the prespecified rules. The owner gave the go for this adoption PR on November 8. Live play stays a separate decision.

## What changes

[`routes.json`](routes.json) adds `"fallback": "network:net1"` to the `widemix` short route at 3, 4, 5 and 6 players. No other route changes: heads-up, the 100 BB band and the mixed-stack routes are as before.

| | |
|---|---|
| Network | `net1`, step 2's seed-1 network, the one whose run decided step 3: file `5e276263…`, source weights `d222a165…`, 8.8 MB |
| Policy | `widemix` (#458 run 1), binary `702e10cf…` |
| Mass receipt | `afd951ff…`, keyset `1e7b1314…` |

At a `widemix` decision whose row has no positive mass (zero mass or missing), the service plays `net1`'s strategy on the real table's observation. Every other decision plays the row, as before. 5-player hands follow the 4–6 group, as the protocol set.

The service and the paired arena call the same function, `PolicyNetwork::play`. The journal records each such decision's row status and the network's distribution.

## Checks

All ran on bb128 with [checks.sh](checks.sh), on commit `b7416d87`, and passed:

| Check | Result |
|---|---|
| Build, native `policy_network` and paired-arena host tests, client and fallback Python tests | passed |
| Arena reproduction: #469's smoke manifest (38 cases) rerun with the refactored host | all 76 traces byte-identical to #469's ([hashes](arena-compare.txt)) |
| Service–arena parity: every focal decision in the 38 network-arm smoke traces replayed through `nplayer_serve` | 16,536 decisions, same row status everywhere; the 1,808 network decisions give bit-identical label probabilities; 0 mismatches ([receipt](fallback-parity.json)) |
| Deploy check: the full route set, all 10 policies plus `net1`, 200 sandbox tables, stacks from 1 BB | passed ([report](deploy-check.json)) |

From the deploy check:
- **Loading:** all policies and the network load in 174 s, with a service peak of 45.3 GB.
- **Latency:** p50 0.09 ms, p99 2.0 ms, max 2.2 ms per decision, far below the 5 s limit.
- **Fallbacks:** the only ones are the 106 permitted "possible all-in blind" cases.
- **Network play:** 42 of the 1,133 `widemix` decisions, all at missing rows, and none at a positive-mass row. That share is small because the sandbox draws stacks log-uniformly from 1–250 BB and seats scripted opponents. In step 3's arena the network played 3–16% of focal decisions.

## A client fix found on the way

The first full deploy check ([attempt 2](attempts/attempt2-deploy-check.json)) failed on 1 of 4,014 decisions. The tracker reported a stack of −40 where the engine had 0:
- the hand had 3 players, two of them below one big blind, and the deep seat posted the 20-chip big blind;
- the client caps each stack at the largest other seat's, here 12 chips, which is below that blind.

This was a latent capping bug, not a network fault. The network's different actions only steered the random sandbox into this spot.

**The fix:** a seat is never capped below the blind it posted. Any cap at or above the largest other stack plays the same hand. A regression test plays that table, fails without the fix and passes with it.

[Attempt 1](attempts/attempt1-status.txt) stopped earlier, at the arena reproduction: the check script didn't create the trace folders. That was plumbing, fixed in the script.

## Limitations

- **No live hands.** The network has been tested against scripts and copies of the live client in step 3, and in the sandbox here.
- **Step 3's open question:** `check-call` at the deep six-player tables was +11.6 and +10.3 BB/100 with `net1` in run 1, but the seed-2 and seed-3 networks leaned negative in runs 2 and 3 with wide intervals. This PR adopts `net1` only.
- **No 5-player table** was tested in step 3.
- **The network file and models stay on bb128.** The repository pins their hashes.
