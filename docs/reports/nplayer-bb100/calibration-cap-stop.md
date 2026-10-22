# 100 BB calibration reaches2B, stops before cap qualification

**October19 12:31:49UTC /14:31:49Madrid:** the reviewed corrected attempt stopped
at its predeclared admission check. Native calibration completed successfully
(returncode0), but the table had**244,485,627entries**, below the fixed250M freeze
threshold. The cap had not activated at2B, so frozen-table costs/behavior were
not qualified. The launcher correctly refused to proceed under the declared
fixed-endpoint rule. No final10B seed, mature audit/evaluation or strength
readout ran. This is not another wrapper-memory or thermal failure.

[Compact native events, failure and small-matrix proof](calibration-cap-stop.json).
Frozen deployed sourcec4b04bf8 and all checkpoints/partials remain unchanged.
No automatic retry, endpoint/cap change, deadline extension, cleanup or adoption.

| Endpoint | Actual nodes | Entries | Checkpoint bytes | Save seconds |
|---|---:|---:|---:|---:|
|1B|1,000,005,743|169,218,506|6,148,015,941|196.10|
|2B|2,000,003,197|244,485,627|9,132,902,417|289.88|

All2B training took423.45active seconds (**4.72M nodes/s**); native whole-stage
wall24m45s, childCPU2.524hours, sampled whole-family peak22.23GiB.
The2B full-average export took179.68s. Both checkpoints and the2B average were
saved and hashed by the native host. Independent mature export audits and policy
load qualification had not run; these are retained research inputs, not admitted
release artifacts. Zero discarded keys/visits and `frozen_at=null` are expected
for this observed pre-cap trajectory.

The corrected small qualification passed before calibration: exact CLI/thread/host/
resume/compression fixtures, all3072probe hands replayed, and the36-case matrix
replayed432hands plus432exact reproductions. The matrix proved12actual distinct
cache loads. This addresses the first attempt's test-coverage/K50-cache bug; it
does not substitute for the mature repeated-model load/RSS test.

## ETA and a prospective next step

The observed rate gives **1.76hours of active traversal for30B total nodes if
unchanged**. This is a scenario, not a completion ETA: frozen-table throughput,
fully populated memory, large every-row audits and the mature persistent
play/replay costs are still unmeasured. Save/export/hash/I/O and verification are
additional. No pretraining-freeze/cost quote exists, so the8h main allowance has
not started and is not a forecast.

We ended5,514,373entries (**2.21%**) short of the selected cap. Recommend a
prospectively declared, fixed **3B calibration endpoint**, reusing the pinned2B
checkpoint and leaving cap/recipe/guards unchanged, then completing the same
mature audit/matrix admission. This is a proposal; the fixed2B protocol forbids
automatically extending until a desired result occurs. It needs a new declared
continuation/budget before launching. Do not lower the cap on this existing
checkpoint or silently alter the retained source/results.

## Retained paths and pins

Owned root:
`bb128:/mnt/data2tb/research-cloud/PR-350-nplayer-bb100/bounded-20261019-v2`.
Final calibration checkpoint:`calibration/2000000000.gz`,
SHA256`43320d93b5dda9981d4f99e1d8b4898b924e38acfe8f809f6693ff79cdc41566`.
Average:`calibration/2000000000-average.gz`,
SHA256`4637b9911b89a241be9dd4d3b03e0d80f483669516bd56009c8ada6e5ccb3bb7`.
1BcheckpointSHA256`ff06f5396b7152e253dd4c0e93473e65ea8054cbba9054c7653d9759c0499605`.
Source/config/binary pins remain in[reviewed launch](reviewed-launch.json).
Supervisor483894 exited. At validation stop the sampled CPU47°C/Thermistor52°C,
103.41GiB available RAM, zero swap growth; these are last readings, not whole-run
thermal maxima. All models/traces remain onbb128; only compact metadata/log tail
was retrieved. PR350 remains open, originals/dependencies protected and
Research-Cloud archival/upload acceptance pending.
