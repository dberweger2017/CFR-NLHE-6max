# Proposed three-lineage 200 BB model campaign and acceptance

[Research proposal403](https://github.com/dberweger2017/CFR-NLHE-6max/issues/403), following merged [PR402](https://github.com/dberweger2017/CFR-NLHE-6max/pull/402). **Planning only: no new main run, training-cost pilot or confirming hand has started.** The owner supports moving to a fixed model campaign; this document makes the complete proposed allocation reviewable before launch.

The recommended allocation is **18 hours of planning allowance**, with a central scenario of **7h51m** and component reserves totaling **17h33m**. This is not an8–12-hour completion promise or an elapsed-time kill guard. Runtime, memory and trace sizes remain conditional scenarios, not guarantees. Cleanup, movement, staging and uploads belong to the owner's vacuum-cleaner agent; this campaign agent performs none of them.

## Frozen candidate family

Continue existing seed `2026102240001` from PR402's1,000,008,098-node checkpoint, SHA256 `55d89c553ba1756eac1af117847b30e8b18e4f901afba942ee5a906bc00249ad`. Add two fresh independent seeds `2026102261001` and `2026102261002`. Each lineage has exactly **3B and10B** cumulative-node endpoints, allowing whole-iteration overshoot. Retain all six checkpoints and averages. This is one candidate family, not checkpoint selection.

Keep three players/200BB,50/100blinds, K50, current menu/schema, unpruned fast mode,16threads, eight roots/seat, all-street float64 opponent-sampled averages, parallel gzip and250M freeze threshold. Native freezing happens after a whole iteration; entry count can exceed250M slightly. Keep membership/keyset identical within each3B→10B continuation. Cross-seed sets may differ. No search/pruning/menu/abstraction/default/release change, additional node endpoint or automatic extension/retry.

250M is a bounded candidate, not established capacity sufficiency. At1B,27.3% of reached check-call river lookups miss, and33.4% of all stored rows have zero average mass. Those are different quantities. Further fixed-membership training can refine retained states, but cannot insert missing keys. Acceptance, rather than affordability or a post-hoc coverage threshold, decides whether this family qualifies.

## Execution phases and proof barriers

1. **Qualification, not another cost pilot.** Reuse exact qualified native sources/binaries only after source/hash/receipt checks. Exercise real200BB game identity, legal play, binary conversion/readback, positive/zero/missing lookup handling, float64 action/probability parity, seed/config mutation refusal, native-compatible cap overshoot, source/endpoint failure propagation and one-use/duplicate refusal. Tiny correctness fixtures have separate seeds/roots and do not size costs or select a policy.
2. **Fixed model training.** Continue the existing1B parent; train two fresh lineages. Save/export/audit each3B and10B endpoint. Check seed/recipe/source/count/hash, full-row checkpoint/export equivalence and exact within-lineage canonical membership. No model acceptance readout or sample selection during training.
3. **Inference qualification.** Use the existing binary format, with source/checkpoint/schema/dtype/byte-order/mass pins and full-row bit/action/probability audits for all six derivatives. Do not infer200BB correctness from100BB alone. Do not add a loader optimization or alternate player. Binary conversion and its audit are separate priced work, not hidden in training cost.
4. **Fresh fixed acceptance.** Execute the declared counts below with eight arena workers sharing read-only loaded policy tables; lineages sequential. Every initial hand independently replays. Reproduction must match bytes. Freeze the six model hashes before confirming hands. No global payoff readout until all lineages, source/input/mass/count/zero-sum and replay/reproduction barriers pass.
5. **Readout and closeout.** Publish every gate, ordinary descriptive intervals, physical seats/positions, street/lookup/fallback coverage, tail behavior, complete cost/RAM/thermal/source/proof/failure records. Retain adverse and inconclusive results. Owner decides release and any next work; no automatic extra hands, tuning or release.

Before main launch, a committed, source-pinned controller must implement these phases and pass end-to-end qualification with all36case shapes, independent reproduction/replay and deliberate mutation/failure fixtures. This PR initially supplies the fixed proposal and reproducible pricing/sizing, not a launch-ready controller. No runtime plan may silently inherit a past campaign's hardcoded100BB source, seed, count or staging authority.

## Acceptance question and fixed counts

Use the established [v0.6 acceptance definitions](nplayer-v06-acceptance.md) at200BB. One **one-sided simultaneous95% Bonferroni family of30 Student-t lower bounds**:

- Each10B must profit against all eight fields (24 tests):random/random,check-call/check-call,TAG/TAG,pot-pressure/pot-pressure,own3B+check-call,own3B+pot-pressure,check-call+pot-pressure,random+TAG. Lower bounds strictly>0.
- Each10B must beat its own3B (three tests):half the paired difference of reciprocal10B-vs-two3B and3B-vs-two10B singleton returns. This is the mean oriented singleton contrast, not pooled individual-player return. Lower bounds strictly>0.
- Cyclicexisting→fresh1→fresh2→existing (three tests):candidateA-minus-baselineA singleton return against the **same two fixed3B_B opponents**, without halving. Lower bounds strictly>−5BB/100. This is continuation robustness, not a10B-vs10B tournament.

Require all30. Unresolved bounds are inconclusive, not proof of loss; they do not qualify the family. Keep all eight fields and earlier adverse evidence. Do not average seeds or drop a panel to pass.

The [exact30-row table](../configs/research/nplayer-bb200-model-campaign-proposal.json) fixes **4× each PR367 prospectively declared block count**, mapped before any200BBoutcome:historical003→existing,601→fresh1,602→fresh2. Counts emphasize historically weak pressure and cyclic tests; they do not repeat8,192blocks uniformly. These are conservative planning allocations based on100BB evidence, not measured200BB requirements or predicted effects.

Totals: **36cases,1,757,184case-blocks,10,543,104initial hand instances and10,543,104reproductions**. An independent unit is a six-seat-permutation duplicate deal block; seat permutations and reproduction add no independent information. Reciprocal and cyclic comparison arms share their reserved roots/counts. Reserve confirming roots `20261022620001`–`20261022620030` in sizing-row order; qualification roots `20261022629901`–`20261022629930`. No root is reused from PR400/402 or a prior strength study.

## Prospective power scenarios, not200BB assurance

The sizing JSON names all source statistics explicitly as **historical**. Planning uses a normal approximation; final intervals use Student-t and observed independent block variance. For planned countn, assumed blockSD multiplierk gives `SE = historical_SE8192 × k × sqrt(8192/n)`; approximate power is `Phi((assumed_mean−margin)/SE−z(1−.05/30))`.

| Conditional scenario | Weakest per-gate power | Family union-bound lower estimate | Illustrative independent all-pass |
|---|---:|---:|---:|
| Historical100BB means, sameSD | >99.99% | >99.99% | >99.99% |
|75% historical means, doubleSD |99.67% |96.14% |96.21% |
|50% historical means, doubleSD |79.77% |0% (uninformative) |2.56% |
|75% script means, neutral own/cyclic continuation, doubleSD |0.17% |0% (uninformative) |<0.000001% |

DoublingSD and quadrupling counts approximately restore PR367's conditional planning power. That algebra **does not establish200BB effects, variance or pass chances**. Historical effects are estimated, tails may be worse, and gate dependence makes the product illustrative. The neutral-continuation scenario correctly cannot satisfy improvement gates. No200BBpayoff was read to choose counts, and no unfavorable outcome triggers an extension. This is an acceptance attempt with meaningful uncertainty, not a guarantee of release.

## Full proposed allocation

[Reproducible arithmetic and input hashes](../configs/research/nplayer-bb200-model-campaign-proposal.json):

| Component | Central minutes | Reserved minutes |
|---|---:|---:|
| Models:training,saves,six exports,checkpoint audits |229.62 |574.80 |
| Six binary conversions |33.51 |67.02 |
| Six full-row binary parity audits |34.12 |68.24 |
| Qualification and fixed fixtures |15.00 |30.00 |
| Acceptance native processes,including reproduction |57.05 |124.19 |
| Independent replay and reconciliation |52.39 |104.78 |
| Global barrier/readout |19.32 |38.64 |
| Analysis/report |30.00 |45.00 |
| **Total** |**471.01 (7h51m)** |**1,052.67 (17h33m)** |

Round the complete reserve to a proposed **18-hour allocation**. Model-only3h50m/9h35m is the first component, not the whole campaign.

Model arithmetic is PR402's4.355M added-node/s scenario, explicit1.61× checkpoint-byte scaling for future capped resume load/hash residuals, and six measured save/export/checkpoint-audit costs. Binary conversion/audit each use six times the slowest corresponding PR367 observation, then2×reserve. Native acceptance assumes the same18loads at1.25× the historical load cost;4×counts and2× per-hand play cost. Reserve doubles loads/other overhead and triples play. Replay assumes4×counts,2× depth/work cost and2×reserve; readout scales4× with2×reserve. Qualification/reporting are explicit allowances.

These are **conditional extrapolations**, not measured200BBbinary/acceptance timings. Ordinary host caches/order/storage affect them; do not flush caches. There is no separate training-cost pilot, native latency benchmark or strength screening run hidden in the quote. No release packaging/publication is included. Owner-owned cleanup/staging/upload time is outside this science allocation and must not be promised as a completion time.

Binary derivatives reduce pair RAM/loads but add one-time work and storage. Historical conversion/audit amortizes only after repeated evaluation; a JSON-only one-off can be cheaper while using much more RAM. The recommended proposal retains the existing binary acceptance pipeline to minimize new correctness plumbing and keep paired-model RAM near the previously measured28GiB class. No format race or additional benchmarking is proposed; any change to this chosen path must update the quote before launch.

## Storage and resource ownership

The six checkpoint/average pairs project83.88GB; six historical-size binary derivatives add84.89GB; six zero-mass-key files about8.02GB. At an explicit8KiB per initial/reproduced hand, raw traces add172.74GB. Combined science output scenario is **325.52GiB**; add30GiBheadroom and request **360GiB free NVMe** before admission. This is not a guaranteed trace-size upper bound. All originals/inputs are additional retained files, not candidates for this agent to delete.

The owner's vacuum-cleaner agent handles cleanup and any proposed staging/upload. This campaign agent will not move, remove or upload files. If an accessible staging plan replaces the all-NVMe scenario, it must preserve source paths/hash identity, all proofs and global readout access; price its I/O explicitly before promising a finish. Do not silently reuse PR367's staging permissions. Existing PR400/402checkpoint/build/environment and PR398Git/environment/K50 dependencies remain protected and readable at their pinned paths.

Before launch, inspect actual disk/RAM/swap and check the normal bb128 mutex plus an owned campaign mutex. Plan training16threads/evaluation8workers, no other machine. Automatic resource stops remain only **CPU90°C, Thermistor15 100°C, or missing/nonfinite required sensors**. OwnerSTOP, mutex and correctness failures are terminal. No elapsed/RSS/disk/swap/address-space cutoff is added; the18h allocation is planning, not a timer that discards a valid checkpoint. Manual resource checks continue. No fan/driver/BIOS/environment/cache-tool changes or automatic scientific retry.

## Admission and remaining work

The owner has accepted the direction and fixed model endpoints. **The complete18h allocation,30-row confirming counts and storage preparation remain proposed for review**, not silently authorized by the old model-only estimate. Main science also requires the completed, source-pinned controller and successful qualification described above. No new run is launched by generating this proposal.

Reproduce pricing/counts without any host access or poker execution:

```sh
python3.11 -m scripts.plan_nplayer_bb200_model_campaign \
  --out planning/campaign-proposal-fresh.json
```

The generator reads only committed PR402 and PR367 metadata, pins their SHA256s, and refuses to overwrite its output. No model, raw trace or binary payload is added to Git. Results from PR400/402 remain feasibility evidence, not200BBacceptance.
