# Matched-teacher six-player 100 BB: preparation

[Protocol](../../neural-six-imitation.md), [proposal #473](https://github.com/dberweger2017/CFR-NLHE-6max/issues/473),
[PR #474](https://github.com/dberweger2017/CFR-NLHE-6max/pull/474).

The protocol and tooling were committed as `99d93ebc` before any main export,
training or evaluation. `cf004640` adds the cgroup-v1 memory guard required by
the actual host. No game logic, features, regret math or scientific recipe changes.

## Local qualification

20 focused tests passed initially (sample reader, imitation, everywhere gates,
new matched-teacher study, existing RunPod supervision). After adding cgroup-v1
support, all eight matched-teacher tests passed, including the new entitlement
fixture. Cached and RAM-backed training produce bit-identical CPU weights on
the fixture. Repository storage and diff checks pass. Full CI and actual-host
qualification are separate; no outcome is claimed here.

Both policy binaries and mass receipts were retrieved read-only from bb128
and match the frozen protocol pins. The full input bundle has nine members;
member hashes, lengths and original source locations are retained with the
operations record outside Git. bb128's independent Deep CFR pilot remains active.

## Rental, November 8, 2026

One RTX 4000 Ada Generation, 20 GB VRAM, in EU-RO-1 Secure Cloud. The deployed
host reports AMD EPYC 7352, advertised 9 vCPUs and 50 GB RAM. The actual cgroup
CPU entitlement is `765000/100000`, or 7.65 CPU equivalents; use seven native
threads and three Python scan/replay workers. Memory limit is 49,999,998,976
bytes. Guard the cgroup's remaining memory, not the physical host's free RAM.

Compute $0.28/hour plus 200 GB temporary disk at $0.028/hour: $0.308/hour,
or $3.696 for 12 hours. The UI rounds the total to $0.31/hour. No persistent
volume, savings plan or additional paid service was selected.

Rental was performed in the internal browser after the owner signed in.
Direct SSH was verified with the owner's existing registered key; no new key
or credential was created. Source/environment setup and input transfer run
before native/CUDA/parity/smoke qualification. This record is preparation,
not evidence that qualification or the main run has completed.

T3 check-ins are armed every 20 minutes. A separate cutoff is scheduled for
November 9 at 09:47:51 UTC, earlier than 12 hours after rental; the scientific
work deadline is 08:17:51 UTC to reserve 90 minutes for retrieval. These are
T3 scheduled tasks, not a provider-side timer. The controller itself stops work
at its deadline; stopping provider billing remains an explicit scheduled action.
Private operations identifiers and SSH details are kept outside Git.
