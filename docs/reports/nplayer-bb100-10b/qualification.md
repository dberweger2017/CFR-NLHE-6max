# Fixed 100 BB 3B→10B study: qualification and authorized launch

[PR355](https://github.com/dberweger2017/CFR-NLHE-6max/pull/355) implements
[proposal354](https://github.com/dberweger2017/CFR-NLHE-6max/issues/354).
The release build and realK50 engineering qualification passed on bb128.
**The owner-authorized main campaign launched October19 at20:08:19UTC, PID544891.**
Owner-requested completed-evidence relocation resolved the NVMe output-space
shortfall. The campaign uses its unchanged prepared configuration.
[Launch receipt](launch.json).

[Compact qualification/source/native/config receipt](qualification.json),
[informational full-job forecast](forecast.json),
[protocol and commands](../../nplayer-bb100-10b-study.md).

## Evidence

- 59 native library tests pass after the optional inference-row mass tag change.
  Three diagnostic example tests pass, including metadata lineage/corruption
  rejection and proof that the tag fits existing Row alignment padding.
- 31 focused Python tests pass, one existing Linux-only process test skips on
  macOS. All32focused tests pass on bb128 with no skips, and the three native
  mass-loader tests also pass against the pinned historical build on x86_64.
  The actual Linux guarded fixture pipeline passes all nine stages.
- The historical host trains a small100BB/K50/frozen10K reference to200Knodes.
  The new host resumes its100Kfixture parent to200K with **identical checkpoint
  and full-average export SHA256s**, and identical frozen key membership.
- Both every-row fixture audits produce checksum-bound original-mass metadata.
  A positive-mass uniform distribution is distinct from a zero-mass uniform
  fallback. Missing metadata/incorrect binding or counts refuse.
- All18mixed/direct/scripted fixture lineups complete216initial plus216exact
  reproduction hands; every hand independently replays against the pinned engine.
  Diagnostics-off evaluation reproduces another216identical hands. Against the
  old homogeneous host,120hands have identical deals/actions/states/payoffs.
- Persistent native evaluation proves exactly two model loads and one K50 set.
  Fixture evaluation loads in4.893seconds and plays in0.027seconds; these tiny
  model times are correctness/cost observations, not mature-table predictions.
- Qualification stages take31.054seconds combined wall. Sampled CPU maximum54°C,
  Thermistor15 maximum43.5°C. Native build used two compiler jobs and took28.12s.
  There was no thermal stop. The normal compute lock is released after fixtures.

The qualified source is`ecb08ada`; training library source is
`b9882e7e728847a58691995e64eabd4563ea0991`. Overlays are restricted to shared
checkpoint I/O/new hosts and the optional inference-row diagnostic tag. CFR
updates, sampling, keys, averaging, stored model formats and training table
layout remain the historical recipe. All native/code hashes are recorded in the
compact receipt; the complete source-file map remains in the qualification root.

## Why mature-table metadata needs care

PR350's retained full audit records79,729,265zero-average-mass rows out of
250,000,475entries (31.89%). This is a **table-wide fraction**, not a fraction
of encountered decisions, and is not a measurement of wrong actions.

The native loader streams the audited sorted zero keys and tags the already
resident rows; it does not retain a second huge key set or search it during
play. Ordinary policy loading leaves original mass unknown. Diagnostic labels
never change probabilities, RNG consumption or inputs available to a player.
Independent verification workers use read-only memory mapping and binary
search rather than eight large Python hash sets. Model-lookup decisions record
both policies on exactly the same reached observation.

The earlier PR352 report incorrectly wrote seven/79zero-mass rows after a
truncated preview was misread. Its unchanged committed audit JSON always
contained79,715,556/79,734,186; PR355 corrects only that prose. The strength and
timing numbers, raw models and inference probabilities are unchanged.

## Main-run forecast and physical storage

The forecast combines mature PR352 measurements with explicit allowances:

| Component | Approximate minutes | Basis |
|---|---:|---|
| Additional7B active traversal |24.2| Historical post-freeze4.83Mnodes/s |
| One endpoint processing |11.5| Half of prior two-endpoint nontraining overhead |
| Checkpoint reload |6.7| Planning assumption |
| Two full audits plus metadata |17.0| Prior audit cost plus30% |
| Two policy loads plus mass tags |8.1| Prior load cost plus15% |
| Native non-load work and replay |5.0| Planning allowance |
| Final verification and readout |3.0| Planning allowance |
| **Total** |**75.4**| Prospective, not a measured complete run |
| **With25% planning allowance** |**94.3**| Informational, not an automatic deadline |

These estimates can move with storage throughput, thermal/frequency behavior,
policy serialization size and actual reached histories. The3B→10B continuation
is one scientific endpoint, not another multi-seed overnight campaign. No
runtime/RAM/disk/swap kill thresholds were added: automatic resource stops are
stillCPU90°C/Thermistor15100°C/missing temperature readings; manualSTOP and
real correctness/accounting/replay failures remain terminal.

Predicted new output is **25.11GB decimal**, including about7.24GB of raw traces,
15.31GB of checkpoint/export and up to2.55GB of zero-key metadata. Trace sizes
scale the small qualification, while model sizes use the current3B artifacts;
10B serialization may grow even with fixed membership. Temporary space and
working headroom are additional. The manual snapshot shows only **18.50GB free
on NVMe**. This is a physical space shortfall, not a code-imposed budget refusal.
That qualification-time shortfall was resolved by the owner-requested
[completed-evidence relocation](../../artifacts/nvme-relocation-20261019.md):
verified free NVMe is now64.36GB. All open PR roots and protected model inputs
remain in place. The original18.50GB snapshot is retained as dated evidence.

## Retained roots and reproduction

All paths below belong to this PR under
`bb128:/home/dberweger/nplayer-bb100-10b-20261019/`:

- `source-v1/`: qualified source checkout at`ecb08ada`; original library commit
  retained in Git for the pinned native archive.
- `build-v1/` and`build-v1.log`: preserved SSH PATH/Cargo setup failure, before
  native compilation or any fixture/main science. No retry of final science.
- `build-v2/`: successful build, original-library source snapshot, binaries and
  complete build receipt. Cargo's installed absolute path resolves the setup.
- `qualification-v1/`: fixture checkpoints/exports/mass metadata, traces,
  failed/success receipts, exact replay proofs, resource logs and qualification.
- `main-v1/config.json`: unchanged frozen configuration. The owner-authorized
  launch is recorded in[launch.json](launch.json); source/runtime pins remain
  the qualified values.

To retrieve a compact proof into a fresh ignored directory:

```sh
mkdir -p results/pr355-retrieval
scp bb128:/home/dberweger/nplayer-bb100-10b-20261019/qualification-v1/qualification.json results/pr355-retrieval/
shasum -a 256 results/pr355-retrieval/qualification.json
```

The expected qualificationSHA256 and main configSHA256 are in[the receipt](qualification.json).
`source_files_canonical_json_sha256` commits the full file map using sorted keys,
compact JSON separators and UTF-8. The full map is retained in the remote proof.
Quote reproduction is`python -m scripts.quote_nplayer_bb100_continuation
/ABS/qualification-v1/qualification.json`; it reads costs only and launches no
work. Repeating real fixture qualification requires a **fresh owned root** and
the declared small-work command in the protocol; never rerun the main launcher
as a status/readout operation.

PR350 model inputs and PR352/353 evidence remain read-only dependencies.
Research-Cloud namespace`PR-355-nplayer-bb100-10b` is reserved; archival and
Drive acceptance are pending. Open roots, failed setup and raw fixture evidence
remain on bb128. No archive coverage, deletion or main strength result is claimed.
