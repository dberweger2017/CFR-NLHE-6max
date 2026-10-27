# First live Open Poker session (protocol)

This protocol is committed before the session. The owner authorized one session of up to 200 hands from bb128, with no rebuy. It is a plumbing test, not a strength measurement: nothing is promoted, and no default or release changes.

## Why

Every check so far ran against the local sandbox, which encodes this repository's reading of the Open Poker documentation ([client](openpoker-client.md)). Only the real server can show whether that reading holds:
- whether blinds arrive as `player_action` events;
- whether a broadcast raise `amount` is a raise-to total or an increment;
- which fields `player_action` and `your_turn.players` carry;
- whether the engine's replay agrees with the server's `valid_actions` and chips at every decision.

## What plays

- **Client:** `scripts.openpoker_bot` from this branch, with the `nplayer_serve` service built from the same commit.
- **Routes:** exactly the set from #450's final deployment check:
  - 100 BB models (`hu100`, `p3`, `p4`, `p5`, `six`) when every dealt stack is within [89.4, 136.9] BB;
  - mixed-stack models (`humix` heads-up, `mix` at 3–6 players) otherwise.
- **Pins:** the seven binaries and SHA256s of that check, verified at load.

| Alias | SHA256 |
|---|---|
| `six` | `f894a59f…` |
| `mix` | `64c693c4…` |
| `p3`, `p4`, `p5` | `1a607613…`, `66ec2f87…`, `bdc5ab50…` |
| `hu100`, `humix` | `1722f0d8…`, `9d39dda9…` |

## Session

- **Host:** bb128. The API key comes from the M4's Keychain over SSH standard input into the bot's environment. It never touches a disk, a command line or the journal.
- **Buy-in:** 2,000 chips, which is 100 BB at 10/20.
- **Limit:** `--max-hands 200`. The session also ends on `busted` or `table_closed`.
- **No rebuy and no rejoin:** auto-rebuy is set off after joining, and the client sends no manual rebuy.
- **Clean exit:** `leave_table`, then wait for `player_left` for the bot's seat or `not_at_table`.
- **Manual stop:** a stop file, used only if the bot misbehaves, for example repeated rejected actions. A manual stop is reported.
- **Journal:** every message and decision, kept on bb128 under `/mnt/data2tb/openpoker-live-pilot-20261027/`. Only the offline audit's summary is committed.

## What the report states

From `scripts.openpoker_audit`:
- hands played and how the session ended;
- decisions by status, fallback reasons and routes used;
- rejected actions by code;
- the server details listed under **Why**;
- the bot's chips at the start and the end.

The chip result is descriptive only. No-limit results vary by roughly 100 BB per 100 hands or more, so 200 hands can't tell a winning bot from a losing one.

## Reading the result

- **Plumbing holds** if all of these are true:
  - the session joins, plays and exits cleanly;
  - no action is rejected;
  - every fallback is a possible all-in blind or a hand outside the contract that the client correctly refuses, such as a dead button.
- **Engine disagreements, rejected actions or unknown messages** are client findings. They are reported with journal excerpts and fixed in a follow-up before any longer session. They are not retried in this PR.
- **The owner decides** any longer or repeated live play.
