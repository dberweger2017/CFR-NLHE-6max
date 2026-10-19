# Three-player100BB campaign: cost admission first

[Proposal349](https://github.com/dberweger2017/CFR-NLHE-6max/issues/349).

The owner requested the same style of overnight campaign at100BB after the
three-player20BB study, and asked to put the idle bb128 to useful work.
This first phase measures whether that requested workload is practical; it
does not launch the full training or claim poker strength.

## Question and fixed pilot

Use the already qualified native fast CLI pinned by the20BB study (binary
SHA256`fc37a562f8d3753d920b07b5d35c6deabe75fc846196b176f749187a3b3ac790`), full-street
averages, K50, minimum/pot/conditional-jam menu,8roots/seat,16threads and
three100BB stacks (10000chips, blinds50/100). Fresh training is mandatory:
20BB checkpoints have a different game identity and cannot be resumed here.
PR336 pruning, PR344 compact keys and PR347's new store are excluded. The enclosing
overnight configuration is source4cd199a5; the reused CLI comes from the earlier
fast-mode qualification, not a new build from current main.

Before measurement, verify fresh200K checkpoint identity at1vs16threads and
fresh400K vs200K+resume400K. Checkpoint SHA readback and headers must match
the100BB game, sampling, full-average scope and seed. Then train one separate
cost-only seed2026101935001 continuously through100M/200M/500M, saving at
each endpoint and using the preceding checkpoint for the next segment.
Node targets end on complete iterations. The150M-entry cap never freezes.
Calibration seed/outputs are excluded from any later final strength claim.

Report nodes/iterations, entries and marginal growth, sampled total stage RSS,
training/save/overall wall and child CPU time, checkpoint size/hash, temperatures
and swap telemetry. Native training time is elapsed minus save; remaining wall
includes loading/hash/monitor overhead and is not labelled pure loading time.
Any20/100BB comparison states the existing20BB data used a different trajectory.
The old production size study saw9.67M vs4.91M keys at20M nodes; its old
allocation forecasts predate compact storage and are not current RAM estimates.

Local linear3B/10B scenarios describe extrapolation, not confidence bounds,
proof of saturation or permission to start the full campaign. No poker outcomes are collected.
A capacity/resource/identity/numerical failure is terminal, preserved and
reported; no automatic retry, target reduction, cap increase or budget reset.

## Resources and storage

bb128 only, both study and normal compute mutexes nonblocking. All16 logical
CPUs, nice10, one-thread BLAS/OMP,32GiB child-family RSS and48GiB address-space
limits. CPU90C/Thermistor15100C immediate stops; missing sensors stop; admission
belowCPU70C/Thermistor80C. Available RAM floor8GiB. Swap absolute/growth is
telemetry only, following the owner's instruction. A fixed20-minute outer
fail-safe starts at pilot launch, covering fixtures, input checks and all saves;
individual CLI training has a600s bound, and a time stop cannot pass a node gate.

Retain50GB free on both homeNVMe and the output HDD. Reserve12GB new output
growth in a fresh owned cache subdirectory. Tables remain in RAM; checkpoint
writes go to the HDD at rest because old unique evidence still occupies tmpfs
and NVMe has only~5.5GB above its floor. Include that I/O placement in timings.
Source/config/logs/failures/checkpoints remain protected; no cleanup, archive,
other-job changes, OS/driver/fan changes or M1/M4 scientific compute.

## Full campaign decision after the pilot

The owner selected a10B-node endpoint for each of three fresh100BB seeds,
establishing earlier100BB
anchors and comparing later fixed checkpoints with them and all four scripts,
with TensorBoard development curves, independent replay/reproduction and fresh
reserved final roots. The20BB models are not same-game baselines. Exact targets,
entry/storage/evaluation-memory budgets and total cost must be frozen from
measured admission before that main study starts. The current PR admits only
the pilot; it never silently starts an unquoted full campaign. The200BB campaign
is a separate run and is outside this PR. Neither campaign is a release promise.

## Proposed100BB main design (not admitted by this pilot)

The owner accepted100BB only at10B nodes per seed. Use three fresh final seeds,
separate from the calibration seed, with the established unpruned fast recipe.
Retain1B/3B/10B recovery checkpoints; the1B average is the same-game anchor.
The20BB policies are not valid same-game opponents or resume inputs here.

Use immutable in-memory probes every1B nodes,128six-hand blocks against each
of random/check-call/tight-aggressive/pot-pressure. Reused monitoring deals are
for development curves only. Before main, prove the100BB monitor equals exported
policy probabilities and played paths, reproduces/replays, preserves training
checkpoint bytes, and has projected monitoring overhead below10%.

The intended final matrix is the earlier overnight design at the new depth:
10B vs own1B and cyclic other-seed1B, both singleton orientations, plus10B and
own1B as singleton against all four scripted pairs. Each of36 lineups has8192
fresh six-hand blocks:1,769,472 final hands plus the same reproduction count,
all independently replayed before a global readout. Report per-seat, position,
coverage and every adjusted scripted contrast. Primary improvement requires
all three same-seed oriented singleton-contrast lower95 bounds above zero;
cyclic noninferiority requires all three lower bounds above-5BB/100. These
contrasts are not pooled per-player returns. Scripted differences have12-way
Bonferroni intervals; an upper bound below-10BB/100 is a severe adverse result.
Neither favorable monitoring curves nor inconclusive final results extend work.

Provisional planning allowance is4–8hours including verification, with an8-hour
outer maximum for a separately admitted main launch. This is not a measured ETA.
Before main, freeze seeds and noncolliding roots, source/binary hashes, qualified
100BB harnesses, an entry ceiling and memory/storage/evaluation budgets. Require
the measured forecast with25% allowance to fit the full remaining allocation.
A credible model-growth envelope and a successful evaluation-memory qualification
are required; a fast traversal measurement alone cannot admit10B. The pilot's
150M-entry ceiling is not permission to freeze the table or raise limits in place.
