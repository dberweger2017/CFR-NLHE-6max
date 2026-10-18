# Three-player20BB overnight blueprint campaign

Owner-authorized [proposal345](https://github.com/dberweger2017/CFR-NLHE-6max/issues/345).

## Question and owner authorization

Does extending the three validated fast-mode three-player20BB blueprints to30B nodes improve playing strength over their existing~3B anchors, consistently across all three seeds? Owner authorized “please do the small run we talked about and then the long run” on October18. The compact-key pilot in#343/PR344 passed100M logical-state checks but refused its larger comparison on cost. This campaign uses the established v1 fast recipe; it does not adopt a new encoding or change defaults.

## Frozen design before training

- bb128 only,16 threads, seeds2026101541/42/43,20BB50/100,K50,menuv1,fast8roots,full-street averages,150M entry ceiling with no freezing. Resume the exact audited PR340~3B checkpoints read-only, verified bySHA256.
- Fixed final30B nodes per seed; recovery saves10B/20B/30B. Light immutable in-memory average-policy probes at the starting anchor and5B increments,128six-hand blocks against each of random/check-call/tight-aggressive/pot-pressure. Separate fixed monitoring roots per seed/bot, reused for curves; no seed/checkpoint selection or budget extension based on curves.
- TensorBoard records training speed, nodes, rows, RSS, temperature and I/O/monitoring costs, plus per-bot BB/100 and uncertainty. Qualify in-memory probabilities/actions against the normal export/loader, all-hand native replay, exact training-state identity and probe overhead before main admission. Target<5% monitoring slowdown; refuse main if measured probe/telemetry projection exceeds10%.
- Final confirmation uses8192fresh six-hand blocks per lineup: final vs own~3B anchor and cyclic other-seed anchor in both singleton orientations (12lineups), plus final and ownanchor as singleton against each of four bot pairs (24lineups).589,824direct/cross hands +1,179,648scripted hands, all independently replayed and exactly reproduced before readout. Roots reserved20261018346001–018, distinct from monitoring. The cyclic pair consists of two identical opponent policies; no mixed-population robustness claim.
- Primary gate: all three same-seed oriented singleton-contrast lower95 bounds>0. Secondary cyclic safeguard: all three lower95 bounds>−5BB/100. Scripted differences use paired singleton block returns and Bonferroni-adjusted12comparison intervals; report every contrast and coverage, no aggregate-only claim. Means are oriented singleton contrasts, not pooled individual-player returns. Failure/inconclusive is retained, no extra hands or rerun.

## Runtime and storage

Designed around an overnight~8h task from81Badditional nodes plus checkpoints/qualification/final verification. This is a forecast, not a promise: measure a200M resumed qualification segment and freeze the cost quote before main. Maximum campaign10hours from first qualification compute; main admission requires the forecast including25%allowance and final evaluation to fit that original deadline. No extension or automatic retry after scientific/resource failure.

Keep CPU90°C/Thermistor15 95°C immediate stops, missing-sensor stop,80GiB whole-child-family RSS,8GiB available RAM,256MiBswap-growth,48GiB per-process address space, normal+study exclusive mutexes. No PR336/search/GPU/OS/fan/driver changes or other-job edits. HomeNVMe has only~5.7GB above its50GBfloor: active unique outputs/checkpoints use owned tmpfs, with immutable retained at-rest copies on the2TB research cache. Measure tmpfs usage and availableRAM; cap owned tmpfs output at48GiB and preserved HDD output growth at100GB, retaining50GBfree on both disks. Never delete checkpoint originals or modify other PR roots. Stop rather than exceed resources.

A fresh implementation PR will contain the controller, qualification, telemetry and results. No merge, default-model change, publication or cleanup is authorized by this campaign. Raw evidence stays onbb128 pending Research-Cloud archival/acceptance.

## Owner-authorized thermal amendment, October 18

The original supervisor stops at CPU90°C or Thermistor15 95°C. After observing the live monitoring curves, the owner explicitly requested Thermistor15 100°C and approved applying it “on the next completed checkpoint.” MSI has not confirmed this sensor's physical location or safe continuous limit;100°C is an owner-selected campaign stop, not a manufacturer rating.

The one-time `scripts/nplayer_overnight_thermal_handoff.py` waits for the first seed's next20B save and hash event. It checks the exact process identities, pauses and terminates the original trainer/supervisor only after that event, retains the interrupted segment, verifies the checkpoint SHA256, acquires both existing mutexes and resumes the unchanged native binary from20B toward30B. The original stage is recorded as owner-interrupted, never as a successful exit. Any brief unsaved work after the checkpoint is discarded. The resume emits only25B/30B monitoring points; the original anchor/5B/10B/15B/20B points remain intact. The other two seeds and final evaluation retain the original protocol.

CPU90°C, missing-sensor stops, affinity/16threads, memory/swap/disk ceilings and the original October19 05:19:08UTC deadline remain. Existing owned bytes are charged in full after restart, rather than resetting growth budgets. The zero-swap baseline is required. Original source files, binary, anchors and already completed qualification remain frozen. The amendment script has separate provenance; no original source/config/qualification evidence is overwritten. TensorBoard appends a new event file and continues the first seed's cumulative active/monitor seconds. A terminal failure before the checkpoint aborts this handoff; no failed science is retried.

`thermal-handoff-armed.json` means pending at95°C; `thermal-handoff-active.json` records activation of100°C. The one-shot helper becomes the continuing supervisor; no recurring schedule is created. Its command, SHA256, process IDs, checkpoint identity and transition/failure receipts remain in the owned run root and retained evidence.
