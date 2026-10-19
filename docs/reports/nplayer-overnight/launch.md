# Overnight blueprint campaign — launch and qualification

Owner authorized the small speed run followed by the long campaign. The compact-key pilot’s100M logical-state checks pass, but its larger comparison was refused before launch on the fixed budget. PR344 retains that failure and all evidence. This separate campaign keeps the validated v1 fast recipe and resumes all three existing PR340~3B checkpoints, preserving their hashes and lineage.

Frozen orchestration/native host source `4cd199a5fef18b24cac188617d767b3f49a422de`;722 source files verified before execution. [Input/launch pins](input-pins.json); [protocol](../../nplayer-overnight-blueprint.md); [proposal345](https://github.com/dberweger2017/CFR-NLHE-6max/issues/345); [PR346](https://github.com/dberweger2017/CFR-NLHE-6max/pull/346).

Qualification launched October18 19:19:08UTC /21:19Madrid, PID358105, root `bb128:/tmp/nplayer-overnight-20261018`. The original ten-hour malfunction deadline is October19 05:19:08UTC /07:19Madrid; it is not a promised finish time and will not be extended. The measured forecast is frozen after resumed200M qualification, before main admission.

Owned active tmpfs output stays within48GiB, with hash-verified retained copies under `/mnt/data2tb/research-cloud/PR-346-nplayer-overnight-blueprint`. Old PR340/292/342 roots and their dependencies remain read-only. Nothing has been deleted or archived to Drive; cloud acceptance is pending. tmpfs is volatile, so completed-stage and seed copies are retained on HDD; no reboot is authorized.

TensorBoard2.20.0 is installed only in the new owned `/home/dberweger/nplayer-overnight-20261018-runtime` environment. Its EventAccumulator successfully reads the scalar files; HTTP logdir/scalar-tag endpoints pass. ServerPID359798 binds only127.0.0.1:6006 onbb128; an owner-host SSH tunnel exposes http://127.0.0.1:6006 (localPID74169). Shared environments, drivers, fans and OS configuration are unchanged. The UI reports development probes; final strength claims require the fresh verified matrix.

Local validation:10 focused Python tests pass, covering matrix identity, TFRecord CRC32C and preservation refusal; native example compilation passes. Full native regression/recovery/probe qualification and the fixed cost gate execute automatically before main training. No main outcome has been inspected or inferred.

## First measured cost quote

The old trainer and the monitored host reach exactly the same200M continuation endpoint and compatible checkpoint SHA256 `7d60d9f9a260e9451a9234bc29abad4bff53f4af28e2a7aa342fa7d8b053af05`. At3,149,727,814nodes /iteration598,645 /45,796,661rows, the monitored host records41.2362active seconds (**4.850M nodes/s**) and167.4076save seconds. Its four128-block scripted probes take0.02527s total; this measures probe execution, not every telemetry/UI cost. Old-trainer elapsed minus save is39.3073s; the monitored qualification also loads a reference average for per-decision probability comparison, an extra qualification-only cost.

The frozen quote is30,161.43s (**8h22m41s**) of remaining work:16,728.60s active traversal,4,520.01s conservative save allowance,0.53s projected probe execution,25% growth allowance and3,600s final verification allowance. It passes the original remaining-time gate. This is a one-segment forecast with allowance, not a measured30B runtime; main admission still requires probe replay and the complete matrix smoke. The owner received~06:00Madrid October19, with05:30–06:30 as a planning range; later table growth and thermal/resource stops can change that.

[Compact cost/recovery receipt](qualification-cost.json). The monitored qualification's321.13s wall includes reference loading, saving and hashing, so it must not be compared directly to main active-training time or described as monitoring slowdown.
