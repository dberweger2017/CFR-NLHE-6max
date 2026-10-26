# PR436 handoff: completed M4 model-backed river qualification

This is the entry point for an agent reviewing or building on PR436. Read the
[human results report](results.md), then use the maps below to inspect existing
evidence. The fixed run is finished and its research locks were released.
**Do not relaunch its campaign commands to inspect or reproduce its records.**
Saved-output verification requires no model loading, training or poker actions.

## 1. Decision and boundaries

PR436 closes the input gap left by [PR433](../river-second-to-act-m4/results.md):
the optional second-to-act path now has a genuine, small learned-policy panel,
beyond synthetic native fixtures. It qualifies an engineering path and retains
its limitations. It does not promote search or change a player default.

| Question | Existing evidence | Remaining limitation |
|---|---|---|
| Can second-to-act requests install learned-model search? | 34 of 36 fixed roots install; two zero-reach fallbacks remain | Deliberately constructed roots, tiny immature policy; no population coverage estimate |
| Does first-to-act behavior stay unchanged? | All 12 controls have bitwise profile/action/quality/work parity with pre429 | Same diagnostic shell links both libraries; not an unmodified historical executable comparison |
| Is the panel deterministic? | All 48 current and 12 baseline roots reproduce in fresh processes | Exact environment and inputs are pinned; this is not cross-platform determinism |
| Can a retained root be queried consistently? | All main re-entries preserve profile/probability bits, zero solver advances, successful release | Re-entry repeats the same observation; not a learned-model whole-hand continuation test |
| Is local convergence adequate? | All 46 installed profiles pass both players' frozen best-response-gain targets | Projected modeled beliefs and capped search menu only |
| Is it fast enough for deployment? | Installed median 278.5 ms, p95 1,008.2 ms, max 1,349.9 ms | Tiny M4 fixture, ordinary caches; no mature-policy or throughput forecast |
| Does this improve poker strength? | No new arena hands were played | No strength evidence, adoption decision or safe-resolving guarantee |

No further experiment is implied. Preserve PR398's prior deferred search
candidate verdict and PR434's separate blueprint-confirmation priority. A new
mature-model test or strength campaign needs its own question, frozen protocol,
measured full cost and owner allocation. Optional support for a request type
should not be mistaken for complete arena integration or deployment readiness.

## 2. What changed, and what was only exercised

PR429's solver/library behavior was exercised rather than changed by PR436.
PR436 changes the `river_live` example and adds a bounded research harness.
There is no game, information-access, regret-update, search-menu or default
change. Ordinary calls to the example with its original three positional
arguments retain their prior path.

| File | Responsibility / useful entry points |
|---|---|
| [`examples/river_live.rs`](../../../native/hu20-trainer/examples/river_live.rs) | Persistent line-delimited JSON worker; optional mass sidecar; ready/begin/continue/release transport |
| [`support/nplayer_mass_metadata.rs`](../../../native/hu20-trainer/examples/support/nplayer_mass_metadata.rs) | Existing audited original-average-mass loader; validates receipt/keyset/zero-key metadata and tags rows without changing probability values |
| [`scripts/river_model_panel_m4.py`](../../../scripts/river_model_panel_m4.py) | Fixed controller, `Worker`, `batch`, fixture validation, historical wrapper build, admission and preserved transport-only continuation |
| [`scripts/river_model_panel_protocol.py`](../../../scripts/river_model_panel_protocol.py) | Frozen inventories/seed, float-bit signatures, exact comparison, public-observation whitelist, cost-only quote |
| [`tests/test_river_model_panel_m4.py`](../../../tests/test_river_model_panel_m4.py) | Framing, signed zero, profile/work mutations, incomplete-probe provenance, fixed recipe, wrapper lock/profile and persistent transport tests |
| [`src/river/live.rs`](../../../native/hu20-trainer/src/river/live.rs) | Existing reconstruction, likelihood/projection, opponent-prefix conditioning, solver execution and quality accounting |
| [`src/river/live/retained.rs`](../../../native/hu20-trainer/src/river/live/retained.rs) | Existing retained profile, root-prefix replay, immutable binding, continuation and fallback semantics |
| [`retained/tests.rs`](../../../native/hu20-trainer/src/river/live/retained/tests.rs) | Native later-continuation/off-tree and blocked-action controls; distinct from this panel's same-root probes |
| [`qualify_river_second_to_act_m4.py`](../../../scripts/qualify_river_second_to_act_m4.py) | PR433 generator-manifest and native-test receipt validation reused here |
| [`nplayer_four_player_feasibility.py`](../../../scripts/nplayer_four_player_feasibility.py) | Existing Mac resource supervisor, thermal sampling and K50 pins; borrowed read-only |

