# Three-player200BB pilot: affordable at500M, mature table not qualified

[PR400](https://github.com/dberweger2017/CFR-NLHE-6max/pull/400), [proposal399](https://github.com/dberweger2017/CFR-NLHE-6max/issues/399), [frozen protocol](../../nplayer-bb200-feasibility.md).
The owner-approved fixed pilot **completed in23m40s**, inside the prospective30–45minute central/90minute reserve allocation. Correctness, every-row export audit and all replay/reproduction checks pass. Active training reaches4.77Mnodes/s in the final interval; sampled training peak13.31GiB and overall19.13GiB. No resource stop, scientific failure, retry or endpoint extension.

**Do not admit a three-lineage long campaign from this pilot alone.** At500Mnodes there are159.4Mentries, no capacity freeze and continuing growth. The next proposed bounded task is a fixed500M→1B continuation of this lineage,250Mcap unchanged, to measure mature-table behavior; about31m central/66m calculated reserve, proposed90minute allocation. It is **not authorized or launched**. If it does not reach capacity, stop at1B rather than extending. A full model-training allocation and three-lineage acceptance remain separate decisions.

## Fixed recipe and endpoints

Fresh seed2026102240001; three players,200BB/20,000chips each,50/100blinds, K50,min/pot/conditional-jam, unpruned fast path-v1,eight roots/seat,16training workers, float64 all-street opponent-sampled averages, parallel gzip and250Mfreeze-at-cap. Generic trainer/policy code already supports200BB; the only production native change admits200 to the duplicate arena whitelist. No100BB checkpoint is resumed or relabeled. Existing released policies and search are untouched.

Active times are **added-interval** native elapsed minus save; use actual node differences. Cumulative node targets allow whole-iteration overshoot. Process wall includes native load/startup, compression and checksum/teardown/supervision costs. These are not isolated load benchmarks. GB is decimal;GiB binary.

| Actual nodes | Entries | Iterations | Active training s | Interval Mnodes/s | Save s | Process wall s | Sampled peak GiB | Checkpoint GB |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100,017,787 | 44,585,102 | 3,335 | 18.86 | 5.304 | 22.29 | 52.73 | 4.64 | 1.460 |
| 200,021,099 | 79,266,287 | 6,813 | 20.53 | 4.871 | 38.34 | 123.46 | 7.30 | 2.641 |
| 500,027,427 | 159,384,070 | 18,435 | 62.89 | 4.770 | 78.27 | 256.96 | 13.31 | 5.458 |

Total active traversal102.28s, saving138.90s and training-process wall433.15s. Remaining191.96s within those processes is startup/load/hash/other overhead, not pure model load. The full job is much longer than its active traversal. Do not forecast a full campaign by dividing target nodes by4.77M alone.

All159,384,070 final policy rows independently audit against the original checkpoint's keys/owners/streets/actions/float64 probabilities (existing1e-14 normalization tolerance). Final checkpoint5,457,867,989bytes SHA256`704e35dd04d8290fc49c9d4505f6371bf0e8a50200e185c8881807ce727af625`; average export3,281,260,304bytes SHA256`ff5e74b1ee6b8171f9207d44ad44b600a31c2cc6446c5f770b6ce6d13846b97e`; keysetSHA256`9eb7365e89f8877630f081a6267531be325098125584cf1a94c5dc4cf4b5466a`. All three endpoint files and the final export pass post-completion SHA readback; [exact proof](verified-readback.json). Checkpoints total9.558GB, excluding exports/mass/trace/source/build evidence. No originals are removed.

## Growth and what the cap means

Marginal key growth falls from0.446 to0.347 to0.267keys/node, but does not demonstrate saturation. Last-interval uncapped linear scenarios give827.0Mentries at3B and2.696B at10B. They are **local scenarios, not forecasts, bounds or evidence that this growth continues**. The same tangent intersects250M around0.839Bnodes; it does not establish the actual freeze point. Reaching the cap would freeze membership, not stop training. Later training refines retained keys; it cannot add newly encountered states.

At this endpoint,69.6% of retained entries are river keys. The final table contains106,543,248positive-average-mass rows and52,840,822zero-mass rows (**33.15%**), which use the existing uniform fallback. There are95,101,804rows with zero recorded traverser visits; that does not mean unused or invalid: opponent-sampled averaging can accumulate mass on opponent-only encounters. Keep visit/mass and lookup status separate.

For context, the earlier100BB500M pilot held113.0Mentries and trained its last interval at5.21Mnodes/s. This200BB pilot holds41.1% more entries, while traversal remains in the same broad rate range. Different seed, writer, source/toolchain and host/cache conditions prevent a causal depth or speedup claim. In particular, the historical100BB compatible-gzip389s save versus this parallel-gzip78s save does **not** establish a200BB speed advantage. [Historical100BB evidence](../nplayer-bb100/results.md).

## Held-out coverage, not a strength test

Four128-block identical-script lineups, fresh roots2026102240101–104, six seat permutations:3,072initial hand instances independently replay, plus3,072byte-identical reproductions. Independent sampling unit is the128deal blocks per script, not768independent hands. All lineups remain, with no payoff readout, checkpoint selection or strength gate. [CoverageCSV](coverage.csv) retains exact counts.

Focal missing-key lookups / focal decisions, by street:

| Script pair | Preflop | Flop | Turn | River |
|---|---|---|---|---|
| random | 8/1132 (0.7%) | 12/394 (3.0%) | 19/159 (11.9%) | 14/72 (19.4%) |
| check-call | 0/768 (0.0%) | 0/506 (0.0%) | 18/506 (3.6%) | 214/506 (42.3%) |
| tight-aggressive | 0/599 (0.0%) | 0/136 (0.0%) | 2/69 (2.9%) | 2/20 (10.0%) |
| pot-pressure | 0/706 (0.0%) | 1/180 (0.6%) | 3/84 (3.6%) | 3/43 (7.0%) |

The check-call river miss rate42.3% is substantial in this panel; TAG and pressure river denominators are only20and43decisions, so their percentages are fragile. Calling scripts reach many more rivers. A found key can still have zero average mass; these counters do not classify per-decision positive versus zero mass. Do not interpret found-share as the share of decisions using a well-trained nonuniform strategy.

Training audit `missing_decisions` counts first encounters/key creation before capacity, not the same held-out fallback statistic. Both discarded-key and discarded-visit counters are0, and `frozen_at` is null at every pilot endpoint. Neither these facts nor modest RAM establishes effective learning, profitable poker or v0.6.1 acceptance. We deliberately did not compute win rates from this cost/coverage panel.

## Qualification and complete costs

Real-K50 seed2026102240091 with a10K-entry cap exercises freezing:100K at1/16threads,100K→200K resume and fresh200K. Compressed checkpoints match across threads and uninterrupted/resumed paths; resumed/fresh exports and canonical keysets match. Both full-row audits pass. A deliberate200BB→100BB resume exits2 with the exact expected configuration error and writes no forbidden output; this is the sole expected nonzero stage, not a scientific failure. Four two-block script fixtures give48initial+48reproduced hands, all initial hands independently replayed. Native121library tests and the200BB arena example pass onhost; the existing table-dependent resource example remains explicitly ignored. [Qualification](qualification.json), [source/input/build/stage receipts](receipts.json).

| Component | Actual cost |
|---|---:|
| Launch→completion, Oct22 16:56:09–17:19:49UTC | 1,420.00s /23m40s |
| Build/native-library/arena-example stages | 62.57s |
| Three pilot training processes | 433.15s |
| Active traversal, included above | 102.28s |
| Saving, included above | 138.90s |
| Final average export process | 246.54s |
| Independent159.4M-row final audit | 252.50s |
| Final coverage native initial+repeat processes | 324.82s |
| Model/K50 loading reported within coverage | 276.59s |
| Actual native coverage play, both passes | 0.1261s |
| Final independent replay stages | 8.06s |
| Whole preparation/build/main child CPU | 6,528.50s /1h48m49s |

Components overlap where noted; residual is qualification/configuration/hash/supervision/startup/teardown work. Outer child CPU already includes descendant build/worker CPU; do not add inner totals again. Later publication and final readback are excluded. The JSON average loader is used here; its measured loading cost reinforces using the existing qualified binary inference path when a future200BB campaign is designed. That requires depth-specific qualification and its conversion/audit costs in the future quote, not another loader implementation in this pilot.

Sampled maximum worker-family RSS19.13GiB occurs in inference; training100M/200M/500M peaks4.64/7.30/13.31GiB, final export12.02GiB, streaming audit0.34GiB. CPU max74°C/Thermistor15 max86°C (during audit); no90/100°C stop. Minimum available RAM103.46GiB, NVMe207.12GiB/HDD393.16GiB free. Swap rises from378,445,824 to388,669,440bytes overall (**9.75MiB**); this is observed host usage, not proof which process caused it. Sampling is approximately2s, not an exact high-water bound. No wall/RSS/disk/swap cutoff or address-space limit was added. All locks release when supervisors exit; no full training follows automatically.

## Proposed next allocation, not launched

The measured pilot answers affordability at500M, not mature250M-entry behavior. A single fixed continuation to1B is a smaller next commitment than three10B lineages, and can reuse the verified500Mcheckpoint without repeating completed work. [Exact prospective arithmetic](next-allocation.json):

- Same seed, source recipe,250Mcap and parent SHA; final target1B, save/export/audit once. No extra seed or search/pruning change. Record actual freeze/retained membership/discards/coverage and post-freeze rate if observed.
- Four new128-block descriptive coverage panels at roots2026102240201–104, initial+reproduction+independent replay. No strength readout or outcome-driven continuation.
- Central calculation1,887s (~31m27s);2x nontraining/3x traversal reserve plus300s gives3,939s (~65m39s). Proposed allocation90minutes. Growth, load and I/O scale linearly to250M for planning only; mature costs/peak RAM may be nonlinear. No time or RSS kill is proposed.
- Stop at1B even if the table is not frozen; do not automatically add nodes. Then propose the fixed multi-lineage training/checkpoint/evaluation budget using measured mature costs. This proposal is not accepted by the owner's earlier approval of the completed500Mpilot.

For the eventual model family,3B/10B is a schedule to price, not a copied conclusion from100BB. Three independent200BB lineages must each satisfy unchanged v0.6.1 absolute-scripted-profit, own-earlier-checkpoint improvement and cyclic continuation noninferiority requirements, with fresh roots/counts/margins/multiplicity/pass-chance planning frozen before confirming hands. The pilot seed is one lineage, not three independent confirmations. Search remains deferred. No deployment, merge or release is authorized here.

## Reproducibility and preservation

Frozen execution735e3d3b5f32de5913f50686cb3a861c18734037; configSHA256`36c4e69cd780dcdcac61279ca3eceea2603230b7f4fe9182857efc88b2e57b28`; sourcebundleSHA256`40b8343cbd3225f48434cbd8f8685489c0a2a2558d537a695e01f122da488536`. [Provenance](provenance.json) pins source files, K50/binaries/managedPython, owner authorization, protected dependencies, all endpoint/export/proof hashes. Later commits publish evidence only. [Unchanged precomputed results](results.json), [costs/resource aggregates](costs.json), [endpointsCSV](endpoints.csv), [supplement](supplement.json). Offline publication:

```sh
python3.11 -m scripts.summarize_nplayer_bb200_feasibility   docs/reports/nplayer-bb200-feasibility/receipts.json   docs/reports/nplayer-bb200-feasibility/supplement.json   --out results/pr400-publication-fresh
```

The helper validates receipt hashes, endpoint/proof/count/return-code barriers and preserves the result bytes. It performs no poker execution or strength analysis. Nonfatal Git alternate-store depth warnings are preserved; source/bundle/checkout/build identity checks pass, and no other Git store was modified to suppress them. No scientific failure or failed setup was retried.

**Archive pending.** All original raw checkpoints/averages/mass files/traces/partials/builds/sources/resources remain at `/home/dberweger/nplayer-bb200-feasibility-20261022`. No copy/upload/Drive acceptance or deletion is claimed. The prior398source objects/managed environment and K50 files are read-only dependencies and must remain protected. Proposed future destinations `/research/PR-400-nplayer-bb200-feasibility/` and `gdrive:PR-400-nplayer-bb200-feasibility/` are not completed restore paths. Use the original root until policy-compliant verified archival. No new monitor or schedule was created; the passive completion observer has finished. PR400 is ready for review with a feasibility result, not a strength or release verdict.
