# Three-player 200 BB: all 30 acceptance gates pass

The fixed three-lineage family passes the declared fresh acceptance at 200 BB: **24/24 scripted-profit, 3/3 own-checkpoint improvement and 3/3 cyclic noninferiority gates**. The six 3B/10B endpoints, all 36 cases and all adverse or unresolved historical evidence are retained. [Protocol](../../nplayer-bb200-model-campaign.md), [unaltered settled readout](results.json), [all gates](gates.csv), [provenance and proof hashes](provenance.json).

This supports the specified capped 200 BB candidate family toward v0.6.1. It does not publish a release, change a default or merge this PR. The owner makes those decisions.

## Fresh strength results

BB/100; bounds below are **one-sided simultaneous 95% Student-t/Bonferroni across the complete family of 30**. Script and direct lower bounds must exceed zero; cyclic bounds must exceed −5. Ordinary unadjusted two-sided descriptive intervals and standard errors remain in the CSV/JSON. Each independent sample is a six-permutation deal block; reproduction is verification, not another independent sample.

| Seed | Own 10B vs 3B contrast | Adjusted lower bound | Cyclic continuation delta | Adjusted lower bound |
|---|---:|---:|---:|---:|
| 2026102240001 | +79.66 | +69.06 | +77.02 | +59.87 |
| 2026102261001 | +69.75 | +56.94 | +67.99 | +58.57 |
| 2026102261002 | +78.25 | +67.63 | +66.06 | +52.54 |

The direct statistic is half the paired difference of reciprocal singleton returns (10B against two own-3B policies and 3B against two own-10B policies), not pooled player return. Cyclic deltas compare each 10B and its own 3B against the same fixed other-lineage **3B** pair, without halving; they are not a 10B-vs-10B tournament. Cycle: existing → fresh1 → fresh2 → existing.

| Script field | 2026102240001 mean / lower | 2026102261001 mean / lower | 2026102261002 mean / lower |
|---|---:|---:|---:|
| random | 551.31 / 436.77 | 454.98 / 376.61 | 504.74 / 426.73 |
| check-call | 235.74 / 191.98 | 213.77 / 170.32 | 228.82 / 190.19 |
| tight-aggressive | 58.40 / 42.27 | 56.52 / 40.29 | 57.60 / 41.74 |
| pot-pressure | 50.02 / 33.61 | 57.97 / 44.33 | 44.03 / 30.43 |
| trained-call | 188.35 / 134.91 | 266.21 / 209.98 | 216.90 / 161.56 |
| trained-pressure | 54.75 / 41.36 | 54.03 / 43.32 | 59.72 / 52.91 |
| call-pressure | 123.00 / 79.55 | 130.21 / 86.93 | 123.94 / 78.23 |
| random-tight | 266.23 / 221.41 | 290.82 / 244.86 | 273.45 / 229.24 |

All 24 profit bounds are positive; the smallest is **+30.43 BB/100** against pot-pressure for fresh2. Trained mixed fields use the focal lineage's fixed 3B policy plus the named script. Positive absolute returns do not establish maximal exploitation or remove prior 100 BB relative random/check-call/mixed regressions in PR357. No 200 BB script-relative 3B→10B regression gate was declared here. No equilibrium, human or external-opponent claim follows.

## Training, capacity and coverage

| Seed / checkpoint | Actual nodes | Iterations | Retained keys | Added-node active seconds | Save seconds | Load/hash/other seconds |
|---|---:|---:|---:|---:|---:|---:|
| 2026102240001 / baseline | 3,000,016,876 | 135,890 | 250,002,537 | 422.34 | 149.23 | 350.51 |
| 2026102240001 / candidate | 10,000,017,024 | 528,824 | 250,002,537 | 1486.10 | 133.00 | 361.63 |
| 2026102261001 / baseline | 3,000,013,803 | 135,990 | 250,000,924 | 622.59 | 168.12 | 39.15 |
| 2026102261001 / candidate | 10,000,003,556 | 526,686 | 250,000,924 | 1479.02 | 146.62 | 367.24 |
| 2026102261002 / baseline | 3,000,011,211 | 137,273 | 250,001,937 | 617.84 | 154.31 | 41.35 |
| 2026102261002 / candidate | 10,000,009,688 | 532,447 | 250,001,937 | 1507.58 | 143.86 | 367.58 |

The existing baseline continues the verified PR402 1,000,008,098-node parent; fresh lineages start from scratch. Candidate active seconds cover 3B→10B, not cumulative 0→10B. Save/load/hash time is excluded from active traversal. [Exact endpoints, rates, bytes and hashes](endpoints.csv), [complete endpoint metadata](endpoints.json). All six endpoints stop at the declared node target with whole-iteration overshoot. Training uses 16 threads and eight roots per seat; evaluation uses eight workers.

Membership is exactly identical between 3B and 10B within each seed. The 250M threshold freezes after merging a complete iteration, so the small key-count overshoot is expected. Further training refines retained states and mass; it cannot add missing states. Cross-lineage membership may differ.

