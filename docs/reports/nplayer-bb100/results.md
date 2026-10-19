# Three-player 100 BB cost admission: 10B remains unadmitted

[PR 350](https://github.com/dberweger2017/CFR-NLHE-6max/pull/350), [proposal 349](https://github.com/dberweger2017/CFR-NLHE-6max/issues/349). October 19, 2026. Cost-only evidence; no poker outcomes or strength claim. 200 BB is outside this PR.

## Result

The fixed 100M/200M/500M pilot completes cleanly in **16.16 minutes** (2026-10-19T10:15:31.013559+00:00 to 2026-10-19T10:31:40.556602+00:00). All seven native stages return 0; all three node gates, checkpoint SHA readbacks, full-average/game-header checks and both thread/resume identity checks pass. No capacity freeze, discarded updates or guard stop.

| Cumulative nodes | Entries | Added-node training s | Training Mnodes/s | Save s | Stage wall s | Sampled peak GiB | Checkpoint GB |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100,016,079 | 37,061,110 | 18.99 | 5.27 | 110.68 | 138.84 | 4.48 | 1.237 |
| 200,012,007 | 62,276,130 | 21.21 | 4.71 | 186.99 | 260.18 | 6.70 | 2.124 |
| 500,008,669 | 112,968,920 | 57.57 | 5.21 | 389.17 | 535.93 | 10.53 | 3.990 |

The three cost segments use **97.77s active training**, **686.84s saving**, **934.95s child wall** and **0.649 child CPU-hours**; qualification and controller checks account for the rest of the pilot wall. All seven stages together use 0.656 child CPU-hours. Checkpoint files total 7.350 GB, excluding four small fixture files.

Training seconds equal the native elapsed timer minus save time and exclude startup/loading and checkpoint hashing. The remaining stage wall (9.17/51.98/89.19s) includes those operations plus monitoring overhead; it is not a pure load-time measurement. Native objects remain in RAM, while checkpoint output is on the owned HDD cache. The compatible compressor and 16-worker formatter remain unchanged; these results do not isolate HDD performance from serialization/compression.

## Capacity decision

**Do not launch the unchanged three-seed 10B campaign from this admission.** The table already has 112,968,920 entries at 500M, versus a 150M-entry pilot/old-overnight ceiling. Marginal growth slows from 0.371 to 0.252 to 0.169 keys/node across the measured intervals, but has not demonstrated saturation. The last-interval linear scenario reaches 150M near **0.719B nodes**, before the proposed 1B anchor. It gives **535.4M entries at 3B** and **1.718B at 10B**.

Combining that local entry scenario with the measured marginal peak RSS (81.1 bytes/entry) gives **131.8 GiB process RSS at 10B**, before host/other-job headroom or simultaneous evaluation policies. This exceeds bb128's 125.7 GiB OS-visible RAM. These are early one-seed **scenarios, not bounds, saturation forecasts or proof that 10B cannot fit**. A fresh larger-capacity qualification and evaluation-memory proof are needed to admit a different resource plan. No cap or guard was raised, and no table freezing was used.

At the last measured rate, 30B total nodes across three seeds would take 1.60 hours of traversal alone. That is not a full-run ETA: larger tables may slow traversal, and checkpoints, exports, every-row audits, monitoring, final play, reproduction and independent replay are additional costs. The earlier 4–8h planning estimate remains unadmitted.

Recommended next decision: keep 100 BB and the full-average recipe, qualify growth through fixed 1B/2B endpoints under a newly declared entry/storage budget, and measure mature export/policy-load memory before committing to 10B. This is a proposed follow-up, not an automatic extra experiment. Native 100 BB monitoring/arena support still needs the qualification described in the protocol. No default, release, algorithm, pruning or table-freezing adoption.

## Resources and correctness

Maximum CPU **64.0°C**, Thermistor 15 **74.5°C**; available RAM minimum **91.10 GiB**. Absolute host swap stayed **22.85 GiB with zero growth**; it is telemetry only and cannot be assigned to this process. CPU 90°C/Thermistor 15 100°C, 32 GiB family RSS, 48 GiB address space, 8 GiB available RAM, 12 GB output growth and 50 GB physical-disk floors stayed in force. Both mutexes were acquired. No OS/fan/driver/cache/other-job changes or cleanup.

The 200K one-vs-sixteen-thread SHA is `0bd5db8a933d7a605d08f227dd9fe23e17b994e8c4c4bfea7d55d2329815f79f`; the 400K fresh/resumed SHA is `7453700ad65226a6d8c7d66945ab9f7dedab21a6d6c5e14c118291ac65abbf88`. Both comparisons match complete compressed bytes. Final checkpoint hashes and exact counts are in [costs.csv](costs.csv); commands and per-stage completion/resource receipts are in [receipt.json](receipt.json). One cost-only seed 2026101935001 and fixed order; sampled RSS can miss short peaks. No full campaign, evaluation or final-strength seed ran.

## Provenance and reproduction

Frozen pilot controller source `0b8d16c9e0a7299b164a543200f535a48d216a05`; later commits contain protocol/readout/evidence only. Native CLI SHA `fc37a562f8d3753d920b07b5d35c6deabe75fc846196b176f749187a3b3ac790`, reused unchanged from the fast qualification. Source hashes, K50 identities, invocation and launch settings are in the receipt. PR 336/pruning, PR 344/compact keys and PR 347/store changes are excluded.

Raw root: `bb128:/mnt/data2tb/research-cloud/PR-350-nplayer-bb100/pilot-20261019`. Control/source/config originals: `/home/dberweger/nplayer-bb100-pilot-20261019/{source,source-v2,config.json,config-v2.json}`; the initial source/config were deployed but never launched and remain retained. Supervisor 466186 exited normally. Original remote results.json SHA256 `76b4e7ca27bc5587a0282c45e4c35ff68016da536cac57f6fbca7131f0cbdf3e`. Compact receipt retrieved into ignored `/Users/dberweger/Local/cfr-nplayer-bb100-20261019/results/bb100-pilot-20261019T103150Z`; no checkpoint or trace was copied to the Mac.

```sh
ssh bb128 python3 - /mnt/data2tb/research-cloud/PR-350-nplayer-bb100/pilot-20261019 < docs/reports/nplayer-bb100/collect.py > FRESH_IGNORED_RECEIPT.json
python3.11 docs/reports/nplayer-bb100/summarize.py FRESH_IGNORED_RECEIPT.json
```

The readout reproduces the checked-in [analysis.json](analysis.json); four deliberately corrupted return-code, thread-identity, RSS and node-count receipts are rejected. 14 focused guard/pilot/overnight tests pass. Full CI remains separate. All raw checkpoints, measurements, partials and sources remain protected on bb128; Research-Cloud upload acceptance is pending. No Drive recovery link exists yet, and no archival or deletion is claimed. Read-only shared trainer/venv (PR 340) and K50 tables (PR 292) remain protected dependencies.
