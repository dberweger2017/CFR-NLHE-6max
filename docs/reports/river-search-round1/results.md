# v0.6 river search, round 1: partial engineering qualification

[#376](https://github.com/dberweger2017/CFR-NLHE-6max/pull/376) follows [#375](../live-river-pilot/results.md), which solved legal first-river decisions on the frozen v0.6 10B (seed 2026101935003) but covered only three of six hand-picked roots, at 1.9 s each for an 801-node tree. This round measured whether river search can be made practical on a **representative** panel. It is a **partial engineering qualification, not deployment readiness**:

- **Deferred:** stages 4 (one loaded model serving many threads) and 5 (retained-strategy reuse on later river actions).
- **Not run:** no strength match, training or default change.

**In short:**

- **Real river decisions are almost all heads-up.** 98.7% of first river decisions have two live players, so #375's heads-up scope loses about 1%.
- **A capped search menu makes every eligible decision solvable and fast.** It covers 5,580 / 5,580 held-out decisions, against about 30% for the full menu. With DCFR stopping at the quality target, the median decision takes 0.28 s and p95 0.98 s.
- **DCFR (α 1.5, β 0, γ 2) converges about 4× faster than linear CFR** at the same cost per sweep. On the dev panel it reaches the target on 300/300 roots, against linear CFR's 273/300.
- **Three gates fail, and they are reported separately:**
  - **Capped-game quality:** 598 / 600 held-out roots reach the target, so the every-decision gate fails.
  - **Belief projection:** 17 of 40 exact-joint controls exceed the 0.05 BB tolerance. The excess grows with the pot, at about 0.6% of it.
  - **Full menu, reported separately:** the deployed policy (capped solution, blueprint after an omitted raise) is half as exploitable as the blueprint alone at the median, but more exploitable on 24% of decisions.

Lower exploitability in the capped, projected game does not show that the complete decision improved. Before any strength study, round 2 should address full-menu quality and the belief law.

## Gates (held-out, frozen configuration)

The [configuration](frozen-config.json) (SHA256 `2ac3d6f0…`) was set from development results and committed before any held-out root was solved. Nothing was tuned after the held-out run.

| Gate | Requirement | Held-out result | Verdict |
|---|---|---|---|
| Coverage | at least 90% of eligible heads-up decisions supported | 5,580 / 5,580 (95% CI 99.93–100%) | **pass** |
| Latency | median at most 0.5 s, p95 at most 2 s | median 0.278 s, p95 0.979 s (mean 0.363 s, max 1.979 s) | **pass** |
| Capped-game quality | each player's best-response gain at most min(1% of pot, 0.1 BB), every decision | 598 / 600 (99.7%) | **fail** |
| Beliefs | approximate-belief gain at most 0.05 BB above a qualified exact-joint reference, every control | 23 / 40 within; all 40 references qualified | **fail** |

Latency covers the complete decision, quality checks included, measured with six concurrent workers on one i7-10700KF host. The omitted-raise evaluation is offline and excluded from it.

## The three errors

**1. Solver error in the declared game: nearly solved.**
- **Held-out:** DCFR met the target on 598 / 600 held-out roots, at a median of 256 sweeps (p90 512).
- **The two misses:** both pots are large enough that the 0.1 BB cap binds, and the larger player's gain was about 0.20 BB after 2,048 sweeps.

**2. Action-menu restriction and off-tree fallback: the largest error.** The capped solution and the blueprint after an omitted raise were measured in the full production-menu game, against the blueprint alone in the same game (600 held-out roots):

| | Median | p90 | p95 |
|---|---|---|---|
| Deployed policy, max player gain (BB) | 0.97 | 4.08 | 6.20 |
| Blueprint alone (BB) | 1.97 | 7.55 | 13.02 |
| Paired improvement (BB; p10 / p50 / p90) | −0.65 / +0.69 / +4.75 | | |

- **Only 3 / 600 deployed decisions meet the quality target in the full game.**
- **On 143 / 600 the deployed policy is more exploitable than the blueprint.**
- **The solver isn't the cause:** on the dev panel, linear CFR and DCFR give nearly identical full-menu numbers.
- **Not separated:** this round does not attribute the error between the omitted options and the blueprint's own off-tree play. Round 2 should decompose it.

**3. Belief projection: material, and it grows with the pot.**
- **What was compared:** the solver's law is a product projection of the three-seat action-likelihood law. The exact-joint controls solve the same capped tree under the original joint law; the references reach at most 0.01 BB.
- **References:** all 40 held-out references qualified (at most 0.0098 BB, median 1,024 sweeps, up to 8,192).
- **Effect:** the deployed strategy's gain rises from a median of 0.047 BB in the projected game to 0.052 BB in the exact one; at the p90, from 0.094 to 0.159 BB.

| Pot | Controls | Within 0.05 BB | Median excess | Median projection TV |
|---|---|---|---|---|
| under 5 BB | 10 | 10 | 0.019 BB | 1.7% |
| 5–15 BB | 23 | 13 | 0.048 BB | 2.1% |
| 15–40 BB | 5 | 0 | 0.150 BB | 3.8% |
| 40 BB and over | 2 | 0 | 0.251 BB | 3.0% |

The excess correlates with the pot (r = 0.87) more than with the projection's total variation (r = 0.65). It is about 0.5–0.8% of the pot throughout, so a fixed 0.05 BB tolerance fails every larger pot.

## What was run

All measurements ran on bb128 (16 threads; stops at CPU 90 °C and VRM 100 °C, with peaks of 72 °C and 95 °C). Builds and small fixture tests ran on an M1. In total the round used about 70 minutes of bb128 time, within the 3–5 hour budget.

### Stage 1: representative panels

- **Self-play:** three fresh 10,000-hand traces with all three seats on the frozen 10B, from the native `nplayer_policy play` harness (seed 2026102101 for dev; 2026102102 and 2026102103 for held-out).
- **Counting and classification:** every river decision was counted by type, and every eligible decision was classified without solving (support, rejection reasons, tree size, projection).
- **Panels:** a fixed seeded draw of 300 per trace, giving the dev panel and a 600-root held-out panel.

| Per 10,000 hands | Range across traces |
|---|---|
| Hands reaching a river decision | 2,745–2,898 |
| First decisions, heads-up (eligible) | 2,719–2,861 |
| First decisions, three-way | 26–37 |
| Later decisions, heads-up | 3,754–3,948 (+104–137 facing a river shove) |

- **Under #375's limits only 29–32% of eligible decisions were supported.** Almost every rejection was the 2,000,000 strategy-cell cap; 7% also exceeded 4,096 nodes.
- **Full-menu trees are bounded but large:** median 2,235–2,553 nodes, maximum 4,491. Typical rivers have small pots (median 8 BB, 96 BB behind), where re-raise ladders multiply.
- **No zero modeled reach and no belief failure occurred in self-play.** Off-model lines, from humans or agents, will exercise those paths.
- **Model coverage:** 99.97% of range lookups hit positive-mass rows.

### Stage 2: capped search menus (dev)

The search menu `pot-jam-cap{2,3}-v1` keeps the production menu at the root; below it, it keeps fold, check or call, the pot-size raise and the production all-in, with at most 2 or 3 river raises including the root's.

- **Tree size:** median 21 nodes (cap 2) and 33 (cap 3).
- **Coverage:** both caps support all 2,773 dev decisions.
- **Cap 3 was chosen:** its omitted-raise vulnerability was lower (median paired improvement over the blueprint +0.66 against +0.11 BB at 256 linear sweeps), for about 0.1 s more.

### Stage 3: profiling, fold leaves and DCFR (dev)

- **Profile:** at 256 sweeps the per-sweep update (finiteness checks, regret matching, averaging) is the largest phase, about 35% on both the 801-node fixture and the capped dev roots. Showdown leaves, traversal and fold leaves follow. Range construction (about 25 ms) and quality checks are small. Loading and JSON were not material.
- **Fold leaves** skip the showdown rank pass: 62 identical requests on the old and new binaries gave bit-identical distributions and quality, with solving 1.22× faster (p10–p90 1.21–1.26×).
- **DCFR against linear CFR** on 300 dev roots, with the same roots, menu, beliefs and simultaneous updates:

| | Reach target by 2,048 sweeps | Sweeps to target (p50 / p90) | Seconds to target including checks (p50 / p90 / p95) | Median max gain at 1,024 sweeps |
|---|---|---|---|---|
| Linear CFR | 273 / 300 | 1,024 / 2,048 | 0.85 / 1.76 / 2.20 | 0.042 BB |
| DCFR | 300 / 300 | 256 / 512 | 0.25 / 0.59 / 0.98 | 0.010 BB |

DCFR uses the published fixed parameters and averaging rule inside the existing simultaneous-update solver. Its gain here is measured on these roots only, not assumed in general.

### Stage 6: exact-joint belief controls

A dev pilot on six roots set the frozen budget. Two references missed 0.01 BB at 4,096 sweeps, so the budget became 8,192 sweeps; the control count was set to 40, the first 20 of each held-out panel. Each control solves the root as deployed and a DCFR reference under the joint law (dense pairwise leaves, parallel), then measures the deployed strategy in the exact game.

**The control run was interrupted at 10:29 by a plumbing fault**:
- **The fault:** an earlier launch script had exited early without stopping its heat guard. That guard, still set to stricter limits than this round's (VRM 95 °C), fired as the 16-thread controls reached 95 °C. Its process pattern also matched the driver's command line, so it killed the driver and its worker.
- **Recovery:** the 30 completed controls, the frozen rule's first 30, were kept, and the remaining 10 were run unchanged with a resume option that checks that prefix.
- **Future scripts** stop guards on any exit and match the worker by exact process name.

### Stage 7: held-out assessment

The frozen configuration was run once:
- **Coverage:** classification of all 5,580 eligible held-out decisions under the capped menu.
- **Latency, quality and full-menu evaluation:** the 600 panel roots, stopping at the target.

The results are in the gate table and the three error sections above.

## Round 2

1. **Full-menu quality first.** Decompose the deployed vulnerability into the omitted options against the blueprint's off-tree play. Then test re-solving after an off-tree action (with consistent belief updates) or keeping the minimum raise in opponents' responses.
2. **The belief law.** Solve under the joint law directly where it is affordable, or scale the tolerance question with the pot; the error is about 0.6% of the pot. The dense joint leaf costs O(n²) and needs its own speed work.
3. **The per-sweep update** is the next solver cost to reduce, once the search game itself is worth deploying.
4. **Stages 4–5,** concurrency and reuse, come after full-menu quality justifies them.

Any later whole-hand pilot must measure actual cost and paired-return variance before choosing strength-study sample counts.

## Reproduce

```sh
cargo build --release --example river_live --example nplayer_policy --manifest-path native/hu20-trainer/Cargo.toml
# stage 1: self-play trace, then classification and panel
native/hu20-trainer/target/release/examples/nplayer_policy play K50 10000 SEED TRACE MODEL SHA MODEL SHA MODEL SHA
python -m scripts.river_search_panel TRACE --role dev --out OUT --binary .../river_live --k50 K50 --model MODEL --sha256 SHA --panel-seed N --panel-size 300
# stages 2, 3, 6 and 7
python -m scripts.river_search_stage2 DEV_PANEL_DIR --out OUT --binary ... --k50 ... --model ... --sha256 ...
python -m scripts.river_search_stage3 DEV_PANEL_DIR --fixture FIXTURE --out OUT --binary ... --before-binary ... --k50 ... --model ... --sha256 ...
python -m scripts.river_search_stage67 controls --config docs/reports/river-search-round1/frozen-config.json --stage1 STAGE1 --out OUT ...
python -m scripts.river_search_stage67 heldout --config docs/reports/river-search-round1/frozen-config.json --stage1 STAGE1 --out OUT ...
```

The compact summaries of every stage are in this folder. The traces, every per-decision record, launch scripts and logs, temperatures and the interrupted control file are archived as `PR-376-river-search-round1.zip` (97 files, about 95 MB unpacked); see [RESULTS_INDEX](../../../RESULTS_INDEX.md).
