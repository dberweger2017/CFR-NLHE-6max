# Combined five/six-player 100 BB M4 feasibility

**Completed:** [results, costs and limitations](reports/nplayer-five-six-feasibility/results.md). Both sizes pass; main5m59s, qualification3m18s, peak3.06GiB, nominal thermal state/no swap growth. Execution source37cf758f remains frozen; later changes clarify reports only.

Proposal [407](https://github.com/dberweger2017/CFR-NLHE-6max/issues/407), following merged [406](https://github.com/dberweger2017/CFR-NLHE-6max/pull/406). The owner recommends continuing the four-to-six-player sprint. This task tests the existing five/six-player train/resume/export/play workflow and early cost/capacity. No strength verdict, release/default change or long continuation.

## Fixed design

Run five players then six, sequentially on the AC-powered 16 GiB M4. One fresh main seed each: **2026102305001 / 2026102306001**. Each has cumulative **25M then 50M nodes**, **20M-key freeze threshold** allowing whole-iteration overshoot; unpruned fast mode, 10 threads, eight roots per seat, 100 BB, 50/100 blinds, current K50/v1-menu and all-street float64 opponent-sampled averages, parallel gzip. All native game/key/regret/policy code is unchanged. No matched player-count causal claim or mature-table forecast.

Per size, qualification uses independent fixture seeds2026102305091/6091 and cost-only seeds2026102305092/6092. Independently verify128 engine fixtures including all-ins/unequal stacks; 100K/200K checkpoints with10K cap must match bytes under1/10 threads and fresh/resume. Full-row export audits, 30 self-play hands per fixture/cost model plus identical reproduction and independent engine replay. Every button is represented. At each main endpoint save/validate/export/audit all rows and play **60 initial plus60 reproduced hands** with one independently seeded policy per seat sharing one read-only table. Those hands support correctness/coverage only; no aggregate return readout.

Trace qualification bases2026102305081/6081 (engine, then fixture-a/b/cost +1/+2/+3); main bases2026102305011/6011 (25M/50M +0/+1). No prior experiment roots reused. No additional seed, endpoint, sample or automatic scientific retry. Every failure/partial is retained and terminal for that attempt.

## Admission and execution

One combined **3600-second planning allocation**, including qualification, both main jobs and600seconds reserved reporting, not a runtime kill. Before main, publish a combined quote. For each size use the slower of its1M qualification rate and PR406's final interval scaled by players/4. For each endpoint use the larger of PR406's20M-row tool cost scaled by players/4 and the new qualification cost: export/audit scaled by retained rows, play/replay scaled by2 to account for30→60 hands. Fixed K50/model startup is never multiplied by row count. Add the greater measured/extrapolated non-traversal train residual, double main work for reserve, then add qualification elapsed and600seconds once. Historical/full-work paths and SHA256 are bound. This is a conservative scenario, not an upper bound or measured five/six-player mature cost.

Require successful qualification for both sizes, identical frozen source, child/config/binary/K50/Python/quote bindings, combined reserve<=3600, and available RAM >= the largest sequential forecast plus1GiB. Forecast is qualification sampled family peak plus200bytes per additional key up to20M. Recheck available memory before launch. If admission fails, report the quote and stop; do not resize or start only a favorable subset.

The M4 normal research lock and owned five/six lock cover qualification/main. Apple serious/critical/missing/unknown thermal state or owner STOP stops owned children; no invented Celsius reading. Root STOP is checked during both sizes, including native stages. No automatic elapsed/RSS/disk/swap cutoff; inspect these manually. Protect existing PR317/371/404/406 environments, inputs and outputs. Read-only K50 and managed Python; new isolated source/build/output roots. No OS/fan/driver/cache changes, cleanup, staging, uploads, new schedules or bb128 compute.

## Evidence and interpretation

Keep per-street pre-freeze growth/visits and played missingness separately from table-wide zero-average-mass rows; the reused generic policy-play tool does not distinguish reached positive-mass from zero-mass rows, and no new instrumentation is claimed; report freeze/discard/censored growth. Capture active traversal, save/load/hash/wall, exports/audits/play/replay costs, CPU, sampled family RAM, swap/pressure/storage and thermal states, source/config/build/K50/binary/engine/proof pins. Full-row audits and all initial hands must pass replay and identical reproduction before a complete result. Small correctness samples cannot establish coverage adequacy or playing strength; table mass is not played fallback frequency. Very short traversal windows are not steady-state throughput. Cap censoring is not natural saturation.

Raw evidence remains in the owned M4 root. Only compact reports/CSV/JSON enter Git. Archival and Drive acceptance are owner-managed pending; originals retained, no deletion or claimed acceptance. The [four-player campaign draft](nplayer-four-player-campaign-plan.md) is preparation only; PR404 must release bb128 before any separate authorized campaign.
