# Finer live-order keys don't help; 50B beats 10B head-to-head

[#442](https://github.com/dberweger2017/CFR-NLHE-6max/pull/442) follows the [protocol](../../nplayer-live-order-variants.md) committed before training. Both experiments are one-lineage screens at six players and 100 BB: nothing is promoted, and no default changes.

**Verdicts:**
- **Seat variant, not shown.** Trained field −1.8 BB/100, decision interval [−12.7, +9.0] (Bonferroni over the two variants). Harm flag: random.
- **Street variant, not shown.** Trained field −54.3, decision interval [−67.7, −40.8]. Harm flags: random, tight-aggressive and pot-pressure. Its table filled the 250M cap at iteration 117,863.
- **Head-to-head, descriptive:** #439's 50B beats #431's 10B on both fields:
  - **+19.1 [+13.6, +24.7]** against five copies of the 10B;
  - **+14.0 [+9.1, +18.9]** against five copies of the 50B.

**Decision:** plain live-order keys stay the recommended six-player key. Neither variant is followed up as specified.

## Head-to-head: 10B against 50B

The same deals, all-in adjusted, 16,384 blocks (196,608 hands) per field, individual 95% Student-t intervals ([h2h/h2h.json](h2h/h2h.json)):

| Field | 10B's result | 50B's result | 50B − 10B |
|---|---|---|---|
| Against five copies of the 10B | −3.2 | +15.9 | **+19.1 [+13.6, +24.7]** |
| Against five copies of the 50B | −13.2 | +0.9 | **+14.0 [+9.1, +18.9]** |

Each focal's result against copies of itself is close to zero, as it should be by symmetry; the small departures are card variance. The 50B beats tables of either checkpoint.

**Reading, together with #439:**
- On this lineage, the 50B is the stronger player against these two opponents: the 10B, and itself. Against #439's panel it scored lower, mainly against weak and loose fields.
- That fits the balance-versus-exploitation hypothesis from #439. It doesn't establish progress toward equilibrium or a lower exploitability.
- Which checkpoint plays better against a given pool depends on that pool.

## Key variants against #431's 10B

Paired change, all-in adjusted, 16,384 blocks per field ([variants.csv](variants.csv), each variant's `summary.json`):
- **The trained field** shows its decision interval, Bonferroni 95% over the two variants.
- **Every other field** shows its Bonferroni 95% interval over seven tests, the interval behind the harm flags.
- **Pot-pressure** also shows its individual 95% interval, because the protocol names it as a secondary.

| Field | Seat variant | Street variant |
|---|---|---|
| **Trained (#417 3B ×5)** | **−1.8** [−12.7, +9.0] | **−54.3** [−67.7, −40.8] |
| Pot-pressure | −6.2 [−14.8, +2.4]; individual [−12.5, +0.1] | **−32.3** [−43.1, −21.5], harm; individual [−40.1, −24.4] |
| Tight-aggressive | −1.5 [−7.4, +4.3] | **−12.6** [−19.8, −5.5], harm |
| Random | **−47.0** [−67.3, −26.6], harm | **−112.7** [−138.9, −86.6], harm |
| Random-tight | −2.2 [−11.4, +7.0] | −1.9 [−12.7, +9.0] |
| Call-pressure | −18.4 [−47.2, +10.3] | **+56.6** [+26.5, +86.8] |
| Trained/call/pressure | −9.8 [−34.2, +14.7] | **+38.5** [+11.6, +65.3] |
| Check-call | −8.0 [−59.3, +43.2] | +26.1 [−26.6, +78.7] |

**Absolute adjusted results, control → variant:**

| Field | Seat variant | Street variant |
|---|---|---|
| Trained | +189.0 → +187.2 | +189.0 → +134.8 |
| Pot-pressure | +32.2 → +26.0 | +32.2 → −0.1 |
| Call-pressure | +112.5 → +94.1 | +112.5 → +169.1 |

The control is the same #431 10B on the same deals in both columns.

## Mechanism (descriptive)

**Tables at 10B** (each variant's `training.json`):

| Key | Entries | Frozen at iteration | Learned rows | Training decisions without a row | Discarded traverser updates | Regret updates per row (preflop / flop / turn / river) |
|---|---|---|---|---|---|---|
| Live-order (#431) | 38.6M | — | 18.7M | 0.66% | 0% | 66 / 32 / 49 / 51 |
| Seat | 79.0M | — | 32.6M | 1.35% | 0% | 32 / 16 / 23 / 26 |
| Street | 250.0M (cap) | 117,863 of 462,275 | 57.4M | 9.84% | 6.1% | 1.1 / 5.4 / 10.8 / 14.6 |

**What each variant did:**
- **Seat:** the key doubles the table and halves the updates per row. Coverage in play stays near complete: against the trained field, 99.5% of decisions and 99.5% of river decisions land on learned rows.
- **Street:** keeping the current street's exact actions brings back the capacity limit live-order keys had removed.
  - The table freezes a quarter of the way through training, so a share of updates is discarded and rows get far fewer updates. Preflop rows average about one.
  - Against the trained field, decisions on learned rows fall from 99.7% to 94.5%.
- **Only the street variant improves the calling fields** (call-pressure, trained/call/pressure). The current street's exact sequence may matter in multiway called-down pots, where the summary merges different call orders. That is a hypothesis: this screen doesn't separate it from the capacity change, and check-call's river stays at 0% learned in every arm.

## Checks

- **Plain live-order unchanged:** at 100M nodes, the branch reproduces the pilot's checkpoint exactly (`482a0f8f…`). The golden key test pins plain live-order keys.
- **Variants deterministic:** each gives identical checkpoints at 16 and 8 threads (seat `7a9fec36…`, street `80e6abf3…`).
- **Inputs:** #431's 10B checkpoint and binary and #439's 50B binary match their pins.
- **Pipeline:** both variants pass export, mass audit, conversion and verification (binaries `76f1f014…`, `b24d7c37…`).
- **Opponents unaffected:** #417's 3B found positive-mass rows for 89.3–89.7% of its decisions in every arm.
- **Trace integrity:** all 144 traces pass the replay scan with zero fallback violations, 49,152 hands each.

## What it means

- **Plain live-order keys sit at a good point.**
  - Adding the hero's seat adds nothing measurable against these fields.
  - Keeping the current street's exact actions costs capacity and loses strength against betting fields, while gaining against calling fields.
- **If calling fields matter later,** a street variant that fits under the cap could be worth one screen. For example, exact actions on the river only, or a larger table. That is not authorized here.
- **For tomorrow's external tests:**
  - **#431's 10B** scores best against the panel's weak and loose fields;
  - **#439's 50B** beats it head-to-head, and holds even or better against pot-pressure and tight-aggressive;
  - playing both is the cheapest way to learn which the external pool rewards.
- **Limits:** one lineage for each variant and for the head-to-head. The variants' sizes, and the 50B's head-to-head edge, could vary by seed.

## Cost

- **Run:** 22:20–03:26 UTC (5h06m) on bb128, alone. Peaks 76 °C CPU and VRM.
- **Training:** each variant took about 2,227 s.
- **Evaluation:**
  - head-to-head: about 6 minutes of arena and 2 minutes of all-in scoring;
  - each variant: about 18–23 minutes of arena and 64–67 minutes of all-in scoring.
- **Disk:** 41 GB on the HDD ([costs.json](costs.json)). Nothing was deleted.
