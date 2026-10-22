# PR380, PR382 and PR384 archive receipts

Verified on October 21, 2026, at 19:33 UTC from bb128. This updates the archive status recorded as pending when the three research reports were written; it changes no scientific results or original evidence.

## Verification and coverage

For each ZIP, a read-only check matched the current Drive file ID, size and MD5 to the deployed cache tool's `.drive-receipt.json` and the local ZIP. The local ZIP SHA256 matches the published index. Every ZIP member was read back and matched its uncompressed cache file, and every evidence file matched its embedded SHA256 entry. The inventory, checksum list and evidence-member sets agree. All files in each cache folder, excluding the receipt itself, have unchanged size/mtime and receipt coverage.

The existing ZIP format contains `MANIFEST.txt` (evidence path inventory) and `SHA256SUMS` (SHA256s relative to `evidence/`), rather than `ARCHIVE-MANIFEST.json`. The hashes below pin both files. Evidence counts exclude those two metadata members; receipt coverage counts include them and the ZIP itself. No archives were repacked, uploaded or deleted during this check. Drive acceptance is a size/MD5 metadata check, not a remote SHA256 or member readback.

Original `source/`, `target/` and `venv/` trees remain outside these archives. Each archived `evidence/source.bundle` advertises the measured commit listed below. Existing Git object-store dependencies, model and K50 input paths remain protected: these are evidence archives, not self-contained model/environment packages. Retain the original provenance and dependency paths linked in each research report; no standalone rebuild or deletion clearance is claimed.

## PR380

- Cache: `bb128:/research/PR-380-river-continuation-qualification/`.
- Drive: [PR-380-river-continuation-qualification.zip](https://drive.google.com/file/d/1GpH0Se-yBOVpN-ceuFDIkV825CamW97K/view), ID `1GpH0Se-yBOVpN-ceuFDIkV825CamW97K`; path `gdrive:PR-380-river-continuation-qualification/PR-380-river-continuation-qualification.zip`.
- ZIP: **6,911,055 bytes**, 97 evidence files + 2 metadata files = 99 file members. Receipt covers 100 local files including the ZIP.
- ZIP SHA256: `4727ffe84d145d961c90b5be1461d880d8b18528c8bc86664de1eb85eb43cbf1`.
- Accepted/current Drive MD5: `65f08c7a0fd3ae78763c0d1de5ba4682`.
- Embedded `MANIFEST.txt` SHA256: `5f3c9a19cd8a9c3480ee987c1f184a227f360f97630f9f43b925391f3976941a`.
- Embedded `SHA256SUMS` SHA256: `61bf1c02cf76375b5b919a172ded34c8c22e812a02342bc22598f541c6963aa9`.
- Original receipt: `bb128:/research/PR-380-river-continuation-qualification/.drive-receipt.json`, issued `2026-10-21T18:04:47Z`; SHA256 `473aeebd7eab7b66576aba1e6bc95ba97f5f016dee8ba5d909d165377fdace19`.
- Source bundle advertises `0bb9c621cbf5f4d89bed9fc92d0419fb9825ea66`; full source/input provenance remains in the [PR380 index entry](../../RESULTS_INDEX.md#pr380--fresh-river-panel-exact-retained-continuation-belief-gate-failure).

## PR382

- Cache: `bb128:/research/PR-382-river-exact-beliefs/`.
- Drive: [PR-382-river-exact-beliefs.zip](https://drive.google.com/file/d/1jqPoU1Gi1eT3VkI_ia0rVX6Mkt3qlR9y/view), ID `1jqPoU1Gi1eT3VkI_ia0rVX6Mkt3qlR9y`; path `gdrive:PR-382-river-exact-beliefs/PR-382-river-exact-beliefs.zip`.
- ZIP: **3,229,811 bytes**, 100 evidence files + 2 metadata files = 102 file members. Receipt covers 103 local files including the ZIP.
- ZIP SHA256: `425c2152222167d486eedc5ef7c2fb61410690bd31b454473757cb8be15aad1f`.
- Accepted/current Drive MD5: `bee66d5a2ca333c142de8a660dd71a6d`.
- Embedded `MANIFEST.txt` SHA256: `f0ad821133d6daa6348c6624a4acf5248cf83cc5aae859630f7c88fed1ad9fd3`.
- Embedded `SHA256SUMS` SHA256: `de04e269eedd3f0a1523f8cec62efd6bb7c5290f72cff0fbe900fa993569ac93`.
- Original receipt: `bb128:/research/PR-382-river-exact-beliefs/.drive-receipt.json`, issued `2026-10-21T18:04:55Z`; SHA256 `716487961bfc9d10c64361f41f0d3d33c882562f709bd62aed4ca36a648f94e2`.
- Source bundle advertises `e2a91181f77d9c5b0a4de545bccbe498391875fe`; full source/input provenance remains in the [PR382 index entry](../../RESULTS_INDEX.md#pr382--exact-modeled-river-beliefs-verified-latency-and-every-root-gates-fail).

## PR384

- Cache: `bb128:/research/PR-384-river-harm-diagnosis/`.
- Drive: [PR-384-river-harm-diagnosis.zip](https://drive.google.com/file/d/11N9XwuYmdI8SlzZTprBWQB4BU_ieFLwc/view), ID `11N9XwuYmdI8SlzZTprBWQB4BU_ieFLwc`; path `gdrive:PR-384-river-harm-diagnosis/PR-384-river-harm-diagnosis.zip`.
- ZIP: **9,467,380 bytes**, 88 evidence files + 2 metadata files = 90 file members. Receipt covers 91 local files including the ZIP.
- ZIP SHA256: `252455dd7e415243a4e8474edcb7212ec89357899e37c955069a3ce774f1c551`.
- Accepted/current Drive MD5: `c78ed79b635a85c78e16eca3d00ede07`.
- Embedded `MANIFEST.txt` SHA256: `d5fffd631c4ef363eeeb3eeffd419e4d9641d2698ed0db795facbeb1e388dd80`.
- Embedded `SHA256SUMS` SHA256: `f7053c1cf8fc6e8c9c5a753aa8c97b27aa749f323335018366f1bca2c8734bee`.
- Original receipt: `bb128:/research/PR-384-river-harm-diagnosis/.drive-receipt.json`, issued `2026-10-21T18:05:55Z`; SHA256 `bed42cb97f216666367a14f2925b1ed82aa1134f5371d734d2719d5606d2cf64`.
- Source bundle advertises `895f853f407f6f618fce396f1a5c36c17f778941`; full source/input provenance remains in the [PR384 index entry](../../RESULTS_INDEX.md#pr384--saved-profile-river-harm-diagnosis-verified).

All 24 main float64 snapshots are included under `evidence/main-v1/capture/snapshots/`, along with the three calibration snapshots. This preserves the saved-strategy evidence independently of reconstructing it.

## Retrieval

Use the existing cache first: copy the required files from `bb128:/research/PR-<n>-<name>/evidence/` into a fresh ignored working directory. After a cache miss, restore the named ZIP to a fresh directory on bb128, for example:

```sh
rclone copy 'gdrive:PR-384-river-harm-diagnosis/PR-384-river-harm-diagnosis.zip' FRESH_DIRECTORY
```

Verify the indexed ZIP SHA256 before extraction, then check the inventory and `SHA256SUMS` relative to the extracted `evidence/` directory before using the files. Substitute the corresponding exact folder/ZIP for PR380 or PR382. Preserve originals and active inputs; restoring these archives does not restore their separately pinned model/K50 dependencies or grant permission to remove working roots. See [storage policy](../artifact-storage.md).
