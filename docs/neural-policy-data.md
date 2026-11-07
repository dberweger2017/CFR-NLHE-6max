# Training data for neural policies

The first step of the [neural-policy track](../ROADMAP.md): situations from seeded play, each with the strategy of several tabular teachers and whether each teacher has a trained row there. Later steps train a network on these samples and test whether it generalizes to spots the tables never learned.

## Features

[`policy_features`](../native/hu20-trainer/src/policy_features.rs) turns one acting seat's observation into 612 numbers, each in [0, 1]. It reads only the observation, so a network never sees another seat's cards.

| Group | Count | What |
|---|---|---|
| Hand state | 22 | street, player count, live share, hero slot, pot, amount to call, price, hero and effective stack (in BB and against the pot) |
| Menu | 9 | the six legal menu labels and the size of each legal raise against the pot |
| Cards | 183 | hole and board cards (one bit per card), the hole cards' ranks and shape, and the K50 bucket after the flop |
| Seats | 126 | for each of six slots: present, hero, folded, all-in, live, stack, stack against the pot, chips this street and in total, then raises, calls and checks on each street |
| Recent actions | 272 | the last 16 actions, each with its slot, street, kind, raise target and chips paid |

- **Slots:** seats occupy six slots by position, the way the projected view places them. The button and blinds go in slots 0–2 and the other seats in the last slots. So a three-player table fills the same slots a six-player one does after three early-position folds. Empty slots read as absent, not folded.
- **Scaling:** amounts in BB are scaled by ln(1 + x) / ln(501), which is 1 at 500 BB. Ratios to the pot are capped at 32.
- **Pinning:** `SCHEMA` (`nplayer-policy-features-v1`) and `layout_sha256()`, a hash of every feature name in order, pin the layout. Each sample file records both. The network's Rust forward pass will use the same encoder, so training and play can't drift apart.

## Samples

[`nplayer_features`](../native/hu20-trainer/examples/nplayer_features.rs) plays seeded hands from a manifest. Seats are model or scripted players. At every decision of every seat, it writes one fixed-size record:
- the hand and decision index, player count, street, the actor's slot and whether a model or a script acted;
- the legal-label mask and the label chosen;
- for each teacher: its row status (positive mass, zero mass or none) and its strategy over the six labels, which is zero unless the row is trained;
- the 612 features, one byte each.

Teachers see the table through the projected view, as the Open Poker client and the paired arena do.

Everything is seeded per hand, by deck, stack draw and seat, through `stream_seed`. Hands run in parallel but are written in order, so a manifest reproduces its file byte for byte at any thread count. A file starts with `NPFEAT01`, a header length and a JSON header holding the layout, the teacher pins and the job. [`scripts/neural_policy_samples.py`](../scripts/neural_policy_samples.py) memory-maps it into NumPy arrays.

## Several teachers

A table can only label spots it trained. #458 trained three `widemix` seeds and #461 trained `widecap`, and a spot missing in one may be trained in another; this run measures how often. Samples carry all four teachers, so the imitation step can measure the network against a real strategy on spots the live model (`widemix` run 1) never learned.

## Measurement run

This PR makes no research claim. [The run](reports/neural-policy-data/run.sh) on bb128 checks the tool and sizes the next step:
- library tests, including the postflop encoding with the K50 tables;
- byte-identical files at 16 and 8 threads;
- throughput, bytes per sample and peak memory with four teachers loaded;
- each teacher's coverage by street and job;
- how often another teacher has a trained row where `widemix` run 1 has none.

The jobs are self-play and mixed fields on the wide grid at 3–6 players, plus #461's seven short tables with each of their fields. Results are in [the report](reports/neural-policy-data/results.md).
