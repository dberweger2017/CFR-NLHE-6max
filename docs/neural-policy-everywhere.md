# The network at every decision: protocol

Committed before any implementation run or arena hand. This is step 4 of the [neural-policy track](../ROADMAP.md), after [step 3](reports/neural-policy-fallback/results.md) passed and [#470](https://github.com/dberweger2017/CFR-NLHE-6max/pull/470) put the network fallback on the live short route.

## Question

Can the step-2 network replace the table outright, playing every decision, without losing to the tables it would replace? There are two places to check:
1. **Short tables:** against the live `widemix` with the network fallback (#470), at #461's seven short tables. This is where the network learned.
2. **100 BB six-handed:** against the live 100 BB route model `six`, #431's live-order 10B. The network never trained on this configuration as such, so this tests whether one small model can cover the deep game too.

These are the change-of-direction gates agreed on November 7: beat `widemix` plus routes at #461's seven short tables, and stay within 10 BB/100 of live-order 10B at 100 BB, on 3 seeds.

## Why

- **Step 3 showed the network generalizes to spots the table never trained.** Step 4 asks the harder question: does it match the table where the table *did* train?
  - Offline, the network is closer to its teacher (TV 0.10–0.125) than another seed of the same recipe is (0.23–0.28, #467). Training seeds of this recipe play about equally well, which suggests the gap may cost little.
  - Many positive-mass rows were barely visited: 68% of #467's rescue labels were near-uniform. The network might do better than the table there too.
- **The payoff is large if it holds.**
  - One 8.8 MB network covers 3–6 players at every depth it saw, where `widemix` takes 14 GB.
  - Step 5 (self-play beyond the teacher) needs a network that already plays whole hands. This measures where it starts.
- **This changes nothing live.** Any route change would be its own PR with your go.

## The network

Step 2's three networks are used exactly as in step 3, with the same files and pins (`5e276263…`, `ae573149…`, `f5fd32c6…`). There is no new training and no tuning. Run *k* uses network *k*.

- **Network everywhere:** at every focal decision, the focal samples the network's strategy on the real table's observation, through the same `PolicyNetwork::play` as step 3 and #470.
- **No table and no projected view.** The network reads the table directly.
- **Random draws:** the focal draws one random number per decision, as every policy does.

## Gate S: short tables

| | |
|---|---|
| **Arm 0** | the live client: `widemix` (`702e10cf…`) through the projected view, with the `net1` fallback, as #470 routes it |
| **Arm 1** | network *k* at every focal decision |
| **Tables** | #461's seven: `3p-5bb`, `3p-short-deep`, `3p-unequal`, `4p-short-deep`, `6p-5bb`, `6p-short-deep`, `6p-unequal` |
| **Fields** | step 3's: `mixed` (primary), `pot-pressure`, `tight-aggressive`, `check-call`, `random`, and at six players `live-copies` |

`live-copies` are now copies of the live client: `widemix` with the `net1` fallback. The host's network mode is extended to opponent copies for this.

In run 1, both arms play `net1` at `widemix`'s untrained rows. **So run 1's contrast isolates the network against the table at the rows the table trained.**

## Gate D: 100 BB six-handed

| | |
|---|---|
| **Arm 0** | `six` (#431's 100 BB live-order 10B, `f894a59f…`), the live band route's model, in the native view at its own trained configuration |
| **Arm 1** | network *k* at every focal decision |
| **Table** | six players, 100 BB each |
| **Fields** | `trained` (primary: five copies of #434's seed-2026102661001 live-order 10B, `ab7f8e16…`, foreign to both arms), `pot-pressure`, `tight-aggressive`, `check-call`, `random`, `mixed` |

Live-order keys at 100 BB have a learned row at almost every decision: #434 measured 99.6–99.8% even on the river against the trained field. So this is close to a pure network-against-table test. The exception is `check-call`, whose rivers #434 found entirely unlearned.

**Amendment, November 8, before any run or implementation hand:** the trained field was #417's 3B (`6cd50bf1…`), as in #434. That model has been archived off bb128. #434's seed-2026102661001 live-order 10B replaces it: the same recipe as `six`, from a different seed, so it's still foreign to both arms, and it's a stronger peer than a 3B. Its binary (`ab7f8e16…`) and mass receipt (`36650754…`) are pinned.

## Runs

| Run | Network | Gate S: banks × blocks per field | Gate D: banks × blocks per field | Roots |
|---|---|---|---|---|
| 1 (decides) | `net1` | 4 × 4,096 | 4 × 4,096 | `20261109100000 + 1000·bank + case index` |
| 2 (replicates) | `net2` | 1 × 4,096 | 1 × 4,096 | run 1's + 100,000 |
| 3 (replicates) | `net3` | 1 × 4,096 | 1 × 4,096 | run 1's + 200,000 |

Every block plays every cyclic seating, and both arms play the same deals.

## Decision rules, fixed now

All contrasts are arm 1 minus arm 0, all-in adjusted, BB/100, over blocks.

**Gate S, per table, run 1:** a Bonferroni 95% interval over the seven tables.
- **Network better:** lower bound above 0.
- **Table better:** upper bound below 0.
- **Otherwise no difference shown.**
- **Harm flag:** any other field whose Bonferroni 95% interval over the table's other fields lies entirely below −10 BB/100.
- **Replication:** runs 2 and 3 replicate a "network better" table when both their point estimates are above 0.

**Gate S passes** if:
- no table reads "table better";
- at least one table reads "network better" and replicates;
- no table has a harm flag.

**Gate D, run 1:** a one-sided 97.5% lower bound on the `trained` field.
- **Non-inferior:** the lower bound is above −10 BB/100.
- **Harm flag:** any other field whose Bonferroni 95% interval over the five other fields lies entirely below −10 BB/100. Check-call is reported but exempt: #434 flagged it for live-order keys themselves, and a flag there wouldn't separate the network from the table.

**Gate D passes** if run 1 is non-inferior with no harm flag, and runs 2 and 3 both have point estimates above −10.

**What follows:**

| Outcome | Next |
|---|---|
| **Both gates pass** | The network can replace the tables. A route PR (your go) would drop `widemix` from the short route, and the 100 BB question goes to step 5. |
| **Gate S passes, Gate D fails** | A network-only short route becomes possible (your go). The deep game keeps its tables, and step 5 targets it. |
| **Gate S fails** | The tables stay. Every table's interval is reported: the gap the network must close is step 5's baseline. |

A failure is reported as is, with no retraining or tuning in this study.

## Also reported

- **Agreement:** the share of focal decisions where the arms' strategies differ, that is where arm 0 plays a positive-mass row. Reported by table, field and street, with the network's TV from the row at those decisions. Arm 0's traces already record the row, and arm 1's record the network's distribution.
- **Absolute results per arm,** realized beside all-in adjusted.
- **Gate S's `check-call` field at the deep six-player tables,** step 3's open question.
- **Gate D's full field table,** including `check-call`.
- **Forward-pass cost per decision** and the arena's wall time.
- **Per-run results.**

## Qualification (the run stops on any failure)

1. **Tests:** native library and paired-arena host tests pass on bb128, including new tests for the `network-only` focal mode and for network-fallback opponent copies.
2. **Existing play unchanged:** with the new code, #469's 38-case smoke manifest reproduces its 76 traces byte for byte.
3. **Service and arena agree:** `scripts.openpoker_fallback_parity` passes on #469's smoke traces, as in #470.
4. **Pins:** the `widemix`, `six` and trained-field binaries, their mass receipts, and the network pins all match.
5. **Smoke:** run 1's network on every table at 64 blocks per field, on separate roots, through arena, scan, independent replay, all-in equity and report.

## Rules

- **Host:** bb128, all 16 threads, one job at a time. Stops: CPU 90 °C, VRM 100 °C, below 4 GB of available memory, below 10 GB of free NVMe. The GPU isn't used.
- **Expected cost:** step 3 took 6 h 17 min for seven tables. Arm 1 now runs the network at every focal decision, at about 1.8 ms each. Gate D adds a 100 BB table with fewer all-ins to settle. Estimated 8–10 hours.
- **Failures:** a research failure is reported as is, with no retry or retuning. Plumbing problems go in the PR.

## Limitations, known now

- **The networks imitate `widemix`.** Gate D tests generalization from `widemix`'s deep-grid rows to equal-stack 100 BB play. A miss there says little about what a network trained at 100 BB would do.
- **No 2-player or 5-player table.** Heads-up has its own models and no network.
- **Opponents are scripts and copies.** There are no live hands.
