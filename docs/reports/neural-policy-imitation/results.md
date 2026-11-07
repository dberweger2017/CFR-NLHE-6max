# Can a network imitate the blueprint where it never trained? Results

[Protocol](../../neural-policy-imitation.md), committed before any export or training. Run on bb128 on November 7, 2026, 22:39–23:03 UTC. The export ran on commit `2b1ddbfa`, and training and evaluation on `f7a6b421`, which changes only the controller (see Plumbing).

**Verdict: fails on all three training seeds.** On the rescue spots, the network is about 0.019 TV *further* from the other teachers than uniform is. The rule needed it to be at least 0.05 closer. Under the protocol, step 3 doesn't follow from this test. The result stands as reported, with no retraining or tuning.

The breakdown below shows why the test was weaker than it looked. It doesn't change the verdict.

## Primary test

The rescue spots are test samples where the live `widemix` (run 1) has no trained row and another teacher has one. The contrast is TV(network, target) − TV(uniform, target), with a 95% interval over hands.

| Seed | Rescue spots | Contrast | 95% upper bound | Passes (upper < −0.05) |
|---|---|---|---|---|
| 1 | 51,897 | +0.0184 | +0.0195 | no |
| 2 | 51,897 | +0.0188 | +0.0199 | no |
| 3 | 51,897 | +0.0186 | +0.0198 | no |

By split, on every seed, the contrast is +0.019 to +0.020 on the wide grid and +0.015 to +0.016 on the 3- and 4-player short tables. The six-player short tables, reported but not pooled, give +0.025 to +0.027. [decision.json](results/decision.json), `results/measures-seed*.json`.

## Imitation where the teacher trained

| | Wide grid (held-out deals) | 3- and 4-player short tables (unseen in training) | 6-player short tables (unseen) |
|---|---|---|---|
| TV(network, `widemix` 1), all streets | 0.116 | 0.125 | 0.102 |
| TV(uniform, `widemix` 1) | 0.519 | — | 0.534 |
| TV(another seed, `widemix` 1): seed noise | 0.245 | 0.279 | 0.230 |
| Network picks the teacher's top label | 83.8% | 83.0% | 85.8% |

These are the same to the third decimal on all three seeds.

By street on the wide grid:

| Street | Preflop | Flop | Turn | River |
|---|---|---|---|---|
| TV(network, `widemix` 1) | 0.065 | 0.25 | 0.26 | 0.25 |
| Seed noise | 0.21 | 0.34 | 0.35 | 0.32 |

So the network reproduces its teacher's trained rows more closely than another training seed of the same recipe does, on tables it never saw. Postflop the margin is smaller, about 0.08–0.09 TV.

## Why the primary test was weak (exploratory, after the decision)

[`explore.py`](explore.py), written and run after the decision and added in this PR, splits the rescue spots by how far their target is from uniform. Seed 1 is shown: shares pooled over all splits, TV as the range across splits. Seeds 2 and 3 agree within 0.01. `results/explore-seed*.json` has the rest.

| Target's TV from uniform | Share of rescue spots | Network TV to target | Uniform TV to target |
|---|---|---|---|
| under 0.1 | 68% | 0.04–0.07 | 0.001–0.004 |
| 0.1–0.2 | 7% | 0.16–0.17 | 0.15–0.16 |
| 0.2–0.3 | 8% | 0.23 | 0.25 |
| 0.3–0.5 | 10% | 0.31–0.33 | 0.37–0.38 |
| 0.5–1.0 | 6% | 0.50–0.56 | 0.60–0.62 |

- **Two thirds of the rescue labels are effectively uniform.** The other teachers did visit those spots and hold positive mass there, but their strategy never moved off uniform. The protocol treated "positive mass" as "trained". Here it mostly means "barely visited", so uniform wins those spots by construction, and the test mostly measured that.
- **Where the labels carry information, the network beats uniform.** That's the 0.2–1.0 bands, 25% of rescue spots: by 0.02–0.10 TV, more as the target moves further from uniform. It's still far from the target in absolute terms, but that target is a different seed, and seeds differ by 0.23–0.35 even where both trained.
- **This is a description, not a test.** It doesn't revise the verdict. A follow-up should define informative labels before looking, for example by the teacher's visit count or its TV from uniform, and then test generalization in play (step 3), where it finally matters.

## Data and models

| | |
|---|---|
| Export | 2.63M hands, 23.4M samples (15 GB): train 2.4M hands, test-wide 120,000, test-short 114,000 |
| Export time | 13.3 min: about 9.5 min loading four teachers, 3.5 min play (110,000 samples/s), peak 61.9 GB |
| Training samples | 16,971,858 (`widemix` run 1's positive-mass rows) |
| Training | 4 epochs × 12.5 s on the RTX 2070 SUPER (1.36M samples/s); 86–87 s per seed including data loading; GPU peak 74 °C |
| Loss by epoch (seed 1) | 0.636, 0.589, 0.576, 0.571 (seeds 2 and 3 within 0.001) |
| Weights | seed 1 `d222a165…`, seed 2 `734d9b17…`, seed 3 `3d76edb5…`; metadata and data pins in `results/model-seed*.json` |
| Evaluation | about 10 s per seed over 2.4M test samples |

## Plumbing

- **Attempt 1:** the run stopped after a complete export because the controller never created `models/`, the training log's folder. Fixed in `f7a6b421`. The controller's markers skipped the finished tests and export, so the same data was trained on. Attempt 1's stages are in [attempts/](attempts/attempt1-stages.json).
- **GPU temperature stop:** the sampler compared the driver's decimal GPU temperature as an integer, so its GPU stop couldn't fire. A separate watchdog on bb128 covered training at the protocol's 87 °C; the peak was 74 °C. Fixed in `f7a6b421`.
- **Connection:** the controlling Mac lost its link to bb128 twice during the run, which was unaffected.
