# All-root assessment: less variance, little wall-cost benefit on the primary

PR391 completes proposal389 after merged PR390. All384 saved roots and a fresh
reproduction pass verify. Future-action averaging reduces observed variance in
every nonzero panel. **On the trained-opponent primary, the conservative cost
ratio is0.925 with loading and1.104 with loading amortized: no material wall-time
saving is established.** Several scripted/mixed panels improve much more. This
is development evidence about an evaluator, not a search-strength verdict.

## Complete frozen assessment

Assessment source `aff3228b79268a8b0766874f7fa60c51e6fa148a`, same tree as merged
PR390; qualified native source `9998501a4a6794d7c682d39e4edb436b69e04d29`.
The qualified binary,384-root inventory, original profiles, models, menu,
search work and blueprint fallback are unchanged. All381 installed profiles
complete both arms, each within200,000 visited states; the three original
quality fallbacks cancel identical policies explicitly. No root was dropped,
including roots with unchanged sampled actions. No final scientific retry.

The initial and fresh repeat match **every strategic field**, including original
profile hashes, float64 values, visited work and fallback labels. Raw record
file hashes differ because timings differ; the strategic reproduction proof
passes. Each lineup still has128 independent six-permutation blocks; replication
adds no samples. Noneligible hands contribute zero. The privileged evaluator
owns hidden cards; each actual policy receives only its own legal observation.

## Variance and complete cost, separately by lineup

SDs are over original six-permutation block contrasts, in BB/100. Ratios below1
favor averaging. These are observed development-sample ratios, not guaranteed
future speedups. Cost columns include the full supervised assessment.

| Lineup | Sampled SD | Averaged SD | Variance ratio | Cold wall variance × cost | Amortized wall variance × cost |
|---|---:|---:|---:|---:|---:|
| Trained + trained | 157.68 | 101.40 | 0.414 | 0.925 | 1.104 |
| Trained + pressure | 196.34 | 43.99 | 0.050 | 0.112 | 0.134 |
| Pressure + pressure | 147.59 | 24.81 | 0.028 | 0.063 | 0.075 |
| Check-call + check-call | 0 | 0 | undefined | undefined | undefined |
| Check-call + pressure | 243.32 | 163.73 | 0.453 | 1.012 | 1.209 |
| Random + TAG | 129.77 | 31.42 | 0.059 | 0.131 | 0.157 |

The primary loses58.6% of its observed variance, but measured costs consume that
benefit. Check-call/pressure also fails to improve amortized wall efficiency.
The other three nonzero panels have encouraging point ratios; do not pool them
into a claim that the primary is affordable. Check-call/check-call has no search
intervention and therefore no defined efficiency ratio, not a measured zero
effect for all future deals.

**Cost basis matters.** The full original PR388 generate/play/replay pipeline
is retained as a conservative allowance for producing future common prefixes,
then the new measured assessment is added. Baseline728.23s wall becomes
1,627.97s, a2.236× multiplier. Removing measured model startup from both old and
new work changes258.16s to689.25s, a2.670× multiplier. This is the predeclared
common whole-panel cost basis applied to separate lineup variances; it is not a
marginal per-lineup timing or a measured fresh integrated pipeline. A differently
sized/mixed future campaign needs a new quote.

The raw frozen readout uses895.90s of assessment-driver wall time. The table adds
its supervised tests/polling overhead, using899.75s; both versions are preserved
in the linked JSON. CPU is separate:910.42s baseline plus898.22s assessment gives
a1.987× CPU multiplier. The primary CPU variance × cost ratio is0.822, versus
1.104 for amortized wall time. The original pilot used four arena workers;
assessment reconstructed roots sequentially with RAYON1. No unmeasured parallel
speedup is assumed.

## What changed in the descriptive means

| Lineup | Original sampled contrast | Averaged-action contrast, BB/100 |
|---|---:|---:|
| Trained + trained | +2.90 | +8.33 |
| Trained + pressure | +26.76 | −1.09 |
| Pressure + pressure | −13.67 | −0.43 |
| Check-call + check-call | 0 | 0 |
| Check-call + pressure | −25.91 | −14.81 |
| Random + TAG | +14.19 | +0.12 |