## 3. Solver semantics to preserve

A second-to-act observation includes the opponent's first river action. The
implementation reconstructs the first river decision and retains that action
as a prefix. The root opponent action distribution remains fixed to the
blueprint, the strategy is read at the child corresponding to the action
actually observed, and retained continuation replays that prefix before later
history. Removing the prefix or reading the first-to-act row changes the game.

The quality gate checks **each player's best-response gain**, not only average
exploitability. Its bound is `min(0.01 * river_start_pot_BB, 0.1 BB)`, scaled by
the taken action's probability under the compatible modeled joint law for a
second-to-act subtree. Do not replace that with an independent marginal action
probability. Existing native controls distinguish compatible 1/3 and 2/3 cases
from the incorrect marginal 1/2 calculation.

A zero-reach holding, blocked action or convergence failure must not install
an unusable strategy. The unchanged fallback selects the actual blueprint row.
Off-tree fallback is not a re-solve. Later retained strategy correctness is
covered by existing native fixtures; this panel only re-enters the same public
observation once after each successful begin.

The request framing distinction matters:

- `retained-begin`: outer mode plus hand identity; inner observation includes
  the fixed solve controls and public observation.
- `retained-continue`: outer mode, hand identity and opaque handle; inner
  observation contains exactly `format`, `button`, `board`, `seat`, `hole`,
  `actions`, `players`, `legal`.
- `retained-release`: outer mode, hand identity and handle; no observation.

No deck, other players' private holdings or random seed is passed as a player
observation. The diagnostic benchmark does not sample poker actions.

## 4. Executed configuration and accounting

| Item | Frozen value / actual endpoint |
|---|---|
| Game | Three players, 100 BB; stacks 10,000 chips; blinds 50/100 |
| Fixture seed | `2026102643601` |
| Keys | History schema `nplayer-button-live-actor-history-equity-k50-v1`; not the separate live-order experiment |
| Training | Existing unpruned fast K50 recipe, two threads, eight roots/seat, full average scope 3 |
| Endpoint | Target 25M; actual 25,002,307 nodes |
| Membership | 1M threshold, actual 1,010,695 keys, freeze iteration 92; merge-boundary overshoot is expected |
| Export | One ordinary float64 average gzip, all 1,010,695 rows independently audited |
| Solver | Projected law, DCFR 1.5/0/2, `pot-jam-cap3-root-min-responses-v1` |
| Work | Checkpoints 8,16,32,64,128,256,512,1024,2048; stop at the unchanged target |
| Concurrency | One worker/session at a time, versions sequential, Rayon 1 |
| Panel | Four histories × three boards × four entries; IDs 0–47 |
| Entry IDs | `id % 4`: 0 first-to-act, 1 after check, 2 after min opening bet, 3 after pot opening bet |

Preflight current IDs: `0,5,10,15,24,29,34,47`; baseline IDs: `0,12,24,44`.
Initial plus fresh-process repeat gives 24 declared begins. Main current IDs
are all 48; baseline IDs are `0,4,...,44`. Both versions run initial and fresh
repeat, giving 120 main begins and **144 total begins**. Calibration repeats
are not independent data or additional strength samples.

Raw wire totals are 144 begins, 144 continues and 143 releases. One continue
was malformed and rejected; 430 of 431 transport requests succeeded. All 120
main begins, 120 main continues and 120 main releases succeed. The missing
release belongs only to initial preflight root0, explained below.

## 5. Failure chronology: preserve the distinction

| Root / native or adapter source | What happened | Science repeated? |
|---|---|---|
| `run-v1`, source `88d86bc8` | Historical wrapper Cargo lock omitted its new root package; `--locked` refused baseline build | No fixture or request existed |
| `run-v2`, native source `469ffa3c` | All builds/tests pass; fixture trains once, export/audit pass; root0 begin succeeds; malformed continuation is rejected | No repeated fixture or extra begin |
| `completion-v1`, adapter `116f1be6`, same native source/binaries | Reuses audited inputs and original root0 begin; finishes remaining preflight and full main | Original total remains 144 begins |

The wrapper fix appends only its owned package entry to the historical lock;
all historical dependency entries/checksums and opt-level 3/thin-LTO/one-codegen
release profile remain pinned. No replacement historical dependency resolution
is being claimed.

The framing failure was in the harness: solve settings appeared inside a legal
continuation observation. The native API correctly rejected it with
`unexpected field in legal river request`. The old wire/partial/failure remain
unchanged in `run-v2`. `completion-v1/carry.json` binds the valid original begin
and the rejected follow-up provenance. It records follow-up/release as null,
not successful. `incomplete_initial_followups=[0]` is allowed only for that
initial preflight pair. Its begin still must reproduce bitwise. The fixed
repeat and both main root0 passes qualify corrected follow-up/release.

