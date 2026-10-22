# Paired evaluation arena for four to six players

Owner-requested engineering work, proposal[409](https://github.com/dberweger2017/CFR-NLHE-6max/issues/409). Use existing PR406/408 models as correctness fixtures, not strength candidates. No training, search, default, release or large strength campaign. PR404 stays isolated on bb128.

## Estimate and scope

Allow2–4hours implementation/review and provisionally15–30minutes M4 checks, not a completion promise. Publish a concrete small-run quote before qualification. A separate opt-in native paired command preserves the existing three-player executable, six-permutation schedule, policy sampling and trace bytes. No trainer/regret/rules/observation or legacy inference changes.

Each block reserves one independently seeded deck. Both arms share deck, button, seating and labeled opponent specifications plus identity-specific action RNG seeds. Only focal identity0 changes. Independent policy instances share read-only tables. Opponent actions may diverge after histories differ; the **opponent policies and RNG seeds**, not arbitrary action sequences, remain fixed. Identical focal policies must produce identical whole arm traces and exactly zero block/aggregate contrast. No arm label, output path or nondeterministic timing enters trace bytes.

## Seating and statistic

Default4/5/6 schedule has N cyclic rotations: rowr maps physical seats to `(seat+r)%N`. Every labeled identity sees every physical hand and every button-relative position once per block. Button=`block%N`. This balances positions without requiring24/120/720permutations. Opponent relative circular order is fixed: the estimand is this declared schedule/field, not an average over all opponent orderings. An explicit balanced schedule may be declared and pinned; validate permutation rows, uniqueness and equal identity-by-seat counts. Three-player legacy schedule remains all six permutations in the existing command.

Primary descriptive paired statistic is the focal return of armB minus armA, averaged within an independent deal block and converted to BB/100. No reciprocal halving. Rotations, hands, paired arms and reproduction are not additional independent samples. Future campaigns must predeclare lineups/roots/counts/interval families/margins; engineering fixtures carry no strength inference. A verified readout requires all-hand independent replay and exact separate-process reproduction, no exclusions.

## Coverage and evidence

Model loading requires source-bound full-average mass receipts from the existing full-row auditor. Missing, found-zero-average-mass and positive-mass tags are determined from actual rows and audited source mass, never inferred from uniform probabilities. Every model decision records its status/key/actor/identity/street/position in evaluator-owned traces. Policies receive acting-seat legal observations only; hidden deck/cards stay in privileged replay logs. Aggregate status counts by identity, physical seat, button-relative position and street; scripts are labeled not-applicable.

Require legal actions, chip conservation, complete schedules, controlled opponent pins, exact self comparison, source/hash/mass/schema mutation rejection, serial/four-thread byte equivalence and reproduction. Preserve every failure/partial. No automatic scientific retry or outcome-selected extension.

## Fixed M4 qualification

Read-only PR406 four-player and PR408 five/six-player qualification exports at100K/200K with audited mass. No new models. For eachN: one identical-focal self case and one changed-focal case, each **8blocks**, Nrotations, both arms. Fixed ordered opponent lists are[earlier,check-call,pot-pressure] for4players;[earlier,check-call,TAG,pot-pressure] for5;[earlier,check-call,TAG,pot-pressure,random] for6. Both arms use that identical list. Root bases20261023410000+100*N+case; cases0=self,1=changed. Reproduce in a new process and independently replay every initial hand. At4workers, total480initial hand instances plus480reproductions. A serial copy of the same fixed tiny fixture checks thread-order identity, not new deals.

Cap-size smoke uses eachN's existing25M/50M exports, same two cases with **2blocks** and separate reserved bases20261023420000+100*N+case, including reproduction/replay:120initial+120repeat hand instances. Keep at most two read-only tables resident and clear between sizes; quote memory/load work before admitting this smoke. Legacy three-player script-only regression at20/100/200BB compares exact outputs from unchanged base and new builds under fixed roots20261023430020/100/200, two blocks/six permutations each. No three-player training or model transfer.

M4 AC, normal research mutex plus owned arena mutex, thermal serious/critical/missing/unknown/ownerSTOP/correctness stop; no added time/RSS/disk/swap cutoff or OS/environment/fan changes. No bb128 compute, cleanup, upload, new timers or later experiments. Raw evidence stays owned M4 root; archive acceptance owner-managed pending/originals retained. Stop after qualification and leave M4 free.
