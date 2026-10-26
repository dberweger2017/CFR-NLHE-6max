# PR438: conditional values localize a missing-row weakness

The owner-approved fixed M4 panel is complete: **36 roots, all129 legal root
actions,64 discovery plus2,048 held-out worlds/root, and exact reproduction**.
Seven discovery-selected alternatives clear the predeclared simultaneous95%
empirical-Bernstein bound. **All seven occur at missing keys using uniform
fallback; none of the22 positive-mass roots clears that test.** No player was
changed and no training or whole-hand arena ran.

This is conditional evaluation of the frozen PR431 live-order10B model against
five known check-call scripts. It does not establish general playing strength,
attribute PR431's −110.7BB/100 relative regression, or compare that model with
its history-key predecessor. Both original models' positive absolute check-call
profits and the adverse relative panel remain unchanged evidence.

[Protocol](../../six-player-counterfactual-m4.md) · [all36 roots](roots.csv) ·
[all129 action estimates](actions.csv) · [complete readout](results.json) ·
[analysis counts](analysis.json) · [verification](verification.json) ·
[source/input provenance](provenance.json) · [costs](costs.json).

## What the panel supports

Every cell below contains six roots, one per physical seat. Roots were selected
by a frozen hash rule from the four original initial check-call banks without
using rewards, original hidden cards or continuation values. They are deliberately
stratified reached decisions, not a frequency-weighted sample of all play.

| Root stratum | Positive-mass / missing | Selected alternatives clearing family95 | Individual actions worse than mixture at family95 |
|---|---:|---:|---:|
| Preflop weak sampled raise |6 /0|0|0|
| Preflop good sampled fold |6 /0|0|0|
| Preflop other |6 /0|0|0|
| Flop |4 /2|1|3|
| Turn |0 /6|3|5|
| River |0 /6|3|7|

There are no zero-mass root rows in this selected panel. All14 missing roots
have positive held-out selected-alternative point estimates; seven clear the
corrected bound. Across all actions, ten contrasts clear above zero and15 clear
below zero, all at missing roots. These are action comparisons within seven
gaining roots and other missing roots, not25 independent mechanisms.

The seven selected gains are below. Values are **BB per conditional decision**,
relative to the original root probability mixture with the same continuation.
Raise-to amounts are total street chips, at100 chips/BB; they are not increments.
The alternative was chosen using only64 discovery worlds. The table uses only
its2,048 separate held-out worlds.

| Stratum | Discovery-selected action | Gain | Simultaneous95% bounds |
|---|---|---:|---:|
| Seat0 turn |Check|+21.74|[+11.32,+32.17]|
| Seat2 river |Check|+13.85|[+3.68,+24.03]|
| Seat3 turn |Raise to100 chips /1BB|+23.44|[+8.70,+38.18]|
| Seat4 flop |Raise to3,900 chips /39BB|+47.51|[+30.59,+64.43]|
| Seat4 turn |Raise to9,200 chips /92BB|+33.23|[+11.52,+54.95]|
| Seat4 river |Check|+42.75|[+32.57,+52.93]|
| Seat5 river |Check|+33.33|[+20.94,+45.72]|

Four of these alternatives check, while three raise. Thus the mechanism is more
specific than “bet less.” Uniform fallback spends probability on badly priced
actions in some states and fails to extract value in others. For example, at
seat4 flop, checking is33.10BB worse than the uniform mixture, while the39BB
raise is47.51BB better; both contrasts clear the corrected bound. At seat4
river, checking is42.75BB better, while the86BB raise is43.25BB worse. These
examples illustrate the full published table; they do not estimate how often
either situation occurs in ordinary play.

## What remains inconclusive or adverse

All six good-fold preflop roots have positive estimated call-versus-fold value
(about4.73–12.50BB), and the largest-menu raise at all six weak-raise roots has
lower estimated value than call/check (about2.86–15.51BB). **None of those
passive-reference contrasts clears the conservative simultaneous bound.**
The panel therefore does not establish that the model's supported preflop folds
or raises explain its whole-game exploitation regression. It also does not
establish that these decisions are correct: these particular bounds are wide.

Four discovery-selected alternatives have negative held-out point estimates:
seat0 flop −11.04BB; seat4 preflop/other −12.50BB; seat5 flop −0.89BB; and seat5
preflop/other −0.0075BB. None clears below zero at family95. In total32/36
selected estimates are positive, but there is no population-weighted aggregate
or retrospective strength gate. Do not replace the declared bounds with the
narrower auxiliary normal intervals or add worlds to resolve these results.

Held-out continuations across **all counterfactual action branches** record
57,110 positive-mass,1,777 zero-mass and374,147 missing lookups:86.40% missing
of433,034 lookups. This is branch-weighted exposure on selected roots, including
actions the blueprint rarely takes. It is not the model's ordinary on-policy
missing rate. Support and street are confounded in this small panel: every
turn/river root is missing, so these data cannot isolate a causal effect of
missing membership from the kinds of states that are missing.

