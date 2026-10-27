# Mixed-stack training: results

This is a run of [the protocol](../../openpoker-mixed-stacks.md), committed before training. It was one lineage on bb128, from source `ac6bf061`, with [controller](run.sh) and [guard](guarded.sh). The data files are [`results.json`](results.json) (every field, interval and missing share) and [`fields.csv`](fields.csv).

All values are BB/100, all-in adjusted, over 4 banks × 4,096 blocks. Each contrast is `mix` minus `six`, with both models seen through the projected view.

## Primary results

| Table | Primary field | `mix` − `six` | Decision interval | Verdict |
|---|---|---|---|---|
| `100bb` | `six` copies | −14.6 | [−22.2, −7.0] | inconclusive |
| `50bb` | `six50` copies | +32.4 | [+25.1, +39.8] | mixed better |
| `20bb` | `mixed` | +63.3 | [+55.8, +70.8] | mixed better |
| `200bb` | `mixed` | −11.7 | [−64.2, +40.9] | no difference shown |
| `unequal-a` | `mixed` | +78.9 | [+52.3, +105.5] | mixed better |
| `unequal-b` | `mixed` | +82.0 | [+58.8, +105.2] | mixed better |
| `unequal-4p` | `mixed` | +63.2 | [+49.9, +76.5] | mixed better |

**Recommendation under the prespecified rule: keep `six`.** Of the four conditions, three hold:
- no harm flag at `100bb`;
- no depth table reads "fixed better";
- five depth tables read "mixed better".

The first condition fails. At its home depth, `six` beats `mix` by 14.6 against copies of `six`. The interval's upper bound, −7.0, rules out a gain, but its lower bound, −22.2, crosses the 10 BB/100 margin, so "mixed adequate at 100 BB" is not shown.

## What the numbers say

- **Away from 100 BB, `mix` wins by a lot.** It gains 32–82 at 50 BB, at 20 BB and at all three unequal tables. In #445, the cost of playing at the wrong depth was about 50 BB/100; mixed-stack training recovers most or all of that.
- **The results hold across fields.**
  - Against `pot-pressure`, `mix` gains 49–61 at every off-depth table.
  - Against `tight-aggressive`, it gains 27–50.
  - Against copies of `mix` itself, `six` loses 62–76 more than `mix` does.
- **At 100 BB the cost is modest but real:**
  - −14.6 against copies of `six`;
  - −13.1 against copies of `mix`;
  - −29.9 against the mixed scripts;
  - +9.8 against `pot-pressure`.
- **200 BB is noisy:** the standard error is 19.9, against 3–10 elsewhere. The other fields there favor `mix`: +69.6 against `mix` copies, +50.0 against `tight-aggressive` and +57.8 against `pot-pressure`. Two fields favor `six`, `check-call` (−24.0) and `mixed` (−11.7), and neither interval excludes zero.

**Missing shares** (decisions without a positive-mass row, all streets):

| Table | `six` | `mix` |
|---|---|---|
| `100bb` | 10.4% | 14.0% |
| `50bb` | 22.7% | 13.8% |
| `20bb` | 42.3% (flop onward ≥ 99.9%) | 15.8% |
| `200bb` | 18.8% | 16.8% |
| `unequal-a` | 27.9% | 15.1% |
| `unequal-b` | 36.9% | 14.7% |
| `unequal-4p` | 38.7% | 7.6% |

`mix` covers about 14–17% missing at every six-player table, whatever the depth. `six`'s coverage collapses off-depth: at 20 BB it has essentially no trained rows after the flop.

## Findings beyond the rule

1. **The table filled.** `mix` reached the 250M-entry cap at 9.44B of 10B nodes, so the last 5.6% of training updated existing rows only. The fixed-depth models used 18–35M entries; drawing depths sends training through about 9× as many distinct rows. More capacity, or more nodes, might narrow the 100 BB gap, but that wasn't tested.
2. **The model is 14.1 GB** as a binary (6.3 GB gzipped), against 2.2 GB for `six`. It doesn't fit the 16 GB M4 alongside anything else. Open Poker play with `mix` would run on bb128, or would need a smaller model.
3. **Routing by effective depth** would keep `six` near 100 BB and use `mix` elsewhere. The data are consistent with it, but no depth band was tested: there are no tables between 50 and 200 BB other than 100. Choosing a band would need its own prespecified test.

## Qualification and checks

- **Library tests** passed on bb128.
- **Fixed training unchanged:** the fixed 100 BB checkpoint at 100M nodes is still `482a0f8f…`.
- **Mixture determinism:** the 16-thread and 8-thread mixture checkpoints at 100M nodes are byte-identical (`2e4b5b77…`).
- **Inputs:** `six` and `six50` matched their pins.
- **Smoke:** the full pipeline passed at 100M nodes and 64 blocks per field.
- **`mix`:**
  - checkpoint `d3f9dbd5…`, binary `64c693c4…`;
  - 250,000,227 entries, frozen at iteration 603,800 of 639,385;
  - training drew each of the 13 depths for about 14.16M seats.
- **Replay:** all 86 bank-0 traces (2,031,616 hands) replay independently in the reference engine.
- **Fallbacks:** no fallback violations.

## Costs

| Stage | Time (UTC) | Duration |
|---|---|---|
| Build and qualification (library tests, three 100M trainings) | 11:29–11:33 | 4 min |
| Smoke | 11:33–11:38 | 5 min |
| Training `mix` | 11:38–12:15 | 37 min |
| Export, mass audit, conversion and verification | 12:15–12:44 | 29 min |
| Arena, scan and replay, 4 banks | 12:44–13:09 | 25 min |
| All-in equity | 13:09–16:05 | 2 h 56 min |
| **Total** | | **4 h 36 min** |

- **Resources:**
  - CPU and VRM both peaked at 76 °C.
  - Memory peaked at 24.6 GB.
  - Free space stayed at 60 GB or more on the NVMe and 89 GB or more on the HDD.
- **Disk:** about 34 GB under `/mnt/data2tb/openpoker-mixed-stacks-20261027/`.
- **No plumbing failures.** One pre-existing flaky test, which races on a shared temp file, ran single-threaded as planned.
