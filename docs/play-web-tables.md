# Multi-seat local table (2–6 seats)

`src.play_api.table_server` runs one local table with 2–6 seats. Each seat is one of:

- `human`: you (at most one seat);
- `policy:NAME`: a hash-pinned native n-player export (`nplayer-policy-v1`, gzip or binary), loaded with `--policy NAME PATH SHA256`;
- `script:NAME`: one of the native scripted controls used by the n-player arenas: `random`, `check-call`, `tight-aggressive` or `pot-pressure`.

Stacks are 20, 100 or 200 BB with 0.5/1 BB blinds and reset every hand. The button moves one seat clockwise each hand, starting at seat 1. A table without a human seat is a bot table: you watch it with Play, Pause and Step, and every seat's cards and decisions are visible.

## Launch

Build the native decision service once, then start the table. This example seats you against two 100 BB three-player models:

```sh
cargo build --release --example nplayer_serve --manifest-path native/hu20-trainer/Cargo.toml
python -m src.play_api.table_server --stack-bb 100 --card-buckets K50_TABLES_DIR \
  --policy model-a MODEL_A_PATH MODEL_A_SHA256 --policy model-b MODEL_B_PATH MODEL_B_SHA256 \
  --seat human --seat policy:model-a --seat policy:model-b
```

Open **http://127.0.0.1:8766/** and enter the token from `results/play-web-tables/access.token`. Scripted seats need no tables or models, for example `--seat human --seat script:tight-aggressive --seat script:pot-pressure --seat script:check-call --seat script:random --seat script:random` for six seats.

- Several seats may name the same policy, and one file pinned under several names loads once.
- Every policy must match the table: its player count, stacks and blinds are checked at startup.
- Each table configuration keeps its own private journal under `--data-dir`, and a session only reopens on the configuration that created it.

## Bet sizing

**With a model seat, sizing is restricted to the models' training menu** (`min-pot-conditional-jam-v1`): fold or check, call, minimum raise, pot raise and, when it is within twice the pot, all-in. A model looks up each decision by the exact bet sizes so far, so an off-menu size reaches a spot it never trained and it plays uniformly at random from then on. Free sizing is offered only at tables with scripted seats, until n-player action translation exists.

## How a decision is made

The Python hand engine deals and keeps the authoritative hand; it is the same engine as the heads-up table. For every bot decision, the server sends the deck and the action record to the native decision service (`examples/nplayer_serve.rs`). The native engine replays them and checks that its legal actions, stacks, street bets, contributions and folds equal the Python engine's. Only then does it give the bot the acting seat's observation. The bot never receives the hand itself. Any disagreement stops the request.

A bot's action probabilities depend on its private cards. At a table with a human they are shown only after the hand ends, in **Bot decisions this hand**.

## Journal and replay audit

Each session journals the starting states of its deal and bot generators, every hand's deal seed, every action, and for each bot decision its sampling seed, menu, probabilities and whether the spot was trained. `--verify-session SESSION_ID` replays every completed hand and checks that:

- every deal seed and bot seed is the next draw from the journaled generators;
- the native service still gives the same action and probabilities for every bot decision;
- the public events still hash to the journaled digest;
- the Python result equals the native settlement for every seat, and the session totals add up.

## Benchmarks

A table with a human seat offers **Benchmark** sessions alongside casual play. A benchmark fixes its hand count (1–5000) before the first deal; the page shows **Hand X / N** and **Deal hand X / N**.

**While it runs, nothing beyond the table itself is shown:** no running total, no hand-history results and no bot decision details. **End benchmark early** keeps the completed hands and marks the result incomplete, recording any unfinished hand.

When it ends, the result shows your net and BB/100, your result in each position, each player's net and its trained and uniform lookups, and wins, losses and ties. **Download result JSON** saves the same report, served at `/api/sessions/ID/benchmark/export`.

**Seat swap.** At a table with two or more different bots, a benchmark can swap their seats. Every arrangement of the bots around your fixed seat plays one equal block of hands, in a fixed order: with two bots, the first half is you → A → B and the second half is you → B → A. The hand count must be a multiple of (arrangements × seats); for three seats that is a multiple of 6. Then every arrangement also gives you every position equally often. Cards are fresh every hand; no deal is repeated. The report adds your result per arrangement.

**The rules are the same for every player.** Everyone has the same stack, blinds and button rotation, and everyone sees only their own cards. At a table with model seats, everyone also bets from the same menu, the models' own.

`--verify-session` also checks a benchmark's hand count and status. It checks that the button followed its schedule and that every hand used its scheduled seat arrangement.

## Limits

- **Large models load fully into memory.** Large 100 BB checkpoints need disk-backed loading on a 16 GB machine; that is a separate change.
- **No action translation.** See *Bet sizing*.
