# Three-player variable stacks: engineering qualifies; pilot not launched

[PR441](https://github.com/dberweger2017/CFR-NLHE-6max/pull/441) /
[proposal440](https://github.com/dberweger2017/CFR-NLHE-6max/issues/440) /
[protocol](../../nplayer-variable-stack-feasibility.md).

One research policy can now represent the declared27 ordered stack tuples from
{20,50,100}BB, with independently uniform stacks and button at each new hand.
**The small guarded qualification passes. The5M→25M→100M pilot has not started.**
This is a three-depth grid, not arbitrary20–100 BB interpolation or a release.

## What changed and why

The new stack-owner schema retains the live-order K50/history summary and adds
button-relative initial/current stacks, wagers, contributions, fold flags,
actor/blinds and exact legal-menu targets. It includes folded contributors,
which matter for side pots. This is a conservative correctness baseline;
fragmentation and affordability remain empirical questions.

One strict cash-identity parser binds the mixture through checkpoint, resume,
export and inference. Fixed-only consumers now return an explicit error for a
mixture, rather than choose a representative stack. The existing fixed formats,
key bytes, sampler sequences and defaults remain unchanged. No mature model is
relabeled, no opponent mixture/exploration or regret estimator is changed, and
no search or bb128 science is included.

An opt-in immutable callback observes the existing per-root deltas before the
same deterministic merge. It records aggregate nonzero regrets, update
opportunities, opponent-only averaging and frozen-table declines without
consuming RNG or changing training values. The27-tuple chance law is sampled
directly; no new importance-weight correction is necessary.

## Qualification evidence

[Verification and summaries](qualification.json), [complete costs](costs.json),
[retention/provenance](provenance.json), [review](review.json).
Source `4f3a9183`; frozen baseline `2474309d`.

- M1: 160 library tests pass in213.08s; all native examples compile including
  their test configurations. Four pilot-guard tests pass without real training.
- M4: all 16 guarded stages return0; complete81.04s including targeted tests,
  source/baseline builds, fixture work and independent proofs. Nominal thermals;
  sampled family peak1,412,792,320bytes(1.316GiB), swap1MiB before/after.
- New identity/key fixtures cover undeclared distribution/depth refusal, hidden-
  world invariance, stack ownership, rotation, folded contributions and menu
  amounts. Golden stack-owner key5c806ad4cb68fd3515ec4360cb6a3997 locks framing.
  Existing expected side-pot/refund/odd-chip/reopening tests remain unchanged.
- Twelve tiny training iterations reach105,801 nodes and62,957 rows; the100k
  fixture cap does not bind. Two-thread continuous training matches a saved/
  resumed one-thread continuation byte for byte, also checking observer parity.
- Full-row float64 average/export/binary parity passes for all62,957 rows.
  Mixture inference accepts all 27 configurations and rejects an undeclared90BB
  stack. Actual global native worker count is fixed at2.
- All 81 played hands cover27 tuples×3buttons, with five settled multi-pot hands;
  initial and repeat traces are byte-identical. Every initial AND repeated hand
  passes the pinned independent engine's state/action/settlement replay.
- Separate old/new100k-node fixed fixtures produce byte-identical checkpoints
  AND average exports for both history and live-order schemas. They are legacy
  behavior checks, not mixed-stack trained controls.

A separate receipt hashes the qualified executable AFTER qualification and
binds its original completion/source manifest. Its mtime precedes completion;
that is supporting provenance, not a claim it was hashed during execution.
Original receipts remain unchanged. The pilot launcher checks this binding,
qualified config/source hashes, current Python/thermal, owner receipt, locks,
headroom and all six replay barriers before marking completion.

## Useful early observations, with strict limits

The fixed324-hand synthetic observation panel contains3,074 decisions.
It yields2,094 legacy live-order keys and2,962 stack-owner keys: about41% more.
Of the old keys,559 split under the ownership-preserving representation. No
stack-owner key merges distinct exact-history keys ON THIS PANEL. This is an
important warning against assuming the earlier compact-table savings transfer.
It is not proof of zero compression in training or a reason to change the schema
after seeing a strength result—there is no strength result here.

The checkpoint is deliberately tiny. Only32/3,074 common-panel observations
have positive average mass;9 are zero-mass and3,033 missing. Its separate
81-hand self-play panel has595 missing,4 zero-mass and11 positive-mass lookups.
These are fixture support counts, not population coverage estimates.
[All tuple/seat/street common-panel cells](common-panel.csv) retain sparse and
zero-denominator strata, all-in exposure and provisional contribution layers.

Of2,962 predetermined watch keys,2,953 are never reached by a traverser update;
nine receive one nonzero root-aggregated regret contribution, none repeats.
Across retained rows,43,444/62,957 have no traverser visit yet. This does NOT
establish admission waste or failure: opponent averaging has a distinct role,
the fixture runs only 12 iterations, and zero final regrets can hide cancellation.
[Learning cells](learning-cells.csv) distinguish these quantities. Full raw watch
records, including never-reached keys, remain ordinary retained evidence.

The larger pilot should measure whether learning becomes repeated/useful within
each configuration, and whether growth/support remain affordable. Positive
average mass, visit counts, nonzero root aggregates and nominal weight ESS are
not interchangeable. ESS is a concentration proxy under adaptive policies;
pathwise zero-target-reach/underflow attribution remains explicitly deferred.
Coverage or nonzero updates alone cannot establish playing-strength success.

## Reviewable pilot allocation

[Machine-readable quote and arithmetic](pilot-quote.json): fixed endpoints5M,
25M,100M nodes; fresh seed20261026441011;10M retained-key threshold with whole-
iteration freeze;2 workers; one lineage; all 27 configurations. Retain checkpoints,
averages, inference binaries, update/watch diagnostics, common panels,81 played
hands per endpoint, exact play reproduction and independent replay. No strength
arena or extra training beyond100M.

**Central19m59s / reserve57m53s; proposed allocation60minutes M4.** The quote
is a conservative extrapolation of tiny-fixture work, NOT a measured mature-table
rate. It deliberately uses the whole0.75649s native fixture processing time in
both training and row-processing proxies:100M/105,801×time for training,
3×10M/62,957×time for endpoint processing. Reserve uses3×training,2×processing,
2×startup plus600s proofs/readout. Rare expensive paths and table growth remain
uncertain. A reserve is not a completion guarantee or an elapsed-time kill.

Planning memory5GiB plus1GiB available-RAM headroom. New disk14GiB plus4GiB
free headroom; qualification's final free space was24.54GB(22.85GiB), so this
scenario fits that snapshot without deletion or staging. It is not a reservation.
The scenario allows20% whole-iteration row overshoot, training+inference+K50+
buffers, and compressed-byte entropy growth; fresh admission must pass at launch.
The10M protective threshold may freeze early: report uncensored growth and
explicitly separate later refinement from membership growth.

The implementation and reviewable budget are concrete. **Owner acceptance of
this measured compute/storage quote is still required before launch.** No pilot
owner receipt has been created, and no pilot is running. The qualification is
not a substitute for that acceptance. Failure/partial evidence must remain
incomplete evidence; no automatic scientific retry, extension or tuning.

## Retention and next decision

All ordinary sources, baseline, fixtures, raw watch records, checkpoint/export/
binary, initial/repeat traces, logs and resource receipts remain under
M4`~/Local/nplayer-variable-stack-20261026/`, with local ignored planning copies
of compact metadata and development logs. [Provenance](provenance.json) records
pins and the current retrieval path. Cleaner-owned bb128/ZIP/Drive archival is
pending, with no Drive acceptance claim. No old study/model/runtime or system
setting was modified. Qualification locks are released.

The first meaningful scientific outcome will be an affordability/learning
assessment of the fixed pilot. A mature comparison would need a separate budget,
matched opponents and per-configuration strength safeguards. Neither the pilot
nor this qualification establishes generalization between depths or superiority
to independently trained depth specialists.
