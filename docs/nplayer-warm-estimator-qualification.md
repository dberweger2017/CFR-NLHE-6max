# Frozen warm-policy estimator qualification

Research proposal [424](https://github.com/dberweger2017/CFR-NLHE-6max/issues/424).
The owner requests implementation and correctness fixtures before the short
warmed-checkpoint run. Mature science and release training remain paused.

Use the existing four-player PR413 10B **current regrets**, read-only. Compare
external sampling from `sigma` with `q = 0.75 sigma + 0.25 check/call`.
Counterfactual prefix weights exclude the traverser's own actions. Correct
returned values, regret increments and the existing opponent-sampled averages;
never reset a missing history's prefix weight to one. Exact zero probability,
positive-product underflow, tied values and all-zero update vectors are distinct.

The diagnostic holds the warmed policy fixed. It accumulates research deltas in
an independent shadow ledger, never feeds them back into policy, and never
unfreezes, resumes, exports or rewrites the input checkpoint. The 100K shadow
threshold follows whole-batch admission, including zero-update entries. Report
overshoot, zero slots at admission/freeze/end, later positive learning, and
positive updates discarded after freezing. Shadow findings do not establish
successful admission during from-scratch training.

The fixed warmed workload is 32 batches × four traversers × eight roots: 1,024
root contexts per sampling mode, plus separate-process reproduction. A fixed
prefix cohort takes the first 64 blocks and eight balanced seatings from each
PR413 check-call, call-pressure and trained mixed field: 1,536 saved hands.
Inspect the entire upstream counterfactual reach rather than starting at the
missing turn/river state. Keep never-reached watch keys.

Measure nonnegative importance coefficients and root-grouped Kish ESS, not
ESS of signed regrets or payoffs. Report positive regret and average evidence
separately. A replicated-learning diagnostic requires both, four distinct
positive-weight roots and grouped ESS at least four. It is not a strength gate.

The planning allowance remains 26 minutes central / 60 minutes reserved, with
12 GiB new NVMe and a 25–40 GiB RAM scenario. This does not reserve space.
Source/input hashes, estimator review, exact small fixtures and fresh manual
resource admission precede any warmed run. Numerical/correctness failures stop
and remain retained; no scientific retry, parameter sweep or 10B run follows.

The companion release revision restores cyclic noninferiority to **−5 BB/100**,
all 24 seatings for mixed fields, and eight forward/reverse rotations for
homogeneous fields. It will explicitly settle the release watch-ledger policy,
explain reciprocal versus fixed-opponent peer estimands, and price hash-only
reproduction. No release allocation is accepted or launched by this PR.
