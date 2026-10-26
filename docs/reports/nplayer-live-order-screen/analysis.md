# Live-order keys for six-player training: detailed analysis

A self-contained guide to #431 for anyone, including coding agents, continuing this work. It covers:
- what was wrong;
- what changed in the code and where;
- how the experiment was run and how to reproduce it;
- what the results are and where each gain or loss comes from;
- what is and isn't established, and what to try next.

**Related documents:**
- **Verdict and tables:** [results.md](results.md).
- **Protocols, committed before their runs:** [key and pilot](../../nplayer-live-order-keys.md), [screen](../../nplayer-live-order-screen.md).
- **Earlier steps:** [pilot report](../nplayer-live-order-pilot/results.md), [trace measurement](../nplayer-key-collapse/).

## 1. In one paragraph

The six-player bot stores one table row per information key. The released key encodes the full public history with exact amounts, so six-player self-play produces far more keys than the 250M-row table holds. #417's table filled at iteration 23,678 of 390,401. From then on, 68% of regret updates were discarded and two-thirds of training decisions found no row and played uniform. The live-order key instead encodes each seat only by its order among the live players, plus a capped summary of the betting. At 10B nodes the table holds 38.6M rows and never fills, only 0.66% of training decisions find no row, and each row gets 30–66 regret updates instead of 2–3. On identical deals the bot improves by **+105.4 BB/100 [+92.9, +117.9]** against the trained field. It **beats pot-pressure** (−31.0 → +27.3) and improves against every betting field. It loses value against check-call (−110.7), whose multiway rivers self-play never visits under any key. This is one training lineage, not release evidence.

## 2. How we got here

All rows use #417's six-player recipe at 100 BB (seed 2026102361001, fast mode, 8 roots per seat, 250M-entry cap with freeze, average scope 3, 10B nodes) and the same evaluation fields.

| PR | Change | What it showed |
|---|---|---|
| #417 | Six-player 3B/6B/10B/15B lineage | 10B is the control. Gains against its own 3B; −22 BB/100 against pot-pressure (after all-in adjustment, #426) |
| #426 | Loss diagnosis on saved hands | Pot-pressure is the gap, and a passive fallback in untrained spots doesn't fix it |
| #427, #428 | Forced opponent pot raises at 5%, 15%, 30% | Pot-pressure never improves (−71 at 30%): the random raises teach the wrong lesson |
| #430 | New keys only from traverser updates | Training gets denser, strength doesn't move. Opponent-only rows held 60% of the table but only ~2% of played decisions |
| **#431** | **Coarser keys** | **Large gains on every betting field** |

The lesson of #430 set up #431: what blocked progress was the **size of the key space relative to the table**, not which keys got admitted.

## 3. What changed in the code

### 3.1 The live-order key

The schema string is `nplayer-live-order-summary-equity-k50-v1`, built by `live_order_payload` (`native/hu20-trainer/src/multi_holdem.rs:177`) and hashed to 16 bytes with BLAKE2b like every key. The payload, in order:

| Bytes | Content |
|---|---|
| schema string, `0` | domain separation from the history key |
| `n`, `live`, `hero`, `street`, `all_in` | player count; live players; the hero's index among live players counted from the button; street; live players with zero stack |
| pot bucket | pot at the street's start (`contributed − street_bet`) against edges 2, 4, 8, 16, 32, 64, 128 BB |
| SPR buckets, sorted | for each live player, (stack + street bet) over the street-start pot, against edges ½, 1, 2, 4, 8, 16 |
| raise counts | raises per street from preflop to the current street, each capped at 3 |
| previous aggressor, current raiser, action count | the previous street's last raiser and the current street's last raiser, by order among live players (255 if none or folded); actions so far this street |
| price bucket | call / (pot + call) against edges 0.1, 0.2, 0.3, 0.4 |
| card class | unchanged: preflop rank class or the current street's K50 bucket |
| action label code | the menu's label bitmask (`u16`), so a row's action count is fixed |

