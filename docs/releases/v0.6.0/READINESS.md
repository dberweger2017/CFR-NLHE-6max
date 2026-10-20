# v0.6.0 release readiness

The owner authorized publication on October 20, 2026 after reviewing the release
preparation. PR367 merged as `606bfc58de2a7147338253de0c4150389894f1a0`;
PR369 merged as `1faacabf710dd6f1d73f368ee740831fec6e0878`, each after all five
checks passed. The authorized publication uses fresh approved manifests bound to
the reviewed tag source. Actual upload/readback status belongs on the
[v0.6.0 release page](https://github.com/dberweger2017/CFR-NLHE-6max/releases/tag/v0.6.0).
Default-model changes are outside this release.

## Fixed contents

- Three explicit 10B-node seeds: `2026101935003`, `202610200601`, `202610200602`.
- Exact qualified float64 binary derivatives, source-average/checkpoint hashes,
  original-mass tags, game/menu/card schema and K50 pins. No reconversion.
- Per-seed manifests and SHA256SUMS; each model has fourteen ordered parts of
  at most 1 GiB, plus common tables, model card, notes and stdlib verifier.
- An explicit three-seat 100 BB launcher using the existing persistent native
  service. Human play has two model seats; spectator play has three. Seats
  share one weight table and sample decisions independently.
- Fresh acceptance and the earlier adverse relative scripted panels are both
  retained. The model card makes no human-strength or equilibrium claim.

The exact pins live in `src/policies/v060_bundle.py`; manifests bind the settled
PR367 result SHA256 `15c573e88d9b3b3c9ab81f6f3150eff6b91d577b6aa26fdad0a2af3045f32453`.
The verifier detects damaged, missing, reordered or substituted parts and
source/schema/count mismatches. An approval field is a workflow declaration,
not a cryptographic signature: users must obtain the verifier and expected
source commit from the reviewed release through a trusted channel.

## Completed qualification

All three exact models pass full part reconstruction and native runtime checks:
36 integration hands, independent replay before/after journal restart, one shared
weight table, legal restricted sizing and human privacy. All 14 stages return
zero. Wall 66.46 minutes; sampled peak 14.53 GiB; CPU/Thermistor 15 maxima 57°C.
81 new files / 89,046,108,651 bytes are verified on the 2 TB cache. No publication
has occurred. The first setup's missing-pytest failure is preserved separately.
[Results, measurements and retained paths](verification/qualification.md) ·
[Compact manifests and proof](verification/qualification.json).

## Qualification scope

Small real-format fixtures cover exact reconstruction, preserved partials,
source/publication refusal, changed manifests, truncation, symlinks and whole
model substitution even after an attacker recomputes part hashes. The shipped
verifier imports only the Python standard library.

The bb128 packaging check is separate from poker-strength acceptance. It uses
an isolated source checkout and new output paths, reads PR367's models and K50
tables without changing them, and processes one model at a time. It verified
full-model reconstruction and exercised the existing human/spectator runtime,
chip conservation, privacy, restart and independent replay on a small hand set.
Prepared bundles remain unapproved. Large files and private journals stay off
Git; compact receipts record the exact source and measurements. Any completed
new artifacts staged to the 2 TB cache retain verified paths and copies; archive
and Drive acceptance remain pending until their own receipts exist.

## Distribution

The GitHub release is the versioned entry point for code, documentation, manifests,
checksums and the split models. Each 1 GiB part is below GitHub's per-file 2 GiB
limit ([GitHub documentation](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases));
the complete release may contain all three models. A dedicated public
Drive release folder will offer each exact combined binary as a single download,
with the same model SHA256. Keep private runtime journals and other research
artifacts out of that public release folder.

Drive URLs remain pending until uploaded from bb128's owned cache, public access
and full downloaded bytes have been verified. Link exact version/seed files from
the GitHub release; do not rely on an unverified broad research-folder link.
GitHub parts remain an alternative if a Drive download is temporarily unavailable.
A user needs one model plus common K50 tables, rather than all three models.

## Publication checklist

The owner has approved publication and PR369's qualification receipts. Merge the
publication documentation with passing checks before tagging. Bind the approved
bundles to that exact reviewed source/tag commit rather than silently changing
source provenance in an existing prepared manifest. Build into fresh paths:

```sh
python -m scripts.build_v060_bundle --seed SEED --model QUALIFIED_BINARY \
  --card-tables QUALIFIED_K50 --out FRESH_BUNDLE --source-sha REVIEWED_COMMIT \
  --publication-approved
```

For each seed, independently run the shipped verifier with `python3.11 -I -S`,
`--require-publication --expect-source REVIEWED_COMMIT`, and reconstruct/load
its pinned model. Publish all common assets and the three seed-specific part,
manifest and checksum sets. Read back every uploaded asset and verify its byte
count and SHA256; verify public download, reconstruction and runtime before
claiming publication complete. Separately upload the three exact combined binaries
to the dedicated public Drive release folder, verify no-sign-in download and
whole-file SHA256, then add their stable per-model links to the release notes. Do not replace retained research inputs or infer
Drive archive acceptance from GitHub release publication.

PR369 completed preparation; the subsequent owner-authorized publication executes
this checklist. Its per-asset receipts must distinguish uploaded, publicly
verified and runtime-verified files. Research ZIP/Drive archive acceptance remains
a separate operation. The dedicated public release folder is
[here](https://drive.google.com/drive/folders/1H2MVAmOHHku1LhmZtxbkVYN3LyP8Xz0j).
