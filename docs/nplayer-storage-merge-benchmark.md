# N-player storage and saving comparison

Owner-authorized October 18, 2026; implements the host-side review experiments
already requested in issues #323/#324 for PR331/PR333. The objective is an
engineering comparison, with no playing-strength, new-recipe or release claim.

## Fixed comparison

Three sequential arms: main `3f9bfbdcb54b17ca530419b0e84e663fcf0d8b47`,
main plus PR331's two commits (`8303aa77`, `7bcbce9d`), then that combination
plus PR333's `16dbe015`. Store complete patch/source hashes and binary receipts.
The common harness adds only phase timing/reporting around the existing library
load, training step and save functions. Same Rust toolchain, locked dependencies,
release settings and path remapping for all arms. No fast training, pruning or
fast gzip. Native code in main differs from PR331's original base only in an
unbuilt HU200 blend example before these patches.

Each arm independently resumes PR292 seed2026101541's three-player20BB raw
checkpoint at1,000,000,057 actual nodes and29,025,056 entries:
`bb128:/home/dberweger/nplayer-blueprint-phase2-20261015/training/2026101541/1000m.gz`,
1,199,517,402 bytes, SHA256
`262334b77373c7f418078861ea57fbce181d126c5dda032aa2ff22758a876f21`.
Its accepted archive/member restoration provenance remains in PR292's
[member index](reports/nplayer-blueprint-phase2-artifacts/archive-model-members.json)
and RESULTS_INDEX. Confirm the input-owning PR is merged before using its
retained input in place; never modify that root.

Keep full-average scope3, menu v1, K50, blinds50/100, stacks2000 each,
seed2026101541, max_entries150M and freeze disabled. Save at the first complete
iteration at/above1.1B,1.2B,1.3B nodes. Do not restart between saves. No extra
exports, hands, growth arms or outcome-driven repetitions. Each arm adds300M
nodes approximately; total new work is900M, with nine retained checkpoints.

## Measurements and decision

For each arm/milestone retain actual nodes, iterations, entry count, training
seconds/nodes per second, save seconds/bytes, sampled training and saving RSS,
and input-load duration. Retain wall time, CPU seconds, read/write counters,
temperature/fan/resource traces, output hashes, failures and any partials.
Save time includes the existing writer's flush/fsync and atomic rename; hash
verification is separate. Saving MB/s refers to compressed bytes, not raw rows.
Memory is sampled every0.5s with boundary samples and can miss transient peaks.

Compare checkpoint SHA256 at every milestone. Mismatch, changed inputs,
incorrect counts, invalid training, resource stop or nonzero exit stops the
campaign, retains evidence and forbids automatic retry. A non-nodes cap stop
is not a completed endpoint. No automatic merge follows these numbers.

Report all nine rows plus arm totals and ratios versus baseline. Report shared
host load and fixed run order baseline→331→333. Inputs are read/verified before
the arms; no system cache flush, external-job changes or host tuning. One pass
is suitable for large effects, not a precise claim about a few-percent change.

## Resources and preservation

Hold `/tmp/cfr-cygnus-exclusive.lock` nonblocking from build/admission through
the fixed run; refuse if another owner holds it. Owner reported release, and
read-only verification at08:54:30UTC October18 found no holder. Recheck before
launch. Use logical CPUs0–3 (four different physical cores), four Rayon threads,
one serial training thread and sequential arms. Same allocation for every arm.
Keep all work on owned NVMe paths; M1 only edits/coordinates.

Reserve20GB total owned working/output growth beyond launch usage, retain50GB
free NVMe, and allow no more than24GiB own child RSS/48GiB address space. Require
8GiB available RAM, host swap growth≤256MiB, CPU<70C/VRM<80C at admission; stop
only own child group on CPU≥80C, VRM≥85C, available RAM<8GiB, RSS/disk/swap breach
or missing sensors. A four-hour malfunction fail-safe protects this fixed task;
it is not work to fill or permission for a retry/extension.

All builds, hashes, input checks, fixture qualification and the full run stay
under the same resource supervision. Preserve three isolated source trees,
common harness, Cargo/toolchain receipts, patches and logs; keep bulky source
bundles/results under ignored working roots. Record input stat/hash pins and
restoration commands in RESULTS_INDEX. Archive through bb128's research cache
under the designated Drive root with manifests and upload receipts at closeout;
no local original is removed or uploaded acceptance claimed prematurely.
