# First live Open Poker session: results

This is a run of [the protocol](../../openpoker-live-pilot.md) and its amendment, from bb128 with [`run.sh`](run.sh). The offline audits are [`audit-1.json`](audit-1.json) and [`audit-2.json`](audit-2.json). The journals stay on bb128 under `/mnt/data2tb/openpoker-live-pilot-20261027/`.

## Summary

- **The bot busted after 45 of its 200 hands.** Under the no-rebuy rule that ends the pilot.
- **Plumbing holds** after the session 1 fixes:
  - no rejected actions;
  - no fallbacks in session 2;
  - clean exits in both sessions.
- **Both busting losses came from missing policy rows.** When a decision has no trained row, the policy plays uniformly at random over its whole action menu, all-in included. Those two decisions lost 2,137 chips, more than the whole 2,000-chip buy-in.

## Sessions

| Session | UTC | Hands | Decisions | Ended | Chips |
|---|---|---|---|---|---|
| 1 | 22:19–22:28 | 17 | 15 policy, 3 fallback | stop file, after the two client findings | 2,000 → 1,924 |
| 2 | 22:34–22:51 | 28 | 48 policy, 0 fallback | `busted`, then `leave_table`, then `player_left` | 2,000 → 0 |

- **Net:** −2,076 chips, about −104 BB over 45 hands. That sample says nothing about strength.
- **Session 1's three fallbacks** were the two client findings in the protocol amendment: street labels and mid-hand joins. The session 1 source is kept as `source.session1`, and session 2 ran the fixed commit.
- **Routes:** every policy decision went to `mix`, through the projected view.
  - Session 1: 15 decisions at 6 players.
  - Session 2: 22 at 5 players and 26 at 6 players.
  - The 100 BB band never matched, because one opponent held about 2,240 BB.

## Decisions without a trained row

Six of 63 policy decisions (9.5%) had no row: one in session 1 and five in session 2. The arena studies measured 1–4%. Chips are server chips; the bot's raises are its total for the street.

| Hand | Street | Situation | Uniform draw | Result |
|---|---|---|---|---|
| `a7f6dfe5` | preflop | facing 113 to call | fold | no chips lost |
| `f98d561c` | flop | facing 99 to call | call | the bot won the hand |
| `39b8f323` | flop | facing a check-raise, pot 349 | raise to 627 | 4-bet, so it folded: **−707** |
| `c69df4e8` | turn | checked to, pot 510 | raise to 992, all-in | opponent folded: **+270** |
| `2c70ab3f` | turn | jacks on an ace-high board, facing 207, pot 495 | raise to 1,430, all-in | called and lost: **−1,430** |
| `7a4916b6` | preflop | 4 BB left, below the trained grid | raise to 72, all-in | busted |

**What it means:** the uniform fallback was also in every arena study, so the measured results include it. Self-play opponents rarely exploit it, but live opponents with deep stacks punish a random all-in. A safer missing-row rule is the obvious follow-up, for example check or fold, or the nearest trained row. Two more things raise the miss rate here:
- stacks far off the grid, like 2,240 BB and 4 BB;
- live lines the blueprint rarely reaches.

## Server details now confirmed

- **Blinds** are not broadcast as events.
- **`player_action` fields:**
  - every action carries `contribution_delta`, `stack_before`/`stack_after` and `amount_mode`;
  - all 82 raises and all-ins are `to_total`, so `amount` is the raise-to total;
  - folds, checks and calls are `incremental`.
  - The audit's 9 "increment" readings in session 2 came from its own use of the street labels, not from the server. The audit now takes streets from `community_cards`; rerun on both journals, it reads all 81 raises as raise-to totals. The committed `audit-*.json` files are the original outputs.
- **Street labels:** an action's `street` is the street after it, `showdown` included.
- **Seat lists:**
  - `your_turn.players` lists every seated player, with `seat`, `name`, `stack`, `avatar_url`, `public_profile_slug` and `is_pro`, but not who was dealt in;
  - `table_state.seats` gives `in_hand` and `folded`.
- **Rebuy and leaving:**
  - `set_auto_rebuy` with `enabled: false` is answered by `auto_rebuy_set`;
  - `leave_table` after a hand is answered by `player_left` with reason `left`;
  - after `busted`, it is answered by reason `busted`.
