# v0.6.1 installation (pending publication)

These commands describe the proposed release. No v0.6.1 tag, assets or verified
public availability exist yet. Use the final reviewed tag and source/manifest
hashes from its publication receipt only after owner approval and publication.
Local reviewers can use the feature commit with an explicitly prepared bundle.

Choose seed `2026102240001`, `2026102261001` or `2026102261002`. Each is a separate
qualified 10B average; there is no blended or highest-score default. Use Python
3.11, Rust, 32 GB RAM or more and 35 GB free disk for one seed. Download about
14.307 GB plus 1.384 GB K50 dependencies; reconstruction keeps a second model
copy. The 16 GB Macs can use a loopback SSH tunnel to a larger machine.

```sh
git checkout v0.6.1 # only after approved publication
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-play.txt
cargo build --release --locked --manifest-path native/hu20-trainer/Cargo.toml --example nplayer_serve
python -m scripts.download_v061 --seed 2026102240001 --out models/v0.6.1/bundle \
  --expect-source REVIEWED_RELEASE_COMMIT --manifest-sha256 APPROVED_SEED_MANIFEST_SHA256
python3.11 -I -S models/v0.6.1/bundle/verify_v061_bundle.py models/v0.6.1/bundle \
  --seed 2026102240001 --expect-source REVIEWED_RELEASE_COMMIT --require-publication \
  --assemble models/v0.6.1/cache/NP3-200BB-v061-seed-2026102240001.bin
python -m scripts.play_v061 --bundle models/v0.6.1/bundle --seed 2026102240001 \
  --expect-source REVIEWED_RELEASE_COMMIT
```

The downloader is run from the trusted checkout, not from a remote script. It
pins the seed manifest by SHA256, then checks exact release/model/dependency/
source/approval fields and each download's size/hash. A complete valid file is
reused; partial downloads resume only when the server honors the exact Range.
A corrupt complete file or bad partial is preserved and refuses further progress.
Inspect failures and choose a fresh directory when needed; no automatic deletion
or replacement is performed. Reconstruction separately verifies ordered parts,
whole-model SHA256 and binary source/game/schema/dtype/mass metadata in one pass.
Do not run a separate full `verify_bundle` pass immediately before `--assemble`.

The K50 dependencies reuse the exact public v0.5.3 asset URLs/hashes. To reuse
existing regular files in a physical K50 directory, pass `--card-tables K50_DIR`
to the downloader, verifier and launcher. Their hashes are always checked.
No Google Drive login, sharing change, mirror or archive is required. A later
optional whole-file mirror must use the same model hash and have its own receipt;
no such mirror is currently promised. A complete model already in the cache
can be verified/launched without retaining its split parts.

Open http://127.0.0.1:8766/ and enter the token stored in
`results/play-v061/access.token`. The human table has two independently sampled
bot seats sharing one weight table; `--watch` uses three bot seats and exposes
the spectator decisions/cards. Human privacy and disclosure follow the existing
table contract. Journals are private and replayable; do not distribute SQLite files.
For a laptop UI with the model on a larger host:

```sh
ssh -N -L 8766:127.0.0.1:8766 USER@HOST
```

Read the host token over SSH; keep it out of URLs/logs. The server binds loopback.
Stacks reset to 200 BB, blinds 50/100, button rotates over exactly three seats.
Restricted minimum/pot/conditional-jam sizing applies to everyone. Search,
free sizing, other depths, rake, antes and adaptation are outside this release.
Missing and represented zero-mass rows retain uniform legal-menu fallback.
Wrong stack/player/schema/menu/cards/export/dtype pins fail before use.

For review, build from a clean exact feature commit:

```sh
python -m scripts.build_v061_bundle --seed SEED --model QUALIFIED_BINARY \
  --card-tables QUALIFIED_K50 --out FRESH_BUNDLE --source-sha FEATURE_COMMIT
python3.11 -I -S FRESH_BUNDLE/verify_v061_bundle.py FRESH_BUNDLE --seed SEED \
  --expect-source FEATURE_COMMIT --card-tables QUALIFIED_K50 --assemble FRESH_CACHE/MODEL_FILE
python -m scripts.play_v061 --bundle FRESH_BUNDLE --seed SEED --expect-source FEATURE_COMMIT \
  --card-tables QUALIFIED_K50 --cache-dir FRESH_CACHE --allow-prepared --data-dir results/play-v061-review
```

`--allow-prepared` is a local review opt-in, never publication approval. Prepared
manifests default to `publication_approved: false`; approval fields are workflow
declarations, not signatures. Trust the reviewed source and release receipt.
A stale `.assembling` file is preserved; use a fresh reconstruction path after
diagnosis. Existing defaults and v0.6.0 bundles/launch commands remain unchanged.