The player did not change. Averaging the remaining actions changes each fixed
deal's estimate and removes some action noise. Earlier large positive/negative
sampled means can move substantially. The trained-pressure sign flip illustrates
why the sampled headline was not a strength verdict; the adverse check-call/
pressure panel remains visible. None of these means establishes an improvement
or regression on fresh deals or independent training lineages.

## Rare-tail limitations

The largest block supplies **80.5% of the primary's remaining centered squared
variation**, up from53.3% before averaging. Deal/prefix variation remains, and
one focal training lineage cannot establish cross-seed behavior.

The frozen10,000 paired-block bootstrap gives variance-ratio sensitivity ranges
0.123–0.631 for trained,0.008–0.749 for trained-pressure,0.331–0.613 for
check-call/pressure and0.020–0.115 for random/TAG. These development bootstrap
percentiles do not guarantee nominal coverage or control unseen rare tails.
Pressure is especially unstable:61/10,000 resamples have zero sampled variance;
the reported0.014–32.368 range is conditional on9,939 defined ratios. Treat that
panel's attractive point saving cautiously. No sample extension or method change
was made after seeing returns.

## Actual operating cost

| Both passes and supervised tests | Measured |
|---|---:|
| Total wall /child CPU | 899.75s /898.22s (about15min each) |
| Two model/K50 startups | 468.66s |
| Original-profile reconstruction | 414.68s |
| Action enumeration | 0.587s /446,036 visited states |
| Other work, including proofs/bootstrap/supervision | 15.83s |
| Maximum states in one arm | 3,891 /200,000 |
| Sampled peak worker-family RSS | 27.68GiB |
| CPU /Thermistor15 maxima | 59 /58.5°C |
| Swap growth /minimum NVMe free | 0 /258.02GB |

All supervised stages return0; no failure or thermal crossing. The run completes
inside the21.67-minute central forecast and3h43 planning allowance. No elapsed,
RSS, disk or swap cutoff was introduced. Original inputs, source/environment/Git
stores and prior evidence are unchanged and retained.

## Next decision

Keep the player frozen and **do not launch a large strength campaign on the
assumption this standalone path makes it much cheaper**. It qualifies complete
future-action integration and improves several safeguard panels, but does not
materially improve the trained primary's amortized wall efficiency. The old
multi-hour strength scenarios are not superseded by a credible short quote.

The focused engineering candidate is to evaluate directly while the persistent
arena already owns the loaded models and captured root profile, avoiding a
second load and reconstruction. Enumeration itself costs under a second here;
that is a component measurement, not an end-to-end speedup or study quote.
A small integration/cost qualification would need to retain legal-information
boundaries, fallback, every eligible root and reproduction. Price a fresh fixed
peer-and-scripted study only after measuring that complete path or explicitly
accepting the present cost. This report launches neither. Menus, off-tree
re-solving and training remain deferred during that decision.

## Reproduction, provenance and retention

[Admission](assessment-admission.md), [protocol](../../river-conditional-evaluation.md),
[unaltered precomputed results](assessment-results.json),
[full-supervision derived analysis](assessment-analysis.json),
[lineup CSV](assessment-lineups.csv), [verification](assessment-verification.json),
[cost/resources/work](assessment-costs.json), [pins and original paths](assessment-provenance.json).
The study is deterministic saved-data development, not new hands. Reproduction
requires the pinned inputs, source and binary in fresh owner-authorized output;
never rerun the completed allocation in place.

Raw inventory/cards/expected-value records and all logs remain at
`bb128:/home/dberweger/river-conditional-evaluation-20261022/assessment-v1`.
Only compact results were retrieved to the Mac. [Archive receipt](assessment-archive.json):
[Drive ZIP](https://drive.google.com/file/d/1wSdmfm9U3V2FfYvgPIKD0YMaCKMKDR-b/view),
1,880,831bytes, SHA256
`379c09a81eae8e1edc87e1ef56a83b88de40e686dd1ca859c6efe5f06979c27c`.
All77 payload members plus embedded manifest read back locally; the deployed
tool accepts Drive MD5/size and covers79 local files. This is not a remote-byte
SHA256 audit. The at-rest copy is `/research/PR-391-river-conditional-efficiency/`;
the receipt records the Drive fallback, exact raw-record/source/binary members
and protected external inputs. KEEP and all originals/dependencies remain,
with no cleanup, other-job/environment change or new experiment.
