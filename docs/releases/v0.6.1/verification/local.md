# Local preparation checks

October 23,2026; clean isolated worktree based on PR404's actual squash merge
`bbb71f408db6b1964541e22978628f8c60105313`. Original research checkouts untouched.

Python3.11 play dependencies plus pytest in an isolated temporary environment:

```sh
python -m unittest tests.test_v061_bundle tests.test_v061_distribution \
  tests.test_v061_runtime tests.test_v060_bundle -q
```

**30 pass**: 20 new v0.6.1 tests and10 unchanged v0.6.0 tests. Small real-format
fixtures exercise exact reconstruction, corrupt/reordered/missing/truncated parts,
whole-model pin enforcement even with recomputed part hashes, source/approval
refusal, metadata/depth/schema/menu/dtype rejection, preserved partials, symlink
refusal, external K50 reuse, metadata-only rebinding with retained parts, HTTP
Range resume and ignored/wrong ranges, verified-file reuse, publication inventory
conflicts/duplicates, exact research-manifest consistency, and real table-service
200BB/restricted-sizing/wrong-depth/player-count boundaries. The shipped verifier
runs with `python -I -S --help`, without runtime dependencies. This is not a
full-size native model qualification or a strength test.

Live read-only inspection: PR404 was open at `ccad689f` with auto-merge enabled;
all five checks succeeded, and it auto-merged at10:03:38UTC. PR369 is merged;
PR371 is open/incomplete. v0.6.0's55 live assets total43,830,087,031 bytes; existing
K50 assets at both v0.6.0 and v0.5.3 have the campaign's exact sizes/SHA256 digests.
No v0.6.0 asset upload or payload audit was repeated.

The original bb128 `results.json` is258,550 bytes and has the owner-provided SHA256
`6909662e4b2372c13981467723759ba5a37ffde7daa3899514e8d52c72c969b8`.
It parses identically to the committed readout (formatting hash
`3784cd2d4b5b3d79a5461510bf206577aaff0927708ac407a6a4c1008d06e26d`).
All 30 gate booleans and six checkpoint/export/binary audits reconcile. Three
small binary headers and file sizes match the release metadata. No model was
converted, trained, strength-tested, copied to a Mac or loaded by these checks.
[Full-sized part/readback/native proofs](qualification.md) subsequently passed as a separate barrier.
The broader local pytest selection (these four test files plus `test_repository_artifacts.py`
and `test_ci_scope.py`) passed 47 tests / 54 subtests in 24.55s. A helper help invocation
with base Python lacked the pinned engine; the isolated play environment passes.
