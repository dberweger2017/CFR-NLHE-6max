# v0.6.1 staged publication procedure and quote

Preparation only. The owner must approve merge, tag and publication explicitly.
**Release-asset upload is a separate proposed action**, not archival authorization.
Do not run the old v0.6.0 coordinator. Do not move/delete research originals,
change Drive credentials/sharing, or stage archives as part of this work.

## What v0.6.0 taught us

[PR369](https://github.com/dberweger2017/CFR-NLHE-6max/pull/369) qualified all three
100 BB binaries in 66.46 minutes, including roughly 35 minutes of verified HDD
staging and 89.046 GB of additional retained files. The publication coordinator
then uploaded all 55 assets and did 55 authenticated full readbacks (43.830 GB,
4,014.68 seconds). [PR371](https://github.com/dberweger2017/CFR-NLHE-6max/pull/371)
is still open/incomplete as inspected October 23: it stopped on HTTP404 because
it retained draft `untagged-…` download URLs after publication. The October22
metadata receipt matches all live asset IDs/sizes/digests and three small public
readbacks; 52 public payload checks, reconstruction/runtime and Drive mirrors
remain incomplete. Inspection is not authority to change that work.

v0.6.1 reuses its existing audited binaries: no JSON export, conversion, float32
variant, repeated full-row mathematical audit, or duplicated research staging.
K50 assets already exist at v0.5.3 with identical sizes/SHA256s; reuse those URLs.
A fresh local bundle holds parts and small metadata, with an external K50 path.

## Distribution decision and network cost

Recommend **GitHub split assets**, fourteen ordered parts per seed, each <=1 GiB,
plus source-bound manifests, SHA256SUMS, three documents and the stdlib verifier.
Three models total **42,918,983,478 bytes**; dependencies **1,384,031,032 bytes**.
Do not upload the dependency bytes again. One user needs one seed. Per-seed
manifest hashes enter the final publication receipt; they do not exist until
parts and exact release source are fixed.

At a conditional 4 MB/s uplink, model uploads alone take **2h59m**. One anonymous
readback of all models takes **1h12m at 10 MB/s**, or **2h59m at 4 MB/s**. Allow
roughly **4.5–7 hours** after owner publication approval, including metadata,
reconstruction and three short native checks; rates are scenarios, not promises.
Refresh ETA after the first completed part. GitHub uploads resume at asset
boundaries: inspect live names/IDs/sizes/digests after a lost response before
retrying. Client downloads resume within each part by HTTP Range.

A mandatory Drive whole-model route would add another **42.919 GB upload (~3h)**
and another full anonymous readback (1.2–3h), plus HDD staging, owner-managed
cache-tool upload/MD5-size acceptance, sharing/public-download prerequisites and
receipt coordination. It offers a whole-file download and lower consumer disk
use, but duplicates payload traffic and introduces another availability dependency.
It is not selected. Consider it only under separate owner approval with receipts;
never infer Drive acceptance from GitHub digests or research metadata.

## Bounded bb128 preparation quote — not yet run

Finish small local implementation/tests first. Proposed host-only packaging and
runtime qualification: **25–35 minutes central, 60-minute planning reserve**,
not an elapsed-time cutoff. Historical v0.6.0 splitting/verification, 59-second
reconstruction and 123-second native startups guide this estimate; ordinary
cache/disk/source-build conditions may vary. Full-size checks are pending.

New NVMe space: 42.919 GB parts + at most14.307 GB sequential reconstruction
scratch + <=1 GB source/logs; request **65 GiB free plus 20 GiB working headroom**.
No HDD staging or duplicate dependency copies. Expected one-model worker memory
about15 GiB; recommend32 GB. No payload crosses to a Mac: only small code/receipt
transfers over SSH. Mac payload transfers, if separately needed, wait for M4 and
use its confirmed `bb128-lan` Ethernet link. The M4 can stay off for this plan.

Read-only October23 preflight saw idle bb128, no campaign mutex owner, ~126 GiB
free NVMe/~228 GiB HDD, ~122 GiB available RAM/~432 MiB used swap. These are dated
observations, not admission guarantees. Recheck open PRs, actual jobs, disk/RAM/
swap, required sensors, and the normal `/tmp/cfr-cygnus-exclusive.lock` immediately
before work. Acquire that mutex nonblocking and an owned release mutex. Do not
wait on, stop, reprioritize or change another job. Use the existing CPU90°C/
Thermistor15 100°C/missing-sensor guard and owner STOP path, no new scheduler or
machine configuration. Requote if another job or changed storage invalidates this.

Protected dependencies: PR404's entire `main-v1` root, all six endpoints/mass
receipts/traces/failures/source/build/environment; PR400/402 parent/build/environment;
`/home/dberweger/cygnus-qualification-20261014/tables`; PR398/search inputs;
v0.6.0 PR369/371 parts, source, binaries, receipts and journals; all open PR roots
and dependencies. Read selected model/K50 files only. Use a fresh owned release
output root; no modification or relocation of protected inputs. The vacuum-cleaner
owns research cleanup, staging and archival upload; coordinate before host admission.

## Verification barriers and recoverable publication

1. **Research provenance (done, compact).** Retain the original settled-result
   hash, frozen source and six audit receipts. Committed result JSON has a separate
   formatting hash and parses identically. Small header/stat inspection is not a
   fresh full-model audit. No new science is required.
2. **Prepare parts (pending).** On clean source, run `build_v061_bundle` once per
   seed into fresh directories. One source pass writes parts and calculates part/
   whole SHA256, checks the header and source stability. Save exact manifest hashes
   and the output receipts. It reports prepared, not independently read back.
3. **Independent reconstruction/runtime (pending).** Run the shipped verifier
   `-I -S --assemble` once, checking all parts and the whole pinned binary together;
   omit a redundant preceding full verifier pass. Run `check_v061_runtime` per seed
   with explicit source/K50/cache/binary/output paths: six human +six spectator
   integration hands, one shared weight table, exact identity, restricted sizing,
   privacy, conserved chips, replay before/after restart. These hands estimate no
   strength. Process one model at a time. Retain private journals outside Git.
4. **Review and approval (pending).** Attach compact measured proofs to this PR;
   green CI and resolve review findings. Owner explicitly approves merge/tag/
   publication. Tag exactly the reviewed merged source. Rebind approved metadata
   in fresh paths using `--reuse-bundle OLD --reuse-source QUALIFIED_COMMIT`;
   hardlink existing parts on the same filesystem, copy new small source assets,
   and regenerate checksums. Rebinding checks lengths and declares reused parts;
   it does not pretend to be another payload audit. Keep prepared manifests intact.
5. **Inspect live release before uploading.** Fetch current release/tag target
   and all asset metadata (paginated if using the API); compare with retained
   receipts. `gh release view v0.6.1 --json assets > live-assets.json`, then:

   ```sh
   python -m scripts.plan_v061_publication --bundles APPROVED_BUNDLES \
     --expect-source REVIEWED_MERGE --live-assets live-assets.json
   ```

   A missing release is an explicit empty inventory after checking the tag/release
   list, not an excuse to start a second publisher. The planner never uploads.
   Reuse matches by name, bytes and GitHub SHA256 digest/asset ID; stop on missing
   digests, conflicts, duplicates or unexpected assets. Do not clobber/delete.
   Upload only missing approved assets sequentially, record returned ID/size/digest
   immediately. After an ambiguous failure refresh inventory before retrying.
6. **Public proof (pending).** Check draft asset digests against local pins; skip
   a redundant authenticated full download when GitHub has the exact digest.
   After approved publication, re-fetch the release by tag and refresh every
   canonical `browser_download_url`, retaining the same asset IDs. Never reuse
   `untagged-…` URLs. Run the resumable downloader anonymously against every seed
   with its approved manifest hash. Reconstruct while checking part/whole hashes
   and run each short runtime check. Reuse already downloaded identical files
   and receipt-covered unchanged K50 files, never replay successful transfers
   merely to restart a coordinator. The native loader's own validation is still
   mandatory. Record public availability separately from uploaded/digest-matched.
7. **Closeout.** Only then state public download/reconstruction/runtime verified,
   save per-asset/source/manifest/runtime receipts, release notes and final status.
   Preserve all failures/partials. No claim about a Drive archive without the
   owner's matching receipt; storage relocation records remain off GitHub.
