# Cheaper weights for traversal inference

An exploration for the Deep CFR runs: one seed and a quick read, not a gate. Traversals spend much of their time in the advantage network ([timing](../advantage-2m-timing/results.md)). Could 16- or 8-bit weights make them cheaper without changing the targets?

- **Tool:** `nplayer_net_precision` (source commit `7de60454`). It runs a study kernel with the production kernel's layout (input-major weights, zero inputs skipped, f32 accumulation) and stores the weights as:
  - **f32:** a check. It gave the production kernel's bits on all 50,000 rows for every network.
  - **bf16:** the top 16 bits of each weight, rounded to nearest even.
  - **int8:** one symmetric scale per input row (max |w| / 127).
- **Reference:** the production f32 kernel (`Fast`).
- **Inputs:** the first 50,000 held-out rows of the 13M-row advantage subsample ([#480](../neural-capacity-sweep/more/results.md)): real feature vectors with their legal masks, 59 nonzero features per row on average.
- **Networks:**
  - `adv1375`: run 1's 0.5M advantage network at iteration 1375;
  - `run2-adv72`: run 2's 2M advantage network at iteration 72;
  - `net1` and `strategy800-s4000`: 2M policy networks from the neural-policy track;
  - `u-1024-1024-512`: an untrained uniform 2M advantage network. Its output is zero, so it is exact in every format; it only measures speed.
- **Machine:** the M4 (base M4 MacBook Pro, 16 GB), single thread, 10 seconds per format, November 11, 2026. Unit tests passed first ([build.log](build.log)).

[Runner](run.sh) · per-network JSON in [out](out)

## Answer

**Keep f32. bf16 saves 13–16% per network call, about 5–11% of a traversal decision, but on run 1's late advantage network it changes the strategy by 5.7% TV on average and the top action on 6% of rows. int8 is less accurate and no faster.**

| Network | Kind | f32 µs per call | bf16 µs | bf16 TV mean | bf16 top action same | int8 µs | int8 TV mean | int8 top action same |
|---|---|---|---|---|---|---|---|---|
| `adv1375` | advantage 0.5M, late | 3.81 | 3.40 (−11%) | **0.057** | **94.1%** | 3.95 | 0.365 | 62.4% |
| `run2-adv72` | advantage 2M, early | 14.50 | 12.43 (−14%) | 0.0067 | 99.2% | 14.93 | 0.082 | 91.8% |
| `net1` | policy 2M | 28.97 | 25.08 (−13%) | 0.0006 | 99.9% | 30.26 | 0.0055 | 99.1% |
| `strategy800-s4000` | policy 2M | 36.28 | 31.12 (−14%) | 0.0003 | 99.96% | 38.14 | 0.0021 | 99.7% |
| `u-1024-1024-512` | advantage 2M, untrained | 59.90 | 50.81 (−15%) | 0 | 100% | 61.71 | 0 | 100% |

Output error (largest absolute error per row, in the network's units): for bf16 on `adv1375`, mean 0.10, p99 0.25, max 4.4; for int8, mean 0.90, p99 3.0, max 63. The p99 TV is 1.0 for both formats on `adv1375`, and for int8 on `run2-adv72`: on 1% of rows or more the strategy flips entirely.

## Reading

- **Advantage networks are the sensitive ones.** Regret matching keeps only positive regrets and normalizes them. When those are small, a small error moves the strategy a lot, and when none are left it switches to a single action. Policy networks pass through a softmax, and bf16 barely moves them.
- **The late network is the most sensitive.** Under bf16, `adv1375`'s TV is about eight times that of run 2's iteration-72 network. A plausible cause is that late networks keep small positive regrets on several actions. If so, run 2's own late networks will be closer to `adv1375` than to `run2-adv72`.
- **The error is systematic, not noise.** One sample's sampling noise moves a late strategy by about 0.10 TV ([target noise](https://github.com/dberweger2017/CFR-NLHE-6max/pull/490)). bf16 would add a fixed 0.057 shift on top, every time, for the same decision.
- **The speed gain is small.** At one thread a decision costs about 24 µs outside the network. The bf16 saving is 2.1 µs on the 2M advantage network (14.5 → 12.4, about 5% of a decision) and up to 9 µs on the untrained one (about 11%). Any change also breaks byte parity with f32 runs.
- **int8 with one scale per row is no faster.** The extra multiply per input cancels the smaller loads, and it's an order of magnitude less accurate.

## Not measured

- **bb128** (x86, AVX2), where the memory system differs. The gain could be larger there, but the accuracy result wouldn't change.
- **Finer int8 scales** (per weight block), or **int8 with SIMD dot products**. These might be faster, but the accuracy bar set by `adv1375` is hard to meet.
- **The effect on a whole run.** A small strategy shift each iteration could compound, or wash out. Given the small saving, it's not worth a run to find out.
