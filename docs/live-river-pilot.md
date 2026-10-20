# Legal river decisions: bounded engineering qualification

Owner-approved follow-up to PR373. Resolve its two small-range finite-work
quality discrepancies, then connect one frozen v0.6.0 blueprint to legal public
history, range construction, the production river action menu and a persistent
native solver. This PR stops with a measured strength-study quote. It does not
launch an arena, change a default, claim safe resolving or strengthen a release.

## Numerical review

Keep both original misses and the unchanged 5% screen. Isolate terminal-kernel
rounding from traversal/averaging errors using identical supplied profiles and
a scalar native control. Locate the first divergent learned strategy and check
its preceding near-zero regrets. Test ties, blockers, zero reach and numerical
failure. Report finite-work quality differences honestly; a trajectory
explanation does not turn an original failed screen into a pass.

## Legal inputs and approximation

The new boundary accepts an acting player's immutable observation. Only public
configuration, public actions, board and that player's own holding cross it.
No actual other private cards, deck, seed, trace or future result is accepted.
Representative simulated cards reproduce betting only and never enter policy
lookups or leaf values. Every public action must match the declared blueprint
menu; unsupported histories are reported rather than assigned invented mass.

Compute each of the three seats' public action likelihoods over every holding
compatible with the public board, including the folded player's actions. No
likelihood floor or opponent-type information is added. Keep positive-mass,
zero-mass and missing-key lookup counts. Explicitly document any projection of
the resulting three-seat belief into the solver's product-compatible two-seat
law. Folded-card effects, correlations and zero likelihood must not silently
disappear. Own cards select the returned strategy row, not the public root law.

The native betting tree uses the existing N-player rules and exact
`min-pot-conditional-jam-v1` menu, without PR373's two-raise restriction. Scope is
the first river decision with exactly two live non-all-in players and one
contested pot at a three-player 100 BB table. Other states get an explicit
unsupported result. A finite tree allocation ceiling is an implementation
support limit, not a changed menu. Off-tree reuse is not claimed.

## Fixed small pilot

Before measurement freeze six deterministic legal public roots with different
boards, positions, pot sizes and prior folded-seat histories. The first four
are deeper, short-history states; the last two are declared near-all-in support
controls with long minimum-raise histories. These are synthetic engineering
fixtures, not a representative frequency sample or an eligibility-rate estimate.
Use the existing
seed2026101935003 10B binary and pinned K50 tables read-only on bb128; load once
into a persistent process. Run 16/64/256 sweeps with three fixed repetitions,
then one 1024-sweep engineering reference per supported root. No outcome-based
root selection, extra work levels or automatic arena continuation.

Report model verification/load separately; public reconstruction, range
construction, tree preparation, solving, quality measurement, transport,
first-use and warm complete-decision costs; resident memory; unsupported roots;
and quality of each fixed strategy under the exact same stipulated law. Check
numerical quality independently on supplied profiles and scalar fixtures.
The high-work profile is a reference point, not a known equilibrium or a
whole-game safety certificate. The returned action distribution must be legal.

Estimated allocation: one model load (about14.15 GB input, roughly15–20 GiB
resident), one solver thread, two build jobs, laptop-scale fixtures followed by
roughly5–15 minutes of pilot compute on bb128. Shared release transfers remain
untouched; no M1 heavy compute or new large model copies. Quote any larger work
before running it. Only existing authorized CPU90 C/Thermistor15100 C thermal
stops apply to the measured pilot; correctness and owner STOP remain terminal.
Disk and swap are observed manually. All original inputs/partials remain.

The final quote must distinguish measured per-decision cost from assumptions
about eligible-river frequency, paired-return variance and statistical counts.
A fixed-state pilot cannot supply empirical whole-hand power or pass chances.
Those require a separately approved cost/variance pilot before confirmation.
