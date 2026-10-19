# Unpruned three-player 100 BB 3B model diagnosis

Post-hoc analysis of the fixed PR350 model using only the baseline singleton
hands already played, exactly reproduced and independently replayed in PR352.
No new training, matches, policy loading, tuning or game behavior changes.

## Questions and scope

Measure absolute return against each of the four existing scripts, by physical
seat and button-relative position; missing-key frequency by street; recurring
costly betting paths and pot sizes; and the frequency of actionable two-live-player
river situations. These are descriptive diagnostics of one model, not a release
gate, an exploitability estimate or a causal explanation of its decisions.

Two disjoint deal cohorts, originally named `nodes` and `clock`, use the exact
same unpruned baseline. Pool their 8,192 six-hand blocks per script, yielding
16,384 blocks / 98,304 hands per opponent. There are 393,216 distinct initial
hands total. Exact reproductions are verification, not additional samples.

Intervals use Student-t uncertainty over independent six-hand block means;
seat and position summaries also average their two hands within each block.
Report pointwise95% and an exploratory family95% correction across the four
scripted absolute returns. This diagnostic readout was chosen after PR352;
it is not a new prospectively declared strength gate. Its intervals condition
on this one trained model and this opponent panel.

| Opponent pair | Absolute BB/100 | Pointwise95% interval | Exploratory family95% interval |
|---|---:|---|---|
| random | +312.75 | [+290.44, +335.06] | [+284.31, +341.19] |
| check-call | +252.60 | [+231.51, +273.69] | [+225.72, +279.47] |
| tight-aggressive | +46.90 | [+39.51, +54.28] | [+37.48, +56.31] |
| pot-pressure | +30.78 | [+20.36, +41.19] | [+17.51, +44.04] |

All four lower bounds are positive for this fixed model and these scripts.
This is useful internal evidence, not confirmation across independent training
seeds or against a varied population.

### Position and coverage

| Opponent | BTN / SB / BB return, BB/100 | Missing keys: preflop / flop / turn / river |
|---|---|---|
| random | +318.83 / +367.61 / +251.81 | 0.139% / 0.731% / 2.856% / 4.916% |
| check-call | +230.62 / +200.42 / +326.75 | 0.000% / 0.000% / 0.084% / 8.817% |
| tight-aggressive | +40.06 / +53.25 / +47.38 | 0.001% / 0.000% / 0.000% / 0.036% |
| pot-pressure | +31.29 / +39.22 / +21.81 | 0.002% / 0.004% / 0.099% / 0.317% |

Pointwise block intervals for every physical seat and button-relative position
are in[returns.csv](returns.csv). Position point estimates alone do not establish
significant differences. Missing-key fractions use singleton decisions as the
denominator, not hands. Opponent policies encounter different histories, so
these coverage rates should not be treated as causal effects.

### Recurring costly paths

Preflop sequences below describe only the singleton’s own actions. They omit
opponent actions, raise sizes and cards; the linked hand references retain the
complete histories. Selection: at least100hands, negative realized contribution,
excluding immediate preflop folds, five most negative contributions per opponent.
All groups, including profitable ones, remain in[paths.csv](paths.csv).

| Opponent | Path | Hands / frequency | Contribution to total BB/100 | First example root / hand |
|---|---|---:|---:|---|
| random | BB: call -> fold-flop | 1,750 / 1.78% | -8.77 | 20261019351102 / 3 |
| random | BB: call -> fold-turn | 619 / 0.63% | -6.13 | 20261019351102 / 142 |
| random | BTN: raise/call -> fold-flop | 437 / 0.44% | -4.31 | 20261019351102 / 576 |
| tight-aggressive | SB: call -> fold-river | 395 / 0.40% | -1.84 | 20261019351104 / 351 |
| tight-aggressive | SB: call -> fold-turn | 456 / 0.46% | -1.42 | 20261019351104 / 48 |
| tight-aggressive | SB: call -> fold-flop | 454 / 0.46% | -1.03 | 20261019351104 / 81 |
| pot-pressure | BB: call -> fold-turn | 244 / 0.25% | -2.05 | 20261019351105 / 608 |
| pot-pressure | SB: raise/call -> showdown | 158 / 0.16% | -1.83 | 20261019351105 / 3170 |
| pot-pressure | BB: call -> fold-flop | 333 / 0.34% | -1.58 | 20261019351105 / 78 |

Check-call has no qualifying negative group after excluding immediate preflop
folds. That does not prove every decision is good: check-call never raises or
folds, and this panel is strategically narrow.

### Pot sizes and river-search opportunity

| Opponent | <5BB | 5–<20BB | 20–<50BB | ≥50BB | Two-live-player river decision in a hand |
|---|---:|---:|---:|---:|---:|
| random | -9.34 | -16.33 | -1.10 | +339.53 | 5,970 / 6.07% |
| check-call | -17.23 | +12.20 | +57.33 | +200.30 | 0 / 0.00% |
| tight-aggressive | +39.91 | -0.21 | -3.86 | +11.06 | 4,434 / 4.51% |
| pot-pressure | +24.09 | -3.13 | -2.38 | +12.19 | 5,587 / 5.68% |

