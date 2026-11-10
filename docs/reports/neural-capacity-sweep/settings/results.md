# Fit settings for the 2M advantage network

The fourth exploration on the [capacity sweep](../results.md): one seed and a quick read, not a gate. Run 3 can change its fit cheaply once [#484](https://github.com/dberweger2017/CFR-NLHE-6max/pull/484) lands, so: is run 1's recipe right for the 2M network?

- **Data:** [#480](../more/results.md)'s 13M training rows and 499,533 held-out rows, from the pilot's advantage reservoir after iteration 122.
- **Fits:** `mlp-2m` on all training rows, seed `20261110700001`, on the M4 (base M4 MacBook Pro, 16 GB, MPS, fp32), November 10, 2026, 19:26–23:14 UTC.
- **The baseline** is #480's `mlp-2m-r13m`, with run 1's recipe:
  - AdamW at learning rate 1e-3, cosine schedule, weight decay 1e-4;
  - batch 8,192;
  - 20,000 steps.
- **Each fit changes one setting.** Errors are squared big blinds summed over legal labels, on held-out rows; lower is better.

[Runner](../run.sh) (`settings` mode) · [report.json](report.json) · per-fit `result.json` and logs in this folder

## Answer

**Run 1's recipe is about right. The one thing that helps is training on more samples: about 3% from 3× the steps.**

| Change | Error | vs baseline | Deep CFR rows | Warm rows | Training-row error | Minutes |
|---|---|---|---|---|---|---|
| None: baseline (#480) | 681 | | 1122 | 106 | 515 | 17 |
| **60,000 steps** | **659** | **−3.2%** | 1075 | 117 | 334 | 67 |
| Batch 32,768, 20,000 steps (4× the samples) | 669 | −1.7% | 1090 | 121 | 366 | 69 |
| No weight decay | 679 | −0.3% | 1119 | 106 | 520 | 18 |
| Weight decay 1e-2 | 680 | −0.1% | 1121 | 106 | 523 | 19 |
| Learning rate 3e-3 | 712 | +4.6% | 1179 | 104 | 568 | 16 |
| Batch 32,768, 5,000 steps (the baseline's samples) | 726 | +6.6% | 1203 | 104 | 600 | 19 |
| Learning rate 3e-4 | 751 | +10.3% | 1248 | 103 | 639 | 15 |

## Reading

- **More samples help, and small batches use them better.** 3× the samples at batch 8,192 beat 4× at batch 32,768, which took the same time on the M4. At an equal number of samples, the big batch is clearly worse (726 against 681).
- **The 60k fit flattens halfway.** Held-out error is 660 at step 30,000 and 659 from step 36,000 on, so 30–36k steps capture the gain.
- **The gain is all on Deep CFR rows,** which drop 4.2% (1122 → 1075). Warm rows get worse (106 → 117), and the gap between training and held-out error doubles (166 → 325). Longer fits start memorizing the noisy sampled regrets. Runs from scratch, like run 1 and run 2, have only Deep CFR rows, which is the part that improves.
- **Weight decay doesn't matter,** from 0 to 1e-2.
- **A learning rate of 1e-3 is best** of the three tried.

## For run 3

The production fit isn't this one. Each iteration continues the advantage network for 1,000 steps from the last one, and only the strategy network gets a single fresh fit at the end (20,000 steps). Both readings below are therefore hypotheses for run 3, not measurements of it:
- **More continued steps per iteration,** say 2,000–3,000, if #484 makes the fit cheap enough. That is the in-loop equivalent of seeing more samples.
- **A longer final strategy fit,** 30–40k steps instead of 20k. This study fitted advantage targets, so the strategy fit needs its own check.
- **Keep the batch, learning rate and weight decay.**

## Limitations

- **One seed and one subsample,** from early in the warm-start pilot. Late rows from scratch runs may be noisier.
- **Static data.** In Deep CFR the reservoir and its targets change every iteration, so steps per iteration trade fit quality against tracking.
- **The two long fits ran slower** (67–69 minutes against an expected 50–60), probably because another job shared the M4. That changes time, not the results.
