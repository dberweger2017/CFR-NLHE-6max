# Retain the opponent's minimum raise after a root bet: retained

[#386](https://github.com/dberweger2017/CFR-NLHE-6max/pull/386) tests [#384](../river-harm-diagnosis/results.md)'s hypothesis by solving again, not by restricting audits. The baseline `pot-jam-cap3-root-check-min-v1` is compared with `pot-jam-cap3-root-min-responses-v1`, which adds only the opponent's production minimum raise at the decision right after a root bet. Everything else is unchanged: the frozen v0.6 10B, DCFR (1.5, 0, 2), the raise cap, the beliefs and the blueprint fallback.

The [frozen protocol](../../river-root-min-responses.md) was committed before calibration. The panel is [#380](../river-continuation-qualification/results.md)'s 200-root development panel (SHA256 `f5b6b270…b919`). Every solve is followed by the retained continuation check and [#382](../river-exact-beliefs/results.md)'s full-menu audit under the exact modeled law.

**The frozen rule's verdict is retain.** On projected-belief deployment profiles:
- **Fewer harms:** decisions worse than the blueprint in worst case fall from **23 to 10**.
- **Positive median change:** the median paired worst-case change is **+0.128 BB**.
- **Latency:** the gates still pass, at median **0.474 s** and p95 **1.751 s**. The median is close to its 0.5 s limit.

This is development-panel engineering evidence, not stronger whole-hand play. There was no arena, training, default or release change.

## Results

All 200 roots under both arms, initial pass; the reproduction pass matched every strategic field. "Worse than blueprint" and worst-case values are measured in the full-menu game under the exact modeled law.

| Phase / arm | Installed (quality met) | Worse than blueprint | Median worst-case change vs blueprint | Median opponent gain | Latency median / p95 / max |
|---|---|---|---|---|---|
| Projected, baseline | 198 | 23 | +0.853 BB | 0.355 BB | 0.368 / 1.381 / 2.797 s |
| **Projected, new** | 198 | **10** | **+0.937 BB** | **0.152 BB** | **0.474 / 1.751 / 3.312 s** |
| Exact, baseline | 198 | 23 | +0.835 BB | 0.321 BB | 3.52 / 13.53 / 27.26 s |
| Exact, new | 198 | 10 | +0.959 BB | 0.130 BB | 4.60 / 17.73 / 32.85 s |
| Strict, baseline | 199 | 28 | +0.818 BB | 0.353 BB | 2.32 / 5.49 / 10.87 s |
| Strict, new | 199 | 13 | +0.969 BB | 0.136 BB | 2.77 / 7.63 / 15.29 s |

**Paired worst-case change, new against baseline:**

| Phase | Better / worse / equal | Median | Mean | Largest harms (case: BB) |
|---|---|---|---|---|
| Projected (the decision) | 164 / 34 / 2 | +0.128 BB | +0.325 BB | 21: −7.70, 91: −2.81, 117: −1.84 |
| Exact | 168 / 30 / 2 | +0.136 BB | +0.332 BB | 21: −7.84, 91: −3.55, 86: −1.67 |
| Strict, 199 matched pairs (1 inconclusive) | 165 / 34 / 0 | +0.127 BB | +0.342 BB | 21: −6.77, 91: −4.21, 86: −2.02 |

**The three views agree.** Matched accuracy (strict) gives the same answer as the deployment target, so the gain isn't a solver-difficulty artifact.

**The baseline matches earlier PRs exactly:**
- **#380's original deployment output:** the baseline arm reproduced it on all 200 roots.
- **#382:** its 23 harms are #382's count for this menu.
- **#382's exact-belief comparison:** its exact against projected result (105 better / 93 worse; worst harms cases 75 and 53 at −1.335 and −1.120 BB) is identical to #382's.

## Exact beliefs, secondary

| Menu | Exact against projected: better / worse | Median change | Harm count change |
|---|---|---|---|
| Baseline | 105 / 93 | +0.002 BB | none (23 → 23) |
| New | 129 / 69 | +0.007 BB | none (10 → 10) |

With the new menu, exact beliefs help somewhat more often. But they change neither harm count and cost about 10× the latency (median 4.6 s, p95 17.7 s). **This is not yet a case for exact-belief runtime work.**

## Does the exposure move? Yes, one level deeper and smaller

The response diagnosis ran on the 27 roots that either arm left worse than the blueprint, using #384's fixed-profile, leave-one-out exact-law restrictions with zero solver advances. Effects overlap and are not additive.

- **Baseline:** the top remaining exposure on **20 of 27** roots is the opponent's **minimum raise right after our root bet**, 28.85 BB of summed leave-one-out improvement. That confirms #384's selected-case finding across the panel.
- **New menu:** that exposure is gone. What remains is mostly **minimum re-raises at the opponent's second decision**:
  - after our bet, their raise and our re-raise: 14.92 BB;
  - after our check, their bet and our raise: 4.03 BB;
  - all-in and pot re-raises: about 4.5 BB.

**Case 21 shows the mechanism.** Its pot is 9 BB:
- **What the new menu put in the tree:** the opponent's minimum raise to 18 BB after our 9 BB bet. The solved strategy answers it with a pot re-raise to 63 BB.
- **The new off-tree entry:** the opponent's minimum re-raise to 96 BB is omitted, so play falls back to the blueprint. Removing that one response would improve our worst case by 7.72 BB.
- **The baseline:** the minimum raise itself was off-tree and played by the blueprint, at a cost of 0.02 BB.

**Each added branch can open a new off-tree entry one level deeper.** Adding branches keeps shrinking the total exposure but can't remove it. That points toward re-solving after off-tree actions as the general fix, rather than a third menu branch. A third branch would also be limited by latency, with the median already at 0.474 against 0.5 s.

## Cost and verification

- **Calibration:** roots 0, 53, 79 and 113, all four phases, took 11.3 minutes. The baseline reproduced #380's output on those roots.
- **Quote:** 66–107 minutes, within the owner-approved 2.5 h, so the main run started automatically.
- **Main run:** about 80 minutes in total: projected 8.6, exact 15.5, strict 11.4 and diagnosis 4.4 minutes per pass, plus loading (five workers per phase).
- **Reproduction:** every phase, including all 54 diagnosis records, matched strategic fields ([verified](verified.json)).
- **Resources:** peak CPU 71 °C, VRM (Thermistor 15) 82 °C; the stops were 90 / 100 °C. No failure and no retry.
- **Source and binary:** source `daf39a62`, binary SHA256 `65159351…6791`; frozen model SHA256 `d835f61f…5189`.

Files: [per-case table](cases.csv), [summary with all arms, comparisons and diagnosis](summary.json), [quote](quote.json), [stage times](stages.jsonl), [resources](resources.json). Raw records and logs are archived; see [RESULTS_INDEX](../../../RESULTS_INDEX.md).

## Next

1. **Keep `pot-jam-cap3-root-min-responses-v1` as the search menu candidate.** It roughly halves the remaining harms (23 → 10) at a modest latency cost.
2. **Don't add a third menu branch by default.** The exposure moves deeper with each branch, and the median latency is near its gate. Off-tree re-solving, with consistent belief updates and continuation, is the general candidate for the remaining 10 harms.
3. **The whole-hand cost and variance pilot** is now better justified with this menu. It needs its own protocol and approval, and #317's HU200 readout should come first.
