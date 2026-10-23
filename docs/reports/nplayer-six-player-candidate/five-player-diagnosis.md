# Saved five-player traces: changes begin mainly at supported preflop decisions

This is the bounded **PR415 five-player3B→10B descriptive analysis**, not preliminary six-player strength. All16initial traces/655,360hand instances were scanned once in69.42s; existing full trace SHA256s, paired returns and independently verified focal lookup counts reconcile. No hand was selected by outcome or excluded, and no new models/hands/rollouts were used. ResultSHA256`f168de277f7af665137144299cb486d6dcd565c43a5438b0bd6cdc5e49590f5c`.

[Compact aggregate result](five-player-diagnosis.json) · [all first-divergence partitions](diagnosis-contributions.csv) · [all reached action/sizing totals](diagnosis-actions.csv) · [original verified PR415 result](../nplayer-five-player-candidate/results.md).

The first unequal focal action is located only while the complete preceding actor/action prefix and public state still match. Opponent/deal/key mismatches before that point fail the scan. Identical trajectories stay in an unchanged group. Full action targets are compared: `raise→raise` means the raise size changed. After divergence, action/lookup aggregates describe different reached histories, not matched states or changed full probability distributions.

| Field | Paired hands | Diverged | First preflop count | Preflop-first contribution | Total10B−3B |
|---|---:|---:|---:|---:|---:|
| trained | 40,960 | 31.82% | 10,441 | +56.66 | +74.05 |
| random | 40,960 | 28.24% | 11,078 | -83.56 | -84.11 |
| check-call | 40,960 | 29.97% | 10,946 | -21.90 | -11.41 |
| tight-aggressive | 40,960 | 25.46% | 8,758 | -0.13 | +1.21 |
| pot-pressure | 40,960 | 26.40% | 9,063 | +43.11 | +44.15 |
| call-pressure | 40,960 | 35.68% | 10,630 | +15.08 | +11.92 |
| random-tight | 40,960 | 31.44% | 10,323 | -27.90 | -37.46 |
| trained-call-pressure | 40,960 | 34.62% | 10,787 | +38.37 | +44.50 |

The adverse random panel−84.11BB/100 includes−83.56 from hands first diverging preflop. Random+TAG's−37.46 includes−27.90 from preflop-first hands, with further negative contributions from later first-divergence groups. Conversely, trained-field+74.05 includes+56.66 from preflop-first hands, and pressure+44.15 includes+43.11. Each partition reconciles to the original full-panel contrast; the different partitions overlap and must not be added to one another.

**All first divergences occur at keys present in both models**: almost all positive-mass in both, with a small zero-mass3B→positive-mass10B subset. No first divergence is missing/missing. Identical membership plus the same legal menu, uniform fallback and per-identity random stream imply the same sampled action while both sides remain missing at an identical prefix; the scan explicitly checks this invariant. This does not make missing support irrelevant: earlier supported changes lead into different later states, and missing fallback may affect those continuations. It does locate where these paired trajectories first separate.

For random, call→fold first differences contribute−42.60BB/100 and raise→fold−29.98; fold→call contributes+20.92. In pressure, call→fold contributes+20.68 and raise→fold+23.61. These are **whole terminal-return differences for hand groups**, not causal values of the first action. Each group includes downstream policy changes, folding/selection and card outcomes. They do not show that calling more against random would fix the model, or that folding more against pressure is generally optimal.

The original near-total check-call river misses remain a serious support limitation; this analysis does not overturn or attribute them to the cap alone. Check-call's paired−11.41 includes−21.90 in preflop-first hands offset by+10.23 in flop-first hands. A river-only narrative would miss that structure.

Action counts and absolute raise-to/BB and raise-to/pot sums are retained by arm/street/lookup status. These reached distributions have different denominators and histories; they are not exact policy probabilities. Raise-to uses the absolute street target, not an incremental bet-size fraction. First-divergence group means/contributions are descriptive localization using already inspected data, with no new significance family or causal attribution. Original deal-block uncertainty/tails from PR415 remain authoritative; duplicate seatings/reproduction are not new independent observations.

**Implication:** the next mechanism investigation should include supported preflop strategy changes and downstream visitation, rather than assume the adverse result originates at missing river keys. The frozen six-player trajectory proceeds unchanged, with no player tuning, new capacity arm or search. A controlled improvement requires a prospective hypothesis and separate budget after the sprint; no new experiment is selected by this descriptive scan.
