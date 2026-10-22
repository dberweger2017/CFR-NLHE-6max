# 200 BB at 1B: affordable, capped, and still incomplete on river coverage

[PR402](https://github.com/dberweger2017/CFR-NLHE-6max/pull/402), [proposal401](https://github.com/dberweger2017/CFR-NLHE-6max/issues/401), [frozen protocol and controller correction](../../nplayer-bb200-maturity.md).

**The fixed continuation is complete.** It reaches **1,000,008,098 nodes** and freezes membership at **250,002,537 entries**, near 961M nodes. The full-row export audit passes; all 3,072 initial hand instances independently replay, and 3,072 reproductions match byte for byte. No training is repeated. This is a capacity/cost result, with **no playing-strength readout or release verdict**.

My recommendation is to retain the **250M threshold as a bounded research candidate** for one fixed, three-lineage 3B/10B campaign, with incomplete river coverage carried explicitly into acceptance. It is not established as sufficient capacity for a release. More training after freezing can refine retained rows; it cannot add missing states. Do not run another cost pilot or increase the cap automatically.

## Endpoint and capacity

Same seed2026102240001 and PR400's verified 500,027,427-node parent. Three players, 200 BB, blinds50/100, K50, existing min/pot/conditional-jam menu, unpruned fast mode, eight roots per seat, 16 threads, float64 all-street opponent-sampled averages, parallel writer and 250M freeze threshold. Existing qualified native binaries are reused byte for byte.

| Measure | 500M parent | 1B endpoint |
|---|---:|---:|
| Actual nodes | 500,027,427 | 1,000,008,098 |
| Retained entries | 159,384,070 | 250,002,537 |
| Iterations | 18,435 | 40,028 |
| Membership frozen at iteration | Not frozen | 38,253 |
| Discarded-key counter | 0 | 6,536,832 |
| Discarded-visit counter | 0 | 2,560,884 |
| Positive average-mass rows | 106,543,248 | 166,456,750 |
| Zero average-mass rows | 52,840,822 (33.15%) | 83,545,787 (33.42%) |
| Checkpoint size, decimal GB | 5.458 | 8.788 |
| Average export size, decimal GB | 3.281 | 5.191 |

The last unfrozen telemetry sample has 249,799,660 entries at959,894,619 nodes; the first frozen sample has250,002,537 at962,122,371 nodes. The checkpoint records the exact freeze iteration38,253; telemetry brackets its node count rather than giving an exact freeze-node value. All19 subsequent frozen observations retain the same entry count. The existing native code merges a whole iteration before checking the threshold, explaining the2,537-entry overshoot (0.001015%).

Added499,980,671 nodes create90,618,467 retained entries:0.1812 retained keys/node. That rate is **censored by the cap**, not an estimate of natural saturation or uncapped growth. Discarded-key/visit counters count discarded update work, not distinct unreachable states. At1B,71.52% of rows are river keys.143,341,391 rows (57.34%) have no recorded traverser visit; opponent-sampled averaging can still give such rows average mass. Neither zero visits nor table-wide zero average mass measures the proportion of played decisions using fallback.

## Fresh descriptive coverage

Each endpoint uses four128-block panels, six seat permutations per block:768 hand instances per script pair, with128 independent deal blocks. The 1B roots are2026102240201–204, distinct from PR400's500M roots. The policies also differ, changing which decisions are reached. These are **descriptive comparisons, not matched-state causal effects or strength measurements**. [All32 endpoint/script/street rows](coverage.csv).

Focal missing lookups / focal decisions at1B:

| Script pair | Preflop | Flop | Turn | River |
|---|---|---|---|---|
| Random | 9/1127 (0.8%) | 7/306 (2.3%) | 17/137 (12.4%) | 15/45 (33.3%) |
| Check-call | 0/768 (0%) | 0/490 (0%) | 2/490 (0.4%) | 134/490 (27.3%) |
| Tight-aggressive | 0/584 (0%) | 0/143 (0%) | 0/77 (0%) | 0/40 (0%) |
| Pot-pressure | 0/661 (0%) | 0/193 (0%) | 0/83 (0%) | 0/44 (0%) |

River comparison:

| Script pair | 500M | 1B |
|---|---:|---:|
| Random | 14/72 (19.4%) | 15/45 (33.3%) |
| Check-call | 214/506 (42.3%) | 134/490 (27.3%) |
| Tight-aggressive | 2/20 (10.0%) | 0/40 (0%) |
| Pot-pressure | 3/43 (7.0%) | 0/44 (0%) |

The calling panel is encouraging but still exposes a substantial river gap. Random's descriptive miss percentage increases, with only45 river decisions. Zero observed TAG/pressure misses on40/44 decisions does not establish universal coverage. Keep every panel; do not pool their different visitation distributions to claim a general coverage gain.

A found key can still have zero average mass. These arena counters do not distinguish positive-mass from zero-mass found lookups, so found share is not trained-policy coverage. The training audit's `missing_decisions` mixes first encounters/creation with post-freeze misses; it is not the held-out statistic above. No numerical coverage pass threshold was predeclared, and none is invented afterward.

**Capacity judgment:**250M is defensible for a controlled first model campaign because it is affordable, the same capped question can be tested across lineages, and the known coverage limitation can be challenged by fresh strength safeguards. It is not defensible to call its coverage complete or to promise that another9B nodes will repair missing keys. A larger cap could admit more states but changes retained membership and costs; this pilot has not demonstrated its strength benefit. Accept or reject the resulting candidate on the declared200BB strength requirements, while preserving these diagnostics and any adverse results.

## Complete costs and temperatures

| Component | Seconds |
|---|---:|
| Added-node active traversal | 114.80 |
| Checkpoint saving | 129.26 |
| Native training process, including load/hash/startup/save | 467.20 |
| Residual within that process: load/hash/startup/other | 223.13 |
| Average export | 396.02 |
| Independent full-row audit | 375.73 |
| Coverage native processes, initial + repeat | 504.32 |
| Model/K50 loads within coverage | 424.92 |
| Actual coverage play within those processes | 0.1238 |
| Four independent replay stages | 8.06 |
| Sum of disjoint measured stages | **1,751.34 (29m11s)** |
| Launch to completed post-processing | **2,020.66 (33m41s)** |
| Sum of disjoint stage child CPU | **7,751.34 (2h09m11s)** |

Active traversal is added nodes divided by114.80s: **4.355M nodes/s**, about8.7% below PR400's final4.770M interval in this one sequential observation. Timing excludes save, loading and hashing. No causal speed claim follows. Coverage process totals include load/play; do not add those subcomponents again. Process residual223.13s is not an isolated load benchmark. CPU includes descendants of each stage once, excluding controller/setup/tests and later publication/archive/readback work.

Launch18:22:56UTC to final completion18:56:37UTC October22 includes the controller bug/fix/handoff and other work between measured stages. Its269.33s excess over stage totals is not hidden. The original31m27s central forecast was about7% low on this elapsed measure; corrected69m39s reserve and approved90min allocation both cover it. No elapsed-time kill was installed.

Training peaks20.73GiB sampled RSS; overall33.68GiB during inference, export19.42GiB and streaming audit0.36GiB. Overall CPU74°C/Thermistor15 87.5°C, below90/100 stops. Minimum available RAM88.90GiB and NVMe192.28GiB; HDD393.16GiB remains available. No observed swap growth in either stage group (host swap remains about370.4MiB and decreases slightly between groups). These are approximately2s worker-family samples, not exact high-water guarantees or process-specific swap attribution. No wall/RSS/disk/swap cutoff. [Exact costs/resources](costs.json).

## Controller failure, preserved and corrected

Training exits0 and the saved checkpoint passes game/recipe/count/hash validation. My new metrics check then rejects its entry count because it incorrectly assumes an exact250M hard cap. Existing native `multi_cfr.rs::apply` freezes **after** an iteration's merge at>=cap; `multi_checkpoint.rs` accepts a frozen table at>=cap. The native code, cap, model bytes, seed, threads and guards do not change.

Original controller failure/status/costs/source and checkpoint remain in `main-v1`. A regression-tested, one-use completion command accepts only this exact config/error/saved checkpoint, verifies original qualified inputs, refuses any prior export/audit/coverage attempt, claims a fresh `completion-v1`, and executes only those originally unstarted stages. It contains no training invocation. All13 focused tests pass locally and onbb128. There is no scientific retry or extra hand/root/endpoint. Do not describe the whole operation as failure-free: the controller failed and was corrected; all scientific stages and subsequent proofs succeed.

## Next model campaign proposal — not launched

[Concrete arithmetic and scope](campaign-proposal.json), [discussion](campaign-proposal.md): preserve this lineage, add two independent fresh lineages, each with fixed3B and10B checkpoints; retain250M threshold and current recipe. Verify fixed membership within each3B→10B continuation and compare each model to its own baseline. No checkpoint shopping, further cost pilot, search/pruning/menu change or automatic extension.

Measured-cost scenarios give **3h50m central /9h35m conservative reserve** for training, six saves, six exports and six full-row audits, including the existing1B parent and two fresh lineages. This is a **model campaign estimate**, excluding acceptance hands/reproduction/replay,200BB binary conversion/parity and optional staging/archive. Those omissions are explicit; it is not a whole-release quote or authorization.

Fresh200BB acceptance must retain all30 established simultaneous95% gates:24 absolute scripted/mixed-profit tests, three own-checkpoint oriented contrasts, and three cyclic continuation noninferiority tests with−5BB/100 margin. Freeze counts, roots, assumed effects/variances and pass chances before confirming hands;100BB effects do not establish200BB power. The present coverage-only hands supply no strength variance estimate. Keep cost and strength admission separate without starting another stand-alone cost pilot.

## Reproducibility and preservation

Scientific execution `b0af16114d1e608159ed2a17118860e4a9414fe4`; completion correction `a6ff4cce162c1a5a04322475cce11177f7131215`; original configSHA256 `4c5b60e14c87dae33689b9ff7364ca183609c4dcd9382ce5bda5f221a6059b65`. Later commits are publication only. [Original launch](launch.json), [preserved failure/correction](training-and-correction.json), [complete compact receipts](receipts.json), [provenance/input pins](provenance.json), [post-completion file/trace readback](verified-readback.json), [unchanged precomputed results](results.json), [table audit](table-audit.csv).

Final checkpoint8,788,049,377bytes SHA256 `55d89c553ba1756eac1af117847b30e8b18e4f901afba942ee5a906bc00249ad`; average5,191,429,099bytes SHA256 `1f745e803c7dd00d1a32a11b35532780ab27091c163df0f26a9fcf3b26ec5dc2`; canonical keysetSHA256 `c37fdf1c6d0a2e92d6193ae285db4c990e5fbecd859c734a33268ae34d41bb11`. All250,002,537 rows audit against the checkpoint's keys/owners/streets/actions/float64 probabilities using the existing1e-14 normalization tolerance. Final checkpoint/export and all initial/repeated traces pass closed SHA256 readback. Reproduction adds no independent statistical information.

Offline publication, without poker execution:

```sh
python3.11 -m scripts.summarize_nplayer_bb200_maturity \
  docs/reports/nplayer-bb200-maturity/receipts.json \
  docs/reports/nplayer-bb200-feasibility/results.json \
  --out results/pr402-publication-fresh
```

All originals, partials, failure and exact source snapshots remain at `/home/dberweger/nplayer-bb200-maturity-20261022`; PR400 parent/binaries/environment and PR398 Git-object/environment/K50 dependencies remain protected and read-only. Nonfatal Git alternate-depth warnings are retained. No other jobs, cache tools, fans, drivers or environments are changed.

Owned completed outputs are copied and verified into `/research/PR-402-nplayer-bb200-maturity/`, excluding external inputs and Git alternate stores. Current owning PR status and all open PRs (402/371/344) were checked before copying. All11,478 ZIP members pass SHA256 readback. The15,900,815,323-byte ZIP has SHA256 `6f927e16d5144f284ac7e710465351400aeee5f64514aca547790402aa777b52`; embedded manifestSHA256 `3fe335344719d06954c06ad72a4f861c111d640acf15a5e47a5e63c201c5da5d`. The deployed upload is the remaining closeout path; **cloud acceptance remains pending until a receipt exists**. Originals are not deleted. Intended Drive fallback `gdrive:PR-402-nplayer-bb200-maturity/evidence.zip` is not yet a confirmed restore location. [Archive state](archive-status.json). Passive science observer has finished; no new timer, full training, acceptance run, merge or release follows automatically.
