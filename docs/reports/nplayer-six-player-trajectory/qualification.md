# Six-player saved-trajectory diagnosis: approved, awaiting source I/O

[PR421](https://github.com/dberweger2017/CFR-NLHE-6max/pull/421),
[proposal420](https://github.com/dberweger2017/CFR-NLHE-6max/issues/420),
[fixed protocol](../../nplayer-six-player-trajectory.md).

Implementation and small M4 engineering qualification pass. **No recorded PR417
trace has been transferred or analyzed by this new job.** Owner accepted the45-minute allocation. Main awaits a source-I/O window
compatible with priorityPR419; the quote below is retained as the pre-approval
record.

The fixed inventory is24 initial files, **7,989,712,885bytes (7.44GiB)**.
It contains1,179,648 distinct physical hand instances; the two contrasts across
eight fields produce786,432 paired comparisons. Reuse10B inputs, not repeat
files. Each analysis pass scans10,641,416,174bytes because the shared10B files
participate in both contrasts. Original replay proof hashes are pinned in the
tracked inventory; full destination SHA verification and streamed hashes must
match. No new engine replay or statistical confirmation is claimed.

Local26 focused tests pass. On M4, the16 directly relevant tests pass, including
an end-to-end synthetic paired trace scan, deterministic repetition, every-hand
and dealblock accounting, all support counters and refusal of corrupted hashes,
changed fixed opponents, wrong means/coverage and incomplete blocks. Same source
`ed5ac7804c97e12a6bd50f3aaa133703c637e55e`; [source/runtime/proof receipt](qualification.json).

The first M4 package attempted the broader10 legacy paired-suite tests without
their unrelated qualification/report-module dependencies. That package and
failure logs remain atqualification-v1. The corrected qualification-v2 runs the
16 relevant tests; the full26 already pass locally. No study input was copied
or scanned in either engineering attempt.

A synthetic20-focal-decision-per-hand workload runs256 identical repetitions:
6,144 synthetic comparisons /137,262,592streamed bytes in **1.177s**.
Peak qualification self RSS **26MiB**. These are format/
accounting fixtures, not newly played poker hands or representative full-trace
performance. The quote takes the slower extrapolation by bytes or comparisons,
then reserves3× scan time. It does not assume an order-of-magnitude speedup or
actual measured Ethernet payload throughput.

## Complete allocation — owner approved

**13.6min central /32.0min reserved;
request45min on M4**, one worker,512MiB memory planning allowance and10GiB new
workspace. M4 has~98GiB free. Python3.11.14 already exists; no installation,
native build, mature model or bb128 compute-lock exception is required.

| Component | Central min | Reserved min |
|:--|--:|--:|
| Ethernet single stream, cap32MiB/s; reserve16MiB/s | 3.97 | 7.94 |
| M4 destination SHA verification, central200MiB/s scenario;2minreserve | 0.63 | 2.00 |
| Two full scans, max pair/byte synthetic scaling;3xreserve | 5.02 | 15.06 |
| Source/pin/ordinary mutex setup | 1.00 | 2.00 |
| Global reconciliation and compact reporting | 3.00 | 5.00 |

Ethernet en8 is active1000baseT full-duplex; authenticated SSH aliasbb128-lan
resolves192.168.77.1 and M4 routing uses192.168.77.2/en8. Use one source stream,
cap32MiB/s, nice19/ioniceidle on bb128. Source reads must yield toPR419 critical
save/export/audit/conversion/load/replay I/O; the source transfer may need to
wait until a suitable traversal window or after419 finishes. **That wait is
outside the active-job estimate.** No source copy or scan has started and there
is no new watcher/timer. Actual slower transfer or different trace complexity
can exceed a reserve; it is a planning estimate, not a kill limit/guarantee.

## Interpretation and retained evidence

Every fixed hand is retained. Compare where the first changed sampled action
occurs, its positive/zero/missing row pair, fold/check/call/raise or raise-sizing
change, position, and later missing exposure. Matched-prefix action counts and
all reached action counters are separate from first-divergence hand partitions.
All grouped contributions must sum to the existing paired mean, while block
means/SE and every focal lookup count must reconcile with old verified results.
Two deterministic full analysis outputs must agree before global readout.

This can locate recurring changes and guide a controlled next hypothesis. It
cannot establish the causal value of that action, identify changed probabilities
when sampled actions coincide, or determine the benefit of capacity. After the
first divergence the histories differ; terminal returns grouped there are
associations. The data was already inspected, uses one training lineage and
restricted circular seating orders. PR419 remains independent; no new lineage,
menus, search, tuning, release changes or expanded analysis follows automatically.

All M4 inputs, source, manifest/proofs, results, partials and failed package logs
remain protected in the new ignored working root. Owner-managed archival is
separate; no research-payload Drive acceptance or cleanup is claimed.

## Approved finite continuation — October24

Owner replied **“approve421”**. M4 controller24255 starts at12:18:46UTC /14:18:46Madrid
with immutable config SHA256
`d022f932a9aac337e6dae5e83537dfd07d912834b8f94998fb23b5015ec8d398`.
[Approval/config/operational source pins and first health](launch.json).
The source phase waits on existing419controller929267 using one kernel pidfd exit
event, then requires complete/no-failure/all-stage0 proofs. No repeated checks,
app schedule or passive observer service is created. The ordinary M4 compute
mutex remains free during this dependency wait; the job holds it nonblocking
when source copy, destination hashes and both scans actually start.

At12:19UTC the continuation is healthy in`await-source-io`, no payload copied or
full scan started. PR419 is in candidate-audit, CPU71°C /Thermistor1587°C, nofailure.
A single32MiB/s source rsync runs only after that dependency releases; raw source
files remain untouched. Both full deterministic scans and final equality/hash/
reference-count barriers then advance automatically. Waiting is recorded apart
from the45-minute active-job estimate; it is not hidden in runtime reporting.
No scientific retry/extension or merge authority is granted.

Per the owner's clarified archival workflow, agents retain ordinary working/final
files with their relative paths. The cleaner later packages completed stable
evidence into verified ZIP archive sets on bb128 HDD and uploads those sets. No
pre-ZIP, loose-payload upload or deletion is performed here.
