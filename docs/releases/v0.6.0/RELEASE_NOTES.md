# v0.6.0 — three-player 100 BB blueprint

Owner-approved release of the qualified three-player 100 BB blueprints.
Availability and verified per-file download links are recorded on the
[v0.6.0 release page](https://github.com/dberweger2017/CFR-NLHE-6max/releases/tag/v0.6.0).

- Three independently trained, fixed 10B average policies pass the prospective
  PR367 acceptance study on fresh held-out deals. Choose a seed explicitly.
- Packages the exact audited float64 binary weights and original mass tags in
  1 GiB GitHub parts, with whole-model/source/schema/K50 pins and a standalone
  verifier. Planned Drive links offer the same complete binaries as single files;
  those links remain pending public-download verification.
- The existing native legal-observation service and three-seat web table provide
  human play or spectator mode. One selected model is shared across bot seats;
  journals preserve exact deals, actions and decision seeds for replay.
- No new training, policy averaging, search, free-sized translation or default
  replacement. Existing heads-up releases remain available.

All 30 acceptance lower-bound gates pass; 2,635,776 initial hands independently
replay and reproduce exactly. Own-checkpoint gains are +32.79/+35.78/+33.70 BB/100.
The previous relative random/random+TAG regressions remain adverse evidence;
positive absolute profit does not establish uniform improvement or equilibrium.
See MODEL_CARD.md and the repository's full PR367 report.

Recommend 32 GB RAM and 35 GB free working space per selected seed. Download
roughly 14.15 GB of model parts plus 1.38 GB of K50 tables. The current eager model
reader is not a 16 GB laptop deployment. No performance or poker-strength claim
is inferred merely from successful packaging/runtime verification.
