# 100 BB qualification completes; main admission refused

**October 19, 2026, 15:02:02 UTC / 17:02:02 Madrid:** the owner-authorized
2B→3B continuation completed its native training, both independent full-average
audits and the complete mature calibration matrix. The measured main-run quote
then exceeded the unchanged time and memory admission budgets. **No fresh 10B
seed started; no main strength result exists.** No automatic retry or settings
change was made. This was an admission refusal, not a thermal or runtime RSS stop.

[Compact cost/proof/identity receipt](continuation-admission-stop.json),
[prospective protocol](../../nplayer-bb100-bounded-protocol.md),
[launch/source/parent pins](continuation-launch.json).

| Admission condition | Quoted requirement | Limit | Result |
|---|---:|---:|---|
| Main wall time, including 25% allowance | 10.106 h | 8 h | Refused |
| Largest sampled/modelled family RSS ×1.25 | 82.538 GiB | 80 GiB | Refused |
| Main output, including allowance | 202.009 GB | 536.610 GB remaining reservation | Pass |
| Monitoring / active training | 0.00967% | 10% | Pass |

Actual largest sampled family RSS was **66.030 GiB**, during the persistent mature
policy matrix; the 82.538 GiB figure includes the prospective 25% reserve. The
continuation's training/save/export stage peaked at **22.872 GiB**. Neither
measurement crossed the actual 80 GiB runtime guard. Sampling can miss brief
peaks; these are process-family measurements, not whole-host RAM consumption.

## Completed qualification

- Saved 2B parent independently verified; inherited small fixture proofs pinned.
- Calibration seed `2026101935003` reached **3,000,011,203 nodes**, return code 0.
  Membership froze at **2,088,867,258 nodes**, iteration 143159, with
  **250,000,475 entries**. The iteration-boundary cap can overshoot slightly.
  The anchor and 3B checkpoint have the identical key-set SHA256
  `a83858109eed965e73acd76787761d9353f2a66cccb482c0271173e3ff731425`.
- Both independent every-row average-policy audits passed, as did guarded
  checkpoint readback. Anchor and 3B checkpoint/export hashes are in the receipt.
- All **36 ×128 six-hand-block cases** passed exact reproduction and independent
  replay: **27,648 hands plus 27,648 reproduced hands**, with 12 policy loads.
  This is calibration/cost evidence; no poker payoff or strength readout was
  inspected or used to select scope.
- The derived 0→3B active-training basis is **630.741 s**: preserved 0→2B
  423.454 s plus the new continuation. The post-freeze rate is **4.830M nodes/s**.
  It is one calibration trajectory, not a three-seed performance guarantee.

| New continuation stage | Measured wall seconds | Recorded CPU seconds |
|---|---:|---:|
| Verify inherited proof | 0.074 | 0.074 |
| Read back parent | 33.749 | 33.745 |
| 2B→3B train, save, export, probes | 1,568.370 | 8,595.458 |
| Read back continuation | 48.985 | 48.978 |
| Anchor full-average audit | 382.934 | 2,586.674 |
| 3B full-average audit | 386.624 | 2,622.990 |
| Mature native matrix, reproduction, replay, scan | 3,628.558 | 3,638.269 |

Whole continuation attempt lasted **1h40m49s**, ending before its fixed
15:21:12 UTC qualification cutoff. CPU numbers are the guardian's recorded
per-stage child accounting; they are not a full-host utilization measurement.
The derived training basis includes the previous 2B prefix, while this stage
table includes only the newly authorized attempt. Checkpoint save times were
197.329 s for the freeze anchor and 266.161 s for 3B; average exports took
155.055 s and 160.807 s respectively.

## Why the forecast exceeds eight hours

These are **prospective costs for all three fresh 10B models and the complete
final comparison**, not work already performed or a new ETA.

| Component | Forecast minutes before the final 25% reserve |
|---|---:|
| Active training | 104.00 |
| Checkpoint saves | 53.23 |
| Average exports | 16.08 |
| Every-row policy audits | 38.48 |
| TensorBoard scripted probes | 0.01 |
| Policy loading | 58.68 |
| Native play and scaled non-load native overhead | 74.67 |
| Independent replay allowance | 15.77 |
| Input/output verification, scans and fixed readout allowance | 124.16 |
| **Subtotal** | **485.07 (8.085 h)** |
| **Including 25% reserve** | **606.34 (10.106 h)** |

The mature 128-block matrix spent 3,520.707 s loading policy tables; its total
native wall was 3,590.712 s. The forecast scales the remaining non-load native
wall with the 64× larger final matrix, while loading is counted once. Therefore
74.67 minutes is not pure measured card-playing time. Verification uses the
predeclared conservative 25 MB/s HDD allowance. These measured costs identify
model/checkpoint I/O and verification as major remaining expenses. Discarding
headroom alone would still leave the quote slightly above eight hours.

Keep the completed calibration and evaluate a revised I/O/evaluation design or
an explicitly larger budget before another launch. Do not silently change the
three-seed science, guards, cadence or deadlines to make admission pass.
PR344 remains a deferred, separate proposal; no work was launched for it.

## Terminal proof, preservation and retrieval

Root: `bb128:/mnt/data2tb/research-cloud/PR-350-nplayer-bb100/bounded-20261019-v3`.
Frozen source `b9882e7e728847a58691995e64eabd4563ea0991`; native v4 binaries
unchanged. Later PR347 compatibility/report commits were not deployed.
Root `failure.json` records `measured overnight admission refused; no final seed
started`. Supervisor 492733 has exited; `pretraining-freeze.json`, final-seed
directories, `training-progress.json`, final evaluation and settled results are
absent. The root's last phase string remains `calibration-persistent-evaluation`;
it is stale stage metadata, not proof of an active run.

At the compact diagnostic check, both `/tmp/cfr-nplayer-bb100.lock` and
`/tmp/cfr-cygnus-exclusive.lock` were free; no owned science process remained.
The retained TensorBoard server (PID492788/6007) still serves the calibration.
The last recorded stage sample was CPU63°C/Thermistor15 60.5°C, zero swap growth;
these are historical final samples, not live temperatures or thermal maxima.

All prior failures, raw traces, checkpoints, exports, sources/configurations and
parent dependencies remain unchanged on bb128. PR350 is open: no root archival,
copy, cleanup or Drive upload acceptance is claimed. Only compact metadata was
retrieved into ignored `results/pr350-terminal-admission-20261019/`.
For a fresh compact status snapshot:

```sh
python3.11 docs/reports/nplayer-bb100/collect_bounded.py results/FRESH_NAME \
  --root /mnt/data2tb/research-cloud/PR-350-nplayer-bb100/bounded-20261019-v3
```

The authoritative cost/proof files are `cost-quote.json`,
`calibration-cost-basis.json`, `calibration-evaluation/evaluation-cost.json`,
`calibration-evaluation/evaluation-verified.json`, `validations/*/verified.json`
and the seven compact `measurements/*/result.json` files. Read costs/proofs only;
raw calibration outcomes have not been used for selection. Checkpoint members
`calibration-continuation/{anchor,3000000000}.gz` and corresponding
`*-average.gz` are pinned in the receipt. Future retrieval must verify those
SHA256s against the original root/index; Drive restoration remains pending.
