# Open Poker client

`scripts.openpoker_bot` plays one bounded session at [Open Poker](https://docs.openpoker.ai/) with native n-player policies, or a local sandbox dry run. It authorizes no live play: live sessions are owner decisions. Routing evidence comes from [the phantom-fold and depth protocol](openpoker-phantom-depth.md).

## How a decision is made

1. **Tracking.** `src/openpoker/tracker.py` follows one hand: `hand_start`, `hole_cards`, `player_action` and `community_cards`.
   - **Chips paid:** taken from `contribution_delta`, else `stack_before − stack_after`, else the change from the seat's last known stack. The broadcast `amount` is never used, because the documentation doesn't define it.
   - **Starting stacks:** the current stack plus everything contributed this hand.
   - **Native layout:** dealt seats in seat order; the dealer becomes the native button.
   - **Chips:** Open Poker's 10/20 blinds become the trained 50/100, so one server chip is five native chips.
2. **Checking.** The native service (`nplayer_serve`) replays the record as dealer and must agree with the server before any policy acts:
   - every action must be legal;
   - the server's `valid_actions` must equal the engine's legal set: check, call amount and raise-to bounds;
   - every action's chips must equal what the engine charges, so the engine's current stacks match the server's.
3. **Hidden cards.** The engine needs a full deck. Unseen positions get unused cards in ascending order, and the policy sees only `Hand::observe` for the hero: its own cards and the dealt board.
4. **Routing.** `src/openpoker/agent.py` picks a route by the number of dealt players, then by depth.
   - **Route lists:** each player count has an ordered list of routes. A route may carry a depth band, `band_bb`. The first route whose band holds every dealt seat's starting stack, in BB, plays the hand. A route with no band always matches.
   - **Views:** live-order policies should use `"view": "projected"` at every size. It keeps the table's real, unequal chips, and adds phantom early-position folds below the model's player count. The native view needs the model's exact equal-stack configuration, which Open Poker never has.
   - **Mixed-stack policies** (`--stack-law`, see [the mixed-stack protocol](openpoker-mixed-stacks.md)) project with 100 BB phantom seats; real seats keep their chips.
5. **Translation.** The native action becomes `fold`, `check`, `call`, `raise` with an exact raise-to amount in range, or `all_in` when only an all-in raise is offered.
6. **Fallback.** Any failure along the way plays check if legal, else fold, and journals the reason: an unrepresentable hand, no route, engine disagreement, untranslatable action or decision timeout. Failures include blinds other than 10/20, a dealer outside the dealt seats, a possibly all-in blind, an unknown action kind and unknown chips.

## Session behavior

- **Authentication:** the API key comes from `OPENPOKER_API_KEY` and travels only in the `Authorization: Bearer` header. It is never printed or journaled.
- **Messages:**
  - `join_lobby` uses the declared buy-in (1,000–5,000 chips).
  - Each action carries a fresh `client_action_id` and the turn's `turn_token`.
  - A rejected action gets one safe retry, unless the token is stale.
- **Stopping:** after `--max-hands` completed hands, when `--stop-file` exists, on `busted`, or when the table closes. The client leaves the table first.
- **No automatic rebuy and no rejoin.**
- **Reconnects:** tried for up to 110 seconds of Open Poker's 120-second seat hold, followed by `resync_request`. Replayed events update the hand without acting. A snapshot that still holds the hero's `turn_token` is acted on once.
- **Journal:** every inbound and outbound message and every decision record goes to a new JSONL file (`--journal`, never overwritten).

## Running

```sh
cargo build --release --locked --manifest-path native/hu20-trainer/Cargo.toml --example nplayer_serve
python -m pip install -r requirements-openpoker.txt
```

`routes.json` from the [routing results](reports/openpoker-routing/results.md): the 100 BB models inside [89.4, 136.9] BB, the mixed-stack model elsewhere. The heads-up route follows the [heads-up study](openpoker-heads-up.md).

```json
{"3": [{"agent": "policy:p3", "view": "projected", "band_bb": [89.4, 136.9]}, {"agent": "policy:mix", "view": "projected"}],
 "4": [{"agent": "policy:p4", "view": "projected", "band_bb": [89.4, 136.9]}, {"agent": "policy:mix", "view": "projected"}],
 "5": [{"agent": "policy:p5", "view": "projected", "band_bb": [89.4, 136.9]}, {"agent": "policy:mix", "view": "projected"}],
 "6": [{"agent": "policy:six", "view": "projected", "band_bb": [89.4, 136.9]}, {"agent": "policy:mix", "view": "projected"}]}
```

The routing studies set the actual routes and bands: [routing](openpoker-routing.md) and [heads-up](openpoker-heads-up.md).

Dry run against the local sandbox (no key):

```sh
python -m scripts.openpoker_bot --routes routes.json --policy six MODEL.bin SHA256 --card-buckets K50_DIR \
  --journal NEW.jsonl --max-hands 200 --sandbox [--sandbox-seats seats.json]
python -m scripts.openpoker_audit NEW.jsonl
```

**Deployment check.** Before a live session, load the exact route set on the host that will play:

```sh
python -m scripts.openpoker_deploy_check --routes routes.json --policy six MODEL.bin SHA256 ... \
  --card-buckets K50_DIR --tables 200 --hands-per-table 20 --out NEW.json
```

It plays sandbox hands at random tables (2–6 dealt players, random seats, stacks log-uniform over 10–250 BB) and reports:
- load time;
- the service's peak memory;
- decision latency;
- fallback reasons;
- routes used.

It fails if any decision takes over 5 seconds, or if any fallback has a reason other than a possible all-in blind. The mixed-stack model is a 14 GB binary, so the bot plays from bb128 (128 GB), not the 16 GB M4.

For a live session, drop `--sandbox` and set `OPENPOKER_API_KEY`. The audit reports:
- decisions by status;
- fallback reasons;
- routes used;
- rejected actions;
- the hero's final stacks;
- the undocumented server details: the fields of `player_action` and `your_turn.players`, whether a broadcast raise `amount` is a raise-to total or an increment, and whether blinds arrive as events.

## Sandbox

`src/openpoker/sandbox.py` serves the documented messages over a local WebSocket:
- the native engine deals and settles;
- seats can have gaps, the dealer rotates, stacks are unequal;
- opponents are scripted.

It encodes this repository's reading of the documentation: blinds are not broadcast, and a raise's `amount` is the raise-to total. It therefore tests plumbing and exact chip handling, not the real server's behavior. The first live session's audit is the test of those readings.

## Checks

`tests/test_openpoker_client.py` plays sandbox hands with 2–6 dealt players, gapped seats, unequal and short stacks:
- **Exact reconstruction:** every decision reconstructs with no engine disagreement. The only permitted fallback is a possibly all-in blind.
- **Disagreement:** an altered legal set always falls back.
- **Translation:** the action mapping is exact.
- **Bounded session:** a WebSocket session joins, plays, leaves at its limit and never journals the key.

## Known limits

- **Heads-up has no trained route.** The released HU100 models use the legacy trainer format, which `nplayer_serve` doesn't load; a two-player live-order model needs training first. Until then, a 2-player route is a script or the fallback.
- **Stack management.** Leaving and rejoining at 100 BB is not implemented; it is an owner decision.
- **Server behavior.** Dead buttons, missed blinds and other undocumented server behavior fall back rather than guess.
