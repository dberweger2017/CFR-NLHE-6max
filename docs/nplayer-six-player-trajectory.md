# Saved six-player trajectory diagnosis

[Proposal420](https://github.com/dberweger2017/CFR-NLHE-6max/issues/420).
Optional descriptive context for activePR419, never its admission prerequisite.
No new hands, models, training, policy changes, search or release work.

Freeze3B→10B and10B→15B across all eight PR417 fields. Use the24 unique initial
traces in [the pinned inventory](../configs/research/nplayer-six-player-trajectory.json):
7,989,712,885bytes,1,179,648 distinct physical hand instances and786,432 paired
comparisons. Every4,096dealblock ×12seatings is included in each of16panels.
The3B baseline comes from6B-initial as in PR417's verified jobs; cross-job3B
trace identity was established there. Reuse10B files for both contrasts.
Original raw result SHA256:
`361e40b70f195d578592d1155738340917d753fdd2cbd3866236adee3bd3e5c1`.

Transfer only the selected initial traces over the confirmed private Ethernet
192.168.77.1↔.2 link, one bounded low-priority stream, with destination SHA256
matching recorded independent-replay proofs. Repeats, models and checkpoints
are not copied. Existing PR417 replay/reproduction remains provenance; this
analysis does not claim another engine replay. Scan every row and recompute
full file hashes during each of two deterministic analysis passes. Results must
match exactly before global readout. Preserve all partials/failures; no automatic
retry, smaller panel, outcome filtering or tuning.

Find the first different sampled action while deal/seat/public prefix and fixed
opponents agree. Classify by street, original positive/zero/missing lookup pair,
action kind, same-kind raise-size direction and position. Include unchanged
hands and exact-zero returns. Record later missing exposure in each arm,
matched-prefix actions and all reached focal actions separately. The scanner
uses no hidden cards to classify decisions; privileged deck values only validate
paired-deal identity. It cannot observe changed probabilities when sampled
actions coincide.

For each partition report hand counts, conditional mean whole-hand delta and
unconditional contributions whose sum equals the old paired delta. These are
associations, not causal action values. After divergence, reached histories and
action denominators differ. Verify the12-seating dealblock mean and standard
error against existing results, and reconcile every focal lookup counter.
No new category hypothesis tests or acceptance gates are introduced. One seed,
restricted circular opponent orders and already-inspected outcomes remain limits.

M4 uses the existing Python3.11, a single streaming worker and no mature model
loading. Working-memory planning allowance512MiB; copied inputs~7.44GiB,
plan10GiB total new workspace. Use the ordinary M4 research mutex nonblocking
for the full scan. No bb128 compute-lock exception is required or granted;
source copying must yield to PR419 critical I/O and uses one capped stream.
Do not modify source models/traces, environments, host settings or timers.

Publish a transfer/verification/two-scan/report quote before full transfer or
analysis. Only tiny synthetic fixture qualification is allowed in preparation.
The main study requires owner allocation acceptance. Record actual transfer,
wall/CPU/RSS costs and concurrent419 context. Git receives compact reports only;
source, manifests, copies, proofs, failures and raw derived data stay in ignored
working roots. Owner manages later archival; no cleanup or Drive acceptance
is implied by this task.

## Completed bounded diagnosis — October 24

Owner approved the45-minute allocation. The finite continuation waits for
PR419completion, then copies/verifies all24inputs and scans all16panels twice;
active operation7m21s, completion13:34:54UTC /15:34:54Madrid. All hashes,
reference counters and deterministic outputs match. [Analysis and complete costs](reports/nplayer-six-player-trajectory/results.md)
supersede historical awaiting-launch language. No new hands, model loads,
scientific retry or follow-up; prior417adjusted strength conclusions unchanged.
Ordinary source/copies/proofs/failed packaging retained for the owner's cleaner
and later verified ZIP archive sets. Research-payload Drive acceptance pending.
