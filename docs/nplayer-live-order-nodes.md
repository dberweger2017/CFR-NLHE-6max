# Six-player live-order node ladder: 10B → 30B → 50B (protocol)

This protocol is committed before any training or evaluation. It asks whether training live-order models beyond 10B nodes keeps improving them. The question decides the node budget for the 200 BB six-player work. It is a one-lineage screen: nothing is promoted, and no default or release changes.

## Why

With history keys, six-player strength flattened after 10B (#417: 10B → 15B was −2.2 BB/100 against the trained field). That table froze at about 6% of training, so extra nodes could only refine rows that already existed.

The live-order table never freezes. In #431 it held 38.6M rows at 10B and was still growing by about 1.9M rows per 2B nodes, and three seeds confirmed a +110 gain at 10B (#434). **The hypothesis:** with nothing frozen, more nodes keep making the bot stronger.

## Lineage and checkpoints

- **Lineage:** #431's live-order lineage: seed 2026102361001, `--key-schema live-order`, #417's recipe (fast mode, 8 roots per seat, 250M entries with whole-iteration freeze, average scope 3, 100 BB).
- **Training:** resumed from its 10B checkpoint (`75245fbb…`) to **30B** and then **50B** nodes. `--nodes` is a total, so each resume continues the same run.
- **Evaluated:** the 10B (`f894a59f…`, #431's binary), 30B and 50B endpoints. The run records the table's growth; if it reaches the 250M cap, that's recorded too.

## Qualification (the run stops on any failure)

1. **Resume:** a live-order run straight to 200M nodes and one stopped at 100M and resumed to 200M produce byte-identical checkpoints (seed 2026102361001, 16 threads).
2. **Input pins:** #431's 10B checkpoint and its decompressed binary match their recorded SHA256.
3. **Pipeline:** export, average-mass audit, binary conversion and verification pass for the 30B and 50B checkpoints.

## Evaluation

- **Contrasts:** two paired arenas, each the earlier checkpoint against the later one as focal:
  1. **10B → 30B**
  2. **30B → 50B**
- **Fields:** the screens' eight fields. The trained fields use #417's 3B (`6cd50bf1…`).
- **Deals:** one new set of four banks shared by both contrasts, roots `20261026800000 + 100·bank + field index`, 4,096 blocks × 12 seatings each. No earlier run used them.
- **Scoring:** all-in adjusted; the adjusted result is the decision quantity.

**Decision rule, fixed now:**
- **Primary:** 10B → 30B against the trained field, all-in adjusted, pooled over the four banks (16,384 blocks). **Improved** if its 95% Student-t lower bound is above 0; otherwise **not shown**.
- **Second contrast:** 30B → 50B against the trained field, classified the same way: **improved** (lower bound above 0), **worse** (upper bound below 0), or **not resolved**. It says whether returns are still positive at 30B.
- **Harm flags:** per contrast, Bonferroni 95% intervals over the other seven fields; a field whose upper bound is below 0 is flagged. Pot-pressure is reported with its own interval.
- **Descriptive:** each checkpoint's table entries, missing and discarded shares, and regret updates per row by street, plus learned-row coverage in play.

**What follows:**
- **If the primary improves:** the 200 BB work starts at 30B, or at 50B if the second contrast also improves.
- **Before that becomes the recipe:** the same extension on #434's two seeds, whose 10B checkpoints are resumable, gives the three-seed result. It gets its own protocol and doesn't start automatically.
- **If the primary isn't shown:** 200 BB starts at 10B.

## Rules

- **Host:** bb128, 16 threads. Stops: CPU 90 °C, VRM (Thermistor 15) 100 °C, below 20 GB free on the HDD, and below 10 GB free on the NVMe.
- **Disk:** all working files on the HDD under `/mnt/data2tb/nplayer-live-order-nodes-20261026/`, about 30 GB. Inputs from #431 are read only.
- **Expected cost:** about 5 hours. Training 10B → 50B takes about 1h30m; each contrast takes about 25 minutes of arena and 70 minutes of all-in scoring.
- **Failures:**
  - A research failure is reported as is, with no retry, retuning or extra hands.
  - A qualification failure stops the run before training.
  - Plumbing problems go in the PR.
