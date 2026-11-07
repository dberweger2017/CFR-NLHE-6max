# Training data for neural policies: measurement run

[Design](../../neural-policy-data.md). Run on bb128 on November 7, 2026, 22:05–22:15 UTC, on commit `2feeae57` ([source commit](measure/source-commit), [tool hash](measure/binaries.sha256)). This is a tool qualification and sizing run, with no research claim.

## The tool works

- **Tests:** the library tests pass on bb128, including the postflop encoding with the real K50 tables, and so do the sample reader's tests.
- **Determinism:** one 2,000-hand job run at 16 and at 8 threads in the same process writes the same 22,837 records, `records_sha256` `68e6c785…` both times.
- **Reader:** all 47 measurement files load through [`neural_policy_samples`](../../../scripts/neural_policy_samples.py) ([readout](measure/read.jsonl)).

## Cost

| | |
|---|---|
| Hands | 78,000 over 45 jobs |
| Samples | 686,511 (every decision of every seat) |
| Play and write | 6.2 s, **about 110,000 samples/s** on 16 threads |
| Bytes per sample | 677 (612 feature bytes, 4 teachers × 13, 12 bytes of context) |
| Loading four teachers | about 9 minutes, single-threaded verification; this is nearly all of the run |
| Peak memory | 61.9 GB resident with all four teachers loaded |

So 30M samples would take about 5 minutes of play and 20 GB on disk. The loader, not the play, sets the cost. A separate session is speeding the loader up without weakening its checks.

## Teacher coverage

The share of decisions where the live `widemix` (run 1) has a positive-mass row, and how often another teacher has one where it doesn't. Teachers are the three `widemix` seeds and `widecap` run 1, the 400M-entry model. These count every seat's decisions, scripted seats included, so they cover far more passive lines than an arena's focal decisions do. Per-job numbers are in `measure/*.summary.json`.

| Jobs | Street | Decisions | `widemix` 1 untrained | Another teacher trained there |
|---|---|---|---|---|
| Wide grid, 3–6 players (self-play and mixed fields) | flop | 63,440 | 9.9% | 52.7% of those |
| | turn | 44,923 | 17.9% | 45.4% |
| | river | 35,311 | 28.8% | 35.6% |
| #461's 3- and 4-player short tables | flop | 25,667 | 8.0% | 62.7% |
| | turn | 18,741 | 18.6% | 41.7% |
| | river | 15,348 | 28.4% | 33.4% |
| #461's 6-player short tables | flop | 33,682 | 54.8% | **15.4%** |
| | turn | 26,144 | 70.9% | **7.9%** |
| | river | 22,536 | 81.7% | **5.1%** |

Preflop, `widemix` run 1 lacks a row for 0.1–2.4% of decisions.

## What it means for the next step

- **Away from six-player short tables, the other teachers cover a third to two thirds of the gaps.** That's a usable held-out test: does a network trained only on `widemix` run 1's rows predict another seed's strategy on spots run 1 never trained, better than uniform does?
- **At six-player short tables, every teacher misses the same spots.** All three seeds and the 400M model leave 85–95% of those postflop gaps uncovered (95% on the river). So no teacher can label the spots that matter most. The imitation step can test generalization there only indirectly, through the held-out test above and through play in the fallback step.
- **The six-player gaps come from fields the tables never saw.** Against `check-call`, `widemix` run 1 has a row for at most 3% of postflop decisions at the six-player short tables. Against copies of itself it's at 96.7–99.1%, and against `pot-pressure` and `tight-aggressive` at 92–99% (per-job summaries). This is the same visitation gap as in #431 and #462.
- **Sizing the next export:** the wide-grid and mixed-field jobs, at about 20–30M samples (14–20 GB), fit bb128's 82 GB free on the NVMe. Holding out whole short-table types and whole fields gives a test of generalization to unseen situations.
