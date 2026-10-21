# Fresh river qualification: affordable continuation, unresolved belief error

PR380 / proposal379, October 21, 2026. **The fixed engineering study completed and reproduced.** The expanded menu improves the chosen full-menu diagnostic on 181 of 199 qualified fresh pairs and meets the deployment latency gates. Retained continuation reads the original solved strategy without new solves. However, two deployment roots miss declared-game quality, and nine of twenty matched-accuracy belief controls exceed the unchanged 0.05 BB threshold. **Do not launch a longer strength campaign on this evidence.** Belief handling is the next concrete engineering target; remaining full-menu harms must also stay visible.

This is one frozen 10B blueprint, one host, two fresh self-play deal roots and no whole-hand search match. It establishes neither stronger play nor safe resolving. No arena, training, default or release change ran.

## Frozen comparison and verification

The [predeclared protocol](../../river-continuation-qualification.md) compares `pot-jam-cap3-v1` with `pot-jam-cap3-root-check-min-v1`: only the opponent's minimum opening bet immediately after hero's root check is added. DCFR(1.5,0,2), projected beliefs, raise cap and off-tree blueprint fallback are unchanged.

Two fresh 5,000-hand traces, roots 202610216501/502, yield 2,961 eligible two-live-player first-river roots. All allocate successfully. Sample 100 uniformly from each trace, using roots 202610216511/512; freeze the 200-root panel and twenty public-pot-stratified belief controls before solving. There are 2,987 hands with any river decision and 26 three-live-player first decisions; this remains a two-active-player solver.

All 16 main stages return zero. Every initial hand is independently replayed against pinned engine `5db20e3d5d6862b32a7402035c1340b622d3b005`, and the repeated traces are byte-identical. Both passes' 400 strict, 400 deployment, 200 retained and 20 belief records match in strategic quantities, statuses and profile digests. Measurement file bytes differ because timing counters and opaque process-local session handles are excluded from equality; no strategic quantity is excluded. [Verification receipt](verification.json).

The owner requested an initial strict-pass inspection before global verification. Those provisional results were disclosed, then confirmed unchanged by reproduction. No source, arm, selection, count, quality threshold or gate changed after that inspection.

## Fresh strict comparison

Both arms target each player's gain at most `min(0.002 × pot, 0.02 BB)`, checking through 8,192 sweeps. Full production-menu best-response evaluation is offline and separate from decision timing.

| Metric | Reference cap3 | Minimum-bet expansion |
|---|---:|---:|
| Matched strict-quality pairs | 199/200 | 199/200 |
| Opponent full-menu deviation gain, median | 0.7433 BB | 0.3152 BB |
| Opponent full-menu deviation gain, mean | 1.4926 BB | 0.6681 BB |
| Cases worse than blueprint, qualified pairs | 56 | 32 |
| Strict decision time, median | 1.065 s | 2.248 s |
| Strict decision time, p95 | 4.466 s | 5.263 s |
| Tree nodes, median / maximum | 30 / 39 | 39 / 51 |
| Solver f64 storage, median / maximum | 2,654,936 / 3,459,200 bytes | 3,459,200 / 4,531,552 bytes |

Paired opponent-gain reductions: **181 improve, 18 worsen, none tie**; median 0.1755 BB, mean 0.8245 BB. Blueprint regressions remove 27 but introduce three new ones. The largest paired worsening is **2.1285 BB** (case79, panel202610216511/hand4045, pot6.5 BB): 0.4809→2.6094 BB, versus blueprint2.4110 BB. All cases and harms remain in [cases.csv](cases.csv) and [results.json](results.json).

Case6 (panel202610216511/hand408, pot42 BB) misses the strict target in both arms and remains inconclusive. Lower deviation gain is the declared modeled diagnostic; the opponent's profile value also changes between arms, so a reduction alone does not prove an improvement in hero's absolute worst-case value. This fresh self-play panel broadens PR377's selected-case evidence but is not a population strength estimate.

## Deployment and retained continuation

Deployment targets `min(0.01 × pot, 0.1 BB)`, checking through 2,048 sweeps. Times include complete worker roundtrip and required per-decision checks, exclude model startup and offline full-menu audit, and retain quality misses.

