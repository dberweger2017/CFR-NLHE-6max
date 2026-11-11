# Deep CFR from scratch on bb128: results

[Protocol](../../neural-deep-cfr-scratch.md) · [PR477](https://github.com/dberweger2017/CFR-NLHE-6max/pull/477) · [issue 475](https://github.com/dberweger2017/CFR-NLHE-6max/issues/475)

## Answer

**Without any table, Deep CFR learned a policy that plays.** The final network (iteration 1,375, a fresh 20,000-step strategy fit) meets the warm-start pilot's "promising" rule against step 2's `net1`:
- **E1 against `net1`:** "scratch better" on two tables, 6p-short-deep (+117) and 6p-unequal (+151). No table reads "start better".
- **E2 against the warm pilot's iteration-300 network:** "scratch better" on 4p-short-deep (+57), 6p-short-deep (+87) and 6p-unequal (+114). "Warm better" on the two 5 BB tables (−7 and −6). That's a practical comparison, not a controlled one: the warm network carries `widemix`'s table regrets.
- **Against tight-aggressive players:** ahead on every table in both evaluations.

**Harm flag.** At 6 players the scratch network loses heavily to the random field, in E1 and E2 alike (decision intervals below −50 BB/100 at 6p-short-deep, 6p-unequal and 6p-100bb). Random aggression exploits it.

**6p-100bb against the trained peers** shows no difference in either evaluation.

One seed and one bank: a pilot read, not a strength claim. No route, default or live play changes.

## Final evaluation

One bank of 4,096 blocks per table and field. Arm 1 (scratch) minus arm 0, all-in adjusted BB/100. The verdict uses the Bonferroni interval.

### E1: scratch against `net1` (the pilot's roots)
| Table | Primary field | Change (95%) | Bonferroni interval | Verdict |
|---|---|---|---|---|
| 3p-5bb | mixed | +0.1 (-4.5 to +4.6) | -6.2 to +6.3 | no difference shown |
| 3p-short-deep | mixed | -5.4 (-23.9 to +13.0) | -30.8 to +19.9 | no difference shown |
| 3p-unequal | mixed | +17.3 (+2.9 to +31.7) | -2.4 to +37.0 | no difference shown |
| 4p-short-deep | mixed | +25.1 (+3.8 to +46.5) | -4.1 to +54.4 | no difference shown |
| 6p-5bb | mixed | +0.8 (-2.6 to +4.2) | -3.8 to +5.5 | no difference shown |
| 6p-short-deep | mixed | +116.5 (+77.4 to +155.7) | +62.8 to +170.3 | scratch better |
| 6p-unequal | mixed | +150.5 (+114.5 to +186.5) | +101.1 to +199.9 | scratch better |
| 6p-100bb | trained | +10.3 (-8.1 to +28.7) | -8.1 to +28.7 | no difference shown |

### E2: scratch against the warm pilot's `strategy300-s4000` (fresh roots)

Here "start better" means the warm pilot is better: that's the script's label for arm 0.

| Table | Primary field | Change (95%) | Bonferroni interval | Verdict |
|---|---|---|---|---|
| 3p-5bb | mixed | -7.4 (-11.8 to -3.0) | -13.4 to -1.3 | start better |
| 3p-short-deep | mixed | +15.2 (-0.6 to +30.9) | -6.5 to +36.8 | no difference shown |
| 3p-unequal | mixed | +14.2 (+1.9 to +26.5) | -2.7 to +31.1 | no difference shown |
| 4p-short-deep | mixed | +57.1 (+37.3 to +77.0) | +29.9 to +84.4 | scratch better |
| 6p-5bb | mixed | -5.7 (-9.2 to -2.2) | -10.5 to -0.8 | start better |
| 6p-short-deep | mixed | +86.9 (+55.7 to +118.1) | +44.1 to +129.7 | scratch better |
| 6p-unequal | mixed | +113.7 (+85.2 to +142.3) | +74.6 to +152.9 | scratch better |
| 6p-100bb | trained | -12.1 (-27.9 to +3.7) | -27.9 to +3.7 | no difference shown |


Every field, with the harm flags, is in [evaluation/](evaluation).

## Learning curve

Monitoring checkpoints: a fresh 4,000-step strategy fit at each iteration, against `net1`, 512 blocks per table on the primary field and one second field. Bold: the 95% range excludes zero. These are diagnostics, chosen before launch, and no checkpoint was selected from them.

| Table | it25 | it50 | it100 | it200 | it300 | it400 | it800 | it1200 |
|---|---|---|---|---|---|---|---|---|
| 3p-5bb | -9 | **-18** | -7 | -5 | +0 | -3 | +1 | +6 |
| 3p-short-deep | +20 | +66 | -31 | **-114** | +10 | +5 | -2 | -17 |
| 3p-unequal | **+49** | -27 | -8 | **-51** | +10 | +7 | -8 | -1 |
| 4p-short-deep | **+184** | +80 | +15 | +3 | **+99** | +44 | +36 | +50 |
| 6p-5bb | **-11** | -2 | -3 | +4 | -0 | -0 | -7 | +4 |
| 6p-short-deep | +82 | +98 | +77 | **+145** | **+137** | **+204** | +71 | **+138** |
| 6p-unequal | **+169** | **+157** | **+112** | +28 | **+127** | **+183** | **+165** | **+108** |
| 6p-100bb | **-61** | -49 | +11 | -9 | +13 | -26 | -4 | -1 |

| Second field | it25 | it50 | it100 | it200 | it300 | it400 | it800 | it1200 |
|---|---|---|---|---|---|---|---|---|
| 3p-5bb (tight-aggressive) | **+9** | **+8** | **+17** | **+14** | **+13** | **+14** | +5 | +5 |
| 3p-short-deep (tight-aggressive) | -21 | -6 | +11 | -10 | +0 | -1 | +8 | +18 |
| 3p-unequal (tight-aggressive) | +4 | +11 | **+21** | +9 | +5 | -4 | **+15** | +13 |
| 4p-short-deep (tight-aggressive) | **-43** | -17 | +18 | -15 | -13 | +9 | **+41** | +10 |
| 6p-5bb (tight-aggressive) | -6 | -4 | **+10** | +3 | **+11** | **+8** | **+15** | **+10** |
| 6p-short-deep (tight-aggressive) | **-47** | -17 | -10 | +2 | -2 | -18 | +14 | -3 |
| 6p-unequal (tight-aggressive) | **-39** | **-33** | -10 | -25 | +6 | -19 | +14 | +6 |
| 6p-100bb (mixed) | **+242** | **+367** | **+238** | **+196** | **+354** | **+319** | **+408** | **+352** |

- **Early (iterations 25–50):** loose and aggressive, close to the uniform start. It wins big against the mixed field and loses to tight-aggressive players.
- **From iteration 300 on:** no primary reads clearly worse than `net1` at any checkpoint, and the tight-aggressive readings turn positive.
- **Iterations 800–1,200:** the gains flatten. The advantage loss kept rising (1,502 at iteration 25, 1,729 at 400, 1,846 at 800, 2,159 at 1,200).

## Training

- **Window:** 24 hours, 12:57 UTC November 9 to 12:58 UTC November 10, giving **1,375 iterations**. Iteration 1,375 started 45 s before the window closed, so it's final under the rule.
- **Time spent:** 13.2 h traversal, 3.7 h reservoir adds, 6.2 h advantage fits.
  - Traversal grew from 32.5 s to 40.2 s per iteration (first 100 against last 100).
  - Add stayed at about 10 s and the fit at 16.2 s.
  - [iterations.csv](iterations.csv) has every iteration.
- **Exploration bound:** 3 per street, 8 per path.
  - Mean nodes per traversal went from 187 at iteration 1 to 277 at iteration 1,375.
  - The largest traversal in the run was 10,915 nodes, against the pilot's 50M-node failure.
- **Machine** ([resources-per-minute.csv](resources-per-minute.csv)):
  - peaks: CPU 88 °C, VRM 61 °C, GPU 68 °C, 53 GB RAM;
  - no guard stop.
- **Snapshots:** every 100 iterations, each checked ([snapshots.jsonl](snapshots.jsonl)).
- **Qualification:** native and Python tests, the bound tests, GPU, pins and thread determinism passed ([qualification/](qualification)). The run's code is commit `4a4bf2bf`.

**Plumbing during the run:**
- **Network outage:** bb128 was unreachable from about 11:00 to 12:05 UTC on November 10 (home Wi-Fi). The run is local and wasn't affected.
- **Relaunch:** a first launch was stopped to address the review on this PR, before any training iteration counted (`stopped-attempt-1` on bb128).

**Found later (PR484):** the stage guard woke every 5 s, so every stage was rounded up to a multiple of 5 s, about 7.5 s of each 65 s iteration. Feature encoding rebuilt all 612 feature names at every decision. Neither changes any result, and both are fixed for later runs.

## Evidence

- **On bb128:** `/home/dberweger/neural-deep-cfr-scratch-20261109`, with every advantage and strategy network, the iteration summaries, the monitoring and evaluation traces and the receipts.
- **Manifests:**
  - The full SHA-256 manifest (11,009 files; source checkouts and TensorBoard logs excluded) is `manifest.sha256` there. [manifest-summary.sha256](manifest-summary.sha256) records its hash and a digest per directory.
  - [networks.sha256](networks.sha256) lists every network.
- **Reservoirs:** the final reservoir snapshot (iteration 1,375) is `/mnt/data2tb/neural-deep-cfr-scratch-20261109/snapshot.tar.zst` (sha256 `1813bbfe…`).
- **Long-term:** bb128's storage process packages the tree into `gdrive:PR-477-neural-deep-cfr-scratch/` and indexes it in `RESULTS_INDEX.md`.

## What came next

The M4 studies found the 0.5M advantage network too small (#478–#480), which motivated a 2M-network run on the same recipe.
- **Run 2 (#481)** failed on two thermal stops.
- **Run 3 (#487)** re-ran it on PR484's byte-identical speed code. Its results are reported there.
