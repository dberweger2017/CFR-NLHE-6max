# 200 BB campaign qualification and admission

The owner accepted PR404's complete 18-hour allocation and fixed counts. The controller is implemented and qualified; **main training has not started**, pending the owner's vacuum-cleaner agent preparing the agreed 360 GiB free NVMe. Actual checked free space is **206.40 GiB** at 2026-10-22T20:13:39.345491+00:00. No further budget approval is required.

[Protocol](../../nplayer-bb200-model-campaign.md), [compact qualification/provenance receipt](qualification.json), [PR404](https://github.com/dberweger2017/CFR-NLHE-6max/pull/404).

## Verification

- 28 focused Python tests, 121 native library tests and six native example tests pass; one existing example test remains ignored.
- All 51 fixture stages return zero. The 36 real-200BB case shapes produce 432 initial hands and 432 byte-identical reproductions; every initial hand independently replays.
- All six tiny endpoints export and pass full-row checkpoint/export/binary probability/action audits. Within-lineage canonical membership matches. First-lineage one-versus-sixteen-thread and fresh-versus-resumed checkpoint bytes match.
- Qualification source `f11edfe5227882980f57925ab0ca93b3a2f790a7` pins 855 files. The previous train/policy/arena binaries remain byte-pinned; the separately built inference/diagnostic binaries have a source-bound test receipt. Only diagnostic manifest depth admission changes natively; game transitions and regret rules are unchanged.
- The verified PR402 1B parent is rehashed successfully at its original path. Protected binaries, managed Python environment and K50 remain readable.

Build/tests took 57.09 seconds; full fixture took 177.51 seconds. The tiny fixture sampled CPU maximum 55°C, Thermistor15 53°C, peak worker-family RSS 152.8 MiB and no swap growth. These are correctness-fixture costs, **not mature model forecasts**. Build's last sensor sample was CPU63/Thermistor15 54.5°C.

## Main and preservation

Main will use the same qualified source and fixed three-lineage 3B/10B recipe, then all 30 gates at the predeclared 10,543,104 initial hands plus equal reproduction. Global payoff readout waits for complete reproduction/replay/input proofs. Accepted estimate: 7h51m central, 17h33m component reserve, 18-hour planning allocation; no elapsed-time stop or guarantee.

No main model or confirming hand has started. The one-use launch is prepared and checks the actual 360 GiB admission before configuring `main-v1`. No waiting timer, cleanup, movement, staging or upload was added. The owner’s vacuum-cleaner agent owns that work; originals, old inputs and all qualification evidence remain retained. Cloud archival of this campaign is pending owner-managed closeout, with no acceptance claim.

Host root: `/home/dberweger/nplayer-bb200-model-campaign-20261022`; qualified source `source-v2`, build `build-v1`, fixture `qualification-v1`. Start once after successful manual storage check using the prepared `launch-main.py`; never duplicate an existing `main-controller.json` or main launch.