Pot columns show contributions to overall BB/100 and sum to each overall
return; they are not conditional BB/100. Pot size is the settled contested pot
sum, excluding refunded unmatched wagers. These are outcome-conditioned strata.
Random/check-call gains concentrate in large pots; the aggressive-script
profits are largely from small pots. This does not imply that making a pot
larger causes better play.

The singleton acts on a river with exactly two nonfolded players in15,991
of393,216hands (4.07%). All observed executed actions
fit the historical betting menu; off-menu count is zero. A solver would still
need its own range/quality/cost validation. This eligibility estimate is specific
to these scripts; check-call keeps both opponents live and contributes zero
two-live-player river opportunities.

## Interpretation and limits

The present evidence supports testing additional training on the existing
unpruned schema. It does not show a dominant coverage failure against these
scripts that would make that experiment pointless. PR350 froze membership at
2,088,867,258nodes /250,000,475entries; further training refines represented
states and can alter upstream decisions, but cannot add absent keys. The model
has3,000,011,203nodes /212,132iterations. These limits should stay fixed in a
controlled3B→10B comparison.

Coverage is strongly opponent-dependent. Check-call’s river missing rate is
8.82%, while tight-aggressive is0.036%; this is consistent with different
history distributions, not evidence that missing rows are harmless. Missing
keys are rare on the other streets in this panel. The repeated BB call→fold
paths are candidates for a future counterfactual decision test, not evidence
that folding is wrong or that this is the same mechanism as the heads-up Slumbot
flop path. Mixed trained/scripted opponents remain an important unmeasured case.

Observed realized losses do not establish wrong decisions. A recurring fold
can be correct, while a won all-in can be strategically poor. These path and
pot strata condition on behavior and opponents; conditional returns are not
counterfactual action values. Full paths are retained, and examples use the
first occurrence per cohort, rather than selecting the largest losing pots.

The native summary counts **missing keys**, not zero-average-mass lookups.
A represented zero-mass row can use a fallback without incrementing misses.
The archived traces do not identify per-decision lookup results, training
visits or action probabilities. They cannot attribute a loss to a missing row,
separate positive-mass from zero-mass lookup frequencies, or determine whether
an abstract card bucket/menu is strategically inadequate. A policy reload or
new instrumentation would be additional work; it is not part of this short
readout.

The menu check reconstructs min-raise, pot-raise and conditional all-in targets
from each pre-action public snapshot, using the historical pinned native menu.
A zero off-menu count establishes only that the **observed executed actions**
fit that menu. It does not prove that every history was represented during
training, or that the abstraction covers human bet sizes.

## Reproduce and retrieve

The read-only analyzer is [analyze.py](analyze.py); [compact results](analysis.json)
include absolute/seat/position intervals, all path and pot groups, coverage,
river counts, exact source paths and input SHA256s. Raw traces and protected
PR350 models remain in place on bb128. No research payload is copied into Git.
Research-Cloud archival and upload acceptance for this diagnosis remain pending.

The analysis scanned each of eight first-pass traces once, checked its full
SHA256 against the committed PR352 proof receipt, checked the original settled
parent and manifest identities, model SHA256, block/permutation/deck/payoff
accounting, and reconciled decision counts with the original native summaries.
It inherits the original independent engine replay; it does not claim a new
engine replay. Eleven focused tests cover singleton seat mapping, block units,
corrupt accounting/order/deals/decision snapshots, checksum refusal and the
public action-menu reconstruction. No production code changes.

To rerun this readout from the repository, on bb128 with the qualified Python
and read-only access to the original roots:

```sh
RECEIPT=$(python3 -c 'import base64,pathlib; print(base64.b64encode(pathlib.Path("docs/reports/nplayer-pruning-strength/metadata.json").read_bytes()).decode())')
/home/dberweger/nplayer-fast-strength-20261018-main-v5/venv/bin/python \
  docs/reports/nplayer-bb100-diagnosis/analyze.py \
  --root /home/dberweger/nplayer-pruning-strength-20261019/evaluation-recovery-v1 \
  --receipt-base64 "$RECEIPT" > results/FRESH_DIAGNOSIS.json
```

Create the ignored output directory first and use a fresh output filename. The
analyzer emits all path/pot groups; the published compact receipt moves those
groups to paths.csv and retains the five displayed candidates per opponent.
Both outputs come from the same scan. Input files are not changed.

For an example, locate the root/cohort and `*-baseline/play-0.jsonl` in the
receipt. HandH is lineH+2 (one header, zero-based hands). Each example’s block
and permutation are also recorded. These privileged logs contain hidden cards;
use them only for offline analysis, never as policy inputs. Existing whole-trace
engine replay is available through`python -m scripts.check_nplayer_policy_replay
TRACE` with the pinned engine; this readout did not repeat it.

Parent model/checkpoint/source pins are in the PR352 qualification and final
results. Baseline policy SHA256:
`c602c3727df28160a9807716d3c9211d988e420c33ed7b0c04c2fd899afef06b`.
Baseline checkpoint SHA256:
`ea0c7dca97ae627b08a39d4196cdd824d6e0767d85ca64c829eae5dcceb2da6b`.
The analyzer SHA256 and all eight trace hashes/paths are in analysis.json.
Both baseline cohorts’ individual point estimates are retained, so pooling is
not used to hide conflicting results. No original trace/model files were copied,
archived, moved or deleted; current owning PR status was checked before reading.
