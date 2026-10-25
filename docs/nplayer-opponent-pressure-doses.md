# Six-player opponent pressure at 15% and 30% (protocol amendment)

This amends the [opponent-pressure protocol](nplayer-opponent-pressure.md) and is committed before either run. Everything not listed here is unchanged from it.

## Why

At 5% ([#427](reports/nplayer-opponent-pressure/results.md)):
- **Pot-pressure:** the change was +5.9 [−2.3, +14.1], **not shown**.
- **Check-call:** flagged as harmed, −57.4.
- **Trained and random fields:** gained.
- **Visitation:** untrained river spots against pot-pressure fell from 21% to 16%.

One run can't separate a real effect from seed-to-seed variation. Doses of 0, 5, 15 and 30% show whether the effects grow with the dose: the pot-pressure gain, the check-call loss and the coverage change.

## Arms

Two new runs, each with exactly #427's recipe except the probability:
- `--opponent-pot-raise 0.15`;
- `--opponent-pot-raise 0.30`.

Both use seed 2026102361001, the same 10B endpoint and no checkpoint choice. **Each is compared with #417's 10B control on #427's four banks** (the same roots). All doses are then paired on identical deals.

The banks' control results were already seen in #427. They were not chosen by outcome, and they are reused only to keep every dose on the same deals.

## Decision rule (per dose, unchanged)

- **Primary:** the pot-pressure paired change, all-in adjusted, pooled over the four banks. **Improved** if the 95% lower bound is above 0; otherwise **not shown**.
- **Harm flags:** the other seven fields, Bonferroni 95% over seven tests, flagged if the upper bound is below 0.
- **Mechanism:** untrained-decision shares by arm and street.

**The dose-response is descriptive.** For each field, the changes at 5, 15 and 30% are reported side by side; no trend test or new gate is added. Neither dose is promoted. A dose that improves the primary without harm flags would only justify a multi-seed confirmation.

## Qualification

The trainer is `main` at the commit below, the same code as #427.
- **#427 already showed:** byte parity with the option off, and identical output across thread counts at 0.05.
- **Each run must show:** a recorded `opponent_pressure` with the declared probability and a positive `pressured_actions`, plus a passing export, average-mass audit, conversion and binary verification. Otherwise that run stops.

## Disk and order

The runs go back to back on bb128: 15% first, then 30%. Each needs about 45 GB of free space at its start; the controller waits for it, which is plumbing, not a result.

To fit two runs:
- **The arena runs one bank at a time.** Each bank's traces are scanned and then gzip-compressed (checked with `gzip -t`), so nothing is deleted.
- **The model binary is gzip-compressed after the arena.**

Stops: CPU 90 °C, VRM (Thermistor 15) 100 °C. Failures: research results are reported as they are, with no retry or extra hands; a failed qualification stops that dose.
