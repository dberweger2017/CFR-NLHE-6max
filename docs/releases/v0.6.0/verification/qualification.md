# v0.6.0 packaging and runtime qualification

All three exact models pass. PR367 merged as
`606bfc58de2a7147338253de0c4150389894f1a0` after all five checks passed;
[PR369](https://github.com/dberweger2017/CFR-NLHE-6max/pull/369) prepares release assets
and an explicit three-seat launch path. Publication, tagging, uploads and default
changes remain pending owner approval.

## What passed

- Three original binary SHA256 pins match after preparing **42 ordered parts**
  and independently reconstructing all three models. No export, retraining,
  quantization, policy selection or float64 probability change occurs. The
  earlier full-row audits in PR361/367 remain the mathematical provenance.
- The shipped stdlib verifier runs with `python -I -S`. Source, schema, game,
  menu, K50 tables, row count, average scope and original-mass tags remain bound.
- **36 integration hands**: six human-table and six spectator hands per model.
  Every hand settles with conserved chips and is replayed before and after
  journal restart (72 replayed hand instances of the same 36 hands).
  Human privacy and refusal of free sizing pass. Each runtime reports exactly
  **one weight table shared across its bot seats**.
- Nine small tests passed on the frozen Linux source. Ten pass locally after
  adding the explicit whole-cache-without-parts contract test, which also covers
  the Drive whole-file route. Final CI checks the current PR head.

These integration hands are not a playing-strength evaluation. The prospective
30-gate acceptance and the adverse relative scripted evidence are retained in
the [model card](../MODEL_CARD.md) and PR367/357 reports.

## Measured costs

| Seed | Prepare parts + verify, s | Standalone reconstruct, s | Native startup, s | Play + two replays, s | Verified staging, s |
|---|---:|---:|---:|---:|---:|
| `2026101935003` | 411.70 | 59.33 | 122.63 | 0.298 | 667.24 |
| `202610200601` | 440.02 | 59.14 | 122.59 | 0.289 | 687.34 |
| `202610200602` | 429.71 | 58.93 | 122.76 | 0.293 | 727.40 |

Native runtime stages also spend about 26 seconds verifying the existing combined
file and common assets before native startup. Reconstruction plus that runtime
stage took about 208 seconds per model on bb128. This is one host with ordinary
warm cache after file preparation, not a cold-cache benchmark or a speedup claim.
Native startup fully validates the model before reporting ready; no deferred
validation is hidden in later play.

The v2 qualification took **66.46 minutes** wall and
**27.33 child CPU-minutes**. Sampled worker-family
peak was **14.53 GiB**; maximum CPU and
Thermistor 15 were **57°C / 57°C**.
Sampling can miss brief memory peaks. Recommend 32 GB RAM for one selected model;
a 16 GB laptop can use the web UI through an SSH tunnel to a larger host.
The original 30–60 minute estimate was exceeded by about 6.5
minutes because of disk staging. No resource limit or deadline was relaxed.

All **14 v2 stages return zero**, with no v2 failure, thermal stop or retry.
The retained v1 setup attempt built the native service successfully in 12.2s,
then stopped because its managed Python had no pytest. It had not read/copied a
model. V2 reuses that successful binary and runs the stdlib tests instead; it
never installs packages into an earlier study's environment. The broader pytest
suite remains in GitHub CI.

## Provenance and retention

Frozen checked implementation: `3b43d05c24b8ec661c416568679d661518a9bb8d`.
Subsequent PR changes are documentation, the tenth cache-contract test and compact
receipts; verifier/runtime/native implementation bytes are unchanged.
The [compact receipt](qualification.json) includes all manifest/part hashes, native
startup identities, costs, resource limits and original receipt pins. It strips
unneeded private session IDs; original journals and receipts remain retained.

Owned working root:
`bb128:/home/dberweger/v060-release-20261020-pr369/qualification-v2`.
Physical retained cache:
`/mnt/data2tb/research-cloud/PR-369-v060-release/qualification-v2/`.
**81 unique files / 89,046,108,651 bytes** copied with source/destination
SHA256 readback and durable relocation records; original working paths remain
accessible through symlinks. Bundle verification intentionally requires regular
files, so use physical cache paths when reviewing staged bundles. About 49 GB
remains free on NVMe. Both compute mutexes were free at completion.

The new parts, reconstructed models and private runtime journals stay off Git.
All earlier PR350/355/357/361/362/367 inputs are read-only and unchanged. The v1
failure, v2 raw logs, source, build and coordinator files are retained. A further
108 support files and the 280,360,960-byte exact source TAR are copied/read back
under `PR-369-v060-release/support-v1/`, with originals retained. Its
`COPY-MANIFEST.json` SHA256 is
`9861d1133b36bbb63fa035c6cf7f43e6f35ce69b533931e4ee22e7f2491efff5`.
The source TAR SHA256 is
`8e89ed38576277ed1bef60c54671ce73b0c99ba9563764f09601a8a3f1603be7`. ZIP/Drive
archive acceptance remains pending; no deletion or cloud receipt is claimed.

## Distribution remains pending

GitHub will carry the release code, model card, manifests, checksums and 1 GiB
split-model assets. Planned Drive links will offer the identical complete binary
for each seed. A user chooses one roughly 14.15 GB model plus 1.38 GB of common
K50 tables. Both routes verify the same fixed whole-model hash. No Drive URL is
represented as public until upload and no-sign-in download have been checked.

Prepared manifests have `publication_approved: false`. Publication needs fresh
approved source-bound manifests for the reviewed release commit, authenticated
and public asset readback, and the owner's approval. Private journals must not
be included in the public release folder. See [readiness](../READINESS.md).
