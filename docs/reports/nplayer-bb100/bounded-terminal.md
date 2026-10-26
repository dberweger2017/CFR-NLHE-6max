# Bounded100BB qualification stopped before training

**October19 11:39:11UTC /13:39:11Madrid.** The first bounded qualification attempt
stopped in the full-matrix smoke test,392.51seconds after launch. The supervisor
exited; no mature1B/2B calibration or final10B seed started, so there is no measured
campaign ETA or100BB strength result. [Exact terminal receipt](bounded-terminal.json).
The earlier500M cost pilot remains unchanged.

The whole worker group reached**80.105GiB RSS**, crossing the80GiB guard.
Available host RAM was23.22GiB;CPU53°C/Thermistor15 58°C. The cause was memory,
not temperature or swap. Swap remained telemetry only. The guard terminated the
owned child process group and preserved the partial traces and all measurements.

## Cause and correction

The new persistent native batch evaluator called `EquityTables::load` separately
for every lineup/reproduction. That existing loader intentionally returns
process-lifetime storage through `Box::leak`; it is designed to load one fixed
K50 set per process. The new wrapper therefore accumulated one additional full
card-table set on every case despite caching the small policy fixture correctly.
The last progress event had one resident policy weight table and completed
`cross-202610193501-0-1`. This is a wrapper resource-lifetime bug, not evidence that
the250M-entry model itself needs80GiB or that frozen-table training failed.

The correction keeps one card-table set in the batch process and passes it to
all cases. A bots-only case remains lazy and does not cause a card-table load.
The old default single-case interface still uses one set. A guarded resource
regression test loads the actual pinned K50 files and checks that72successive
case requests return the same allocation. This engineering test plays no hands,
trains no model, and does not restart the failed smoke/calibration/main attempt.
The [guarded engineering test receipt](card-table-cache-test.json) passes all72
reuse checks:13.48s including compilation,4.93s test execution,1.13GiB sampled
whole-command peak.20focused Python tests also pass. This validates allocation
reuse; it does not replace the failed full-matrix smoke or admit main.

Earlier completed stages had passed CLI1/16/monitored-host checkpoint identity,
fresh/resumed identity, parallel gzip decompressed identity and cross-mode
recovery, direct/separate export identity, independent serial/parallel audit
receipt identity, serial/parallel100BB and legacy20BB trace identity, replay,
and128-block four-script probe path identity/replay. The full36-case smoke did
not complete; do not call the attempt qualified.

## Preservation and next admission

Frozen failed source`24157c92b52998e9eca06fd715ee53f7386dd2db`, deployed
`source-v3`/`binaries-v3`, original config/launch/deadline and the entire stopped
output root remain unchanged. No budget reset, guard increase, checkpoint
rewrite, successful-science replay or automatic scientific retry. No cleanup or
Drive upload-acceptance claim. The correction is prospective; it needs a fresh
qualified attempt before a final training ETA can be measured.

Raw root:
`bb128:/mnt/data2tb/research-cloud/PR-350-nplayer-bb100/bounded-20261019/`.
Control/build roots:
`bb128:/home/dberweger/nplayer-bb100-bounded-20261019/`.
Compact snapshot retrieved with
`python3.11 docs/reports/nplayer-bb100/collect_bounded.py results/bounded-eta-20261019-check1`.
Only status/metadata/failure and a short supervisor log tail were retrieved;
no models or hand traces were copied toMac. [Protocol](../../nplayer-bb100-bounded-protocol.md).
