# Expanded river search: beliefs, continuation and a fresh engineering panel

Owner-approved October 21, 2026, following PR377. This is bounded engineering
qualification, not training, a strength match, release adoption or permission
to launch the later whole-hand pilot. The estimate given before work started
is 4–6 hours for implementation, qualification, compute and reporting, including
approximately 1–2 hours of bb128 measurements. Engineering time is separate
from compute. A development-fixture calibration precedes fresh observations.

## Frozen scope

- Three-player, equal-stack 100 BB; first river decision has exactly two live,
  non-all-in players and one contested pot, under the existing observation
  contract. Later continuation includes legal facing-all-in decisions.
- One unchanged 10B model, seed `2026101935003`, SHA256
  `d835f61f4a5407bd47e8f8a5da849ef82c16ad21fce32f15dce72d5997275189`.
  The PR367 model and existing K50 input are read-only. This is not a
  cross-training-seed strength claim.
- Reference menu `pot-jam-cap3-v1`; candidate menu
  `pot-jam-cap3-root-check-min-v1`, adding only the opponent's minimum opening
  bet immediately after hero's root check. Keep PR377's cap, root menu,
  projected beliefs, DCFR(1.5,0,2) and blueprint fallback unchanged.
- No further menu tuning, off-tree re-solving, shared-model concurrency
  optimization, weighted rank-prefix implementation, added training or arena.

## Independent correctness fixtures

Before measurements, qualify a deliberately nonfactorizable joint chance law
against hand-calculated leaf, profile-value and best-response fixtures, including
both player orientations, ties, blocked holdings and zero probabilities.
Keep the existing product-law and scalar-reference tests. No solver-regret or
chance-law math is changed silently to improve a result.

## Matched-accuracy belief controls

Select 20 controls without reading any solve outcome. From the fresh 200-root
panel, rank cases by SHA256 of `panel-id/hand-id`. Take five in each public-pot
band `[0,5)`, `[5,15)`, `[15,40)`, `[40,infinity)` BB. If a band has fewer than
five, keep all of it and fill unused slots by the remaining global hash order.
Record the actual selection and strata before any control runs.

Both projected and exact-joint solves target each player's best-response gain
at most **0.01 BB**, checking `[64,128,256,512,1024,2048,4096,8192]` sweeps.
Keep the fixed 8,192-sweep limit. A control qualifies only when both solves meet
the target; otherwise that control and an all-control verdict are inconclusive.
The original PR376 controls/results/thresholds stay unchanged and remain indexed.

For each player separately report:

- `S`: the projected strategy's gain in its projected game (solver residual).
- `D`: gain of that same strategy under the exact law minus its projected-law
  gain (law-change diagnostic for a fixed profile).
- `R`: the exact reference's gain in the exact game (reference residual).
- `E = D + S - R`: deployed projected strategy's exact-game gain minus the
  exact reference's exact-game gain. This is the existing reference-comparison
  metric, not a pure causal decomposition of approximation error.

Preserve the **0.05 BB per-player excess threshold**, applying it to every
qualified control, with residuals and the identity above shown explicitly.
Do not relabel a threshold failure as a pure projection failure. A qualified
exact reference still describes the modeled action-likelihood law, not the
true opponent posterior or safe whole-game resolving.

## Retained-strategy interface

The persistent native worker owns at most one active retained hand. The
explicit begin/continue/release protocol binds a session to its public hand ID,
hero seat and own holding, board, complete original public history, verified
model, game/card/menu identities, belief law, algorithm, work/quality settings,
root digest and solved-profile digest. IDs are operational metadata and never
enter strategy calculations. No opponent cards, deck or deal seed enter it.

- Begin solves once. Only a converged supported root installs search play.
  Expected support failures or nonconvergence use explicitly labeled blueprint
  fallback; numerical corruption and invalid information remain errors.
- A later on-tree hero decision reads the appropriate row of the original
  retained profile. It performs **zero new solver advances** and does not
  condition hero history on the old blueprint.
- Validate the new public history, acting hero, own cards, board, payments,
  snapshot and legal menu against engine replay. Histories must extend the
  validated prefix. Reject stale handles and identity mismatches.
- After an off-tree action, remain on labeled blueprint fallback for the rest
  of that river. Missing/zero-mass rows retain the existing actual fallback
  semantics; no likelihood floors or implicit re-solving.
- Release ends the session. A new hand cannot silently inherit old state.
  Worker restart invalidates retained state explicitly.

Tests compare later distributions bit-for-bit with the original solved profile,
not merely repeated requests. Cover multiple paths, both hero orientations,
private-card row selection, all-ins, illegal payments, stale/cross-hand state,
zero reach, nonconvergence and off-tree fallback. Record retained bytes and
lookup latency separately from initial solving. Native independent fixtures
check route/row selection without needing the mature model.

