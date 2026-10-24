# Six-player loss diagnosis: pot-pressure is the gap, and all-in luck explains the TAG spread

[#426](https://github.com/dberweger2017/CFR-NLHE-6max/pull/426) follows the [protocol](../../nplayer-six-player-loss-diagnosis.md) committed before any analysis code ran. It is a diagnosis on saved and replayed hands of the six-player 250M/10B control, with the four- and five-player 10B for comparison. There was no training, gate, default or release change; every verdict of #413, #415, #417, #419 and #423 stands.

**Findings:**
1. **The tight-aggressive (TAG) spread between banks is mostly card luck after all-ins.** Scoring all-ins before the river at their exact expected value brings the three banks from −16.4 / +6.1 / +30.3 to −1.7 / +11.2 / +15.6.
2. **TAG is a modest win at six players, +8.4 BB/100 [+2.0, +14.8]** after adjustment.
3. **The six-player weakness is pot-pressure: −22.3 BB/100 [−30.8, −13.7]**, the same in all three banks. The same opponent gives +31.6 at four players and +0.9 at five.
4. **The uniform fallback is not what loses to pot-pressure.** Replaying the same deals with check-or-fold in untrained spots changes pot-pressure by −4.3 [−9.2, +0.6] and TAG by +4.7 [+1.5, +7.9]. Against every other field it is a disaster, −67 to −582 BB/100: the random fallback earns a great deal against weak opponents.
5. **What is left is learned strategy and missing responses where they matter.** Against pot-pressure at six players, untrained spots grow sharply (river decisions without a trained row: 2.3% at 4p → 18.3% at 6p). Hands that reach them, and preflop lines that invest and then fold, carry the losses. A passive default can't fix this; the bot needs trained responses in those spots.

## Checks

- **Inputs:** all 40 saved trace files match their recorded SHA256. Every published absolute mean (#417 10B, #419 and #423 controls, #413 and #415 10B) is reproduced exactly from the rows.
- **All-in tool:**
  - all 1,162,387 Part A showdowns, and every Part B showdown, reproduce the recorded rewards exactly on the actual board, so pot splits, side pots and odd chips match the engine;
  - expected values sum to zero for every hand.
- **Part B replay:**
  - the uniform arm reproduced the historical control's actors, actions, states, history, settlement and rewards in every one of 24 × 49,152 hands;
  - the check-fold arm had zero violations of the declared rule;
  - the default arena behavior and bytes are unchanged.

The report lists no failures. The intervals below are Student-t on deal blocks, as in the original runs. Pooled six-player figures are the equal-weight mean of three banks that were already inspected, so they are descriptive, not a gate.

## 1. All-in luck and the bank spread

"Adjusted" replaces the actual result of every hand whose betting ended with two or more players in and fewer than five board cards. It uses the exact expected result over every runout of the unseen cards. Other hands keep their result.

| Bank (same 6p 10B) | TAG actual | TAG adjusted | Pot-pressure actual | Pot-pressure adjusted |
|---|---|---|---|---|
| #417 | −16.4 ± 8.0 | −1.7 ± 5.8 | +1.2 ± 13.3 | −22.9 ± 7.3 |
| #419 | +6.1 ± 8.1 | +11.2 ± 5.6 | −33.9 ± 14.4 | −19.2 ± 8.1 |
| #423 | +30.3 ± 8.5 | +15.6 ± 5.6 | −26.3 ± 12.0 | −24.6 ± 7.4 |
| **Do the banks agree? (Cochran's Q)** | Q = 16.0, p = 0.0003 | Q = 5.0, p = 0.08 | Q = 3.7, p = 0.15 | Q = 0.25, p = 0.88 |

BB/100 ± one standard error.

- **The TAG gap:** of the 46.7 BB/100 gap between #417 and #423, 38.3 sits in all-in-before-river showdowns. After adjustment that part is 8.8 and the whole gap is 17.3.
- **Precision:** adjustment also cuts the standard error by about 30% with no extra hands.
- **The other fields:** none showed a significant bank disagreement either way ([luck.csv](luck.csv), `heterogeneity` in [summary.json](summary.json)).

## 2. Strength by table size, adjusted

| Field | 4p | 5p | 6p, three banks |
|---|---|---|---|
| Tight-aggressive | +31.8 ± 5.2 | +25.3 ± 5.2 | +8.4 [+2.0, +14.8] |
| **Pot-pressure** | +31.6 ± 6.0 | +0.9 ± 6.9 | **−22.3 [−30.8, −13.7]** |
| Trained/call/pressure | +133.0 ± 8.5 | +141.2 ± 21.1 | +51.6 [+29.8, +73.4] |
| Trained (own 3B) | +45.0 ± 6.2 | +68.5 ± 9.1 | +70.1 [+57.6, +82.6] |
| Random | +318.1 | +316.2 | +333.1 |
| Check-call | +214.4 | +276.2 | +272.6 |
| Call-pressure | +203.1 | +107.8 | +97.4 |
| Random-tight | +140.5 | +132.5 | +116.1 |

The fields that bet and raise into the bot (pot-pressure, TAG, and the call-pressure mixes) fall as seats are added. The weak and trained fields don't.

## 3. Where the pot-pressure chips go

Additive contributions to the adjusted mean, BB/100, with the share of hands where it helps. Six players is the mean of the three banks; the full tables are in [table-size.csv](table-size.csv) and [partitions.csv](partitions.csv).

| Part | 4p | 5p | 6p |
|---|---|---|---|
| Hands with an untrained focal decision | −4.4 (0.3%) | −13.8 (0.9%) | **−31.8 (2.2%)** |
| …first untrained decision preflop | −1.1 | −5.4 | **−16.6** (0.9%) |
| All other hands | +36.0 | +14.8 | +9.6 |
| Folded preflop after investing (opened or called, then folded to a re-raise) | −15.1 | −21.4 | −31.8 |
| All-in showdown before river, at equity | +9.3 | −3.8 | −15.5 |
| Small blind / big blind | +6.1 / +1.4 | −6.3 / −5.0 | −14.2 / −12.9 |

**Untrained decisions against pot-pressure, share of focal decisions** ([untrained.csv](untrained.csv)):

| Street | 4p | 5p | 6p |
|---|---|---|---|
| Preflop | 0.04% | 0.25% | 0.94% |
| Flop | 0.18% | 1.26% | 3.78% |
| Turn | 1.06% | 3.44% | 9.18% |
| River | 2.26% | 8.70% | 18.33% |

The share of the focal player's chips put in at those decisions rises from 3% to 15%.

**Against TAG the pattern is the same but smaller.** Hands with an untrained decision contribute −16.2 at six players, against −0.9 at four, while every other hand earns +24.5.

**Playing style** ([style.csv](style.csv)): against pot-pressure, the six-player bot folds less to 3-bets than the four-player bot (27–30% against 38%). It goes to showdown more (31–33% against 24%) and wins there less (43–45% against 51%).

## 4. Part B: is the random fallback the cost?

The same deals were replayed with the six-player 10B in both arms. At a focal decision whose row is missing or zero-mass, the check-fold arm checks if it can and otherwise folds. Its random number is still drawn, so later draws stay aligned. Results are paired check-fold minus uniform, adjusted, pooled over three banks (12,288 blocks):

| Field | Change, BB/100 [95%] | Hands with a replaced action |
|---|---|---|
| Tight-aggressive | **+4.7 [+1.5, +7.9]** | 0.6% |
| **Pot-pressure** | **−4.3 [−9.2, +0.6]** | 1.6% |
| Random-tight | −66.8 [−73.2, −60.4] | 2.8% |
| Trained | −160.0 [−171.0, −149.1] | 6.7% |
| Call-pressure | −147.0 [−170.3, −123.8] | 34.7% |
| Trained/call/pressure | −186.5 [−206.4, −166.6] | 25.5% |
| Check-call | −241.1 [−283.5, −198.8] | 45.8% |
| Random | −581.7 [−602.8, −560.5] | 14.3% |

The three banks agree in every field ([summary.json](summary.json), `fallback`).

**What this means:**
- **Against pot-pressure, the uniform fallback is not the cost.** Folding or checking instead doesn't recover the −32 associated with untrained hands; it is about neutral to slightly worse. So that association is mostly selection: the bot reaches those spots in big, already-difficult pots.
- **Against TAG, passivity helps a little, +4.7.**
- **Everywhere else, the random fallback is earning a lot.** Against calling stations, random bettors and mixed fields, betting and calling at random in unlearned spots wins pots that a passive default gives up. The weak-field profits partly rest on that.
- **Check-fold is not a candidate.** No simple passive default fixes six players. The missing responses need to be trained, and the preflop "invest then fold" lines and all-ins below equity are learned behavior.

## What to do next (for discussion, nothing started)

1. **Measurement:** report all-in-adjusted returns next to actual ones in every absolute panel. It removes most of the bank-to-bank spread and about 30% of the standard error at no extra hands.
2. **Target pot-pressure at six players** with training that reaches its spots. Self-play rarely produces repeated pot-sized raises from several players, so those histories stay unvisited or untrained, and untrained spots triple or more from four to six players. Candidates:
   - training against a mix that includes pressure opponents;
   - visitation of raise-heavy histories, the counterpart of #425's passive-line work.
3. **Check where "invest then fold" and below-equity all-ins come from** in the trained six-player rows, for example whether those preflop raise-war spots are merely zero-mass or genuinely learned.

## Cost and provenance

- **Wall time** on bb128 (16 threads, CPU only), about 80 minutes:
  - Part A scan, about 2 minutes;
  - Part A exact all-in expectations, 39 minutes;
  - Part B replay, 5.7 minutes;
  - Part B scan, 1 minute;
  - Part B expectations, 30 minutes.

  For 19 of the uniform-arm files the showdown requests were byte-identical to Part A's, so Part A's results were copied. The 5 uniform files that were recomputed matched Part A byte for byte.
- **Temperatures:** CPU peak 75 °C. VRM (Thermistor 15) ran at 89–90 °C and peaked at 96 °C while a fan was being moved, then held at 77–78 °C at the same load. The stops (90 / 100 °C) never triggered.
- **Source:**
  - Part A scan at `52aa2606` and expectations at `84746fe2`; the Part B manifest at `b33e9a1e`; the Part B scan, expectations and the report at `fde61397`;
  - the arena host is unchanged from `52aa2606` onward. Binary SHA256s are in [costs.json](costs.json).
- **Data:** 16 GB of working files are on bb128's HDD under `/mnt/data2tb/nplayer-six-player-loss-diagnosis-20261025/`; archiving is left to the vacuum cleaner.

Files: [summary.json](summary.json), [luck.csv](luck.csv), [partitions.csv](partitions.csv), [banks.csv](banks.csv), [table-size.csv](table-size.csv), [untrained.csv](untrained.csv), [style.csv](style.csv), [costs.json](costs.json).
