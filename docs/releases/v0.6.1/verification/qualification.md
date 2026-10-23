# v0.6.1 packaging and runtime qualification

**All three models pass.** PR404's exact 10B float64 binaries were split once and
independently reconstructed as ordered byte streams into the pinned whole-model
SHA256, without writing duplicate whole files. All 42 parts and all three binary
headers/source/game/schema/mass identities match. Native runtime then loaded the
exact original binaries with its mandatory whole-file validation. Small fixtures
separately test physical `--assemble` output and cache reuse.

All 36 integration hands pass: six human and six spectator hands per seed,
restricted sizing, human privacy, conserved chips, one shared weight table,
and independent replay before and after journal restart (72 replay instances of
the same 36 hands). These are integration checks, not a strength estimate.
The original six full-row checkpoint/export and binary audits remain research
provenance; none was repeated, and no model was converted or changed.

| Seed | Split + source hash, s | Ordered reconstruction, s | Native startup, s | Play + two replays, s |
|---|---:|---:|---:|---:|
| 2026102240001 | 70.62 | 52.46 | 124.96 | 0.29 |
| 2026102261001 | 72.78 | 48.44 | 122.66 | 0.30 |
| 2026102261002 | 72.84 | 48.45 | 123.15 | 0.22 |

The exact floating timings are in [the compact receipt](qualification.json).
Host qualification ran October 23 **10:24:34–10:37:24UTC: 12m49.94s** wall,
**11.97 child CPU-minutes**. All 11 stages returned zero, no failure/retry/thermal
stop. New native build 16.14s (supervised stage 18.17s), one model at a time.
Sampled worker-family peak **14.66 GiB**, CPU max **56°C**, Thermistor 15 max **59°C**.
Sampling can miss brief peaks. Swap remained **453,697,536 bytes** throughout;
minimum available RAM **108.07 GiB**, minimum free NVMe **84.12 GiB**. Both compute
mutexes were released and no qualification process remains.

Frozen implementation: **`61585713154124802de9b434b04797e05f8a54e8`**.
Later changes improve a negative test and record documentation/receipts; no
`src/`, `scripts/` or native implementation differs from that source. Linux ran
30 focused tests. Current local validation also passes 30, plus the broader
47-test / 54-subtest artifact/CI selection in [local verification](local.md).

## Exact prepared assets and retention

[Three source-bound prepared manifests](../manifests/), [42 part hashes](../PART_SHA256SUMS),
[whole-model/dependency hashes](../MODEL_SHA256SUMS), [full provenance](../MODEL_MANIFEST.json).
All manifests have `publication_approved:false`; these are actual qualified
preparation artifacts, not approved final publication manifests. Their SHA256s:

- 2026102240001: `8e54478399fc64dc30b45bf6f1e6d6907be58ba09b3651eef976bff622ce2afc`
- 2026102261001: `cde4c6b6bf4b185ed65c4157a169b32687e9d8517d20d5a99e84fad6311caf78`
- 2026102261002: `457f1783dae00d46cb3e2c480f45b0789ea5827a3773c1358e461032fa27141f`

Active output root:
`bb128:/home/dberweger/v061-release-preparation-pr412-20261023/qualification-v1`.
Parts/manifests/checksums: `bundles/SEED/`; private journals/receipts:
`runtime/SEED/`; raw measurements/resources/build/terminal result are under the
same root. Separate self-contained source checkout at `../source` uses no
borrowed Git object store; controller `../qualify-v1.py` has its hash recorded in
the compact receipt. Exact native binary/toolchain hash is also recorded there.

42 model parts total **42,918,983,478 bytes**. A real-bundle inventory check plans
**52 unique GitHub assets /42,919,046,577 bytes**, excluding reused K50 downloads.
Its `publication-plan-empty.json` explicitly assumes an empty hypothetical release;
refresh live inventory before any owner-approved upload. No upload occurred.

Retrieve prepared assets from this original active host path while PR412 is open;
restore source from pinned commit `61585713`. Original model paths/hashes and the
build/reconstruction/runtime commands are in the receipt. Do not rerun completed
outputs in place. For an intentional rebuild use `build_v061_bundle` in a fresh
path with the pinned source, original binary and K50; no training/conversion.

All PR404 endpoints, prior PR400/402/K50, v0.6.0 and other jobs remain protected.
No original was moved/deleted; no output was staged to HDD or uploaded. The
vacuum-cleaner owns future research staging/archival; archive/Drive acceptance
and any new restoration fallback remain pending its own receipts. Do not infer
cloud acceptance from these release integrity proofs.

## Publication remaining

Owner review/approval, final source binding, exact-source tag, live-asset
reconciliation, missing-only uploads and canonical anonymous readback/runtime
closeout remain separate. [Procedure and quote](../PUBLICATION_PLAN.md): conditional
**4.5–7 hours** after approval; no mandatory Drive mirror or repeated authenticated
full readback. v0.6.0 and existing defaults remain unchanged.