Do not describe this as every original probe passing. Do not generalize the
exception into tolerance for solver, probability, quality or work mismatches.
The transport-only continuation is a one-off path for this exact preserved
failure, not a general resume/retry facility or authorization to retry a future
scientific failure.

## 6. Evidence map and dependencies

Host alias: `m4`. Original ordinary evidence root:
`/Users/dberweger/Local/river-model-panel-m4-20261026`.

| Relative path | Purpose / retention relationship |
|---|---|
| `source-v1/`, `source-v2/`, `source-v3/` | Original setup, qualified native source and corrected adapter respectively; preserve all |
| `baseline-e6ae0bec/` | Untouched pre429 solver checkout |
| `run-v1/` | Original failed build, logs, costs, resources and failure/status |
| `run-v2/fixture.gz` | Sole original checkpoint |
| `run-v2/fixture-average.gz`, `run-v2/mass/` | Sole original average and validated original-mass sidecars |
| `run-v2/target/` | Exact qualified native executables, including historical-library worker |
| `run-v2/preflight-current-0/` | Original valid root0 begin and rejected continuation, wire/partial/stderr |
| `completion-v1/fixture*`, `mass`, `panel.jsonl` | Compatibility symlinks into `run-v2`; not additional independent payload copies |
| `completion-v1/config.json` | Full source-file inventories, paths, runtime/native/config pins and prior costs |
| `completion-v1/carry.json` | Preserved valid begin plus explicit incomplete follow-up provenance |
| `completion-v1/{preflight,main}-{current,baseline}-{0,1}/` | Per-batch results/partial/raw wire/stderr, all inventories retained |
| `completion-v1/{preflight,main}-verified.json` | Reproduction and historical-profile comparison receipts |
| `completion-v1/quote.json` | Cost/resource admission, generated before main |
| `completion-v1/results.json`, `status.json` | Settled readout and its SHA-bound completion |
| `completed-readback.json` | Post-completion source/input/wire/count/quality/resource/lock verification |
| `launch*.json`, `controller*-result.json`, `preparation*.json` | Dispatch, prior failures, finite-controller exits and complete preparation cost |

Borrowed dependencies remain protected:

- Python: `/Users/dberweger/Local/hu200-river-search/.venv/bin/python`.
- K50: `/Users/dberweger/Local/overnight-equity-hu100-20261009/stage-a/results/equity-bench/tables`.
- Normal research lock inode: `~/Local/.hu20-m4-research.lock`; do not replace
  or unlink it. Each attempt also retains its own `.study.lock`.
- Source checkouts may borrow Git object storage; preserve it until archival
  provides a complete independently restorable source tree.

The ordinary M4 root is the current retrieval location. Cleaner-owned packaging
and verified archival are pending. No accepted bb128/Drive research payload or
archive-set extraction path is claimed. Preserve the original paths and symlink
targets together; archiving only `completion-v1` would omit its payloads.

Published compact evidence:

- [results.json](results.json): unchanged settled native readout, including all
  48 root summaries, profile bindings, costs and explicit incomplete probe.
- [roots.csv](roots.csv): one row per fixed root, including both fallbacks.
- [policy-audit.json](policy-audit.json): every-row audit, table-wide masses,
  retained visits and training lookup counters by street.
- [provenance.json](provenance.json): exact config/input/runtime/binary/wire pins,
  proof summaries and evidence location.
- [verified-readback.json](verified-readback.json): post-run proof and complete
  request counts; no future lock/resource guarantee implied.
- [costs.json](costs.json): all recorded stage attempts, resource samples and
  measured admission. Prior failures are included, not discarded.

## 7. Read-only verification recipes

From a checkout containing this report, this checks published data only. It
neither contacts M4 nor loads models:

```sh
python3.11 - <<'PY'
from pathlib import Path
import hashlib, json
p = Path('docs/reports/river-model-panel-m4')
r = json.loads((p/'results.json').read_text())
v = json.loads((p/'verified-readback.json').read_text())
assert hashlib.sha256((p/'results.json').read_bytes()).hexdigest() == v['result_sha256']
assert r['status'] == 'complete'
assert [x['id'] for x in r['roots']] == list(range(48))
installed = [x for x in r['roots'] if x['classification'] == 'installed']
assert len(installed) == 46
assert [x['id'] for x in r['roots'] if x['classification'] == 'fallback'] == [14, 38]
assert all(max(x['quality']['best_response_gains_bb']) <= x['target_bb'] for x in installed)
assert v['total_requests'] == {'retained-begin':144, 'retained-continue':144, 'retained-release':143}
assert v['proofs']['main']['first_actor_profiles'] == 12
assert v['proofs']['main']['reproduction']['current']['incomplete_initial_followups'] == []
print('Published readout/accounting/quality checks pass; no new requests issued.')
PY
```

