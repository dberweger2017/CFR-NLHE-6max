# bb128 completed-evidence relocation — October 19, 2026

The owner requested moving previous rounds' evidence off NVMe and organizing it
on the 2 TB drive. GitHub was checked before selection: PR339, PR340 and PR342
are merged. This is an explicitly authorized local relocation; it does not
claim Google Drive acceptance or authorize purging the HDD copy.

The operation preserves original directory names below each owning PR's
`roots/` directory in `/mnt/data2tb/research-cloud/`. Original NVMe paths become
compatibility symlinks after verification. Every regular file is hashed before
copy and read back with SHA256 from the HDD; paths, sizes, modes, modification
times and symlink targets must match. Sources are checked again before releasing
the verified NVMe copy. Full manifests, original failures, checkpoints, raw
traces, source/configuration receipts and logs remain available.

PR340's main-v5 virtual environment and small source/control files remain on
NVMe because PR355 uses that runtime. PR350/352/353/355 roots and inputs,
shared K50 tables and Git, other users' work and operating-system settings are
outside this selection. No experiment, schedule, fan/driver or model setting is
changed. Each relocated PR folder has a KEEP marker pending cloud archival.

The first preflight stopped before copying because `/proc` restricts inspection
of the user's systemd/PAM/SSH session daemons. Their identities were explicitly
reviewed; the successful inventory records these inspection exceptions. Research
processes' accessible handles, maps and working directories are checked before
relocation, and any unknown inspection error stops the operation.

The final compact receipt below supplies exact source/destination mappings,
counts, checksums of manifests, timestamps and observed before/after disk space.
Full file inventories stay on bb128 in the indexed receipt directory. No research
payload enters Git. Google Drive ZIP/manifest/upload acceptance remains pending;
only the verified uncompressed HDD copy is currently claimed.

## Organized evidence

| Owning PR | Preserved scope | Regular files moved | Payload GB |
|---|---|---:|---:|
| [339](https://github.com/dberweger2017/CFR-NLHE-6max/pull/339) | Original failed setup and completed storage benchmark |1,413|12.022|
| [340](https://github.com/dberweger2017/CFR-NLHE-6max/pull/340) | Qualification, all four failed attempts, successful training/evaluation/thermal/smoke outputs |17,620|31.248|
| [342](https://github.com/dberweger2017/CFR-NLHE-6max/pull/342) | Completed blueprint comparison, fixtures and source/provenance |860|2.995|
| **Total** | **13 roots/subdirectories** |**19,893**|**46.265**|

GB is decimal. File payload and measured filesystem-space changes differ because
of allocation, hardlinks, directory overhead and other host activity.

Cache folders are `PR-339-nplayer-storage-benchmark`,
`PR-340-nplayer-fast-strength-study` and
`PR-342-nplayer-blueprint-promotion`. Each has `NVME-RELOCATION.md`, `KEEP`,
and a `roots/` directory. The successful PR340 main-v5 small controls are also
copied beside its relocated outputs, while their original copies stay on NVMe.
The shared venv and rebuildable target directory are excluded from this extra
control copy.

## Retrieve or restore

The [compact receipt](nvme-relocation-20261019.json) maps every original path to
its exact HDD destination and hashes each complete per-file manifest. For
example, retrieve the storage benchmark's preserved measurements into a fresh
ignored directory:

```sh
rsync -a bb128:/mnt/data2tb/research-cloud/PR-339-nplayer-storage-benchmark/roots/nplayer-storage-benchmark-20261018-v2/measurements/ results/FRESH_DESTINATION/
```

Copy the required manifest from the receipt directory and verify each selected
member's SHA256 before research use. The original `/home/dberweger/...` paths
also continue to resolve through their compatibility symlinks. To bring retired
work back to NVMe, copy from the indexed HDD path into a fresh ignored working
root and verify it; do not overwrite an existing active root or input.

The full inventories, helper, before/after snapshots and initial preflight
failure are retained under
`bb128:/mnt/data2tb/research-cloud/.storage-receipts/nvme-relocation-20261019T195815Z/`.
Cloud archival is pending: these local HDD locations are the current restoration
source, and no new Google Drive link or acceptance is claimed.

## Final checks and space

The verified relocation moves 46.265GB of payload and recovers
46.270GB of observed NVMe space. Free NVMe rises from18.090GB to
**64.360GB**; the HDD retains about
1.031TB free.
The HDD filesystem sync completed before final closeout. All compatibility
symlinks resolve to the indexed destinations; relocated internal symlink
resolution was checked too.

The prepared PR355 main configuration still hasSHA256
`eb43aa2598151eb291441552e52b1e73915a9a218de8049f8d3645c846cee856`.
Its unchanged managed Python imports both `pokers` and NumPy successfully.
At this prelaunch configuration check, launch/status/failure/results were absent.
The owner subsequently authorized launch during the disk sync: PR355 started
October19 at20:08:19UTC asPID544891 from the same frozen source/configuration.
[Launch receipt](../reports/nplayer-bb100-10b/launch.json). The25.11GB output
forecast now fits with working space.

Compact receipt SHA256: `feab7991d204381caa9cfea4bb490934b247ac66a9c33d57ceb70d364df47b5b`. This receipt includes
full-manifest hashes, PR-status snapshot/helper hashes, retained-control copy
accounting and the current-study check.
