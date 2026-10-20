# v0.6.0 installation

Prepared release candidate: publication is pending. These download commands become
available only after the owner publishes the v0.6.0 release. The release contains
three separately qualified 100 BB blueprints; choose a seed explicitly. There is
no blended policy or highest-scoring default.

Use a 32 GB or larger machine, Python 3.11, Rust and at least 35 GB free working
space for one seed. The download is about 14.15 GB of model parts plus 1.38 GB of
K50 tables; reconstruction keeps another 14.15 GB model. The 16 GB M1/M4 is not a
supported full-model memory target. First reconstruction/start can take several
minutes; later starts reuse the combined file but still verify/load it.

After publication, check out the reviewed `v0.6.0` tag before building:

```sh
git checkout v0.6.0
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-play.txt
cargo build --release --locked --manifest-path native/hu20-trainer/Cargo.toml --example nplayer_serve
```

Example seed 2026101935003
(the other choices are 202610200601 and 202610200602):

```sh
gh release download v0.6.0 --repo dberweger2017/CFR-NLHE-6max \
  --pattern 'NP3-100BB-v060-seed-2026101935003*' --pattern '*-k50.bin' \
  --pattern 'verify_v060_bundle.py' --pattern 'INSTALL.md' \
  --pattern 'MODEL_CARD.md' --pattern 'RELEASE_NOTES.md' --dir models/v0.6.0/bundle
python3.11 -I -S models/v0.6.0/bundle/verify_v060_bundle.py models/v0.6.0/bundle \
  --seed 2026101935003 --require-publication --expect-source REVIEWED_RELEASE_COMMIT
python -m scripts.play_v060 --bundle models/v0.6.0/bundle --seed 2026101935003
```

Open http://127.0.0.1:8766/ and enter the private token from
`results/play-v060/access.token`. You play against two independently sampled
instances sharing one selected model. Add `--watch` for a three-bot spectator
(table cards and decision probabilities are visible there). Human tables hide
opponents' private cards/decision probabilities until the appropriate disclosure.
All sessions keep private replayable journals; do not share their SQLite files.

Stacks reset to 100 BB each hand, blinds 0.5/1, button rotates. The model's fixed
training menu applies to everyone: minimum raise, pot raise and conditional jam
alongside legal fold/check/call. Free sizing, other stack depths, search, rake,
antes and opponent adaptation are excluded. Missing and represented zero-mass
rows keep their qualified uniform fallback. The UI's trained indicator means a
represented information key, not positive original average mass.

For local review of an unpublished, verified prepared bundle, add
`--allow-prepared`. That does not approve or publish a release. Corrupt, missing,
wrong-source/schema or unapproved public bundles fail explicitly; partial
reconstructions remain preserved. Use a fresh output path for an intentional
retry after diagnosing a failure. Do not overwrite original research inputs.
