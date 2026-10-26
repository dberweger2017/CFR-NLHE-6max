# Six-player live-order keys: confirmed on two new seeds

[#434](https://github.com/dberweger2017/CFR-NLHE-6max/pull/434) follows the [protocol](../../nplayer-live-order-seeds.md) committed before training. Two new seeds each trained a history-key control and a live-order model from scratch to 10B nodes with #417's recipe. Each pair played on new shared banks against #417's 3B, foreign to both arms, and the scripted fields. Nothing is promoted, and no default or release changes.

**The frozen rule's verdict: confirmed.** The trained-field change clears zero on both new seeds:
- **2026102661001: +110.4 BB/100 [+97.8, +123.0]**, no harm flags;
- **2026102661002: +113.2 [+100.7, +125.7]**, check-call harm flag.

Across all three seeds, #431's included, the trained-field change is **+109.7 [+99.9, +119.5]**, and pot-pressure **+53.5 [+42.9, +64.1]**.

## Results by seed

Paired change (live-order minus that seed's control), all-in adjusted, 16,384 blocks (196,608 hands) per field. The primary has its 95% Student-t interval; other fields have Bonferroni 95% intervals over seven tests ([seeds.csv](seeds.csv), per-seed `summary.json`).

| Field | #431 (2026102361001)* | 2026102661001 | 2026102661002 | Across 3 seeds, t 95% |
|---|---|---|---|---|
| **Trained (primary)** | +105.4 [+92.9, +117.9] | **+110.4 [+97.8, +123.0]** | **+113.2 [+100.7, +125.7]** | **+109.7 [+99.9, +119.5]** |
| **Pot-pressure (secondary)** | +58.4 | **+51.9** [+40.6, +63.2] | **+50.3** [+39.3, +61.2] | **+53.5 [+42.9, +64.1]** |
| Tight-aggressive | +15.0 | +24.2 [+16.5, +31.9] | +23.4 [+15.6, +31.3] | +20.9 [+8.1, +33.6] |
| Trained/call/pressure | +81.5 | +111.9 [+84.7, +139.1] | +108.4 [+81.2, +135.6] | +100.6 [+59.3, +141.9] |
| Random | +187.7 | +170.2 | +184.8 | +180.9 [+157.5, +204.2] |
| Call-pressure | +5.6 | +16.4 [−13.6, +46.3] | +10.8 [−18.9, +40.4] | +10.9 [−2.5, +24.3] |
| Random-tight | −0.2 | +3.9 [−8.1, +15.9] | +1.3 [−10.7, +13.3] | +1.7 [−3.5, +6.8] |
| **Check-call** | **−110.7, harm** | −39.2 [−91.3, +12.9] | **−106.6 [−158.8, −54.3], harm** | −85.5 [−185.2, +14.3] |

\* #431 used other deals, and its trained field was the control's own 3B. The across-seed interval mixes designs and has 2 degrees of freedom, so it describes the result; it isn't a gate.

**Absolute adjusted results, control → live-order:**

| Field | 2026102661001 | 2026102661002 |
|---|---|---|
| Trained | +74.1 → +184.5 | +68.7 → +181.8 |
| Pot-pressure | **−18.3 → +33.7** | **−22.0 → +28.2** |
| Tight-aggressive | +11.6 → +35.8 | +11.7 → +35.2 |
| Check-call | +252.8 → +213.7 | +277.0 → +170.4 |

## Mechanism

Per seed ([s2026102661001/training.json](s2026102661001/training.json), [s2026102661002/training.json](s2026102661002/training.json)):

| | Control, s1 / s2 | Live-order, s1 / s2 |
|---|---|---|
| Table entries at 10B | 250.0M / 250.0M (frozen at iterations 23,870 / 23,864) | 38.6M / 38.9M, never frozen |
| Training decisions without a row | 66.9% / 67.0% | 0.66% / 0.66% |
| Traverser updates discarded | 68.3% / 68.4% | 0% / 0% |
| Learned rows | 41.2M / 41.1M | 18.7M / 18.8M |
| Training time to 10B | 1,924 s / 1,928 s | 1,321 s / 1,320 s |

The mechanism is nearly identical across all three seeds, and so is coverage in play. Against the trained field, river decisions on learned rows go from about 69% to 99.6–99.8%, and against pot-pressure from about 79% to 99.7%. Check-call's river stays at 0% in every arm ([rows.csv](s2026102661001/rows.csv), [rows.csv](s2026102661002/rows.csv)).

## Checks

- **Qualification at seed 2026102661001:**
  - legacy output is byte-identical to `main` (`ca425dee…`);
  - live-order output is identical at 16 and 8 threads (`06fa282e…`).
- **Pipeline:** all four models passed export, mass audit, conversion and binary verification.
- **Opponents unaffected:** #417's 3B (`6cd50bf1…`) found positive-mass rows for 89.5–89.7% of its decisions in every arm of both seeds. The gains aren't opponent lookup artifacts, and this opponent is now foreign to both arms.
- **Trace integrity:** all 128 traces pass the replay scan with matching hashes and zero fallback violations, 49,152 hands each.
- **Batches agree:** every resolved field has the same sign in all four banks on both seeds.

## What it means

- **The gain is a property of the key, not of one lineage.**
  - Three independent seeds give +105, +110 and +113 against the trained field. Their spread, about 8 BB/100, is smaller than each one's interval.
  - The two new seeds face a foreign 3B, so #431's own-ancestor caveat doesn't explain it.
- **The six-player pot-pressure gap is closed on every seed.** Every control loses to pot-pressure (−18 to −31) and every live-order model beats it (+27 to +34). Tight-aggressive also improves consistently, by +15 to +24.
- **Check-call is the one consistent cost, and its size depends on the seed:** −39, −107 and −111. Every arm still wins clearly there (+170 or more).
  - [The preflop diagnosis](check-call-preflop-ranges.md) locates #431's loss in raising more weak hands and folding more good hands into five-way limped pots.
  - Self-play never visits those spots under any key, so they need a visitation fix.
- **Limits:**
  - These are development screens against fixed scripted and earlier-model fields, not release acceptance or exploitability.
  - The across-seed interval mixes two designs.

**Next, per the protocol:** live-order keys become the recommended six-player recipe for the 200 BB work. That gets its own protocol.

## Cost

- **Run:** 09:19–15:28 UTC (6h09m) on bb128, alone. Peaks 74 °C CPU and 76 °C VRM.
- **Training:** four 10B trainings, 1,320–1,928 s each.
- **Evaluation:** per seed, about 23 minutes of arena and 67–70 minutes of all-in scoring.
- **Disk:** 59 GB on the HDD after compression ([costs.json](costs.json)). Nothing was deleted.
