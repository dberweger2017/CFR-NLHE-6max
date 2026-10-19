# PR352: bb128 launch qualification

The owner authorized qualification and launch on October19: “Perfect do those
things and start the run.” The release build and real K50 engineering fixture
pass. The main3B study is configured but awaits GitHub CI; no main training or
held-out study hand has run. [Compact receipt and hashes](qualification.json).

Frozen controller/harness source is`66150f3b5089edc4c4dabf66c2a3a439d565953f`;
native library/arena is the historical PR350 source
`b9882e7e728847a58691995e64eabd4563ea0991`. Only the new study host and shared
checkpoint writer overlay the archived native tree. The isolated deployed Git
contains exact commit/tree objects and required source blobs, without parent
history or research models. It supports the pinned build and source manifest;
it is not a full historical checkout.

## Qualification evidence

- Release build passed under the temperature supervisor and both compute locks.
- All16 focused Linux Python tests and4 release native example tests passed.
- A separate development fixture used K50,100BB,16threads,100K table cap,
 5M nodes and a5-second cumulative clock. It exercised344 pruned actions by
 the node endpoint. Development deals are disjoint from final study roots.
- Actual active traversal was0.756803895s to the node fixture, then
 4.246661123s after exact-checkpoint resume, totaling5.003465018s. I/O,
 auditing and evaluation did not advance the restored clock.
- Resumed and independently uninterrupted trainer bytes matched exactly:
 SHA256`f2b6bc5284639d8cdf64debe57fbee56349aae94d44d0bf0126d072c2d3f580a`.
 Full-average export bytes also matched.
- Both development comparison phases passed independent policy audits,
 two-model cache accounting, all-hand replay, exact reproduction and readout
 barriers:240 initial hands plus240 reproductions. A separate fixture saved
 the clock endpoint before the node endpoint and bounded its overshoot to one
 completed iteration. These small fixtures establish plumbing, not strength.
- Qualification sampled peak family RSS was1.357GiB, CPU60°C and
 Thermistor1552°C. These are small-fixture observations, not production
 memory/temperature forecasts.

Raw source bundles, build receipt, qualification wrappers, logs, traces,
checkpoints and exports remain at
`bb128:/home/dberweger/nplayer-pruning-strength-20261019/`.
The wrapper hashes are in the receipt; retrieve them with
`scp bb128:/home/dberweger/nplayer-pruning-strength-20261019/qualify{,_child}.py planning/`
into an ignored working directory, then verify their SHA256 before reuse.
No Drive upload, archive acceptance or cleanup is claimed.

## Production configuration

The production configuration was created in a fresh interpreter, without the
development fixture overrides. It retains the [declared protocol](../../nplayer-pruning-strength-study.md):
3B nodes,630.740595090997s cumulative active traversal,250M table cap,
16threads,seed2026101935003,pruning0.05BB after200iterations, full averages,
and8192six-hand blocks for each of10lineups in each phase.

Root:`bb128:/home/dberweger/nplayer-pruning-strength-20261019/study-v1`.
Configuration SHA256:
`29828c1e260c871bfa7b6729d35a1b45486104203fcce488a753ec3a0ee4b9f2`.
The683 controller/source file hashes and both native binary hashes are pinned.
The historical3B inputs and existing K50/Python environments remain read-only.

Temperature is the only automatic resource stop: CPU90°C,
Thermistor15100°C, or missing required readings. Disk/swap inspection is manual;
there are no runtime, RSS, available-RAM or address-space caps. Correctness,
model identity, replay and genuine execution failures still terminate with
preserved evidence. No automatic retry, default adoption or long-run launch.