## Information boundary and uncertainty

One read-only frozen model and its unchanged future Policy implementation serve
all branches. Beliefs use only hero cards and the public prefix. Five check-call
scripts have likelihood1 for every compatible observed nonhero action, permitting
uniform joint sampling without replacement after visible-card removal. Opponent
cards, folded-card removal and future runouts are simulated jointly; original
hidden cards, decks and terminal rewards never enter policy/belief inputs.
This law is specific to these scripts and cannot be reused unchanged for TAG,
random, trained peers or unknown human ranges.

The selected action is the discovery-only argmax, with menu-order ties. Every
held-out action-minus-frozen-mixture contrast uses the preregistered two-tail
empirical-Bernstein family256. There are165 reported action/selected contrasts;
the selected contrast reuses its corresponding action contrast, and the family
was not reduced after seeing results. Action-minus-call/check bounds are derived
by subtracting simultaneous endpoints; no additional testing family is introduced.
Normal95 intervals and point estimates are auxiliary only.

Reproduction uses identical streams and checks bytes, float64 values, profiles
and work; it does not double the independent sample size. Conditional Monte
Carlo intervals cover the legal-world law at these fixed roots, not root
selection, training seeds, between-deal variation, general poker strength or
progress toward equilibrium.

## Qualification, complete cost and preserved reporting failure

The prior [qualification history](qualification.md), [independent review](review.json),
[main review](main-review.json) and [recovery review](recovery-review.json) remain
available. One owner-authorized reviewer cleared the information/branch/RNG
boundary and reviewed the statistical readout. Missing mature guards and
missing-stratum reporting were fixed before the mature panel.

- M1/M4 native library qualification:156 tests; reused on byte-identical library
  source. Main source also passes4 example tests and14 Python tests on M4.
- A fresh24-root synthetic fixture exercises the complete64/2,048-world work,
  reproduction and readout before the main. Final runner/readout regression
  qualification adds7 passing tests, including the path-collision regression.
- Accepted allocation:900s, after134.40s central /630.98s reserve quote.
  Measured M4 qualification + original main wrapper + recovery wrapper:
  **52.76s total** (35.01+15.60+2.15). Engineering, review, transfer and chat
  elapsed time are separate; this is not an end-to-end development-time claim.
- Native main:13.018s internal wall,11.710s model/K50 loading
  (9.047s policy loading),1.307s continuations including reproduction;
  supervised native stage13.283s,13.561s user+0.678s system child CPU.
- All76,032 initial world rows reproduce byte for byte;544,896 branch rollouts
  including repeat. Sampled process-family peak3,571,335,168bytes(3.326GiB).
  All sampled thermals nominal, pressure normal, swap1MiB before/after, final
  disk free24.967GB. One-second sampling can miss short peaks. Ordinary warm
  caches; no cold-load or isolated-runtime speed claim.

The native main succeeded once under source `9709d9ae`. Its reporting stage then
failed because the runner created `main-v1/readout` for stage logs before the
reader's exclusive output-directory creation. Source `8fcfff6d` separates stage
logs from outputs and adds a regression test. The same reviewer cleared recovery;
M4 tests passed, then **only** the unchanged proof-gated reader ran against the
original verified native files in fresh `completion-v1/readout`. No simulations,
worlds or scientific workload were retried. The failed reader cost1.048s; the
successful reader cost1.051s. Both are included above, not added again.

`main-v1/failure.json`, its stale running status, stderr and all files remain
unchanged and hash-bound. The definitive completion is
`completion-v1/COMPLETE.json`; all original file hashes match before/after.
[Costs CSV](costs.csv) separates successful native work, failed report, new-source
qualification and recovered readout. Wrapper walls include child stages; do not
sum both. Stage CPU includes guard-helper children, not only the native PID.

## Decision and handoff

This closes the fixed conditional panel. It supplies a concrete missing-row
weakness and directional supported-preflop hypotheses, with substantial
uncertainty retained. A focused next proposal could test a separately declared
fallback or useful-row-admission intervention while preserving supported-row
probabilities and trained-field safeguards. This result authorizes no such
experiment or adoption. Keep the player frozen; PR434's independent confirmation
remains separate. No extra panel, automatic arena or training follows.

Ordinary input/source/config/model/raw-world/failure evidence is retained at
M4 `/Users/dberweger/Local/six-player-counterfactual-m4-20261026/`; compact copies
and operational scripts are retained in this PR's ignored local
`planning/counterfactual/`. [Provenance](provenance.json) binds original producer,
recovery, model/checkpoint, panel, raw/repeat and readout hashes. Restore from the
retained M4 tree into an ignored working directory, verify those pins, and use
`completion-v1` as definitive; preserve the failed root as history. Cleaner-owned
bb128 staging/ZIP/Drive archival is pending. No archive or Drive payload receipt
is claimed. Normal/study locks are released; no watcher, timer, app cleanup or
bb128 scientific work was started by this panel.
