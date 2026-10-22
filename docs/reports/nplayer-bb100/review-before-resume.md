# Independent review before corrected qualification

The owner explicitly requested a review subagent before restarting PR350.
Independent subagent `/root/bounded_review` reviewed the new bounded host,
persistent arena, policy exporter/loader, parallel audit, guardian, admission quote
and global readout barrier. The failed source/attempt remain preserved; no final
seed or mature calibration had started.

The reviewer found no remaining blocking source defect after these corrections:

| Finding | Resolution and validation |
|---|---|
| Every case retained another process-lifetime K50 allocation | One fixed card-table set per batch; actual pinned-table72-request reuse regression passes. |
| A dead stage/guardian could leave native/replay descendants | Owned group wrapper holds both mutex FDs, parent-death signal kills the group, captured-parent check closes registration race; Linux guardian-death and TERM-resistant-descendant tests pass. |
| Large readback hashes bypassed sampling; STOP/signals missed some phases | Separate guarded validation stages; root STOP checked on every sample; SIGTERM/INT enters group cleanup. |
| Smoke aliases only exercised one cache identity | Six distinct owned paths,12verified loads,≤2resident weight tables and one card set; no duplicate large bytes. |
| One peer case and assumed8x replay scaling did not support admission | Full36-case128-block mature persistent matrix, actual8-worker replay wall, cost-only JSON scan, native/final trace hashes and output-byte forecast. |

The reviewer found no blocking information-access, freeze-boundary, direct-export,
paired-root or statistical-readout defect. This is a bounded source review and
qualification recommendation, not a guarantee that all future failures are ruled
out. Main still requires all correctness/memory/cost gates; one calibration and
three fixed seeds cannot guarantee later cost or thermal stability.

Reviewed controllerSHA256`2bd85318e04806d4d5b7a90cf7a89948f3920863ca6ff4a546ae2e7b46f54c6b`;
group wrapperSHA256`2f876a6ba56ac21a9e896344cecd160ba3ce2000578d9f5769af2e719458cad9`.
[Guarded bb128 engineering receipts](review-engineering-tests.json): native
release build14.03s; actual K50 reuse test7.41s including compilation (4.94s test);
all23Python/process tests pass onLinux. LocalMac passes21with two Linux-only tests
skipped. Native library files are unchanged from the previously passed57-test
build; the changed native arena example is rebuilt and its resource test executes.

The one corrected attempt uses fresh source/output pins, retains the failed root,
and keeps the original13:32:38.711UTC qualification cutoff, all resource limits,
seeds/targets/held-out roots and separate conditional8h main allocation. No
further automatic retry, budget reset, pruning,200BB, default/release or merge.
[Exact prospective amendment](../../nplayer-bb100-bounded-protocol.md#corrected-qualification-after-independent-review-october19).