For a deeper check, after arranging read-only access to the retained evidence,
run this **on M4**. It uses the frozen adapter's pure comparison helpers and
reads saved results/wires; it does not call `run`, `batch`, `continue-transport`
or `verify_phase` (the latter rewrites proof files):

```sh
python3.11 - <<'PY'
from pathlib import Path
from collections import Counter
import hashlib, json, sys
r = Path('/Users/dberweger/Local/river-model-panel-m4-20261026')
sys.path.insert(0, str(r/'source-v3'))
from scripts.river_model_panel_protocol import PREFLIGHT, MAIN, first_actor, verify_batch_pair
read = lambda p: json.loads(p.read_text())
c = r/'completion-v1'
for phase, inventory in [('preflight', PREFLIGHT), ('main', MAIN)]:
    batches = {}
    for version, ids in inventory.items():
        a,b = [read(c/f'{phase}-{version}-{i}/results.json') for i in (0,1)]
        exception = (0,) if phase == 'preflight' and version == 'current' else ()
        verify_batch_pair(a,b,ids,exception)
        batches[version] = {x['id']:x['begin'] for x in a['roots']}
    for i in batches['baseline'].keys() & batches['current'].keys():
        assert first_actor(batches['baseline'][i]) == first_actor(batches['current'][i])
v = read(r/'completed-readback.json')
counts = Counter()
for relative, digest in v['raw_wire_sha256'].items():
    payload = (r/relative).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == digest
    for line in payload.splitlines():
        packet = json.loads(line)
        if packet['direction'] == 'request':
            counts[packet['value']['mode']] += 1
assert dict(counts) == v['total_requests']
print('Saved reproduction, historical parity and raw-wire accounting pass.')
PY
```

The ordinary source unit checks are also small and require no campaign launch:

```sh
python3.11 -m unittest tests.test_river_model_panel_m4 \
  tests.test_river_second_to_act_m4 \
  tests.test_river_arena_expectation tests.test_river_whole_hand_pilot
```

No training/arena reproduction command is included here. Historical dispatch
commands are retained in the evidence for provenance; they are not an instruction
to execute them against a new or existing root.

## 8. Interpreting diagnostics and timing correctly

The audit's 295,329 zero-average-mass rows are table-wide; their exported
normalized uniform probabilities do not reveal that original mass without the
sidecar. The diagnostic lookup tags are `0=missing`, `1=positive mass`,
`2=zero mass`, `3=mass unknown`. Do not confuse these numeric tags with the
separate `MassMetadata::LABELS` reporting-array indices.

The 46 installed roots report 287,232 positive and 60,850 missing range-likelihood
queries, with no zero/unknown queries. These repeatedly query legal holding
combinations across public histories; they are not unique-key counts, gameplay
frequencies or learned coverage over all 48 roots. Fallback roots14/38 stop early
and return no range-coverage array; CSV cells remain empty, not zero. Both
fallbacks have missing-row tag0 and uniform four-action probabilities. Their
zero modeled reach is a distinct property from stored zero average mass.

Complete request time is caller-measured from writing the request through
parsing its response, excluding worker startup. Native component timings exclude
serialization and transport. Quality checks are included in complete time and
reported separately from solving. Median components do not sum to median total.
A fast fallback is not a fast successful solve. Cold-process startup does not
mean cold filesystem caches; no global caches were flushed.

Accounted active preparation/controllers total 309.98 seconds. Summed stage wall
is 277.56 seconds; summed child CPU is 538.63 seconds. These differ in scope and
must not be added together. Dispatch to final completion is 24m07s, including
repair/idle gaps. Final verification/publication are separate. Sampled peak RSS
1.446 GiB is not an exact peak or whole-machine RAM measurement. Mac thermal
state was nominal; the API provides no per-sensor Celsius evidence. All cost
statements are non-isolated M4 engineering observations.

## 9. Suggested review order and future scope

1. Check all-root inventories and the explicit incomplete preflight provenance.
2. Check mass sidecar attachment preserves probability rows and old CLI behavior.
3. Check historical library, dependency and release-profile pins.
4. Check bitwise reproduction and actual installed-profile parity, including
   signed zero, quality and stopping work.
5. Inspect fallback roots14/38 and the missing coverage counters honestly.
6. Check request latency denominators, startup exclusion and complete prior costs.
7. Review integration separately before claiming whole-hand support or strength.

A future agent can inspect saved roots and existing code without consuming more
poker compute. New fixture training, mature loading, additional root requests,
solver/menu tuning, exact-belief controls, full-menu audits, whole-hand integration
or adoption would be new work, not a continuation of this completed allocation.
