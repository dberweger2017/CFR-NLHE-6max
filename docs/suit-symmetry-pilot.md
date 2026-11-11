# Suit-canonical neural-policy pilot on Runpod

Owner requested this pilot on Runpod instead of M4, November 11, 2026. One
fresh single-GPU pod, Secure Cloud preferred, maximum one hour of paid rental
including setup/retrieval; main experiment capped at 45 minutes. No M4/bb128
training, playing-policy change, release or automatic follow-up. Prepare/test
locally before renting; retain the result even if weak or negative.
Owner subsequently authorized unattended execution with a hard **US$5 total**
ceiling. Retain this smaller one-hour plan rather than using the extra budget
for outcome-dependent tuning. Include storage in the estimate. A control-plane
watchdog stops this pod at 55 minutes; experiment outputs live on a temporary
10-GB network volume, retrieved and verified before pod/volume cleanup.

## Hypothesis and boundary

A globally suit-canonical representation may improve policy imitation at fixed
network size and fitting work. This is an offline representation test, not a
playing-strength test. Do not augment sampled Deep CFR regrets: a frozen neural
opponent profile can break suit symmetry. Use only PR467's existing positive-mass
`widemix` seed-1 tabular-policy labels. Its card key is the preflop rank/shape or
K50 lookup of `hu20_buckets::class_key`, which sorts per-suit signatures; all
other key fields are suit-independent public history/state. Prove the signature
and hand-evaluation invariants with all 24 permutations before the main run.

Canonicalization sorts the four signatures `(hole rank mask << 13) | board rank
mask` descending and reorders **both** card channels together. Tied signatures
are identical channels, so the representation is invariant. Only the acting
seat's 52 hole/52 public-board bits change. Rank/shape, K50 bucket, betting,
positions and legal-action features are untouched. No hidden cards, deck or
payoffs become model inputs. No existing encoder or deployment format changes.

## Fixed data and splits

- Source: PR467's `wide-{3,4,5,6}p-mixed.npfeat` in `data/train` and
  `data/test-wide`; verify full source hashes against its published model/result
  receipts. Also pin the existing seed-1 imitation weights for the audit.
- Postflop only, positive teacher-0 rows, valid distributions, legal masks and
  card bits. Normalize rounded uint16 targets to sum to one. Do not select by
  network loss or target distance from uniform.
- Twelve cells: 3/4/5/6 players × flop/turn/river. Seed 20261111860001 selects
  up to 8,192 training rows/cell and 1,024 test rows/cell without replacement.
  Require >=1,024 training rows and 512 distinct training hands/cell, and >=128
  test rows and 64 distinct test hands/cell, otherwise stop as insufficient data.
- Whole source deals are already split between train/test jobs. Purge test rows
  whose full canonical feature vector appears in training. All suit variants of
  a row remain in its source split; report purged counts. Never move an example
  across splits to fill a quota. Original hand IDs are namespaced by source job.
- Pin selected arrays, targets, masks and hand IDs before GPU execution. Both
  arms get identical examples, batches, targets, seed and architecture.

## Audit, fits and decision

1. On up to 256 held-out rows/cell, evaluate the existing imitation network under
   all 24 global suit renamings. Report each row's maximum TV from its original
   prediction and the mean/p99 across rows. Verify exact canonical-input identity.
   If mean maximum TV <=0.005 **and** p99 <=0.05, stop: little measured opportunity.
2. Otherwise fit raw and canonical inputs with `612→1024→1024→512→6`, masked
   cross-entropy, AdamW lr .001, weight decay .0001, batch 4096, 1000 steps.
   Use three fixed seeds 20261111860011/12/13. Each seed shares initialization
   and the batch-index sequence between arms. No early stopping, tuning or retries.
3. Evaluate on original held-out observations, using canonical preprocessing only
   in the canonical arm. Primary: mean paired TV-to-teacher difference,
   canonical minus raw, with each original hand one cluster (average its rows).
   Average over the three fixed fits; bootstrap hands 2,000 times with seed
   20261111860002. Intervals condition on these fits; they are not a general
   training-seed uncertainty estimate. Also report all three seed means.
4. **Advance to a separately approved playing test** only if primary point <=−.01,
   its one-sided 95% upper bound <−.005, and every seed's point is <0. No street or
   player-count subgroup may have an established >.01 TV regression (one-sided
   lower bounds at .05/7 across those seven safeguards). Any such harm rejects.
   Otherwise reject if primary lower95 >=−.005; other cases are inconclusive.
5. Measure end-to-end CPU decision latency (canonicalization + network + legal
   softmax), 256 evenly spaced held-out rows repeated four times per model, two CPU threads,
   alternating arm order by seed. Median canonical/raw ratio must be <=1.25 to
   advance. Report GPU fitting and preprocessing times separately. This PyTorch
   benchmark does not establish native-traversal throughput or deployment latency.

Outputs: fixed-data and source manifests, correctness receipts, audit, all six
fit logs/weights, per-hand errors, latency samples, aggregate result and resource
receipts. Payloads remain ignored ordinary working files. Retrieve and verify
all outputs before terminating this conversation's pod; confirm termination by
MCP read-back and check billing. Never modify an unrelated pod or its storage.
No paid instance may idle while implementation is unfinished. No extra seed,
sample, budget or alternative recipe follows an inconclusive or negative result.
