# v0.6.1 — qualified three-player 200 BB blueprints

Three exact 10B-node average policies from PR404, seeds `2026102240001`,
`2026102261001`, `2026102261002`. Choose one explicitly. The game is unraked,
no-ante three-player cash Hold'em, 200 BB reset each hand, 50/100 blinds,
K50 cards and the existing minimum/pot/conditional-jam menu. All seats use the
restricted menu. Missing and stored zero-mass rows retain uniform fallback.

All 30 prospectively declared gates pass: 24 absolute scripted-profit tests,
three own-3B improvement tests and three cyclic noninferiority tests. Bounds
are one-sided simultaneous 95% Student-t/Bonferroni for the 30-test family.
10,543,104 initial hands independently replay; the same number reproduce
byte-identically. Reproductions are integrity checks, not independent samples.
[Model card](MODEL_CARD.md) explains comparison definitions and capped coverage.

Owner approval to proceed with publication was received October 23, 2026.
The release page and its publication receipt record the exact tagged source,
approved manifest hashes and completed public download/runtime verification.
Approval and local qualification alone do not establish public availability.
[Readiness](READINESS.md), [installation](INSTALL.md),
[publication procedure and costs](PUBLICATION_PLAN.md). Exact hashes and research
paths are in [MODEL_MANIFEST.json](MODEL_MANIFEST.json) and [MODEL_SHA256SUMS](MODEL_SHA256SUMS).

The policies remain float64 and byte-identical to the qualified binaries.
There is no new training, conversion, strength evaluation, search, ensemble,
action translation or model selection. v0.6.0 and existing defaults stay available.
No Nash equilibrium, universal, human or external-opponent strength is claimed.
