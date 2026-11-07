# Target-policy exploration qualification: bb128 main results

One run of the [protocol](../../nplayer-passive-learning-qualification.md) under its bb128 host amendment, November 6, 2026, from source `d355213e`. Files: [results](bb128-main-results.json), [costs](bb128-main-cost.json), [bb128 quote](bb128-quote.json), [review record](review-bb128.json), [owner record](owner-bb128.json).

## Outcome

**No signal.** Neither arm has a single watch key that meets the repeated-learning proxy, so the continuation rule (at least five keys, five more than control) is not met. As declared, this rejects only this small candidate and workload, not exploration in general.

| Arm, 512 sweeps | Rows | Watch keys encountered | Retained | With regret updates | With positive average | Most roots updating one key's regret | Proxy keys | Fully zero rows |
|---|---|---|---|---|---|---|---|---|
| control (epsilon 0) | 2,001,455 | 87 of 2,727 | 76 | 18 | 59 | 2 | 0 | 0.075% |
| exploration (epsilon 0.02) | 2,006,515 | 118 of 2,727 | 97 | 22 | 80 | 1 | 0 | 0.070% |

At 128 sweeps the arms are identical on these counts (21 encountered, 21 retained, 3 with regret updates, 18 with positive average).

## What it means

- Exploration does reach more of the watched passive histories (118 against 87 encountered), as intended.
- But reaching a key is not learning there: no watched key gets regret updates from more than two independent roots in either arm, far from the proxy's four roots with an effective sample size of four. That matches the ex-ante reach scenarios: with zero-probability opponent actions on the path, exploration-only hits are rare at this scale.
- Fully zero rows don't grow under exploration (0.070% against 0.075%).

## Checks and costs

- **Reproduction:** the separate-process repeat matches the initial run on every row value, visit, table identity, watch and cell ledger, and row digest.
- **Host:** bb128, two threads, sharing the CPU with #458's training. Guard: CPU package 90 °C and VRM 100 °C stops, memory-pressure stop; none fired.
- **Costs:** 1 min 57 s for the two stages (initial 56.9 s, repeat 51.4 s), 2 min 0 s wrapper wall, 2.37 GB peak family RSS. The bb128 quote was 4 min 36 s central and 13 min 9 s reserve, inside the accepted 15 minutes.
- **Review:** the native code and math are byte-identical to the independently reviewed source. The host-only port (`d355213e`) was reviewed by the porting session itself, not independently, and the record says so.
