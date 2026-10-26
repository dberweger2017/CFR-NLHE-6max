# PR347 M1 storage check — October19

**Passed and merged.** The owner authorized this fixed smaller M1 comparison and merge only if it passed. PR347 merged at 2026-10-19 14:48:06UTC as`950611b68840fa9b4c01a1e0b9e73c319b434930`, with all five head checks green. The fixed build/science allowance used 17.21 minutes.

Baseline current-main integration `e0472485d1a09822889edd2bb1fa92b638dc7334`, PR347 head `4b92f066cf974c5ab0e7d4c1811cf59976af428b`. Candidate applies only PR347's native store/size changes to the same main source. 59 candidate integration library tests pass. Both release builds use 2 compiler jobs; measured training uses 4 Rayon threads.

3 players, 100 BB, K50/full averages, unpruned fast8 roots/seat, seed2026101934701, 10M-entry freeze cap. Fixed fresh order baseline/candidate/candidate/baseline to80M, each followed by a cross-version resume to100M; one additional fresh 100M per version. Small 1/4-thread fixtures and cross-resume/fresh endpoints are also identical. Compatible gzip on both arms. No successful work or failed test rerun.

| Metric | Baseline | PR347 | Candidate / baseline |
|---|---:|---:|---:|
| Training (s) | 29.111 | 29.029 | 0.9972 |
| Throughput (M nodes/s) | 2.749 | 2.758 | 1.0033 |
| Save (s) | 25.163 | 25.218 | 1.0022 |
| Whole command (s) | 60.040 | 60.183 | 1.0024 |
| CPU (s) | 151.918 | 150.604 | 0.9914 |
| Peak RSS (GiB) | 2.201 | 2.127 | 0.9663 |

Training/save/wall/CPU/throughput are medians of two fresh 80M commands per version. Peak RSS is each arm's maximum across these commands, using the larger of sampled whole-group RSS and macOS wait4 maximum RSS. Training excludes save, input load/hash and the final compressed-file checksum; whole command includes them. Resume and export costs are retained in the JSON. No confidence interval is inferred from two repeats.

## Identity and acceptance

- exact_checkpoints: True
- exact_exports: True
- thread_and_cross_resume_parity: True
- unchanged_frozen_membership: True
- all_guards_passed: True
- training_no_5pct_regression: True
- memory_no_5pct_regression: True
- save_no_10pct_regression: True
- wall_no_10pct_regression: True

All four 80M checkpoints: `9bf29bb3cbeeba3508e3b62dba609a59a3a273b02c615b39cd8c8c65b21658b7`.
All four resumed 100M plus two fresh 100M checkpoints: `acc9e988f418f919b06a58f166c2fde7468b74bd318b1f3b7f493cda440fce2a`.
Both average exports: `da1f61ee0a5573ab42a66074fa022f784fb99acb6607ce44e095462c9cd44d16`.
Frozen key membership: `2af12b3722bd261cb49febf614822a1bbd8f4a84e082866f1480e64412a6bdcf`; 10,008,236 entries at both endpoints. The small batch overshoot beyond the nominal 10M cap is identical.

Predeclared acceptance: all parity/resource checks, median training and peak RSS no worse than 5%, save/whole-command no worse than 10%. All fixed repetitions/endpoints retained. Resource limits: 6GiB RSS, 2GiB estimated available RAM floor, 8GiB disk floor and8GiB owned output budget; fixed 30min combined build/science allowance and 420s stage limit.

## Scope and retention

One M1, one fixed seed, two fresh repeats per arm, 4 threads/10M keys; background load logged. Not a bb128 16-thread/250M benchmark or a playing-strength study.

PR347 does not change CFR sampling/math or checkpoint formats. Exact checkpoint/export identity supports behavioral equivalence for these trajectories; it does not measure stronger poker or certify all possible inputs. Author-reported Intel single-thread speed gains are separate evidence.

Raw commands, resource/background-load samples, both sources/binaries, card-table inputs, checkpoints, exports, protocol and frozen runner remain in `/Users/dberweger/Local/cfr-nplayer-bb100-20261019/results/pr347-m1-20261019`. Compact summary: [receipt.json](receipt.json). Protocol SHA256 `53410a555ab7eba7be5fd540437c2ee307e760b8b652ff9e0de5652a9c7a2edf`; runner SHA256 `7af844d0907949f34e8ad90e81cadf333cbd736460d3ecffe74829019c920cb8`. Original K50 input provenance is the indexed PR163 archive; all member hashes and the whole archive were verified before timed work.

Research-Cloud archival remains pending. No originals removed or cloud acceptance claimed. Active bb128 PR350 source/binaries/guards are unchanged. PR350's pending allocation telemetry now uses the stable `Allocation.total()/index` API, supporting both layouts. Its frozen deployed source/binaries are unchanged.

Pending PR350 allocation telemetry compatibility compiles with `cargo check --locked --offline --manifest-path native/hu20-trainer/Cargo.toml --example nplayer_bounded`. Staged repository artifact and whitespace checks pass.
