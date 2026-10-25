# Frozen warm-policy estimator qualification

Research proposal [424](https://github.com/dberweger2017/CFR-NLHE-6max/issues/424).
The owner requests implementation and correctness fixtures before the short
warmed-checkpoint run. Mature science and release training remain paused.

Use the existing four-player PR413 10B **current regrets**, read-only. Compare
external sampling from `sigma` with `q = 0.75 sigma + 0.25 check/call`.
Counterfactual prefix weights exclude the traverser's own actions. Correct
returned values, regret increments and the existing opponent-sampled averages;
never reset a missing history's prefix weight to one. Exact zero probability,
positive-product underflow, tied values and all-zero update vectors are distinct.

The diagnostic holds the warmed policy fixed. It accumulates research deltas in
an independent shadow ledger, never feeds them back into policy, and never
unfreezes, resumes, exports or rewrites the input checkpoint. The 100K shadow
threshold follows whole-batch admission, including zero-update entries. Report
overshoot, zero slots at admission/freeze/end, later positive learning, and
positive updates discarded after freezing. Shadow findings do not establish
successful admission during from-scratch training.

The fixed warmed workload is 32 batches × four traversers × eight roots: 1,024
root contexts per sampling mode, plus separate-process reproduction. A fixed
prefix cohort takes the first 64 blocks and eight balanced seatings from each
PR413 check-call, call-pressure and trained mixed field: 1,536 saved hands.
Inspect the entire upstream counterfactual reach rather than starting at the
missing turn/river state. Keep never-reached watch keys.

Measure nonnegative importance coefficients and root-grouped Kish ESS, not
ESS of signed regrets or payoffs. Report positive regret and average evidence
separately. A replicated-learning diagnostic requires both, four distinct
positive-weight roots and grouped ESS at least four. It is not a strength gate.

The planning allowance remains 26 minutes central / 60 minutes reserved, with
12 GiB new NVMe and a 25–40 GiB RAM scenario. This does not reserve space.
Source/input hashes, estimator review, exact small fixtures and fresh manual
resource admission precede any warmed run. Numerical/correctness failures stop
and remain retained; no scientific retry, parameter sweep or 10B run follows.

The [corrected release proposal](reports/four-player-next-allocation/release-proposal.md)
restores cyclic noninferiority to **−5 BB/100**, all 24 seatings for mixed fields
and eight rotations for homogeneous/peer fields. It explicitly defers the
unqualified per-key release ledger, explains both peer estimands and includes
hash-only reproduction. Its 23.1h/45.7h all-NVMe scenario needs 850.9GiB new NVMe;
it remains storage-blocked. No release allocation is accepted or launched here.

## Estimator and information boundary

This standalone research example borrows the loaded `Table` immutably. No
production trainer, policy reader, regret matcher, key, menu, game or checkpoint
writer changes. All probability queries use the existing cash adapter's legal
acting-seat key. The evaluator owns decks and terminal utilities; hidden cards
never become policy inputs. The fixed prefix audit evaluates the warmed
self-play law, not the likelihood under the historical scripted opponents.

For traverser `i`, let `rho` be the product of `sigma(a)/q(a)` at sampled
**non-traverser ancestors only**. At an opponent node, recurse down a sampled
action and multiply the returned value by its ratio. At a traverser node,
enumerate every action and return the sigma-weighted sum of the estimated
child values. The diagnostic regret vector is
`linear_weight × rho × (estimated_child_value − estimated_node_value)`.
The existing opponent-sampled average update is
`linear_weight × rho × sigma_vector`, recorded before sampling that node's
action. Own-action reach is excluded from these counterfactual corrections;
it is recorded separately for terminal root-value coefficient diagnostics.
Every prefix/terminal coefficient has event and independent-root grouped
moments, with and without the linear weight. Grouped terminal weights sum all
correlated terminal branches inside one root before squaring; absent groups
contribute explicit zero root weights. Per-key unconditional coefficient
moments remain separate from the update-gated ESS used for replicated learning.
A positive coefficient with tied/all-zero updates is not classified as zero reach.

This targets the expected increments of the **existing** external-sampling
implementation under fixed sigma. It is not a new claim about convergence of
an adaptive training process. No clipping, self-normalization, probability
floor, missing-history weight reset or zero-prefix shortcut is applied.
Positive regret normalization that rounds to zero, nonzero products that
underflow, overflow and nonfinite values fail. True zero reach and tied
estimated action values remain separate. Negative signed regrets/payoffs are
never used as ESS weights.

The reference fixtures exhaustively enumerate opponent action maps in tiny
two-, three- and four-player games. The oracle calls unmodified production
`Traversal`, rather than reimplementing the corrected-walk formulas. The
`q=sigma` supported paths match its values and complete deltas bit-for-bit.
This is correctness evidence, **not a substitute for independent estimator
review** or a production performance measurement.

The shadow ledger has one ordered merge per 32-root batch. It admits all
new keys in a pre-freeze batch, including zero vectors; reports overshoot; and
keeps updating previously admitted keys after freezing. Zero-at-admission is
measured after the entire batch, so a zero first-root event followed by a
positive event in that batch is not misclassified as a wasted slot. Watch
targets remain represented even if never encountered or later discarded.
Regret/average evidence and root-grouped ESS are separate; the replicated proxy
requires four distinct positive contributing roots **for each** update kind.
It remains a learning-support diagnostic, not proof of useful playing strength.

## Commands and gates

Local fixtures, without mature inputs:

```sh
cargo test --locked --manifest-path native/hu20-trainer/Cargo.toml --example nplayer_warm_estimator
python3.11 -m unittest discover -s tests -p test_nplayer_warm_estimator_qualification.py
```

On bb128, use a committed isolated source checkout and fresh owned directories:

```sh
python -m scripts.nplayer_warm_estimator_qualification build NEW_BUILD
python -m scripts.nplayer_warm_estimator_qualification prepare NEW_RUN \
  --build-receipt NEW_BUILD/build-receipt.json \
  --tables /home/dberweger/cygnus-qualification-20261014/tables
```

`build` runs native library and example fixtures and creates a source/binary
receipt. `prepare` hashes all three original traces while parsing only their
fixed prefix cohort; verifies seating, model provenance and whole-source
hashes; pins K50/build/source; and creates a one-use config. Neither loads the
mature checkpoint or runs root traversals. Both acquire the ordinary compute
mutex nonblocking; neither replaces its inode or bypasses another owner.

An independent reviewer must provide a receipt binding `source` and
`binary_sha256` to that prepared config, with `status: approved`, a nonempty
`independent_reviewer`, `scope: frozen-warm-estimator-and-information-boundary`,
and `unresolved_correctness_questions: []`. The agent must not manufacture its
own approval. [CONTRIBUTING](../CONTRIBUTING.md#pull-requests) requires independent
review for regret-math/information changes. Unresolved questions block this run.

After review and a fresh manual RAM/disk/swap inspection:

```sh
python -m scripts.nplayer_warm_estimator_qualification run NEW_RUN \
  --review ESTIMATOR_REVIEW.json --accept-seconds 3600
```

The quoted seconds are a planning allocation, never an elapsed-time kill.
Require 12GiB new free space at admission, inspect the 25–40GiB RAM scenario
manually, and retain the normal/study locks for both passes. The existing
supervisor enforces CPU90°C / Thermistor15 100°C, missing/nonfinite sensors,
owner STOP and correctness failures. There is no during-run time/RSS/disk/swap
cutoff, scientific retry or automatic training continuation.

Each mode has exactly 1,024 ordered root identities; chance and action draws
are separately domain-separated and paired between modes. Native failure logs
identify the mode/batch/traverser/root for deterministic reconstruction. The
initial eight diagnostic artifacts are retained. A fresh process emits the
repeat into a byte-comparing SHA256 sink, retaining receipts and timings but
no second raw tree. A first mismatch preserves file, byte offset and compared
chunks and stops; truncation, duplicate/missing roots and changed input/source
pins fail verification. No archive/deletion or release adoption follows.

## Engineering status

Local validation: **121 existing native library tests, 14 new native example
tests and five Python controller fixtures pass**. New tests cover exhaustive
expected updates, bitwise reference behavior, zero reach at a missing row,
own-zero counterfactual reach, ties, normalization/product underflow, batch
admission, discarded/never-hit watch keys, 1/2/8/16-thread root/ledger parity
and streamed reproduction failures. CI runs the new example fixtures too.
The independent review identified missing grouped/linear terminal summaries
and unconditional watched-key coefficients; both reporting gaps were corrected
before any warmed work, with two focused fixtures. The estimator increments,
fixed workload and player remain unchanged.

**The owner-authorized warmed diagnostic is complete.** The target build and
[independent review](reports/nplayer-warm-estimator-qualification/independent-review.json)
bind source `cc28e45d0d842ec68721d14b9224ce232bcad0dc` and the actual binary.
All three main stages return0; all2,048 initial root contexts reproduce byte
for byte in a fresh process. [Results and costs](reports/nplayer-warm-estimator-qualification/results.md)
show82.73% passive shadow rows remain zero-update, with no qualifying repeated
learning on admitted targeted turn/river rows or watched potential rows. Main
execution is18m09s; no mature continuation follows. Sparse sampling and
compatible hidden states remain explicit limitations of reach conclusions.
The frozen protocol above is retained as the original prospective contract,
not authorization to repeat the run. Four-player release storage remains blocked.