| Frozen gate / cost | Reference | Expansion | Verdict for expansion |
|---|---:|---:|---|
| Allocation support ≥90% | 2,961/2,961 | 2,961/2,961 | Pass |
| Complete decision median ≤0.5 s | 0.274 s | 0.360 s | Pass |
| Complete decision p95 ≤2 s | 0.990 s | 1.345 s | Pass |
| Every attempted decision meets quality | 198/200 | 198/200 | **Fail** |
| Mean / maximum complete time | 0.383 / 1.960 s | 0.488 / 2.660 s | Descriptive |
| Installed retained-search coverage ≥90% | — | 198/200 (99%) | Pass |
| Original-profile continuation, zero new solves | — | 1,482 exact rows / zero advances | Pass |

Both menus miss deployment quality on cases137 and195 at the fixed limit. For the expansion their two-player gains are [0.11453,0.19426] and [0.10639,0.11209] BB against a 0.1 BB target. These become labeled blueprint fallback; correct fallback does not convert a quality-gate failure into a pass.

The 1,482 exact retained-profile checks include 198 roots and **1,284 later hero rows**. Root strategies and profile digests reproduce the stateless deployment output. Median retained begin is0.366 s (p95 1.357 s); stored payload median333,266 bytes, maximum437,938 bytes. Payload counts f64 profiles, paths, menus and holding cards, excluding engine/allocator/JSON metadata. Native batched replay/row/equality auditing costs a median14.50 microseconds per checked row; this is **not individual continuation RPC tail latency**. Public replay, both orientations, own-card selection, facing-all-in, invalid payments, stale/mismatched contexts and off-tree fallback are also covered by fixtures. The opt-in research client is not integrated into the arena or released player.

## Beliefs: matched convergence does not remove the discrepancy

All twenty controls qualify: both projected and exact-joint solves reach **0.01 BB** per-player gain within the fixed8,192 sweeps. **Eleven pass and nine fail** the existing per-player excess gate E≤0.05 BB. The all-control verdict is therefore **fail**, not inconclusive.

For each player, preserve `E = D + S − R`: S is projected-profile gain under projected law; D is the same profile's gain change under exact law; R is the exact-reference residual. Maximum S is0.009830 BB and maximum R0.009547 BB.

| Public pot band | Controls | Passing | Maximum E |
|---|---:|---:|---:|
| <5 BB | 5 | 5 | 0.01476 BB |
| 5–15 BB | 5 | 4 | 0.05929 BB |
| 15–40 BB | 5 | 2 | 0.27195 BB |
| ≥40 BB | 5 | 0 | 1.07138 BB |

The worst control is case136, panel202610216512/hand1529, pot82.5 BB. For player1, S=0.00667773, D=1.07093085, R=0.00622457, giving **E=1.07138401 BB**. Here S−R is only0.00045316 BB: improving convergence to the matched target has not removed the large law-change diagnostic.

These balanced stress strata deliberately oversample large pots: the full panel's band counts are44/106/35/15, while controls select5 each. Nine failures out of twenty is **not a population failure-rate estimate**. E compares two reference profiles and is not a pure causal attribution to projection. The exact law is still the modeled action-likelihood law, not the true opponent posterior or a safe-resolving guarantee. PR376's original results and threshold remain unchanged; different cases, menu and accuracy targets preclude a pass-count trend claim. [All control residuals and identities](belief-controls.csv).

## Actual cost and qualification

Main wall is **4,670.64 s (77.84 min)**, inside the pre-fresh75–110 minute quote. Child user+system CPU is **11.4675 hours**. The initial and repeated exact-control stages consume42.91 minutes together; strict stages13.78 minutes, deployment5.55 minutes and retained5.01 minutes. Trace generation/reproduction, independent replay, panel freeze and verification account for the rest. [Every stage and resource summary](costs.json).

- Sampled family RSS peak **73.43 GiB**; minimum available RAM47.77 GiB.
- Maximum CPU **74 C**, Thermistor15 **95.5 C**, below unchanged90/100 C hard stops. No thermal or other failure.
- Host swap stays367,697,920 bytes throughout; no growth. Final NVMe free39.58 GiB, HDD free495.09 GiB. Sampling cannot establish an exact instantaneous peak or attribute individual swapped pages.
- Main phases reload their workers: **41 model-load instances**, not five total. Five ordinary processes are used per panel phase; one16-thread exact worker is used per belief phase. No shared-model concurrency speedup is measured.
- Isolated calibration startup: **118.56 s**, including113.71 s policy load for250,000,475 rows. Main wall includes loads; main per-load counters were not persisted, so exact aggregate parse time is unavailable.
- Native library94/94 and focused Python8/8 pass on bb128. Local related reference/accounting47, native prepared parity17 and readout2 pass; the final readout/CI-routing check passes14/14. CI's native94 also pass.

