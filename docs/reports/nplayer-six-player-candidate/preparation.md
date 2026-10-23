# Six-player development preparation and one-use launch sequence

[PR417](https://github.com/dberweger2017/CFR-NLHE-6max/pull/417), [proposal416](https://github.com/dberweger2017/CFR-NLHE-6max/issues/416), [frozen protocol](../../nplayer-six-player-candidate.md), [component quote](../../../configs/research/nplayer-six-player-candidate.json), [launch readback](preparation-launch.json).

Owner explicitly said **"you can start and I will organize the extra space"** after the 3B/6B/10B/15B design, all five contrasts, proposed12h planning allocation and240GiB free-NVMe scenario. This authorizes preparing/qualifying/starting the same fixed attempt while space is arranged. It changes storage sequencing, not science, retention, threads or guards. It is not an automatic disk/time/RSS/swap stop or permission for cleanup.

Frozen source **128f021b8abb5c237574aeec9522592ec77a63d5** on main48b6284b; source bundleSHA256`cfa805bc44bb3feb9edb797205e5c7811e4dbb3c387acba1405417027341d70c`. Independent remoteGit/noalternates,81native files byte-identical PR415. Forty focused local tests pass; native build and exact-source six-player qualification are **pending**, not replaced by prior tests. New root`bb128:/home/dberweger/nplayer-six-player-candidate-20261023/` is protected. Subsequent report commits do not mutate remote source.

One-use operational controllerPID899936 began **2026-10-23 18:22:01UTC /20:22:01Madrid**. Sequence: saved-trace diagnosis →native build/tests →tiny six-player qualification →main configure/run only after all proofs. Each science command acquires normal+study mutex nonblocking; no general bypass, schedule or observer. Every failure/partial retained, no retries or reduced acceptance.

At **18:22:57UTC**, diagnosticPID899939 is healthy:CPU51°C/Thermistor15 49°C, workerRSS22,310,912B, availableRAM131,673,530,368B, no failure. **Training has not started.** This dated receipt is preparation progress, not a mature result or completed qualification. Latest actual NVMe119,716,425,728B (~111.49GiB),HDD23,206,940,672B. Count already-written new-study bytes when reviewing remaining growth;240GiB is not a live free-space floor. Owner cleaner is preparing additional space and was notified of the HDD trace-read window.

The diagnostic scans all16PR415 initial traces (~3.6GB) once through verified original-path HDD links, binds existing trace hashes and reconciles return/lookup counts. First action divergence is matched at an identical public state; after-divergence reached behavior is separate. Full action probabilities and legal-belief counterfactuals are absent, so category return contributions are descriptive, not causal. No new hands, native model loading or training is part of that scan.

## Complete provisional cost

| Component | Central seconds | Reserve seconds |
|---|---:|---:|
| active traversal0→15B | 3630.70 | 7261.39 |
| four checkpoint saves | 673.04 | 1346.07 |
| four train startup/resume/hash residuals | 1401.78 | 2803.56 |
| four endpoints export | 2126.30 | 4252.61 |
| four endpoints source audit | 2064.22 | 4128.44 |
| four endpoints conversion | 1678.19 | 3356.39 |
| four endpoints binary audit | 1678.15 | 3356.30 |
| three anchored arena jobs initial+repeat | 2004.27 | 4008.54 |
| initial independent replay including duplicate3B | 1134.43 | 2268.87 |
| five paired verification/readouts | 665.51 | 1331.02 |
| global complete proof/tail readout | 1255.68 | 2511.36 |
| between-stage validation | 647.72 | 1295.44 |
| exact source build+qualification | 600.00 | 1200.00 |
| saved PR415 trace diagnosis | 600.00 | 1200.00 |
| report publication | 900.00 | 1500.00 |

Total **5.85h central /11.62h reserve**, owner-start allocation12h including build/qualification/diagnosis/report, not reset and not a completion guarantee or runtime kill. Costs derive from measured PR415 with a25% six-player scenario allowance; mature six-player rates remain unmeasured. Twelve-versus-ten seating scaling applies only to hand work. Existing two-model runner uses three3B-anchored jobs, deriving adjacent deltas from candidate arms; repeated3B traces are duplicates, never extra statistical observations. All40gates/absolute/coverage/tails and actualcomponentCPU/wall/RAM/thermal/storage are future deliverables, no strength outcome inferred here.

Original250M threshold,unprunedK50/v1fast16/eightroots/fullfloat64averages/parallelgzip; freshseed2026102361001. All8fields4096independentblocks12balancedseatings,2,359,296physicalinitial instances+same reproduction (1,572,864distinctfour-checkpoint/deal/seatinginstances). Independent replay all initial files. Global barrier before outcomes; one40testfamily, no sample extension/tuning/release/default/search or merge authority.

ExistingPR413/415rawtraces and3Bcheckpoints remain verified HDD copies/old-path links; binaries/10Bcheckpoints/exports/source/proofs/K50/sharedruntime protected. PR417 requires400legacyarena,400venvlink+river-pilotvenvtarget+managedinterpreter,404config andcygnusK50. It does not consume PR367/369/412releaseparts/nativecaches orPR402continuationcheckpoint; this is not other-task cleanup clearance. Owner handles any storage exception. No source/payload moved/deleted by this task, no upload or Drive research-payload acceptance claimed. No new timer/observer/subagent/other-machine job.
