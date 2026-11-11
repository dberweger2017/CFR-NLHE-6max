# Deep CFR run 3 (2M advantage network): results

[Protocol](../../neural-deep-cfr-run3.md) · [PR487](https://github.com/dberweger2017/CFR-NLHE-6max/pull/487) · [issue 482](https://github.com/dberweger2017/CFR-NLHE-6max/issues/482) · run 1: [PR477](https://github.com/dberweger2017/CFR-NLHE-6max/pull/477)

## Answer

**No. The 2M advantage network fits its targets better but plays worse than run 1's 0.5M network. Keep 0.5M.**

- **E4, equal iterations and equal fits** (both at 1,375, 20,000-step strategy fits): run 1 is better on four tables:
  - 6p-short-deep (−77), 6p-unequal (−73), 6p-100bb (−52) and 3p-unequal (−22).
  - Run 3 is better on two short ones, 3p-5bb (+13) and 6p-5bb (+8).
- **E3, finals** (run 3 at 1,500 against run 1 at 1,375): run 1 is better on 6p-unequal (−63) and 6p-100bb (−72). Run 3 is better on 3p-5bb (+10).
- **The fixed reading rule** (issue 482: "E3 shows run 2 worse on any table: keep 0.5M") applies.
- **Against tight-aggressive and pot-pressure players** run 3 loses in almost every table of E3 and E4. At 100 BB against the trained peers it's worse than `net1` (E1 −76, "start better"). Run 1 showed no difference there.
- **The plateau question:** run 3's checkpoints peak around 1,200 and fall by 1,500, worst at 6p-100bb (−35 → −95). That's a decline, not a plateau.

**Fit against play.** The 2M network's advantage loss is lower than run 1's at every checkpoint, as the M4 studies (#478–#480) predicted. But the policy is worse against disciplined opponents. The likeliest reading is that the bigger network fits the sampling noise in the regret targets (#478's warning; #490 puts late-run noise at 9–25% of the variance), and that noise shows up as exploitable play. It's one seed per run, but E3 and E4 agree, with 4,096 blocks per table.

**What follows:** the 0.5M advantage network stays the default for the 3-seed follow-up. A bigger network would need less noisy targets (more samples per regret, or averaging) before it can pay off.

## Final evaluations

One bank of 4,096 blocks per table and field, all-in adjusted BB/100. In E3 and E4, arm 1 is run 3 and arm 0 is run 1. The verdict uses the Bonferroni interval. The script labels run 3 "run 2" (written for run 2), and the table shows it as run 3.


### E3: run 3's final (1,500) against run 1's final (1,375)

| Table | Primary field | Change (95%) | Bonferroni interval | Verdict |
|---|---|---|---|---|
| 3p-5bb | mixed | +9.8 (+4.6 to +14.9) | +2.7 to +16.8 | **run 3 better** |
| 3p-short-deep | mixed | -1.5 (-21.7 to +18.8) | -29.3 to +26.3 | no difference shown |
| 3p-unequal | mixed | -16.6 (-30.3 to -2.9) | -35.5 to +2.2 | no difference shown |
| 4p-short-deep | mixed | -2.6 (-25.6 to +20.4) | -34.2 to +29.0 | no difference shown |
| 6p-5bb | mixed | +5.0 (+1.4 to +8.7) | -0.0 to +10.1 | no difference shown |
| 6p-short-deep | mixed | -23.3 (-56.6 to +10.0) | -69.0 to +22.4 | no difference shown |
| 6p-unequal | mixed | -63.1 (-92.7 to -33.5) | -103.7 to -22.5 | **run 1 better** |
| 6p-100bb | trained | -72.2 (-93.1 to -51.4) | -93.1 to -51.4 | **run 1 better** |

Harm flags (decision interval wholly below −10): 3p-unequal check-call (-16), 6p-5bb live-copies (-13), 6p-short-deep pot-pressure (-33), 6p-short-deep check-call (-98), 6p-short-deep live-copies (-43), 6p-unequal pot-pressure (-32), 6p-unequal check-call (-102), 6p-unequal live-copies (-36), 6p-100bb pot-pressure (-39), 6p-100bb check-call (-280), 6p-100bb mixed (-36).

### E4: run 3 at 1,375 against run 1 at 1,375, both 20,000-step fits

| Table | Primary field | Change (95%) | Bonferroni interval | Verdict |
|---|---|---|---|---|
| 3p-5bb | mixed | +12.8 (+7.8 to +17.7) | +6.0 to +19.6 | **run 3 better** |
| 3p-short-deep | mixed | +1.7 (-18.7 to +22.1) | -26.2 to +29.7 | no difference shown |
| 3p-unequal | mixed | -22.2 (-36.0 to -8.4) | -41.2 to -3.2 | **run 1 better** |
| 4p-short-deep | mixed | +27.9 (+4.0 to +51.8) | -4.9 to +60.8 | no difference shown |
| 6p-5bb | mixed | +8.0 (+4.3 to +11.7) | +3.0 to +13.1 | **run 3 better** |
| 6p-short-deep | mixed | -77.4 (-111.5 to -43.3) | -124.3 to -30.6 | **run 1 better** |
| 6p-unequal | mixed | -73.1 (-102.0 to -44.1) | -112.9 to -33.3 | **run 1 better** |
| 6p-100bb | trained | -52.4 (-72.5 to -32.3) | -72.5 to -32.3 | **run 1 better** |

Harm flags (decision interval wholly below −10): 3p-unequal check-call (-10), 4p-short-deep pot-pressure (-10), 6p-5bb live-copies (-15), 6p-short-deep pot-pressure (-21), 6p-short-deep tight-aggressive (-15), 6p-short-deep check-call (-50), 6p-short-deep live-copies (-59), 6p-unequal pot-pressure (-17), 6p-unequal check-call (-63), 6p-unequal live-copies (-40), 6p-100bb pot-pressure (-45), 6p-100bb tight-aggressive (-12), 6p-100bb check-call (-140), 6p-100bb mixed (-90).

### E1: run 3 against `net1`

| Table | Primary field | Change (95%) | Bonferroni interval | Verdict |
|---|---|---|---|---|
| 3p-5bb | mixed | +10.9 (+5.7 to +16.2) | +3.8 to +18.1 | **run 3 better** |
| 3p-short-deep | mixed | +16.8 (-6.1 to +39.7) | -14.6 to +48.2 | no difference shown |
| 3p-unequal | mixed | -6.3 (-21.9 to +9.3) | -27.7 to +15.1 | no difference shown |
| 4p-short-deep | mixed | +56.7 (+30.5 to +82.9) | +20.7 to +92.6 | **run 3 better** |
| 6p-5bb | mixed | +4.9 (+0.8 to +8.9) | -0.7 to +10.4 | no difference shown |
| 6p-short-deep | mixed | +93.8 (+51.9 to +135.6) | +36.3 to +151.3 | **run 3 better** |
| 6p-unequal | mixed | +99.7 (+63.1 to +136.4) | +49.4 to +150.0 | **run 3 better** |
| 6p-100bb | trained | -76.2 (-98.3 to -54.1) | -98.3 to -54.1 | **baseline better** |

Harm flags (decision interval wholly below −10): 4p-short-deep pot-pressure (-23), 4p-short-deep tight-aggressive (-14), 6p-5bb live-copies (-13), 6p-short-deep pot-pressure (-15), 6p-short-deep live-copies (-21), 6p-unequal pot-pressure (-37), 6p-unequal live-copies (-48), 6p-100bb pot-pressure (-35), 6p-100bb random (-50).

### E2: run 3 against the warm pilot's `strategy300-s4000`

| Table | Primary field | Change (95%) | Bonferroni interval | Verdict |
|---|---|---|---|---|
| 3p-5bb | mixed | +4.0 (-1.1 to +9.1) | -3.0 to +11.0 | no difference shown |
| 3p-short-deep | mixed | +17.7 (-2.7 to +38.1) | -10.3 to +45.7 | no difference shown |
| 3p-unequal | mixed | -10.1 (-24.2 to +3.9) | -29.4 to +9.1 | no difference shown |
| 4p-short-deep | mixed | +60.1 (+34.5 to +85.6) | +25.0 to +95.1 | **run 3 better** |
| 6p-5bb | mixed | -1.2 (-5.0 to +2.6) | -6.4 to +4.0 | no difference shown |
| 6p-short-deep | mixed | +78.9 (+45.0 to +112.8) | +32.4 to +125.5 | **run 3 better** |
| 6p-unequal | mixed | +48.3 (+16.8 to +79.8) | +5.0 to +91.6 | **run 3 better** |
| 6p-100bb | trained | -99.5 (-121.4 to -77.6) | -121.4 to -77.6 | **baseline better** |

Harm flags (decision interval wholly below −10): 6p-5bb live-copies (-12), 6p-short-deep pot-pressure (-30), 6p-short-deep live-copies (-49), 6p-unequal pot-pressure (-34), 6p-unequal live-copies (-17), 6p-100bb pot-pressure (-50).


Every field is in [evaluation/](evaluation).

## Checkpoints

Run 1 and run 3 against `net1` at the same iterations: fresh 4,000-step fits, 512 blocks per table, on the same deals. Bold: the 95% range excludes zero. Run 3's checkpoints 25–177 equal run 2's byte for byte. Earlier checkpoints are in [monitor/](monitor).

| Table | Run 1 it400 | Run 3 it400 | Run 1 it800 | Run 3 it800 | Run 1 it1200 | Run 3 it1200 | Run 3 it1375 | Run 3 it1500 |
|---|---|---|---|---|---|---|---|---|
| 3p-5bb | -3 | +2 | +1 | **+24** | +6 | **+24** | +13 | **+22** |
| 3p-short-deep | +5 | +20 | -2 | +53 | -17 | +3 | -40 | -51 |
| 3p-unequal | +7 | +10 | -8 | +23 | -1 | +30 | +18 | -28 |
| 4p-short-deep | +44 | -1 | +36 | +12 | +50 | **+78** | +47 | -33 |
| 6p-5bb | -0 | +4 | -7 | +9 | +4 | **+17** | **+15** | +10 |
| 6p-short-deep | **+204** | +72 | +71 | +21 | **+138** | +100 | +114 | +110 |
| 6p-unequal | **+183** | +88 | **+165** | +80 | **+108** | +62 | +67 | **+98** |
| 6p-100bb | -26 | -35 | -4 | **-56** | -1 | -35 | -39 | **-95** |

| Second field | Run 1 it400 | Run 3 it400 | Run 1 it800 | Run 3 it800 | Run 1 it1200 | Run 3 it1200 | Run 3 it1375 | Run 3 it1500 |
|---|---|---|---|---|---|---|---|---|
| 3p-5bb (tight-aggressive) | **+14** | -5 | +5 | +1 | +5 | -2 | -1 | -10 |
| 3p-short-deep (tight-aggressive) | -1 | -9 | +8 | **-36** | +18 | -13 | -32 | -36 |
| 3p-unequal (tight-aggressive) | -4 | -5 | **+15** | -6 | +13 | +1 | -13 | -14 |
| 4p-short-deep (tight-aggressive) | +9 | -3 | **+41** | +15 | +10 | -13 | +32 | -29 |
| 6p-5bb (tight-aggressive) | **+8** | **+13** | **+15** | **+23** | **+10** | **+13** | **+13** | **+26** |
| 6p-short-deep (tight-aggressive) | -18 | +20 | +14 | -11 | -3 | -41 | -29 | **-39** |
| 6p-unequal (tight-aggressive) | -19 | **-35** | +14 | -13 | +6 | +2 | -25 | **-54** |
| 6p-100bb (mixed) | **+319** | +80 | **+408** | **+193** | **+352** | **+229** | **+221** | **+344** |


## Training and speed

- **Iterations:** 1,500, stopped by the owner's choice (protocol deviation) instead of 24 hours. They took 12.3 hours from 00:41 to 13:58 UTC on November 11, against run 1's 23.1 hours for 1,375.
- **Time per iteration** (last 100 iterations): 31.9 s, of which 17.7 s traversal, 4.3 s add and 9.9 s fit. Run 1 took about 65 s, so run 3 is **about 2.3× faster with a network 4.6× larger**, thanks to PR484's code.
- **Parity:** iterations 1–177 reproduced run 2's records byte for byte (177 of 177, [parity-run2.jsonl](parity-run2.jsonl)), and so did checkpoints 25, 50 and 100. PR484 changes no numbers at full scale.
- **Traversals:** mean nodes per traversal went from 187 to 240, with a largest of 11,290.
- **Machine:** CPU peak 84 °C, GPU 73 °C, 53 GB RAM. No guard stop, after the owner's new fan curve. The short-burst power limit was set to 150 W from about 08:13 UTC.
- **Deviations** ([deviations.jsonl](deviations.jsonl), protocol "Deviations"):
  - the stop at 1,500, with checkpoints at 1,375 and 1,500 and E4 at 1,375;
  - two clean controller restarts between iterations;
  - the resume fix;
  - the power limit.
- **Network outages:** bb128 was unreachable from about 03:15 to 06:20 and around 07:30–08:10 UTC (home Wi-Fi). The run wasn't affected.

## Evidence

- **On bb128:** `/home/dberweger/neural-deep-cfr-run3-20261111`.
  - The full SHA-256 manifest (8,729 files) is `manifest.sha256`. [manifest-summary.sha256](manifest-summary.sha256) records its hash and a digest per directory.
  - [networks.sha256](networks.sha256) lists the kept networks: every 10th advantage network, every checkpoint and the finals.
  - [iterations.csv](iterations.csv) has every iteration's timing and traversal statistics.
  - The final reservoir snapshot is in `/mnt/data2tb/neural-deep-cfr-run3-20261111`.
- **Run 2** (PR481, closed) is on the HDD with a symlink at its old path.
- **Long-term:** bb128's storage process packages these trees.
