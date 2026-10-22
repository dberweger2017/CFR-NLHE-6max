# PR335 strength study: terminal thermal stop

The October 18 study stopped during its first final training seed. **No
playing-strength result is available**, and neither strength gate was evaluated.
Keep PR335 unmerged pending a completed strength comparison. This run must not
be restarted automatically or interpreted as evidence that fast mode plays worse.

[PR335](https://github.com/dberweger2017/CFR-NLHE-6max/pull/335),
[study PR340](https://github.com/dberweger2017/CFR-NLHE-6max/pull/340),
[frozen protocol](../../nplayer-fast-strength-study.md),
[compact terminal receipt](terminal.json).

## What completed

Qualification passed: 50 native library tests, real-K50 default-path identity,
fast-mode checkpoint identity across 1/2/4/8/16 threads, exact cross-thread
resume, and ten identical 100M→120M continuation endpoints. Thirteen focused
Python tests passed before launch. Main-source verification, instrumented
checkpoint parity, export audits, a 120-training-second thermal soak and the
144-hand replay/reproduction smoke also passed. Smoke hands are correctness
fixtures, not held-out strength evidence.

| Threads | Median seconds for 20,001,395 new nodes | Speedup versus fast 1 thread |
|---|---:|---:|
| 1 | 22.695 | 1.00× |
| 2 | 11.811 | 1.92× |
| 4 | 6.656 | 3.41× |
| 8 | 4.361 | 5.20× |
| 16 | 3.972 | 5.71× |

These are two short forward/reverse passes of the fast recipe, not a comparison
with production training. Sixteen threads added 9.8% throughput over eight.
Qualification's maximum recorded CPU/VRM readings were 65/68°C and sampled peak
RSS was 2.48 GiB. Short-run qualification did not establish sustained thermal
capacity: the later main training hit its guard despite the soak passing.

## Terminal evidence

The supervisor launched at 11:59:06 UTC and recorded `RuntimeError('thermal
stop')` at **12:05:39 UTC / 14:05:39 Madrid**, 392.97 seconds after launch.
The one scheduled observation at 12:18:30 UTC found the controller no longer
alive, the root and first-training-stage failure receipts present, and no final
evaluation stage or verified readout. The stage has no successful result receipt.

| Last recorded item | Value |
|---|---:|
| Stage | Fast seed 2026101541, training |
| Progress nodes | 420,956,111 |
| Active training seconds at that progress record | 87.498 |
| Information-set entries | 21,137,855 |
| CPU / VRM, last accepted resource sample | 68 / 84.5°C |
| Family RSS at that sample | 3.006 GiB |
| Available host RAM / swap growth | 119.52 GiB / 0 bytes |
| Free disk at that sample | 82.59 GB |

Progress and resource rows are sampled at different times. The last accepted
resource row was at 12:05:38.445 UTC. The guard raises at CPU≥80°C or VRM≥85°C
**before writing the triggering row**. Its generic failure receipt does not
identify which sensor crossed the limit. The preceding VRM reading suggests
that limit was the immediate concern, but neither the exact crossing reading
nor the sensor responsible is recorded. These rows are not whole-run peaks.

The guard's exception path terminates its owned child process group and exits;
the observation confirms the supervisor exited. It does not establish the
current utilization of unrelated bb128 processes. No settings, cooling controls,
limits, deadline, thread count, seeds or endpoints were changed. No retry ran.

No completed 1B/600-second final checkpoint pair, production arm or final
evaluation is available. Strength intervals, noninferiority/gain decisions,
per-seat results and final-policy coverage are **unavailable**, not zero or a
failed statistical gate. The failed stage lacks completed wall/CPU/peak-RSS
accounting, so its last sample must not be presented as full-job cost.

## Decision and preservation

The useful result is deterministic short-run scaling; stronger play per hour
remains unanswered. Recommend holding PR335 adoption. Before a separately
authorized future strength study, sustained thermal capacity needs to be
resolved or a lower-concurrency protocol predeclared. Eight threads is a
reasonable candidate given its short-pilot throughput, but its long-run thermal
safety has not been established. No new study is launched by this report.

The study's ten-minute timer is disabled. PR335/default adoption remains the
owner's decision; PR336 stays excluded. PR340 remains a draft containing the
protocol, guarded harness, qualification and terminal evidence.

Frozen scientific source: `2ff320d483b0219165518d75d2d92389f48d182a`;
tested PR335 head: `b9923248cb97bc52c7db34491d9ff70e2845b4ec`.
Root: `bb128:/home/dberweger/nplayer-fast-strength-20261018-main-v4/`.
Qualification and all three failed setup sibling roots remain intact, as do
PR292's shared input policies and K50 tables. No full trace or model was copied
for this report. The compact receipt preserves the single monitoring snapshot.
Retrieve specific retained metadata into a fresh ignored directory with, e.g.,
`scp bb128:/home/dberweger/nplayer-fast-strength-20261018-main-v4/failure.json FRESH_DESTINATION/`.

Research-Cloud archival is pending. Current PR335 and PR340 are open; their
roots/dependencies remain protected under the storage policy. No archive copy,
Drive acceptance or deletion is claimed. Intended eventual folder:
`gdrive:PR-340-nplayer-fast-strength-study/`; it is not a confirmed restoration
source yet. Exact existing PR292 restoration pins remain in RESULTS_INDEX.
