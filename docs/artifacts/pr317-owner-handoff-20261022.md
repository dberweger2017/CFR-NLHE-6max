# PR317 scientific completion and owner cloud handoff

On October22, 2026, the owner instructed: “I will handle cloud, fyou can finish
the pr without that step, owner approved”. This authorizes completing the PR
for review without final cloud acceptance. Merge remains the owner's decision.
No release, default, Slumbot play, cleanup or additional research is authorized
by this handoff.

## Completed scientific work

All145,408 blocks /319,488 primary hands pass the global replay, reproduction
and every-file verified-transfer barrier. Primary completion was October21 at
09:14:52Madrid. Predeclared range-model diagnosis and independent interval,
script-probability and telemetry checks pass. The [report](../reports/hu200-river-search.md)
records results, adverse scripted evidence and the interrupted-decision timing
limitation. The [release receipt](../reports/hu200-river-search-artifacts/final-m4-science-release.json)
records M4 science released October22 at10:01:58Madrid. The original deadline,
source, search, counts and roots remain unchanged. Original locks and detached
launcher are retained.

## Evidence retained and storage work handed over

The bb128 PR root is `/research/PR-317-HU200-river-search/`, resolving to
`/mnt/data2tb/research-cloud/PR-317-HU200-river-search/`. M4 accesses it through
the private cable as `bb128-lan`; the administrative host uses `bb128`.

| Evidence | Location under the bb128 PR root | Status at handoff |
|---|---|---|
|145,408 primary blocks|`final-20261017/blocks/PANEL/INDEX/`|Every original manifest member verified on arrival before primary readout; per-block transfer manifests and durable arrival receipts retained.|
|Closed controls, source archive, helpers and consistent primary SQLite backup|`final-administration-20261022/`|149 files /1,022,078,771 bytes pass every-file size/SHA256 readback and durable receipt. Manifest SHA256 `f52a1f95219964f95e6584ab16ceb15ae9d80d34f3bce59d0a020e47110bb9f5`.|
|Full diagnosis, selected hand bodies, pinned requests and profiles|`final-diagnostics-20261022/`|Existing preservation job is copying/verifying; final arrival receipt not yet observed. M4 originals retained.|
|Final block ZIPs and member/whole-archive receipts|`final-closeout-20261022/`|Existing storage-only worker is building15 archives. No completed ZIP receipt yet observed; partial archives are not accepted restoration sources.|
|Earlier seven archives|Existing paths in [RESULTS_INDEX](../../RESULTS_INDEX.md)|Previously accepted; do not establish final/admin/diagnostic coverage.|

The administration arrival receipt is
`final-administration-20261022/copy-arrival-receipt.json`.
No live SQLite was race-copied: `primary/receipts-backup.sqlite` was made with
SQLite backup and passed `integrity_check`. No originals were retired by these
final preservation/archive jobs.

The existing preservation process on M4 was launched as PID76028 at
Unix1792656214.673389. Its script is
`~/Local/hu200-river-search/planning/hu200-river-search/final-scope/preserve_final_administration.py`;
log is adjacent `final-preservation-20261022.log`. Its local output is
`~/Local/hu200-river-search/results/hu200-river-search/final-administration-20261022/`.
Completion requires `preservation-receipt.json` with both verified arrival
receipts; failures remain in `preservation-failure-*.json`. Full source manifests
are `copy-manifest.json` and `diagnostic-copy-manifest.json`. Diagnostic originals
are at the adjacent M4 `final-diagnostics-20261022/`.

The existing bb128 archive process was launched as PID824105 at
Unix1792655833.927112. Under `final-closeout-20261022/`, its script is
`archive-final-blocks.py`, log `archive-worker.log`, verified ZIP receipts
`receipts/ZIPNAME.json`, final marker `block-archives-complete.json`, and failures
`archive-failure-*.json`. Last observation: first direct chunk at11,008 blocks,
354,690 members; worker present, no failures, no completed ZIP receipts. It runs
at low CPU/I/O priority for storage/hashing only. Do not duplicate either job;
verify process command and creation time because PIDs may later be reused.

The owner now manages remaining copy/ZIP verification, final administration and
diagnostic archive coverage, uploads and Drive acceptance receipts. No upload
was launched for these new final files. If using the deployed cache tool, use
the resolved real path above; the lexical `/research` symlink has a known
receipt-path issue. All final cloud coverage remains explicitly unaccepted
until its own durable receipts exist. Retain uncompressed evidence, failures,
manifests and retrieval provenance. Any later retirement still requires exact
file identities, every-file size/SHA256 arrival verification, durable receipts
and the existing dependency/ownership rules. No shared, other-PR or synced files
may be deleted on the strength of this handoff.

## End of monitoring

The existing30-minute task
`pr317-m4-river-final-monitor-30m-20261017-v1` ends at this owner-authorized
scientific-review/cloud handoff. No replacement task or follow-on work is
created. A queued historical run prompt must use this terminal handoff and must
not restore the timer, restart science or duplicate the storage jobs.
