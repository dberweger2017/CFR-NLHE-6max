# How noisy are Deep CFR's advantage targets?

An exploration for the Deep CFR runs: one seed and a quick read, not a gate. The capacity sweep found the advantage fit limited by rows, and longer fits start memorizing the sampled regrets ([fit settings](../neural-capacity-sweep/settings/results.md)). This study measures how much of a target is sampling noise, and whether the exploration bound changes it.

- **Code:** run 1's code (`4a4bf2b`) plus a probe, `nplayer_deep_cfr noise` (source commit `7e8ed016`). Native and Python tests passed first ([tests.log](tests.log)).
- **Probe:** for each deal, play the sampled path, including the traverser's own actions, to the traverser's first decision on the chosen street. Then rerun everything below that decision **32 times** with independent random streams and a fresh exploration budget, keeping each run's regret vector, which is the record the fit would see.
- **Deals:** 40,000 per setting at 3–6 players, seed `20261111000001`, with run 1's K50 tables. Fewer deals reach the later streets.
- **Networks:**
  - **late:** run 1's advantage network at iteration 1375 (`adv1375`);
  - **untrained:** a fresh uniform 0.5M network at iteration 1, which plays every action equally often.
- **Bounds:** 3 / 8 (run 1's: explore every action at 3 decisions per street, 8 on the path), 2 / 6 and 2 / 8.
- **Machine:** the M4 (base M4 MacBook Pro, 16 GB), 10 threads, November 11, 2026, 00:14–10:05 Swiss time. The M4 slept for several hours on battery overnight, so wall time is not compute time.

[Runner](run.sh) · [report.json](report.json) · per-setting metadata in [runs](runs) · [summary log](summary.log) · [analysis](../../../scripts/neural_target_noise.py)

## Measures

All errors are in the fits' units: squared big blinds summed over the decision's legal labels.
- **Noise:** the variance of one sample around its deal's 32-sample mean. No network can learn it away.
- **Signal:** the variance of the per-deal means across deals, minus the noise left in a 32-sample mean. This is what the network should learn.
- **Noise share:** noise / (noise + signal).
- **TV:** total variation between the regret-matched strategy of one sample and that of the mean. 0.10 means 10% of the probability mass moves.
- **All signs agree:** the share of samples whose sign (positive or not) matches the mean's on *every* legal label at once. With 3–6 legal labels this is strict, so it can fall below one half.
- **Nodes:** nodes visited below the probed decision, per sample.

## Answer

**Late in a run, targets are mostly signal: noise is 25% of the variation preflop and 9% on the river. With an untrained network about 60% is noise. Smaller bounds make each row noisier and don't buy more rows per second, so run 1's 3 / 8 stays.**

### Run 1's bound, 3 / 8

| Network | Street | Deals | Noise (± SE) | Signal | Noise share | TV | All signs agree | Nodes |
|---|---|---|---|---|---|---|---|---|
| late | preflop | 38,993 | 96 ± 4 | 291 | 25% | 0.10 | 83% | 242 |
| | flop | 13,660 | 94 ± 7 | 432 | 18% | 0.09 | 87% | 87 |
| | turn | 5,191 | 106 ± 13 | 652 | 14% | 0.10 | 87% | 33 |
| | river | 2,879 | 57 ± 14 | 553 | 9% | 0.06 | 93% | 10 |
| untrained | preflop | 39,209 | 412 ± 6 | 266 | 61% | 0.36 | 35% | 188 |
| | flop | 8,198 | 940 ± 39 | 693 | 58% | 0.39 | 41% | 86 |
| | turn | 2,372 | 1,364 ± 94 | 910 | 60% | 0.38 | 43% | 35 |
| | river | 690 | 1,825 ± 212 | 1,123 | 62% | 0.37 | 45% | 12 |

By player count, preflop noise rises with the table: from 82 at 3 players to 112 at 6 for the late network, and from 132 to 737 for the untrained one. Signal rises too, so the noise share barely moves (late: 23% → 27%). Per-player figures are in [report.json](report.json).

### Bounds

| Network | Street | Noise 3 / 8 | Noise 2 / 6 | Nodes 3 / 8 | Nodes 2 / 6 |
|---|---|---|---|---|---|
| late | preflop | 96 | 100 (+5%) | 242 | 180 (−25%) |
| | flop | 94 | 100 (+6%) | 87 | 72 (−18%) |
| | turn | 106 | 116 (+9%) | 33 | 30 |
| | river | 57 | 57 | 10 | 10 |
| untrained | preflop | 412 | 529 (+28%) | 188 | 124 (−34%) |
| | flop | 940 | 987 (+5%) | 86 | 66 (−23%) |
| | turn | 1,364 | 1,414 (+4%) | 35 | 30 |
| | river | 1,825 | 1,849 (+1%) | 12 | 11 |

- **2 / 8 equals 2 / 6 after preflop:** the samples are identical, byte for byte. From the flop on, 2 per street can never reach 6 explored decisions. Preflop, 2 / 8 visits 194 nodes instead of 180, with the same noise (100.4 against 100.1).
- **The bound doesn't shift the mean targets.** Per deal, the squared difference between the 3 / 8 and 2 / 6 means is 6–71% of what independent noise alone would give. That is below 100% because both bounds share random streams. A systematic shift would push it above 100%. This matches the design: a sampled action still gives an unbiased value.
- **Fewer nodes doesn't mean more rows.** Past the bound, decisions write no advantage sample, so a smaller bound also writes fewer rows per traversal. In run 1's [bound study](../neural-deep-cfr-scratch/bound-study), rows per second were about the same for every bound: 22,900 (3 / 8), 20,600 (2 / 8) and 18,500 (2 / 6) for the untrained network, and 23,600 (3 / 8) against 22,800 (2 / 8) for the pilot's iteration-310 network. A smaller bound therefore gives about as many rows per hour, each noisier. 3 / 8 is at least as good on both counts.

## Reading

- **Late-run targets are good enough that noise isn't the main limit.** A single late sample moves the strategy by about 10%. Most of the variation it carries is real.
- **Early targets are mostly noise.** At iteration 1 a sample gets every sign right only 35–45% of the time. Linear weighting already gives early iterations little weight in the average, but early networks steer the traversals that follow.
- **Noise grows with the table.** Six-player preflop targets are the noisiest late, and by far the noisiest early.

## For run 3 (hypotheses, not measurements)

- **Keep 3 / 8.** Smaller bounds give noisier rows at about the same rows per second.
- **If early noise matters,** a schedule that writes more samples per decision early (for example, a larger bound or repeated probes for the first iterations) would target the 60% noise there. That needs its own study. Linear weighting may already make it unimportant.
- **Mid-run noise is unmeasured.** These two networks are the ends of run 1. A probe at run 2's checkpoints would show how fast noise falls.

## Limitations

- **One seed and two networks,** from run 1. Run 2's networks may differ.
- **One decision per deal,** the traverser's first on each street. Later decisions in the same street aren't probed.
- **Later streets have fewer deals,** and they are the deals the network chooses to continue. The untrained river has only 690.
- **Times are rough.** The M4 shared its cores with another job for part of the night and slept for several hours, so node counts are the cost measure here, and run 1's bound study gives the rows per second.
