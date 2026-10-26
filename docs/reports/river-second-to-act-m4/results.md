# PR433: M4 fixture qualification passes; learned-model panel unrun

**141 native library tests,2 legal-generator tests and12 Python tests pass on M4.**
The48-root legal-observation manifest reproduces byte for byte. Guarded fixture
execution took66.98s, with0.892GiB sampled peak process-family RSS and nominal
thermal state throughout. This qualifies native fixtures, not playing strength,
learned-policy coverage or complete learned-policy decision latency.

## Correctness and scope

The generator constructs48 observations using the legal three-player engine and
production menu:12 first-to-act and36 second-to-act roots, with all histories,
boards, entry conditions and seats retained. [Every root](panel.csv) is labeled
model-panel-unrun; manifest generation is not a solve. Its SHA256 is
`9394fad0bba108f75cf6fbcb7955d259598b2da919711dadf0a753618098eb76` in both processes.

All native library tests pass without ignored tests, including:

- Actual-hero-blocked opponent actions fall back; compatible joint action shares
  match the1/3 and2/3 controls rather than marginal1/2.
- Second-to-act reconstruction retains the opponent prefix; root solving plays
  the taken child and scales quality to that subtree.
- Retained on-tree rows preserve original probability bits; off-tree and
  unconverged paths retain labeled blueprint fallback without re-solving.
- Unsupported second-to-act audits/exports remain refused.

The12 Python checks cover admission boundaries, wrong-game input rejection,
complete panel/test accounting and the existing whole-hand/expectation fixtures.
No production solver, regret implementation, menu or default was changed.

## Resource correction and preserved history

The original fixture-only RAM forecast was unnecessarily conservative.
Execution source `d1da0e569adc3e336dbfb8d1d5987b9143a05ea7` refused admission
before any build/test. A later owner-requested continuation at
`a1f532f4ce5a7157a27a76d3a33770122480f94b` also refused, recording6.401GiB
available against7GiB required. [Original receipts](admission.json) and both
failed roots remain unchanged. These were resource-admission stops, not failed
scientific comparisons or failed native tests.

The owner requested closing non-Google apps. One normal termination pass exited
23 of24 original optional app/helper processes, including Adobe, Logitech,
Ollama, ChatGPT Helper and Weather; photo analysis did not exit within the bounded
wait and was not force-killed. Chrome/Google services, networking and essential
macOS processes were preserved. No service was disabled or repeatedly killed.
RAM availability fluctuated; the receipts do not establish a causal amount
reclaimed by these exits.

Before the successful attempt, we prospectively repriced **fixtures only** using
preserved same-host PR406 receipts: builds peaked at924,106,752B and native tests
at904,413,184B, sampled. The new family forecast is4GiB plus1GiB available
headroom, more than4.6times the largest prior sample. The separate learned-model
forecast ceiling remains6GiB and requires its own admission. No thermal/STOP
checks, sample counts or solver settings changed. This was an explicit resource
amendment for a fresh engineering attempt; it did not overwrite either refusal.

## Measured execution

Frozen source `86504259bfde570ed663e2841520250032ac4b53`, October26
08:27:13–08:28:20UTC. One persistent controller, sequential stages; native tests
and builds use two threads, Rayon one. All seven stages return0.

| Stage | Wall seconds | Child CPU seconds | Sampled peak family GiB |
|---|---:|---:|---:|
| Source-bound thermal helper build | 2.05 | 0.58 | 0.010 |
| Native library build/tests | 48.08 | 170.00 | 0.892 |
| Generator build/tests | 11.28 | 12.69 | 0.525 |
| Python tests | 1.06 | 0.09 | 0.010 |
| Generator executable build | 2.09 | 2.98 | 0.212 |
| Manifest generation, initial | 1.06 | 0.06 | 0.002 |
| Manifest generation, reproduction | 1.06 | 0.06 | 0.002 |

Controller wall66.98s; summed measured child CPU186.46s. These exclude source
preparation, admission refusals, app-closing operations and post-verification.
There were65 resource samples: minimum available RAM6.317GiB, maximum swap1MiB,
thermal state always nominal and memory-pressure level1. RSS is sampled, not an
exact peak or a measurement of total machine memory. This was not an isolated
benchmark. No per-sensor°C claim is available from the Mac thermal-state API.

The complete owned root, including all three source snapshots and prior
attempts, occupies1.749GiB allocated, below the8GiB envelope. Post-verification
free SSD was29.869GiB. All5,990 frozen source files were rehashed; source remained
clean. Both ordinary/study locks were released with their original inodes.

## Input limitation and interpretation

The bounded catalog contains12 policies, all four-, five- or six-player. Gzip
headers were checked without loading their weights; no compatible three-player
policy was admitted. This is a bounded catalog finding, not an exhaustive claim
that no suitable model exists anywhere. Native test fixtures are synthetic;
there were no external learned-policy loads or model-panel requests.

| Deliverable | Verdict |
|---|---|
| Full native library and relevant Python fixtures on M4 | Pass:141 +12 |
| Legal generator on M4 and manifest reproduction | Pass:2 tests;48 roots ×2 identical generation |
| Model-backed48-root panel and12 pre429 controls | Unrun: no compatible input |
| Learned-profile reproduction and pre429 version parity | Unrun |
| Learned-policy support/fallback rates and complete latency | Unmeasured |
| Model-panel cost preflight and budget admission | Unrun |

The planned130 model requests were never sent. M4 fixture correctness is now
qualified; this does not establish a learned-player speedup or strength gain.
Any model-backed continuation first needs an admitted small local three-player
policy with provenance, matching K50 and a cost-only preflight. Do not train,
fetch a mature model or expand scope to fill the gap automatically.

## Evidence and preservation

[Compact verified results/proofs/costs](results.json), [all48 root statuses](panel.csv),
[original admission evidence](admission.json). Result SHA256:
`3143526bf0fb895c8efc58ba7afd35a9185e76575716b834c72e52babfb1b670`;
config `2fc0469a9a472029e65bdf6619d27aa185d2b6bc5a8d00ebd1cd2a4286936c6d`.
Ordinary source, logs, both refused attempts, amendment, app-operation receipts,
manifest copies and post-verification remain at
`m4:/Users/dberweger/Local/river-second-to-act-m4-20261026/`;
successful subroot `qualification-v3-evidence-priced/`.

The original preparation receipt accidentally labeled a Python file descriptor
as a lock inode; its preserved correction identifies the error. Controller
locking uses actual fstat inodes. A separate read-only process snapshot initially
hit an inaccessible process record; it was corrected without affecting tests.

bb128/PR431, cleaner uploads and research inputs were untouched. Only small Git
source fetches and compact metadata retrieval used network. No ZIP, cache/Drive
publication, deletion or archive acceptance is claimed. Cleaner owns future
packaging; use retained M4 originals until then. No merge or automatic scientific
continuation is authorized by this fixture-only completion.
