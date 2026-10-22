# River search: retain the opponent's minimum raise after a root bet (protocol)

This protocol is committed before any calibration or measurement. It is a fixed development comparison, not a strength study: there is no arena, training, off-tree re-solving, default or release change.

## Hypothesis

[#384](reports/river-harm-diagnosis/results.md) found that, in its selected installed exact profiles, the strongest remaining omitted reply was the opponent's minimum raise as the first response to the hero's root bet. Its interventions removed responses from audits of fixed strategies. This study adds the response to the search tree and solves again.

## Arms

The two arms differ by exactly one response:

| Arm | Search menu |
|---|---|
| Baseline | `pot-jam-cap3-root-check-min-v1` (#377, #380, #382) |
| New | `pot-jam-cap3-root-min-responses-v1`: the baseline plus the opponent's production minimum raise at the decision right after a root bet |

Everything else is shared:
- **model:** the frozen v0.6 10B, SHA256 `d835f61f…5189`;
- **solver:** DCFR (1.5, 0, 2), the raise cap and the blueprint fallback after any still-omitted action;
- **beliefs:** the projected law by default, plus a secondary exact-belief arm (`exact-folded-prefix-v1`).

## Inputs

[#380](reports/river-continuation-qualification/results.md)'s frozen 200-root development panel, SHA256 `f5b6b270…b919`, read and verified through #382's `inputs()` checks. No new deals are drawn.

## Phases

Each phase runs every root under both arms, with the arm order alternating by root and five workers per phase:

1. **projected:** the deployment target, min(1% of the pot, 0.1 BB) within 2,048 sweeps. The baseline arm must reproduce #380's original deployment output exactly, or the run stops.
2. **exact:** the same target with exact beliefs.
3. **strict:** matched accuracy, min(0.2% of the pot, 0.02 BB) within 8,192 sweeps. Pairs that either arm fails to solve are inconclusive and excluded from the strict comparison.
4. **diagnosis:** both arms on every root where the projected phase finds either arm worse than the blueprint. It runs #384's fixed-profile response diagnosis on the live retained root, with zero solver advances.

Every solve is followed by the retained continuation check and #382's full-menu audit under the exact modeled law. All four phases then run again as an independent reproduction, and strategic fields must match.

## Decision rule

Every quantity is judged on projected-belief deployment profiles, under the exact full-menu law. The new arm is **retained** only if all three hold:
1. it has fewer decisions worse than the blueprint in worst case than the baseline;
2. its median paired worst-case change against the baseline is positive;
3. it still passes the latency gate (median at most 0.5 s, p95 at most 2 s).

Otherwise the verdict is **revise or reject**.

The report also shows, without changing the decision:
- **Exact beliefs:** exact against projected beliefs, on both menus.
- **Strict accuracy:** the matched-accuracy comparison.
- **Where the exposure goes:** whether the top remaining exposure moves to another response.

## Cost and the automatic start

A calibration on roots 0, 53, 79 and 113 quotes the main run first. The owner approved an automatic start **only if the quote's upper bound is at most 2.5 hours**; otherwise the run stops and waits.
- **Stops:** CPU 90 °C, VRM (Thermistor 15) 100 °C.
- **No retries:** a failure is reported, never retried or extended automatically.
