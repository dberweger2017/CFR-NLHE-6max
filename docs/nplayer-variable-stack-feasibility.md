# Three-player variable-stack qualification and bounded feasibility

Proposal [440](https://github.com/dberweger2017/CFR-NLHE-6max/issues/440).
Owner approved this first engineering/feasibility PR on October26. This is not
mature training, release qualification or a strength comparison. Publish a
measured compute/storage quote before the M4 pilot; no bb128 science.

## Frozen game and representation

Unraked three-player cash,50/100 blinds, K50 and production min/pot/conditional-
jam menu. Each starting stack is independently uniform on{2,000,5,000,10,000}
chips: all27 ordered20/50/100BB tuples have probability1/27. Button is independently
uniform. Stacks are public and fixed during a hand; each root is a new hand,
not a persistent bankroll session. The target chance law equals the sampler,
so no importance-weight change is introduced. Report actual root frequencies;
a balanced observation panel does not make training root counts exactly equal.

One new opt-in stack-owner schema retains the existing live-order K50/history
summary and additionally records button-relative initial stacks, remaining
stacks, street bets, total contributions and fold flags for ALL seats, actor,
blinds and exact ordered legal menu. Folded contributors remain represented.
This deliberately conservative baseline may fragment strongly. It is neither
an optimal abstraction nor a perfect-recall claim. Existing schema bytes,
fixed-game identities, root RNG and defaults stay unchanged.

The stack distribution is part of checkpoint/export identity and resume checks.
Readers reject undeclared depths/distributions; mixture policies do not pretend
to have one fixed configuration. Ordinary fixed-only consumers must fail closed.
No old100BB model is relabeled or resumed into the mixture.

## Qualification before dependent training

Independent review covers public-information keys, initial chance law and
estimator preservation. Fixtures cover hidden-world invariance, ownership,
folded contributions, rotation, unequal-stack side pots/refunds/odd chips and
short-all-in reopening against the existing engine; thread and save/resume
parity, full-row average export/inference parity and exact reproduction. Keep
legacy fixed-format golden/byte parity. Unsupported identities fail closed.

## Prospective science measurements

On a fixed balanced panel covering all27 tuples × three buttons, retain every
observation, including unsupported paths and sparse streets. Measure:

- Per tuple/seat/street root and decision denominators, all-in/side-pot exposure.
- Legacy live-order, new stack-owner and exact-history keys on IDENTICAL
  observations; alias/split counts and distinct concrete public-state signatures.
  This describes representation pressure; it is not a strength comparison.
- Pre-cap inserted-key growth and retained visits at fixed endpoints; cap/freeze
  time and declined updates. A protective cap censors natural growth.
- Positive-weight learning versus zero-valued/zero-weight updates, repeated
  updates, positive/zero average mass and admission waste. Do not call average
  mass or total visits alone useful regret learning. If full update attribution
  is not qualified, label that measure unimplemented rather than infer it.
- Both common-panel and actually played positive/zero/missing lookup rates.
  Policy-induced visitation and fixed-observation support answer different questions.
- Training, save, load, export, auditing, play, independent replay/reproduction,
  readout, complete wall/CPU, sampled peak RAM, thermal/swap and retained bytes.

No aggregate-only success gate: retain all27 configurations and uncertainty in
sparse strata. Equal-depth tuples are internal strata, not independently trained
fixed-depth controls. This first lineage cannot establish strength, transfer to
unseen depths, convergence or an advantage over independently trained specialists.

## Budget and stop

Provisional pilot endpoints5M,25M,100M nodes, one fresh seed and10M retained-key
threshold with whole-iteration freeze; these are planning bounds, not an admitted
launch. Source, seed, endpoints, work/memory/storage forecast and measured quote
must be pinned in the final admission. No automatic extension if learning is sparse.
M4 on AC, nonblocking normal/study locks, at most two workers; refuse insufficient
RAM/disk forecast plus explicit headroom. Owner STOP, thermal serious/critical/
missing, invalid information/play/accounting/nonfinite values, identity/parity/
reproduction failure or resource exhaustion are terminal. Retain all failures
and partials. No app/system changes, other jobs, cleanup or retry loop.

Ordinary working/final files stay in the new ignored study root. Cleaner owns
later stable bb128 staging/ZIP/Drive archival; no payloads in Git and no archive
acceptance claim without a receipt. Finish with an affordability/learning finding
and one reviewable next-allocation quote; no automatic mature training/arena.
