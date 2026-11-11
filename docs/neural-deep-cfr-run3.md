# Deep CFR from scratch with a 2M advantage network, run 3: protocol

Run 3 answers [issue 482](https://github.com/dberweger2017/CFR-NLHE-6max/issues/482): **does a 2M-parameter advantage network learn a better policy than run 1's 0.5M network, per iteration and per day of bb128?** It replaces [run 2](neural-deep-cfr-2m.md) ([PR481](https://github.com/dberweger2017/CFR-NLHE-6max/pull/481), closed as failed). This protocol is committed before launch. Any change after launch is reported as a deviation. Controller: [`run.sh`](reports/neural-deep-cfr-run3/run.sh).

## Why a run 3

Run 2 stopped twice on the CPU's 90 °C guard (plumbing, not research). The first stop was at iteration 65, the second at iteration 178 even on 12 threads, so it can't give a clean 24-hour read.

The stops were short spikes in the first seconds of a traversal. The machine ran 4–5 °C warmer than in run 1's first day in every stage, including the GPU fit, where the CPU is nearly idle, and run 1 had already peaked at 88 °C. The owner has since set the BIOS power limits and fan curve.

After a second failure we start over. Since we start over, the run uses [PR484](https://github.com/dberweger2017/CFR-NLHE-6max/pull/484)'s speed code:
- its outputs are byte-identical on bb128, checked for traversal, reservoir add and CUDA fit;
- it's about twice as fast per iteration.

So run 3 is the same experiment as run 2, at about twice the iterations per day.

## What's the same

Everything in [run 2's protocol](neural-deep-cfr-2m.md) except the points below:
- the one change from run 1: a 612→1024→1024→512→6 advantage network;
- the seed and the uniform first iterate, with the iteration-1 identity with run 1 as a stop;
- the exploration bound, traversals, reservoirs, fits and strategy network;
- the 24-hour window, with stops added back as in run 2's deviations;
- checkpoints 25, 50, 100, 200, 300, 400, 800 and 1,200, on run 1's roots;
- the final evaluation E1–E4 with run 1's roots and pins, and the reading rules.

## What's different, and why

| | Run 2 | Run 3 | Reason |
|---|---|---|---|
| Code | `1cd624a9` (run 1's traversal) | PR484's speed code | About 2× faster per iteration, byte-identical outputs on bb128 |
| Build | default | `-C target-cpu=native` | 1.3× faster traversals on the i7, byte-identical (PR484) |
| Guard | wakes every 5 s, so each stage rounds up to a multiple of 5 s | checks sensors every 5 s, notices a stage's end within 0.1 s | About 2.5 s per stage (PR484). The stops are unchanged: CPU 90 °C, VRM 100 °C, GPU 87 °C. |
| Fits | export in a second process | `train --export` and batch prefetch | Same network bytes on CUDA (PR484) |
| Failed traversal | could carry on to the add (run 2's second stop) | stops the run | Bug found in run 2 |
| Traversal threads | 12 after the first stop | 16, like run 1 | Records don't depend on the thread count, as qualification checks. After the owner's new fan curve, eight back-to-back 16-thread traversals with a 2M network peaked at 80 °C, against run 2's 91–93 °C stops. |

**Parity record.** Run 3's iterations 1–177 should reproduce run 2's records exactly, since it's the same experiment on byte-identical code. `parity-run2.jsonl` records each one, as a full-scale check of PR484. A mismatch is recorded and reported, not a stop. Run 3 is a valid run either way, but a mismatch would mean PR484 changes numbers after all.

**Projection.** Run 2's iterations took about 62–67 s (traversal 33–36 s, add 10 s, fit 16 s). From PR484's bb128 measurements, about 25–35 s per iteration with the 2M network, so roughly 2,000–3,000 iterations in 24 hours, against run 1's 1,375. That's past every checkpoint up to 1,200.

**Equal time (E3) still compares a day of bb128.** It's now a day on faster code against run 1's day on slower code. The report states that E3 mixes the network change with the code speed. E4, at equal iterations, isn't affected.

## Storage

- `/home/dberweger/neural-deep-cfr-run3-20261111` (evidence);
- `/mnt/data2tb/neural-deep-cfr-run3-20261111` (snapshots, every 100 iterations);
- `/dev/shm/neural-deep-cfr-run3` (reservoirs).

**Disk:** the NVMe has about 26 GB free, and the guard stops at 10 GB. A 2M advantage model with its optimizer state takes about 27 MB, so keeping 2,000–3,000 would overrun it. Each iteration's fit continues from the previous model, which nothing needs afterwards, so its directory is deleted. Its 9 MB network file is kept for every 10th iteration and every checkpoint, about 2.5 GB in all. Every network's SHA-256 stays in the next iteration's `it<N>.json`. Run 1 and run 2 kept all of theirs.

Run 2's tree stays as read-only evidence.

## Deviations

- **Stops at iteration 1,500, not after 24 hours** (owner's decision, November 11, about 10:00 UTC, at iteration 1,040).
  - **Why 1,500:** run 1's final is at 1,375 and its last checkpoint at 1,200. A checkpoint at 1,500 (4,000-step fit, like the others) shows whether run 3 keeps improving past where run 1 flattened.
  - **What it costs:** about 11 hours of training, which bb128 gets back for the next run.
  - **E3 changes meaning.** It compares run 3's final at 1,500 with run 1's final at 1,375, nearly equal iterations, both 20,000-step fits. It's no longer an equal-time comparison. Run 3 reaches 1,500 in about 12.5 hours against run 1's 24 for 1,375, which the report states.
  - **E4 is unchanged:** iteration 1,200 against run 1's 1,200.
- **Resume fix.** The controller found its place by scanning for advantage networks, which pruning deletes, so a resume would have restarted at iteration 1. It now resumes after the last line of `progress.csv`. The fix was applied when the controller was restarted for the new stop.
- **Short-burst power limit lowered to 150 W** (owner, about 08:13 UTC, until reboot) to reduce fan noise. Outputs are unaffected and traversal time didn't change measurably.