| Seed | Stored zero-average-mass rows at 3B | At 10B | Check-call river missing at 10B | Check-call river found zero mass |
|---|---:|---:|---:|---:|
| 2026102240001 | 29.95% | 26.20% | 4,688/27,434 (17.09%) | 2 (0.01%) |
| 2026102261001 | 29.96% | 26.23% | 4,612/27,350 (16.86%) | 8 (0.03%) |
| 2026102261002 | 29.91% | 26.16% | 4,642/27,710 (16.75%) | 10 (0.04%) |

Stored-row zero mass and played missing/zero-mass lookup rates are distinct quantities. Visitation differs across policies and fields: these rates are descriptive, not a controlled coverage improvement estimate. [Per-identity/street matched lookup counts](coverage.csv) contain positive mass, found zero mass and missing for both models on the same visited own-lineage observations. [All case policy misses](policy-misses.csv) include cross panels; cross summaries do not provide the positive/zero split. Script decisions are not model lookups. [Physical-seat and button-relative position intervals](seats-positions.csv) are descriptive, without extra multiplicity claims.

## Integrity and complete cost

**10,543,104 initial hands** independently replay; **10,543,104 reproduction hands** match bytes. Nine verified jobs, 36 cases, six full-row checkpoint/export audits, six full-row binary parity audits and exact within-seed keysets pass. All **49 main stages return zero**, no failure or restart, no extra hands or tuning. Preliminary real-200BB qualification separately passes 51 stages/432 initial +432 repeated hands, 28 focused Python tests, 121 native library tests and six example tests (one existing ignored).

Main ran **2026-10-22 20:24:20 → 2026-10-23 02:49:31 UTC** (22:24→04:49 Madrid): **6.420 hours / 23110.69 seconds**. Main stage wall totals 22936.32s; summed child CPU 110035.96s. These exclude prior build/qualification, report publication and owner-managed archival. Accepted allowance was 18 hours; central forecast 7h51m, reserve17h33m, neither a time cutoff nor guaranteed finish.

| Main component | Wall minutes | Child CPU minutes | Peak family GiB |
|---|---:|---:|---:|
| training processes | 142.63 | 1200.75 | 22.37 |
| average exports | 43.67 | 161.62 | 20.35 |
| checkpoint audits | 41.17 | 277.69 | 0.37 |
| binary conversion | 32.95 | 32.93 | 0.01 |
| binary parity audits | 32.57 | 32.56 | 13.33 |
| native evaluation including reproduction | 45.09 | 66.66 | 27.95 |
| replay and reconciliation | 26.19 | 43.76 | 11.94 |
| global barrier and readout | 17.99 | 17.97 | 0.59 |

Across all nine native evaluation jobs, model/K50/mass loading totals **2191.52s** and play/write totals **292.93s**, including reproduction. They are components of native-process wall, not additional wall costs. First use and ordinary host caches are not a controlled loader benchmark. All generated paired traces total **63,096,974,958 bytes**. [Exact cost accounting](costs.json), [component CSV](costs.csv).

Sampled worker-family peak **27.95 GiB**, minimum available RAM **94.39 GiB**; CPU max **75.0°C**, Thermistor15 max **92.5°C**, below90/100 stops. Swap 362.66→437.41MiB (host-level, not attributable solely to this job). Sampled free NVMe minimum **125.19GiB**. Only temperature/missing sensor resource stops were automatic; disk/RAM/swap were inspected manually. Owner cleanup ran independently, so disk changes are not a measured campaign-storage delta.

## Provenance, limitations and disposition

Frozen scientific source **`f11edfe5227882980f57925ab0ca93b3a2f790a7`**, 855 source/config pins; source bundle SHA256 `9ad072eb1aa04c1afd8277da5963a740b0b7e7f87fc52c9e224de10b5aef6b8d`; main config SHA256 `cd6c47f9b13f5384f68f953f615aeae8310b6b1739b0cf1958c7388552a1b7ca`; settled result SHA256 `6909662e4b2372c13981467723759ba5a37ffde7daa3899514e8d52c72c969b8`. Later report commits do not replace the running source. [Launch/storage amendment](launch.md) preserves owner authorization to start with206.40GiB free while their cleaner prepared space.

One host, three fixed training seeds, one abstraction/menu and capped memberships. Statistical bounds use independent deal blocks and Student-t approximations; rare-tail risk remains. The frozen readout includes all observed variance/standard errors and per-seat results but does **not** emit top-block or tail-concentration diagnostics; none are claimed. Raw blocks remain retained for review. No removed outliers, selected panel, post-hoc count extension or robustness guarantee.

Recommendation: accept this family as satisfying its declared 200 BB research acceptance and review v0.6.1 packaging separately. Keep both checkpoints and the prior adverse panels; search remains deferred. No additional training/evaluation has been launched.

All models, raw traces, sources, qualification and prior parent inputs remain on bb128 under `/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1` and the paths pinned in the JSON receipts. **Archival/staging/uploads are owner vacuum-cleaner managed and pending**; no Drive receipt, deletion or cleanup is claimed. Reproduction of this study requires restoring these exact pins into a fresh destination, not rerunning its one-use controller over the completed root.
