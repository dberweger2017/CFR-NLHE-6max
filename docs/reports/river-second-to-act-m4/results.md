# PR433: implementation ready, M4 admission blocked

The M4 attempt stopped **before any native build, test or model load**. This is
an admission result, not a solver correctness or performance result. No policy,
menu, default or prior strength verdict changes.

## What is implemented and checked

The native generator constructs all48 declared observations through the legal
three-player engine and production action menu. Its two local tests pass: the
roots are repeatable, physically seat-balanced, correctly funded and eligible;
requests contain only the acting player's private cards. The manifest has12
first-to-act and36 second-to-act roots; these are synthetic engineering states,
not newly sampled arena hands.

The fixture-only M4 controller records source/runtime/input bindings, acquires
the ordinary and owned study locks nonblocking, and supervises owned build/test
processes using thermal and ownerSTOP checks. It cannot train or load a model.
Four new Python checks and seven existing relevant checks pass locally (**11
total**), including rejection of wrong-game models, missing/skipped test
summaries and incomplete panels. Local validation is on the M1, not M4 timing
evidence. No production solver or regret implementation was changed.

## Why execution stopped

Frozen execution source: `d1da0e569adc3e336dbfb8d1d5987b9143a05ea7`.
At06:53:28UTC on October26, the controller acquired both locks and refused the
6GiB fixture-family forecast plus1GiB admission headroom. It exitedRC1 without
starting a build or test. The original failure and source remain retained.
No scientific mismatch occurred, no automatic retry was made, and no other
workload was interrupted.

A separate06:54:30UTC read-only snapshot measured **6.833GiB available RAM**,
1MiB swap used, **31.142GiB free SSD**, AC power and nominal thermal state.
This was about171MiB below the7GiB admission requirement. It is a later snapshot,
not an exact reconstruction of RAM at the failed admission. The normal lock was
released. The earlier `memory_pressure`79% figure is not interchangeable with
available RAM in bytes.

The bounded local input catalog also contains **12 policies, all four-, five-
or six-player**. Their gzip headers were read without loading weight rows. None
can be substituted for this three-player solver. This is a catalog finding,
not an exhaustive filesystem search or proof that no compatible model exists.

## What remains unmeasured

| Deliverable | Status |
|---|---|
| Legal generator, new controller checks, relevant Python checks | Pass locally:2 native +11 Python |
| Full native and Python qualification on M4 | Unrun: memory admission stopped first |
| Model-backed48-root panel and12 pre429 controls | Unrun: no compatible model admitted |
| Fresh-process learned-profile reproduction and version parity | Unrun |
| Learned-policy support, fallback frequencies and complete latency | Unmeasured |
| Cost-only preflight and model-panel budget admission | Unrun |

Therefore there is no M4 speed, coverage, solver-quality or strength conclusion.
The planned130 model requests were never sent. Existing blocker-conditioning
and retained-session tests are included in the controller's full native suite,
but their M4 passage is not claimed by this attempt.

## Evidence and next action

[Compact admission/input receipts](admission.json) bind launch, failure, source,
catalog headers and the separate resource snapshot. Ordinary originals and logs
remain at
`m4:/Users/dberweger/Local/river-second-to-act-m4-20261026/`.
The preparation receipt's field named `normal_lock_inode` accidentally contained
a Python file descriptor; the preserved correction identifies this error. The
actual controller uses `fstat` for lock identity. No resource/lock exception was
used. A small read-only process snapshot initially encountered an inaccessible
process record; it was corrected without rerunning the controller.

A subsequent source-only improvement writes `admission.json` before rejecting
RAM, so a future attempt retains the exact admission sample. It also compares
stable content metadata rather than access time when checking borrowed policy
headers. Neither change was executed as another M4 attempt.

Keep the PR in draft. Resume fixture qualification only with adequate measured
M4 headroom in a separately retained attempt. The model panel additionally needs
an admitted small M4-local three-player policy and its provenance; otherwise its
status stays unrun. Do not train or fetch a mature model to fill that gap.

bb128/PR431, cleaner uploads, other jobs and protected inputs were not touched.
Only a small Git source fetch and compact metadata retrieval used the network.
No evidence ZIP, bb128 cache, Drive publication, deletion or acceptance is claimed.