`calibration-v1` is preserved: it failed before build/solve because noninteractive SSH PATH omitted `cargo`. The owned process PATH fix produced `calibration-v2`, all four stages zero. No scientific work was retried. Initial CI at analysis head `dfa8da42` failed14 legacy tests; logs explicitly show disk-reserve refusals in two tests, while other campaign tests report incomplete startup. The first hosted-runner repair (`011ad5df`) freed the root disk to104 GiB but left the same eight shard0 failures: tests still used `/tmp`. GitHub [reproduced Ubuntu26.04’s RAM-backed `/tmp` limit](https://github.com/actions/runner-images/issues/14777), which is below these legacy disk reserves. The workflow now exports `TMPDIR` under the disk-backed runner temp directory and logs both filesystems; the unnecessary SDK deletion is removed. Test/production guards and measured science are unchanged. Fresh CI must establish whether this resolves every failure; no full-suite pass is claimed here.

## Decision and a separate pilot quote

**Next: a bounded belief-representation prototype, with exact-joint parity and measured complete latency, plus preservation of full-menu harms.** The matched controls make belief handling a concrete target rather than a convergence hypothesis. A structured folded-card weighted-prefix evaluator is a candidate, not an implemented or qualified solution. Do not silently raise the sweep limit or belief threshold. Retained continuation is now qualified within this protocol; individual-RPC behavior and actual whole-hand integration remain separate work.

A small whole-hand cost/variance pilot would require integration and a new frozen protocol/approval, not a strength claim. For scale, **1,000 first solves at the measured candidate mean cost8.14 serial minutes**, before reproduction and loads. In these self-play traces each designated actor seat has963/970/1,028 eligible roots per10,000 hands (9.63–10.28%); the all-seat29.61% must not be used as a hero-call rate.

A conditional compute quote for three declared lineups ×128 six-hand blocks ×two arms, with independent reproduction, is **45–60 minutes**, not an authorized run. This is4,608 initial plus4,608 repeated hands, of which4,608 are search-on across both passes. Assuming10–30% hero first-solve frequency gives461–1,382 solves, about3.75–11.25 serial solve minutes. Allow eight model startups at118.56 s (15.81 minutes), plus play/replay/process overhead and reserve; do not assume unmeasured concurrent speedup. Mixed/pressure frequency, tail latency, off-tree use and integration cost remain unknown; the quote needs recalibration if those assumptions fail. Integration engineering time is not measured or included. The failed belief/quality gates argue for fixing the concrete limitation before approving this pilot. No automatic continuation follows.

## Reproduction and retention

Measured implementation: **`0bb9c621cbf5f4d89bed9fc92d0419fb9825ea66`**. Readout-only source: **`dfa8da42c4c6a0f40cc1d70c8a8280a529ddc00b`**; later report/CI edits do not alter the measured snapshot. Frozen model SHA256 `d835f61f4a5407bd47e8f8a5da849ef82c16ad21fce32f15dce72d5997275189`; panel SHA256 `f5b6b2706a0b6ee8912a52961b6b8e2795158bd982bea18fa43227f74924b919`. [Source/binary/input pins and setup failure](provenance.json).

Main started11:25:29 UTC and finished about12:43:20 UTC (13:25–14:43 Madrid). All originals, traces, per-request records, logs, calibration failure, source bundle and binaries remain at `bb128:/home/dberweger/river-continuation-qualification-20261021/`; successful measurements are `main-v1/`, independent guarded readout `readout-v1/`. Prior model/K50 inputs stay at their original read-only paths. Cache/Drive closeout is **pending**; no cloud acceptance, restoration receipt or deletion is claimed. No other PR's inputs, environments, jobs, fans or driver settings changed.

After retrieving only completed compact readout files into a fresh ignored local path, regenerate with the readout script from the analysis commit (no new solving):

```sh
PYTHONPATH=ROOT/source ROOT/venv/bin/python ROOT/analysis-dfa8da42.py \
  ROOT/main-v1 --out FRESH_READOUT_DIRECTORY
```

`ROOT` is the owned bb128 root above. The readout requires complete status, no failure, all16 stage return codes zero and deterministic verification passed. CSV line endings are normalized to LF without changing numeric fields. Original traces and measurement records remain necessary to independently audit the compact report.