## Fresh observations and fixed measurement matrix

After source correctness and the development-only cost quote, generate two
new 5,000-hand self-play traces with all seats on the frozen model. Deal/policy
roots are **202610216501** and **202610216502**; panel sampling roots are
**202610216511** and **202610216512**. Prior PR367/375/376/377 traces and outcomes
are excluded. Independently replay every hand with the pinned engine, then
reproduce both traces byte-for-byte before accepting the observations.

Classify every eligible first-river root. Uniformly sample 100 eligible roots
from each trace, sorted by hand after sampling, without filtering unsupported
cases. Fewer than 100 eligible roots in a trace is an inconclusive sampling
failure, not authorization for more hands. Freeze trace/panel hashes and belief
control selection before solving. No tuning after this freeze.

Run the following initial and independent deterministic reproductions:

1. Both menus on all 200 roots, strict target
   `min(0.2% of pot,0.02 BB)`, fixed checkpoints through 8,192 sweeps, with full
   production-menu evaluation. Primary descriptive comparison is the opponent's
   full-menu best-response gain against hero. Both menus must converge to
   qualify a pair; retain all inconclusive pairs and all per-case harms.
2. Both menus on all 200 roots at deployment target `min(1% of pot,0.1 BB)`
   and `[8,16,32,64,128,256,512,1024,2048]` sweeps. Record actual convergence,
   complete latency, root strategy, tree size and memory. No offline full-menu
   audit enters the deployment decision timer; report audit cost separately.
3. The candidate's retained begin and on-tree continuation checks on all 200
   roots, without sampling real hidden worlds for action selection. Verify
   original profile rows and zero continuation solves. On roots that cannot
   install search, test the declared fallback and count them as unqualified.
   Use fixed legal fixture paths to exercise off-tree and invalid-context cases.
4. The 20 matched-accuracy belief controls, both initial and reproduced.

Five ordinary workers serve panel measurements, each loading its own read-only
model once. One exact-joint worker may use the existing 16-thread leaf path.
No speculative concurrency speedup is assumed. Alternate menu order by case;
do not flush global caches. Compare all deterministic numeric outputs, strategy
digests and status/reason fields; timing samples are excluded from identity.

## Gates and interpretation

- Information contract, replay, identity, normalization, finite arithmetic and
  deterministic reproduction must pass; correctness failures stop dependent work.
- Report allocation support and converged installed-search coverage separately.
  The existing at-least-90% support criterion excludes fallbacks from success.
- Preserve deployment latency median <=0.5 s and p95 <=2 s, including required
  per-decision checks and complete worker roundtrip. Loading, audit and
  continuation costs are separate. Retain mean, maximum and every timeout or
  unsupported case. Failing-quality requests are not removed from timing.
- Preserve the every-decision declared-game quality target; any miss is reported
  as a failed gate, even when the majority meets it.
- Preserve the 0.05 BB belief gate above. Unqualified controls are inconclusive.
- Report full-menu harm versus blueprint and versus the reference menu per
  case and in aggregate, including worst harms. The original selected-case
  retention rule is not a fresh strength acceptance rule. No whole-hand
  improvement, safe resolving or release-readiness claim follows from this panel.
- Continuation must match the original installed profile exactly and must not
  start new solves. Invalid contexts must be rejected and fallback labeled.

An adverse scientific result ends this fixed round with its evidence; no extra
roots, seeds, sweeps, variants, gate changes or automatic retries. Plumbing
repairs before science preserve every attempt and do not silently replay
successful scientific work. Counts and source snapshots stay frozen thereafter.

## Compute, retention and handoff

Use bb128 only for mature-model work. Existing development observations first
provide a cost-only calibration before fresh traces or outcomes. Publish actual
load, solve, audit, exact-control, continuation and replay costs and the revised
forecast. The planned task is roughly 1–2 compute hours; it has fixed work
counts rather than an elapsed-time cutoff or permission to extend work.

Retain CPU90 C/Thermistor15 100 C stops and missing/nonfinite-sensor stops. No
automatic RSS, disk, swap or wall-time resource cutoff; inspect these manually.
Use the normal exclusive compute mutex plus a study mutex. Termination targets
only this study's process groups, with no orphaned external heat guard.

Models, earlier inputs, other jobs, environments, fans and driver settings stay
untouched. Keep raw evidence, source/binary/config pins, failures and receipts
in the study's owned NVMe root, with compact reports in Git. Follow
`docs/artifact-storage.md` for any specifically authorized cache/Drive closeout;
never delete originals or claim upload acceptance without receipts.

Finish with an engineering verdict, uncertainty/limits and a measured quote for
a **separate** whole-hand cost/variance pilot, including loading, actual search
frequency assumptions, replay/reproduction and fallback accounting. No pilot,
strength campaign, merge or default adoption follows automatically.
