# Matched-teacher six-player 100 BB imitation: results

[Frozen protocol](../../neural-six-imitation.md) ·
[decision](decision.json) · [all fields](fields.csv) ·
[qualification and training](qualification-summary.json) · [fidelity](fidelity.json).

**Gate D does not pass: non-inferiority is not established. The tables stay.**
The deciding run estimates a loss smaller than the 10 BB/100 margin, but its
lower confidence bound crosses that margin. Both replication point estimates
are positive. No secondary field has a harm flag, including check-call.
There was no tuning, additional evaluation, scientific retry or route change.

## Gate D

All-in-adjusted BB/100, network minus `six`, against the frozen foreign trained
field (#434's seed 2026102661001). The 95% two-sided interval's lower endpoint
is also Gate D's one-sided 97.5% lower bound. Runs 2 and 3 replicate on their
point estimates, exactly as predeclared; their intervals are descriptive.

| Network seed | Banks x blocks per field | Difference | 95% interval | Rule |
|---|---|---|---|---|
| 1, decides | 4 x 4,096 | -6.36 | [-11.99, -0.72] | Lower bound must exceed -10: fails |
| 2, replicates | 1 x 4,096 | +4.41 | [-7.19, +16.00] | Point estimate exceeds -10 |
| 3, replicates | 1 x 4,096 | +3.83 | [-7.45, +15.11] | Point estimate exceeds -10 |

[Run 1](run1-results.json) · [Run 2](run2-results.json) · [Run 3](run3-results.json).
Do not pool the replications after seeing the deciding result or replace the
declared gate with their positive estimates.

### Other fields

Point estimates only below; full nominal and decision intervals are in the
linked reports and CSV. Harm means the Bonferroni 95% upper bound across the
five secondary fields lies below -10. Check-call remains reported but exempt.

| Field | Seed 1 | Seed 2 | Seed 3 |
|---|---|---|---|
| pot-pressure | -1.93 | +1.55 | +4.67 |
| tight-aggressive | -3.29 | -2.11 | +1.18 |
| check-call | -8.32 | -27.42 | +11.64 |
| random | -9.62 | +15.62 | -3.20 |
| mixed | +10.41 | -10.53 | -9.02 |

**No harm flags in any run.** Negative point estimates, especially the seed-2
check-call result, remain adverse descriptive evidence; exemption is not a claim
of safety or equivalence there.

## What the network learned

The export wrote 31,266,891 training records from 2.4M hands. The unchanged
trainer used 25,249,825 positive-mass teacher rows, identically for all seeds.
The fresh 120,000-hand holdout has 1,564,159 records, of which 1,262,840 have
positive-mass teacher rows. The foreign Gate D peer never supplies train labels.

| Seed | Held-out TV from `six` | Teacher top-label agreement | Training wall time |
|---|---|---|---|
| 1 | 0.0651 | 88.57% | 137 s |
| 2 | 0.0644 | 88.58% | 135 s |
| 3 | 0.0631 | 88.74% | 136 s |

Training times include loading and preparing the disk-backed arrays. Four
epochs themselves take about 80 seconds per seed. Fidelity is descriptive on
trained teacher rows; it neither labels the missing rows nor determines Gate D.
Preflop TV is about 0.05, increasing to about 0.11 on the river. Per-field and
per-street numbers, coverage and masked cross-entropy are in [fidelity.json](fidelity.json).

## Interpretation

Matched imitation produces substantially closer 100 BB behavior than the
wide-grid experiment's reported failure suggested, but it does not qualify
network-only adoption under this protocol. The earlier -27 to -29 BB/100
estimates used a different teacher/distribution and fresh deals; comparison
with this study is descriptive, not a paired causal estimate.

This is **an inconclusive non-inferiority result**, not proof that the inputs or
network size cannot express 100 BB play. It also does not establish that teacher
mismatch was the only cause of step 4's failure. This experiment changes teacher
and distribution together. Three optimizer seeds share one teacher and one
training dataset; they are not independent teacher lineages.

The separate Deep CFR pilot was not altered. Adding these examples to a shared
wide-grid network, changing the architecture/loss, or collecting further hands
would need a new protocol. No automatic extension follows this outcome.

## Qualification and accounting

- Actual scientific source: `3316037990e6edbe282e67664ee9d22a8135f0a2`.
  Protocol first committed in `99d93ebc`; subsequent changes address host memory
  accounting and native-test K50 configuration, without changing the recipe.
- 193 native library, 19 paired-host and 17 Python tests pass on the pod.
  The broader local selection has 21 tests. Required PR CI passed on `3316037`.
- Input binary/mass/K50 bundle: all nine member SHA256s match
  [input-members.json](input-members.json). Qualification exports at one and
  seven threads have identical record digests. The full smoke pipeline passes.
- All three networks pass Rust/PyTorch parity on 10,000 held-out samples each,
  within 1e-5. The largest observed discrepancy is below 9e-7.
- 72 main scan receipts report zero fallback violations. Each run's twelve
  bank-0 traces independently replay: 294,912 hands per run, 884,736 total.
  [Replay 1](run1-replay.json) · [Replay 2](run2-replay.json) · [Replay 3](run3-replay.json).
- Controller: November 8, 22:08:35 to 23:46:11 UTC, about 1h38m.
  GPU peak 59 C; minimum guarded available memory 30.67 GB and free disk
  158.74 GB. CPU thermals were not exposed/qualified by this controller.
  No resource stop or scientific retry occurred.

## Preservation and billing

The complete generated experiment tree, including all fourteen sample datasets,
trained weights, network exports, raw/compressed traces, receipts, logs, input
provenance and four native executables, is preserved in a 2,662,575,176-byte
`pr474-evidence.tar.zst`. Only the rebuildable array cache is excluded.
SHA256: `a00a2307b035f1e1b32bf68ce65c2448107e1e535f2f898852e21cf8e59bda5f`.
Local SHA256 matches the pod; zstd integrity, full tar readability and required
member checks pass. See [retrieval and billing receipt](retrieval.json).

Local restoration: the ignored `results/neural-six-imitation/` directory in the
M1 task worktree contains the verified archive and member listing. Extract into
a fresh directory; the root is `experiment/`. Networks are
`experiment/networks/net1.npnet` through `net3.npnet`, training samples are under
`experiment/data/train/`, and the frozen decision is `experiment/decision.json`.
[Network pins](networks.json) and training weight pins in the qualification
summary bind the restored models. Original teacher inputs remain at their
existing bb128 locations and the pinned local input copies; they are reused
dependencies, not new models produced by this study.

The pod was stopped through the internal browser only after verified retrieval.
At November 8, 23:57:11 UTC, RunPod displayed compute/storage **Not running** and
total **$0.00/hour**. Approximate rental cost is **$0.63**, derived from the
observed interval and $0.308/hour quote, not a final invoice. The obsolete hard
billing-cutoff task is disabled. The stopped pod must not be restarted.

Long-term archival completed through bb128's existing deployed cache uploader.
[Archive receipt](archival.json): [Drive evidence.zip](https://drive.google.com/file/d/1qk3WYkE4VmJ6ajrP36Pg4rs80eSqyLrS/view),
`gdrive:PR-474-neural-six-imitation/evidence.zip`, Drive ID
`1qk3WYkE4VmJ6ajrP36Pg4rs80eSqyLrS`, MD5
`1a400492de5d37da624a6d4a5cec187e`.

The ZIP is 6,538,600,123 bytes, SHA256
`0c054eaec84f3cd6181f6787745d1a99fc692b7c85f9216c4b7dfdf8ad6b3077`.
Its embedded `ARCHIVE-MANIFEST.json` SHA256 is
`34156df0b0d89fda7bd729d5d4d9b3be1ef12020dca5d4f76135353a9a9e20fd`.
All 839 ZIP members pass local CRC readback, with SHA256 readback against the
manifest for its 838 payload entries and byte equality for the embedded manifest.
The deployed uploader accepted Drive size/MD5 and recorded all 840 local files
(including the ZIP itself). Receipt paths, sizes and mtimes match the complete
cache inventory; the KEEP marker remains. This is local SHA256/member verification
plus remote MD5/size acceptance, **not a remote SHA256/member audit**.

Fast restoration: copy from `/research/PR-474-neural-six-imitation/experiment/`
on bb128 into a fresh working directory. The cache's real root is
`/mnt/data2tb/research-cloud/PR-474-neural-six-imitation/`.
Drive fallback:

```sh
rclone copy 'gdrive:PR-474-neural-six-imitation/' '/research/PR-474-neural-six-imitation/'
```

Verify the indexed ZIP SHA256 and embedded manifest, extract into a fresh
restoration directory, then verify required model/input pins before use. The ZIP
retains `experiment/`, `source-archive.tar.zst` and `archive-controller.py`.
Network members are `experiment/networks/net1.npnet` through `net3.npnet`;
weight members are `experiment/models/seed1/weights.pt` through `seed3/weights.pt`.
Their SHA256s remain in [network pins](networks.json) and
[qualification summary](qualification-summary.json); external teacher dependencies
and their restoration paths remain in [input pins](input-members.json) and
[preparation](preparation.md). All original local tar, inputs and progress backups
remain retained. No synced Mac Drive folder, deployed cache tooling, eviction
configuration or bb128 pilot was modified. Required CI passed on report commit
`813dda9`; this archival-only follow-up also passes staged storage/diff checks.
