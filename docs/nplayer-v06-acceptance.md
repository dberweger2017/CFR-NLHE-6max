# Fresh v0.6 acceptance: three frozen 100 BB blueprints

Proposal [#366](https://github.com/dberweger2017/CFR-NLHE-6max/issues/366).
Owner approved the protocol/run on October20 before new confirming hands.
This tests the current ROADMAP acceptance criteria; it does not publish a release,
select a default, retrain, tune the models or overwrite earlier findings.

## Frozen candidates and questions

Use the existing all-street float64 averages at3B/10B, unpruned fast recipe,
K50, three players,100BB, hu-v1 menu and250M membership cap. Seeds:
2026101935003 (discovery),202610200601 and202610200602 (independent lineages).
Within each lineage membership is identical at3B/10B; across seeds it can differ.
[Input pins](../configs/research/nplayer-v06-acceptance-inputs.json) bind originals,
checkpoints, key sets, original-mass receipts and qualified binary derivatives.
No original input is modified. Original3B/10B pair needs a new conversion/full-row
bit audit; the other four derivatives reuse #361/#362 full-row audit proofs.

Thirty decisions form **one one-sided simultaneous95% Bonferroni family30**:

- Each10B singleton must profit against all eight fields (24 tests):
  random/random, check-call/check-call, TAG/TAG, pot-pressure/pot-pressure,
  own fixed3B+check-call, own fixed3B+pot-pressure,
  check-call+pot-pressure, random+TAG. Each adjusted lower bound must exceed0.
- Each10B must beat its own3B (three tests). Use half the difference of singleton
  returns in reciprocal10B-vs-two3B and3B-vs-two10B cases, matched by deal block:
  **mean oriented singleton contrast**, not pooled individual-player return.
  Each adjusted lower bound must exceed0.
- Cyclic003→601→602→003 (three tests): compare candidateA singleton with
  baselineA singleton against the **same two fixed3B_B opponents**. Paired
  singleton-return difference (without halving) must clear **−5BB/100**.
  This is PR357's continuation robustness comparison; it is not a10B-vs10B
  tournament or equality of independently trained models.

Acceptance requires all30 bounds. Unresolved bounds mean inconclusive, not proof
of a loss. Report ordinary two-sided95% intervals as descriptive supplements.
Per-seat, button-relative-position and street/lookup diagnostics are descriptive,
not additional pass gates. Do not average seeds or drop adverse panels for a pass.

## Prospective counts, pairing and power

The [fixed30-row sizing table](../configs/research/nplayer-v06-acceptance-sizing.json)
contains every count and historical mean/SE.36 cases total **2,635,776 initial
hand instances**, plus the same number of byte-identical reproductions.
Each independent unit is a six-permutation duplicate deal block, not six
independent hands; reproduction adds no independent information. Each direct
or cyclic pair shares its reserved root and block count. Other gates have
separate roots. Main roots20261020367001–030 and fixture roots20261020367901–930
are reserved here; implementation assigns roots deterministically in sizing-row
order. No root is reused from PR355/357/361/362. Fixed counts do not change
based on observed outcomes.

Normal-approximation sizing discounts each historical effect to75%, retains its
8192-block variance, targets per-test failure0.1/30 and rounds to1024 blocks.
Use n=8192*[SE8192*(z(1−.05/30)+z(1−.1/30))/(.75*mean−margin)]².
Final lower bounds use t(1−.05/30,n−1). Minimum count1024. Weakest pressure panel
(seed602 trained-pressure) gets45056 blocks; weakest cyclic601→602 gets60416.
Conditional union-bound pass probability is about96.14% under75% effects/same
variance, about99.995% at historical means; halving effects gives poor joint
power (~2.6% under an illustrative independence assumption). Historical effects
and variance are estimated: these are sensitivity calculations, not a guarantee.
[NIST sample-size planning](https://itl.nist.gov/div898/handbook/prc/section2/prc222.htm)
and [Bonferroni](https://www.itl.nist.gov/div898/handbook/prc/section4/prc473.htm).

All initial traces independently replay through the pinned engine, every
reproduction matches bytes, model/schema/mass/count/zero-sum receipts reconcile,
and all stage return codes must be0 before the **global payoff readout**.
No interim strength readout, checkpoint selection, additional hands or automatic
scientific retry. Qualification uses only a small fixture, never final roots.

## Cost, execution and preservation

Owner accepted **2–3h bb128 occupancy**, about3–5h to reviewed report including
45–90min qualification and20–40min reporting. Cost forecast is a manual planning
allocation, not an elapsed kill guard. Eight evaluation/replay workers, two
resident policies (~28GiB). Loading, conversion/auditing, restoration and staging
are reported separately from play. No new resident-model cache implementation.

Each own-seed phase loads its pair once. Six cyclic singleton cases load two
models each (12 loads instead of a nine-load all-cycle cache traversal); this
bounds NVMe use to two working models plus one phase's traces. Verified new
copies are staged into this PR's fresh HDD namespace between phases. Cross
restores reuse those same staged derivatives, verify bytes and atomically keep
accessible input paths after returning them to storage. No repeated copies are
retained when an identical verified owned cache file already exists. Existing
PR350/355/357/361/362 inputs stay read-only. Never flush global caches. Ordinary
cache/order/HDD staging effects are reported. No Drive acceptance claim until
an archive receipt exists; all raw outputs, failures and partials remain retained.

The controller uses its own mutex and the normal bb128 compute mutex, respects
owner STOP and terminates only its process groups on failure. Automatic resource
stops: **CPU90°C, Thermistor15 100°C**, or missing/nonfinite required sensors.
No elapsed/RSS/disk/swap stop; inspect disk, RAM and swap manually. No changes
to other jobs, machines, BIOS, drivers or fans. Scientific/resource/correctness
failure is terminal and preserves evidence. No default, merge or release action.

End-to-end qualification covers all36 shapes, three distinct fixture keysets,
full binary row audits, original-mass metadata, realK50 engine parity, exact
reproduction/independent replay, barriers, source/config/input mutation refusal,
staging/restore verification and partial-copy refusal before any final hand.

## Interpretation alongside older evidence

Fresh acceptance cannot erase **PR357's failed relative scripted safeguard**:
random and random+TAG regressed on both fresh seeds, and five−50BB/100 lower
bounds were unresolved. Those remain failed/inconclusive under that protocol.
This study asks positive *absolute* profits, own-checkpoint gain and the declared
cyclic noninferiority on fresh deals. Passing does not establish Nash convergence,
universal strength, best seed, human/external strength or search effectiveness.
Native river implementation is the separate next engineering task; additional
node scaling/pruning schedules/loader redesign are excluded.
