# PR457 preparation: reviewed code and measured qualification quote

**Implementation and small correctness qualification are complete. The fixed
main experiment has not started.** Proposed allocation: **15 minutes on M4**,
covering the one control/candidate workload, fresh-process reproduction and
verification/readout. The measured/proxy forecast is **146.49 seconds central /
500.19 seconds reserve** (2m26s /8m20s). No strength study, mature training,
model export, live play or adoption follows automatically.

[Protocol](../../nplayer-passive-learning-qualification.md) ·
[complete cost evidence](cost-qualification.json) · [main quote](main-quote.json) ·
[ex-ante reach limits](ex-ante-reach.json) ·
[proposal456](https://github.com/dberweger2017/CFR-NLHE-6max/issues/456).

## What is implemented

One standalone research example uses the current three-player live-order K50
game, 13-depth 10–250 BB stack law and production menu. It compares epsilon0
with epsilon0.02 uniform target-policy exploration from empty tables. It does
not add a production option or modify deployed trainer/readers/models/router.
The target strategy and local perturbed-action regret are explicit; this is
not the failed behavior-only warmed-policy sampler from PR425 or a claim about
unconstrained equilibrium convergence.

Each arm has eight roots per seat/sweep, two workers, 2M-row whole-sweep freeze,
fixed128/512-sweep endpoints and a previously declared512-hand watch cohort.
Main repeats in a separate process, retaining logical row copies initially
and using hash-only row reproduction. Both arms retain identical root-input
inventory; node counts and policy-induced visits may differ. No extra seed,
epsilon tuning, cap extension or post-result selection is permitted.

Diagnostics distinguish path vectors, root-aggregate cancellation, admitted
zero-update slots, final row zeros, attempted versus retained/declined work,
raw/linear root-grouped coefficient moments and all never-hit watch keys.
Actual training-family attribution is separate from the public histories that
query a key. Unrelated aliased histories or merged-family root groups cannot
qualify a passive-family proxy. Every P0/P1/P2/other/merged-family street cell
and every watch denominator is retained.

The continuation proxy requires at least five additional retained watch keys
with the predeclared repeated-learning evidence, without excessive fully zero
final-row admission. This is a research heuristic, not playing-strength success.
Magnitude and concentration remain necessary interpretation. The ex-ante path
analysis warns that several persistently zero-probability actions can make the
2% floor impractically rare within this small workload. A negative result would
not reject exploration generally; a positive result would not qualify maturity.

## Correctness and independent review

Qualified wrapper/source commit: `d977d9f3f1c07dfd1448d306ee56d2f6a45674ee`.
Its Rust sources equal implementation commit `9c80ed5c`; the amendment only adds
supervisor-signal cleanup and its fixture. Source manifest:918 files, SHA256
`865febf768513471929882a08faf8b62a74ff079888010892b269fe47ccf2a03`.
Native executable:1,087,920 bytes, SHA256
`2968a771f4d54b0b7772a431b355f8d2b832025f9f4f3c65cd28fe83c6f1cc30`.

- All173 existing native library tests pass; all examples compile.
- Eight new native fixtures pass: exact tiny-game expected values/regrets/
  averages, zero-epsilon production parity, adaptive root/update/freeze parity,
  positive-epsilon1/2-thread table/count/ledger/root-inventory parity, and
  cancellation, never-hit, family-attribution and declined-row cases.
- Eight guard fixtures pass, including missing/nonfinite/malformed sensors,
  runtime failure, owner STOP, changed config, leaked descendants and supervisor
  signal cleanup. The owned process group is terminated and its direct child
  reaped; orphan zombies remain the OS's responsibility, not a claimed waitpid.
- Seven controller fixtures pass, including exact owner scope/budget refusals,
  full reproduction/inventory checks, recomputed family-specific proxy/ESS,
  named review scope, and completed failure-free calibration binding.
- Target-host native fixtures pass on M4. Guard/controller fixtures also pass
  there after the operational amendment. Source/archive/executable hashes were
  verified after transfer, before using the executable.
- The independent reviewer cleared the local perturbed-game math and then the
  exact final source/binary bindings for the fixed cost calibration. The receipt
  includes the reviewer, scope and empty unresolved-question inventory. Main
  remains conditional on explicit measured-budget acceptance and fresh admission.

The local full-library run took337.35s. Compilation/local engineering and source
transfer are already spent preparation, not included in the remaining-main quote.
No claim of isolated host performance or measured mature throughput is made.

## Fixed cost calibration

The cost-only calibration ran once on M4:8/16 sweeps,100K-row threshold,64 watched
hands, both fixed arms. Its final COMPLETE/status settle, no failure exists,
the one guarded native stage returned0 and both research locks were verified
available afterward. No calibration learning result selected the candidate,
workload or decision rule; the published readback contains cost fields only.

| Measure | Observed |
| --- | ---: |
| Guarded stage wall | 7.92s |
| Native process wall | 5.35s |
| K50 load and watch construction | 2.55s |
| Direct-child user+system CPU | 7.71s |
| Sampled family RSS peak | 1.42 GiB |
| Retained calibration files | 29,073,189 bytes |
| Thermal states | Nominal throughout |
| Swap | 517,734,400 bytes, unchanged during calibration |

The prediction scales16→512 sweeps with2x central/4x reserve allowances for
larger-table traversal; it scales row processing to four2.1M-row endpoint
scenarios, with3x reserve, and64→512 watch/readout work. It includes two fresh
processes, hash-only row reproduction, and explicit verification/readout reserves.
This is a proxy from a tiny capped calibration, not a completion guarantee or
statistical power calculation. The parent independently recomputed the totals
from the recorded cost fields.

Proposed main forecast:5GiB family RAM plus1GiB available headroom;4GiB new disk
plus4GiB free headroom. These are not reservations. The calibration admission
had7.06GiB available RAM and13.17GiB free disk; the lowest sampled values during
calibration were6.42GiB RAM and13.12GiB disk. Fresh main admission is required.

## Guard, preservation and next decision

The new controller acquires the ordinary and study compute mutexes nonblocking.
It fails closed on missing/nonfinite sensors or invalid M4 thermal state, owner
STOP, changed config/runtime and declared resource exhaustion. Each command
gets an owned process session/group; stops and supervisor signals terminate the
group, including multiprocessing workers. A clean parent exit with live workers
is not treated as successful completion. No elapsed-time/RSS/swap cutoff changes
the fixed scientific workload. Historical published guards are not rewritten.

Ordinary evidence is retained on M4 at
`/Users/dberweger/Local/nplayer-passive-learning-20261028/`: source-v1/v2,
target-fixtures-v1/v2, immutable review/config/source pins and calibration-v1.
The first source/fixture preparation remains as history; only source-v2 ran the
one NLHE cost calibration. No main-v1, mature model loads, exports, arena hands,
bb128 work, cleanup, new schedules or Drive acceptance occurred. Cleaner owns
later stable packaging/archive acceptance; originals stay retained.

**Next decision:** accept the proposed15-minute M4 main allocation, or retain
this qualified tool and defer the small experiment. Neither decision authorizes
a mature training arm or changes the current Open Poker player.