Bucket comparisons use exact integer cross-multiplication (`bucket`, `multi_holdem.rs:168`), so keys don't depend on floating point.

**Invariants and gotchas:**
- **A row's `owner` is the hero's order among live players,** not the button-relative seat. Every row checks (owner, street, action code) on every hit (`multi_cfr.rs` `Stored::check`). Under live-order keys that identity is what merged decisions share.
  - Keeping the absolute seat instead would halve the merging (level 4 in the [measurement](../nplayer-key-collapse/)).
- **The menu is still built from the exact observation,** so legal amounts are exact. Only the key forgets amounts.
- **Everything comes from the acting seat's `Observation`.** The key removes detail and adds no information.

### 3.2 Schema plumbing

- **The schema enum:** `KeySchema { History (default), LiveOrder }` (`multi_holdem.rs:16`). `name()`, `from_name()` and `from_identity()` map to the identity's `schema` string.
- **Training:** `CashGame.schema` (`multi_holdem.rs:285`) selects the key and writes the schema into the game identity, and so into checkpoints and exports.
  - The CLI is `nplayer_train --key-schema history|live-order` (`examples/nplayer_train.rs:181`).
  - Resume compares the full identity, so it can't mix schemas.
- **Lookups:** `PolicyTable.schema` (`multi_policy.rs:69`) is read from the identity at load (`:418`). Unknown schemas are refused (`:272`). `PolicyTable::decision` (`:428`) keys an observation under the table's schema, and every lookup through the table uses it.
- **Call sites switched to the table's schema:**
  - the paired-arena host (`examples/support/nplayer_paired_host.rs:255`);
  - river-search blueprint rows (`src/river/live.rs:833`);
  - composition (`examples/support/nplayer_composition.rs:129`);
  - the continuation arena (`examples/nplayer_continuation_arena.rs:95`), which refuses two tables with different schemas.
- **Refusals:** shared-observation queries refuse non-history tables (`examples/support/nplayer_shared_observation.rs:123`), because they receive a precomputed history key.
- **Still on history keys:** `multi_holdem::observation_decision` is unchanged and still means history keys. It is used for history-only purposes, such as the matched-regression fixtures with archived keys.
- **Unchanged:** released models, the default, the HU trainer and every history checkpoint byte.

**If you add a tool that computes keys,** call `table.decision(...)` for each model, never `multi_holdem::observation_decision`. Otherwise a live-order model silently misses every row and plays uniform.

### 3.3 Tests

- **Native library tests** (145 in total, 4 new):
  - `live_order_keys_forget_which_earlier_seat_folded`;
  - `live_order_keys_keep_raises_price_cards_and_rotate_with_the_button`;
  - `live_order_preflop_traversal_merges_keys_with_consistent_identities`;
  - `tables_carry_their_key_schema_and_refuse_unknown_ones`.
- **Example tests:** all pass.
- **Byte-identical reports:** the refactored pressure and admission screen reports reproduce #427's and #430's committed outputs byte for byte. They now take an arm name.

## 4. How the experiment ran

### 4.1 Steps

| Step | Purpose | Outcome |
|---|---|---|
| Trace measurement (`scripts/nplayer_key_collapse.py`) | How far four coarsening levels merge #430's played decisions | Level 1 (summarize earlier streets) 1.1–1.4×; **level 3 (live order) 2.3–2.9× postflop, 28× preflop**; level 4 (keep the hero's seat) about half of level 3 |
| Pilot, 2B nodes | Table growth, pipeline, mixed-schema arena; gate fixed in advance | Gate passed: **17.8M entries at 600M nodes**, against a 125M limit |
| Screen, 10B nodes | Strength on fresh deals under a frozen rule | Primary improved; check-call harm flag |

### 4.2 Screen design

