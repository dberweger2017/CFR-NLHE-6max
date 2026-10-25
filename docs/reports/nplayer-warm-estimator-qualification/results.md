# Warmed passive-history estimator qualification

The corrected estimator passes fixtures, independent review and deterministic
reproduction. **This fixed diagnostic does not demonstrate the repeated positive
learning required to justify the proposed visitation campaign.** Passive-biased
sampling admits more new keys, but most of those shadow slots receive zero updates.
No training, new arena hands, model exports or automatic continuation followed.

[PR425](https://github.com/dberweger2017/CFR-NLHE-6max/pull/425),
[proposal424](https://github.com/dberweger2017/CFR-NLHE-6max/issues/424),
[frozen protocol](../../nplayer-warm-estimator-qualification.md),
[complete compact evidence](results.json), [independent review](independent-review.json).

## Fixed workload and correctness

The existing four-player100BB PR413 10B checkpoint is read-only. Policies use
its **current regrets**, not its average export. There are 1,024 root contexts
per mode: ordinary external sampling `q=sigma`, and passive sampling
`q=.75*sigma+.25*legal-check/call`. All2,048 contexts are reproduced in a new
process. Eight initial artifacts match byte for byte, including every root,
row ledger and summary; source/model/K50/config pins still match afterward.
The repeat streams comparison/hashes without retaining a second raw tree.

All121 existing native library tests,14 standalone estimator fixtures and five
Python controller fixtures pass on the target host. The implementation-head CI
also passes all five checks. The owner-authorized independent reviewer found
two reporting gaps before the run: grouped/linear terminal coefficients and
unconditional per-key coefficients. Both were corrected and independently
cleared before loading the warmed checkpoint. Neither correction changed the
estimator increments, fixed workload or player.

The estimator preserves upstream zero reach. Importance coefficients correct
the existing external-sampling increments under fixed sigma; own-action reach
does not enter counterfactual regret/average weights. Evaluator-owned cards and
terminal payoffs do not become policy inputs. This qualifies a frozen-policy
diagnostic, not convergence of an adaptive exploration trainer.

## Learning and admission

The shadow table is separate from the immutable model. It admits whole32-root
batches, including rows whose batch updates are zero, and freezes at a100K
threshold. The two modes share root identities but can traverse different trees.

| Measure | Ordinary sampling | Passive-biased sampling |
|---|---:|---:|
| Traversal nodes | 531,750 | 620,539 |
| Admitted new shadow rows | 90,089 | 105,635 |
| Freeze point | Not reached | Batch17 /544roots |
| Whole-batch overshoot | 0 | 5,635 |
| Zero at admission | 59 | 87,414 |
| Zero at freeze | Not applicable | 87,404 |
| Initially zero, later nonzero by end | 0 | 21 |
| Zero at end | 59 (0.0655%) | 87,393 (82.7311%) |
| Post-freeze discarded key-batch records | 0 | 81,002 |
| Targeted turn/river replicated-learning rows | 0 /0 | 0 /0 |

Discarded records count key appearances per batch, not unique keys. Freeze/end
zeros concern admitted rows only. All-missing coefficient tables additionally
include increments after the cap, even when their keys were not retained.
Of the87,393 passive zero-update rows,87,392 have only zero coefficients;
one has a positive coefficient with zero update. Ten of the21 initially zero
rows become nonzero by freeze and11 afterward. The zero-replication result
applies to admitted rows and watched potential rows, not every untracked
discarded key.

Positive learning does occur on other missing rows. Across the targeted P0/P1/P2
families, ordinary sampling admits3,955 turn rows and35,236 river rows;2,767/25,519
have positive average evidence and1,187/9,692 have nonzero regret evidence.
Passive sampling admits6,411/27,638; the corresponding counts are646/3,969 and
344/1,893. These are separate counts, not their intersection. Neither mode meets
the prospective per-key requirement of both kinds of evidence from at least four
distinct roots and grouped ESS>=4 each. Positive-coefficient per-key median ESS
is1 in these groups; observed maxima remain approximately2 or less. Sparse
revisitation is therefore a separate limitation from zero reach.

P0 means no postflop raises; P1 means only the queried key owner's postflop raises;
P2 means one other aggressor plus at least two non-owner check/calls. These
families describe public histories and do not identify hand strength.

## Saved missing histories and weight concentration

The fixed1,536-hand prefix cohort contains436 missing turn/river decision
prefixes representing267 unique watch keys. **434/436 prefixes have exactly zero
upstream counterfactual target reach** under the warmed current-policy self-play
law. Both positive prefixes occur in call-pressure (one turn, one river).
All324 check-call missing prefixes have zero target reach. These are likelihoods
under the modeled self-play policy, not under the historical scripts.

Ordinary sampling encounters none of the267 watch keys. Passive sampling
encounters two river P1 keys, both with zero learning coefficients;265 remain
unencountered. No watched key receives positive-weight learning. Keeping all
never-hit keys prevents an apparent improvement from selecting only survivors.

This does **not** prove that every compatible hidden state for an abstract key
has zero reach. Nor does a never-hit key prove zero reach: limited root sampling
can miss a positive-probability key. Resetting weights at a missing history would
manufacture learning under a different objective and is not a qualified repair.

Among **all missing** targeted turn/river update events, passive sampling's exact
zero fractions are78.9% turn regrets,81.8% turn averages,76.4% river regrets and
76.2% river averages. Ordinary sampling has no zero coefficients in those
events, although tied action values can still produce zero regret vectors.

For passive missing rows, root-grouped coefficient ESS by family ranges from
11.9–71.3 for turn regrets and9.4–165.2 for river regrets; average counterparts
range17.0–33.7 and16.4–85.6. Each denominator is the same1,024 root contexts,
including zero groups. These pooled family figures do not establish repeated
learning of any individual key. Event ESS treats correlated branches separately
and is reported alongside grouped ESS, never as independent sample count.
The global terminal root-value coefficient ESS falls from1,024 to478.3 under
passive sampling; that is a concentration diagnostic, not a playing-strength ESS.

[All raw/linear missing coefficients](missing-coefficients.csv),
[global root-grouped metrics](root-grouped-coefficients.csv),
[row groups and per-key ESS summaries](rows.csv),
[every watch-key group](watch-keys.csv), [prefixes by field](prefixes.csv).

## Cost, failures and resource context

Main execution October25 00:01:57–00:20:06UTC (02:01:57–02:20:06Madrid):
**18m09.21s**, below the26-minute central estimate and60-minute allocation.
All three main stages return0; no scientific retry or extension occurred.

| Component | Wall seconds | User+system CPU seconds |
|---|---:|---:|
| Target build and native fixtures | 176.15 | 1,401.39 |
| Prefix preparation/source hashing | 10.81 | 10.37 |
| Target controller fixtures | 0.13 | 0.12 |
| Initial diagnostic process | 399.55 | 402.97 |
| Fresh-process reproduction | 641.26 | 644.15 |
| Verification/readout subprocess | 22.25 | 21.90 |
| Entire main wrapper, including controller work | 1,089.21 | 1,100.23 |
| Subsequent compact aggregation | 23.19 | 23.19 |

Rows overlap: wrapper CPU/wall includes its three stages. Review, local
implementation, source transfer and report-writing time are not included as
measured target compute. Initial/repeat native checkpoint loads take298.69/481.78s;
prefix audits0.160/0.268s; traversal/output20.40/36.31s. Native totals359.98/587.17s
also include final checkpoint hashing; stage walls include pre-start hashing.
Do not attribute every residual second to loading.

Sampled process-family peak is**20.35GiB**, minimum host available RAM82.69GiB;
CPU/Thermistor15 maxima**73/76°C**. Maximum sampled swap use475,308,032B is a
host measurement, not study-attributed swapping. Minimum sampled free NVMe
16.45GiB; eight initial diagnostic artifacts total1,098,614,179B (1.023GiB),
excluding source/build/cohort/logs. A concurrent owner-managed HDD backup and
other host activity existed; this is **not an isolated runtime benchmark**.
No causal slowdown or complete concurrent-job CPU/I/O attribution is claimed.

One earlier build attempt failed before starting Cargo because the noninteractive
SSH PATH lacked Cargo. Its source-v1/build-v1 logs and failure remain retained.
The corrected attempt used only a process-local Cargo PATH, then passed all
target tests/build before scientific admission. It was a plumbing failure,
not a repeated scientific run. No global environment, scheduler, other job,
resource guard or production trainer was changed.

## Decision and provenance

**Do not launch the proposed mature visitation campaign from this result.**
The fixed requirement was not demonstrated. A successor hypothesis would need
to address upstream target support and repeated useful admission, with its
objective change stated explicitly. This small sample does not reject all
visitation methods or establish the value of filtering zero rows. Shadow
admission is not fresh-training admission, and coverage is not strength.

Four-player-only v0.7 remains separately priced and storage-blocked; its gates
are unchanged. No release seeds, menus, search, defaults or earlier PR verdicts
change here. All original/partial evidence and borrowed inputs remain protected;
the compute stage has ended and the cleaner received a natural completion notice.

- Scientific source: `cc28e45d0d842ec68721d14b9224ce232bcad0dc`,703source pins.
- Actual binary SHA256: `0286d5ec5ceb7466c68e001cc03cfa3aa19600eb35eb42cc8001cd313e902d23`.
- Config: `094dce6bf86409bd026af020d2e372ab6dcce1e4583292e30f40da31ede06a25`.
- Review receipt: `ab9fa380570a9fdd03fcf5b961f24b5ca43bdf0e313c3b7d48d2a97783040188`.
- Input checkpoint: `2071d1e7fcbf3294942a978cc01ca8c817b4174f3bdedda072758d68c08bd2a1`.
- Prefix cohort: `04f3af02476807b97345443dcdb1bf71de578219a8398151a70db030ac7f82a7`.
- Initial artifact manifest: `8a85d599bd4cb17aaacb03f2749303856b2fa399492a3b0399b5a8d4a64f1e3e`.
- Verified receipt: `d3d864033e3159376acd3c25aaa26d9a225bfc0d85f1e1c1f5e702dfa573d639`.

Use protected ordinary files at
`bb128:/home/dberweger/nplayer-warm-estimator-qualification-20261025/`:
`main-v1/{config.json,prefix-cohort.jsonl,initial,repeat,verified.json,readout.json,stage-costs.json,resources.jsonl}`,
`ESTIMATOR-REVIEW.json`, `build-v2/build-receipt.json`, all source/build versions
and controller logs. The current checkpoint and borrowed historical traces stay
at their original PR413 paths; K50/shared Python runtime remain unchanged.

Cleaner owns later ZIP packaging and verified publication. Prospective retrieval
is `/research/PR-425-nplayer-warm-estimator-qualification/`, with Drive fallback
`rclone copy 'gdrive:PR-425-nplayer-warm-estimator-qualification/' '/research/PR-425-nplayer-warm-estimator-qualification/'`.
**Neither destination is claimed populated or accepted.** There is no ZIP/member
or Drive receipt yet; use protected originals until the archive-set manifest,
hashes, member paths and accepted upload receipts exist. No deletion occurred.