- **Arms:** the control is #417's 10B (`086938a8…`). The live-order arm is the same recipe from scratch with `--key-schema live-order`.
- **Deals:** #427's four fresh banks (roots `20261025900000 + 100·bank + field index`), 4,096 blocks × 12 seatings, so **196,608 hands per field and arm**. Both arms play the same deals.
- **Fields:** trained (five copies of #417's 3B), random, check-call, tight-aggressive, pot-pressure, call-pressure, random-tight, trained/call/pressure.
- **Scoring:** all-in adjusted. Hands that end all-in before the river score their exact expected value over the remaining cards.
- **Rule:**
  - **Primary:** the trained field, improved if the 95% lower bound is above 0.
  - **Harm flags:** Bonferroni over the other seven fields.
  - **Secondary:** pot-pressure, with no gate.

### 4.3 Reproduction

The driver used on bb128 is `/mnt/data2tb/nplayer-live-order-screen-20261026/run.sh`. Its essential commands, from the repository root:

```sh
cargo build --release --locked --manifest-path native/hu20-trainer/Cargo.toml \
  --example nplayer_train --example nplayer_policy --example nplayer_inference \
  --example nplayer_paired_arena --example nplayer_allin_equity
B=native/hu20-trainer/target/release/examples
COMMON="--players 6 --stack-bb 100 --small-blind 50 --big-blind 100 --fast --roots-per-seat 8 \
  --seed 2026102361001 --max-entries 250000000 --freeze-at-cap --last-average-street 3 \
  --fast-gzip --max-seconds 1e100 --card-buckets K50_TABLES_DIR"
$B/nplayer_train $COMMON --threads 16 --nodes 10000000000 --key-schema live-order \
  --out live-10b-train.gz --telemetry live-10b-train.progress.jsonl
$B/nplayer_policy export live-10b-train.gz CHECKPOINT_SHA average live-10b-average.gz --fast-gzip
python -m scripts.audit_nplayer_policy_parallel live-10b-train.gz live-10b-average.gz --workers 8 --lookup-out live-10b-mass
$B/nplayer_inference convert live-10b-average.gz AVERAGE_SHA live-10b.bin --mass live-10b-mass/receipt.json RECEIPT_SHA
python -m scripts.nplayer_live_order_screen manifest --binary live-10b.bin --mass live-10b-mass --out OUT
# for each bank: nplayer_paired_arena batch OUT/arena-manifest-bN.json, then:
python -m scripts.nplayer_live_order_screen scan --out OUT
python -m scripts.nplayer_live_order_screen rows --out OUT --checkpoint live-10b-train.gz
python -m scripts.nplayer_live_order_screen training --out OUT --checkpoint live-10b-train.gz --mass live-10b-mass
python -m scripts.nplayer_live_order_screen equity --out OUT --binary $B/nplayer_allin_equity
python -m scripts.nplayer_live_order_screen report --out OUT --results RESULTS
python -m scripts.nplayer_live_order_screen breakdown --out OUT --results RESULTS --progress live-10b-train.progress.jsonl
```

The control pins and #417's paths are constants in `scripts/nplayer_pressure_screen.py` and `scripts/nplayer_admission_screen.py`. A same-seed rerun on bb128 should reproduce checkpoint `75245fbb…`: the trainer is identical for any thread count.

### 4.4 Artifacts

- **On bb128,** left for the vacuum cleaner, with nothing deleted:
  - checkpoint, average and audit under `/mnt/data2tb/nplayer-live-order-screen-20261026/`;
  - binary (gzipped) and traces under `/home/dberweger/nplayer-live-order-screen-20261026/`.
- **Pins:** [costs.json](costs.json).
- **Compact results in Git:**
  - [summary.json](summary.json): every field's intervals, per-bank changes and row classes;
  - [fields.csv](fields.csv);
  - [rows.csv](rows.csv): row classes by field, arm and street;
  - [training.json](training.json);
  - [breakdown.json](breakdown.json) / [breakdown.csv](breakdown.csv): §6 contributions and the §5.1 growth curves.

## 5. Mechanism

### 5.1 Table growth

Cumulative training telemetry, the same seed and recipe in both runs ([breakdown.json](breakdown.json) `growth`):

| Nodes | History entries | Live-order entries | Decisions without a row, history / live-order (cumulative) | Discarded traverser updates, history / live-order |
|---|---|---|---|---|
| 100M | 59.4M | 9.2M | 89.5% / 14.5% | 0 / 0 |
| 400M | 210.9M | 15.5M | 82.0% / 6.4% | 0 / 0 |
| 600M | 250.0M (frozen at 23,678) | 17.8M | 78.9% / 4.9% | 15.3% / 0 |
| 2B | 250.0M | 25.5M | 73.6% / 2.2% | 58.1% / 0 |
| 6B | 250.0M | 34.3M | 69.0% / 1.0% | 67.2% / 0 |
| 10B | 250.0M | 38.6M | 66.7% / 0.66% | 68.1% / 0 |

The live-order table is still growing at 10B, by about 1.9M rows per 2B nodes, but far below the cap. It reaches 10B in 363,668 iterations (control 390,401) and 1,335 s of training (control about 2,000 s).

**Rows at 10B** ([training.json](training.json)):

| | Preflop | Flop | Turn | River | All |
|---|---|---|---|---|---|
| History entries | 35.1M | 44.2M | 63.6M | 107.1M | 250.0M |
| Live-order entries | 1.18M | 6.26M | 10.2M | 20.96M | 38.6M |
| Regret updates per row, history | 2.0 | 2.7 | 2.8 | 2.0 | |
| Regret updates per row, live-order | **66.3** | **31.8** | **48.6** | **50.9** | |

- **Live-order composition:** 18.7M learned rows (regrets and mass), 14.5M opponent-only rows and 5.4M zero-mass rows.
- **Opponent-only rows:** they remain because traverser admission (#430) was off. With the table far from full they cost nothing.

### 5.2 Coverage in play

Share of focal decisions on learned rows ([rows.csv](rows.csv)):

| Against | All streets, control → live-order | River |
|---|---|---|
| Trained | 88.8% → 99.7% | 69.3% → 99.8% |
| Pot-pressure | 97.1% → 99.9% | 78.4% → 99.6% |
| Tight-aggressive | 99.0% → 100% | 86.5% → 99.8% |
| Random | 72.8% → 97.9% | 14.6% → 98.1% |
| Random-tight | 95.8% → 100% | 72.6% → 99.9% |
| Trained/call/pressure | 66.2% → 90.5% | 5.6% → 73.8% |
| Call-pressure | 55.3% → 68.2% | 0% → 2.8% |
| Check-call | 42.9% → 41.0% | 0% → 0% |

Coverage is near total wherever opponents bet or fold. It stays poor wherever several opponents call down: check-call, and call-pressure on the river.

## 6. Where the results come from

Each table splits a field's paired change into additive contributions. A category's contribution is its summed adjusted result over all hands of that arm, divided by the hands per arm. Contributions sum exactly to the field's change, checked for every field and dimension. Categories are the per-hand labels of `scripts/nplayer_loss_diagnosis.py`: how the hand ended, the preflop line, position, and the street of the first untrained decision. The arms play the same deals, but a hand can end differently in each, so shares can move between categories. Full tables are in [breakdown.csv](breakdown.csv).

### 6.1 Trained field: +105.4

| Category | Share, control → live-order | BB/100, control → live-order | Contribution |
|---|---|---|---|
| All-in showdown before the river | 8.0% → 5.6% | +139.0 → +197.9 | **+59.0** |
| Folded preflop | 74.4% → 76.5% | −112.2 → −57.4 | **+54.8** |
| Folded flop | 4.1% → 4.0% | −49.2 → −25.2 | +24.0 |
| River showdown | 2.1% → 3.2% | +14.7 → +26.8 | +12.1 |
| Won uncontested preflop | 4.4% → 4.3% | +49.0 → +30.5 | −18.5 |
| Won uncontested flop | 2.5% → 1.9% | +42.4 → +24.8 | −17.6 |

By preflop line:
- **3-bet pots as caller:** +59.4.
- **"Fold after investing":** losses halve, from −100.6 to −44.7 (+55.9).
- **3-bet pots as raiser:** −15.9. The bot 3-bets less, 5.8% → 3.5% of hands.

By position, every seat gains, and the blinds most (BB +26.1, SB +13.2). By the first untrained decision, the control had one in 10.1% of hands and the live-order bot in almost none.

**Reading:**
- **All-ins:** the bot goes all-in less often but wins far more when it does.
- **Folds:** it loses much less in hands it folds, so it puts less money in before folding.
- **3-bet pots:** it defends better when re-raised.
- **The cost:** it steals less.

All of this fits better-converged preflop and early-street decisions, which are where #421 found most trajectory changes start.

### 6.2 Pot-pressure: +58.4 (−31.0 → +27.3)

| Category | Share, control → live-order | BB/100, control → live-order | Contribution |
|---|---|---|---|
| All-in showdown before the river | 3.3% → 2.0% | −24.7 → +21.1 | **+45.7** |
| River showdown | 2.0% → 2.5% | −0.2 → +14.3 | +14.5 |
| Folded preflop | 67.7% → 67.5% | −40.5 → −29.3 | +11.2 |
| Won uncontested flop | 4.4% → 3.5% | +32.3 → +22.9 | −9.4 |

- **By preflop line:** 3-bet pots as caller +22.1, "fold after investing" +11.5, 3-bet pots as raiser +8.9.
- **By position:** the blinds gain most (BB +16.6, SB +12.3, BTN +11.8).

**Reading:** pot-pressure raises pot-size with value hands and some cheap bluffs, so its pots escalate quickly to all-in. The control lost those all-ins (−24.7) and the live-order bot wins them (+21.1). It enters fewer of them and with better hands, so it is choosing correctly which raise wars to join. #426 had located the gap in learned strategy rather than in the fallback. This screen supports that: coverage against pot-pressure was already 97% for the control, so the gain comes from better-estimated rows, not from new ones.

### 6.3 Tight-aggressive: +15.0

The gain is smaller but has the same shape. All-in showdowns before the river contribute +15.5 (−7.3 → +8.2); uncontested flop wins −5.9.

### 6.4 Check-call: −110.7, the harm flag

| Category | Share, control → live-order | BB/100, control → live-order | Contribution |
|---|---|---|---|
| River showdown | 44.7% → 42.2% | +229.8 → +139.6 | **−90.2** |
| All-in showdown before the river | 3.9% → 3.9% | +64.5 → +43.8 | −20.7 |

- **By preflop line:** single-raised pots where the bot raised account for **−98.1** (+230.7 → +132.6).
- **By position:** the loss concentrates in the small blind (−54.1).
- **By the first untrained decision:** hands that first leave trained rows **on the flop** contribute −115.3 (+193.5 → +78.2). Those whose first untrained decision is on the turn improve (+14.8), and that group grows from 14.6% to 17.6% of hands.

**Reading:**
- **Where the loss happens:** check-call never folds or raises, so every pot the bot opens goes multiway to the river. Those histories (5 callers, then checks and calls through the river) never occur in self-play. Both arms play them from the uniform fallback, at 49–53% missing rows and 0% learned on the river.
- **What differs between the arms:** the loss is concentrated in hands that are uniform from the flop on in both arms. So the difference has to come from which hands reach those spots, meaning the preflop raising range, not from postflop play.
- **The likely cause, still a hypothesis:** the live-order bot learned a preflop range that is right in self-play, where raises get folds and 3-bets. Against five callers that range has less multiway equity when the hand is then played at random. A preflop raise-frequency comparison would test it.
- **Not a key failure:** the field is unvisited under any key. The fix is visitation, for example training against calling opponents, or a dedicated multiway continuation. The bot still wins +180 against this field.

### 6.5 Other fields

- **Random +187.7:** mostly folded-preflop losses shrinking (+126.2) and all-in showdowns (+66.3).
- **Trained/call/pressure +81.5:** all-in showdowns before the river +49.8.
- **Call-pressure +5.6, unresolved:** river showdowns −30.2, offset by all-ins +28.7. This is the same multiway-calling pattern as check-call, at a smaller scale.
- **Random-tight −0.2, unresolved:** uncontested flop wins −18.1, offset by folds and river showdowns.

## 7. Validity

**Checks that passed:**
- **Control replay:** the control's absolute results match #427 and #430 on every field, so the same deals were replayed identically.
- **Opponents unaffected:** #417's 3B opponents (`6cd50bf1…`, history keys) found positive-mass rows for 89.3% of their decisions against the control and 89.5% against live-order. The trained-field gain isn't caused by broken opponent lookups.
- **Trace integrity:** all 64 traces pass the replay scan (hashes, legality, settlement), with zero fallback violations and 49,152 hands each.
- **Batches agree:** every resolved field has the same sign in all four banks, and the realized and adjusted changes agree in sign and size.
- **Trainer:** legacy output is byte-identical to `main`; live-order output is identical at 16 and 8 threads.
- **Information:** the key is built from the acting seat's public observation only.

**Threats and limits:**
- **One lineage.** Seed-to-seed variation is unknown. For scale, no earlier six-player recipe change moved the trained field by more than about +78 (#428, 30% pressure). That change also broke pot-pressure, where this one fixes it.
- **The trained field is #417's own 3B.** A different lineage's 10B might exploit that ancestor's weaknesses more easily than #417's 10B does. The scripted-field gains (pot-pressure, tight-aggressive, random) don't share this caveat.
- **Imperfect recall of actions.** Merged spots share one strategy, and CFR's convergence guarantees don't cover that. No harm shows on betting fields, but merges could matter in spots these fields don't reach.
- **Evaluation fields:** the scripted fields are fixed heuristics, not strong players. This isn't an exploitability measurement or release acceptance.

## 8. Open questions and suggested next steps

None of these is authorized automatically; the maintainer decides.

1. **Seed confirmation (the most important).** Train two more live-order lineages with new seeds, each with its own history-key control or a shared control, on fresh banks. Use a cross-seed rule like v0.6's acceptance.
   - Training is cheap (about 22 minutes per 10B lineage); the arena and all-in scoring dominate, at about 1h45m per arm against eight fields.
2. **Six players at 200 BB with live-order keys,** toward the owner's goal.
   - Pot and stack-to-pot buckets should transfer between stack depths, where exact amounts don't. Check whether the edges (2–128 BB pot, ½–16 SPR) need extending at 200 BB.
   - Deeper stacks add raise levels, and the raise cap of 3 may matter there.
3. **Check-call visitation.**
   - Test the preflop-range hypothesis in §6.4 first. It is cheap and read-only on existing traces.
   - Then try training against calling opponents, or a multiway continuation for unvisited called-down pots.
4. **Traverser admission on top of live-order keys.** It's irrelevant while the table is far from full, but becomes relevant if 200 BB or more players fill it.
5. **Key-level ablations.** Which summary features matter? Removing the action count or the price bucket, or keeping the hero's absolute seat, are one-flag-each experiments if they're ever needed. Don't chase them before seed confirmation.
6. **Release path.** The Python play stack and the three-player releases use history keys. A live-order release would need the web/runtime loaders to accept the schema. Today `KeySchema::from_identity` covers native tools only.
