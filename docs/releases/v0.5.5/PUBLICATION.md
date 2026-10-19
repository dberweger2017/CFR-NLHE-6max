# v0.5.5 publication record

**Published October 18, 2026 at 07:01:25 Madrid (05:01:25 UTC), stable Latest.**
[Release](https://github.com/dberweger2017/CFR-NLHE-6max/releases/tag/v0.5.5) · [packaging PR #319](https://github.com/dberweger2017/CFR-NLHE-6max/pull/319).
The separate [hu200-frozen-20b-seeds pre-release](https://github.com/dberweger2017/CFR-NLHE-6max/releases/tag/hu200-frozen-20b-seeds)
was published at 07:01:34 Madrid (05:01:34 UTC); it is not Latest.

Both tags, release targets and publication-approved manifests name **`ef0e3a41aee720a220520c10bb248740ae7a7154`**,
#319's owner-authorized merge. All four jobs in [CI run 39069590288](https://github.com/dberweger2017/CFR-NLHE-6max/actions/runs/39069590288)
passed on that exact commit. Stable release ID **416091787**; research pre-release
ID **416091791**. The Latest API returned the stable release after both publications.

## Verification status and owner decision

Before publication, both fresh bundles passed publication-bound standalone
verification, and **all 49 assets passed actual authenticated download byte counts
and SHA256 checks**, totaling **33,416,326,663 bytes**.

After publication, **all 15 v0.5.5 assets passed actual unauthenticated public-URL
byte counts and SHA256 checks**, totaling **7,667,034,369 bytes**. The owner then instructed: “Cancel the verification, new plan, the release is very good,
we don’t need verification.” The remaining post-publication checks were cancelled and the job was stopped at
07:13:56 Madrid.
[Owner decision and retained evidence](https://github.com/dberweger2017/CFR-NLHE-6max/pull/319#issuecomment-6246034238).

The post-publication standalone verifier was not recorded as complete. Public-URL
checks for the 34 research pre-release assets and the additional exact reconstruction
from downloaded public seed parts were **not completed**. The owner waived those
remaining publication checks. Completed results and partial outputs were retained;
no correctness mismatch prompted cancellation. The published assets remain unchanged.

## Fixed model and completed checks

The playable release is #306's original audited three-seed blend average:
**6,282,968,150 bytes**, SHA256
`ce3ecc2cb8ebffa1fb3e0a7f11c79d0900b74008b55d85093e1915ff4dde6485`,
156,208,331 entries, schema `hu200-native-reopening-ordered-history-equity-k50-v1`.
Its PR163 K50 tables and `hu200-public-menu-translation-equity-k50-v1` identity
(512 states / 128 events) are pinned by the bundle. There was no retraining,
model selection or replacement of this release model.

Under protocol version 2 it qualified at **−19.67 [−38.57, −0.76] BB/100**
over 30,000 fresh Slumbot hands. It loses to Slumbot by a small, detectable margin.
[Model card](MODEL_CARD.md), [release notes](RELEASE_NOTES.md).

Completed packaging and publication evidence:

1. **Real cached runtime:** two fresh starts, first building the low-memory cache
   and later mapping it read-only with model-SHA binding; first start 1,214.93 seconds /
   516,747,264 bytes peak process RSS, later start 80.96 seconds / 586,121,216 bytes.
   The extra cache occupies 9,331,096,671 bytes. Human and spectator play covered
   restricted sizing, off-menu wagers, all-ins and restart before a pending bot decision.
   Every one of 30 retained hands independently replays. Wrong model/table/identity,
   stack/adapter and corrupted or mismatched caches are refused.
   [Runtime](verification/runtime.json), [cache starts](verification/cache-starts.json).
2. **Compatibility:** all four old HU100 manifests rebuild byte for byte, their trace
   hashes remain equal, and 1,280 hand records independently replay. The HU20 default
   remains v0.4.2. [Compatibility](verification/compatibility.json).
3. **Prepared-part reconstruction:** two full runs reproduce all three seed averages,
   the exact raw blend `59a6dd35…` and the average `ce3ecc2c…`.
   [Reconstruction](verification/reconstruction.json). The later reconstruction from
   downloaded public parts was cancelled as described above.
4. **Fresh approved bundles:** a clean detached checkout of the merge commit built
   the stable bundle and all three seed averages **plus all three raw checkpoints**.
   Both standalone verifiers passed under `python3.11 -I -S` with
   `--expect-source ef0e3a41aee720a220520c10bb248740ae7a7154` and `--require-publication`.
   All six shipped documents match the tagged source byte for byte. Runtime/native
   source equivalence is documented in [source coverage](verification/source-coverage.json).
5. **Draft and publication:** every one of the 49 draft assets was downloaded with
   authentication and matched the built bytes/SHA256. Publishing created the two
   exact-source tags; title, target, stable/pre-release flags and Latest were checked.
   The stable release's 15 public-URL asset hashes subsequently passed.

## Asset inventories

The byte counts and SHA256s below are the built and authenticated-download pins.
The stable table also passed public unauthenticated readback. The research table's
public readback was cancelled. Model parts are ordered and at most 1 GiB each;
the river table is 1,231,562,564 bytes, below GitHub's 2 GiB asset limit.

### v0.5.5 — stable Latest

| Asset | GitHub asset ID | Bytes | SHA256 |
| --- | ---: | ---: | --- |
| `HU200-v055-three-seed-blend.average.gz.part-001` | 651719114 | 1,073,741,824 | `5ecd9e66c419557039f9629f6d953a96d6addbdc61a280992d8d963a0c879a01` |
| `HU200-v055-three-seed-blend.average.gz.part-002` | 651733440 | 1,073,741,824 | `13b8ecc89354db916650b4a61042dcca6eab21e942e230eb26056e7249bf375d` |
| `HU200-v055-three-seed-blend.average.gz.part-003` | 651746617 | 1,073,741,824 | `7527687e9d64db2bf0f7fa44b432e3f09b79bd51b66ae56b8be63fd4e449ea6a` |
| `HU200-v055-three-seed-blend.average.gz.part-004` | 651760919 | 1,073,741,824 | `1d748c6dc68350590da3e42f889c77ec10831d365873ef3db64fa172fc52006d` |
| `HU200-v055-three-seed-blend.average.gz.part-005` | 651775313 | 1,073,741,824 | `732cadb21718dfc47b1ae342d69a9b09c55dc5cd0cc0f53db8bc6b211ef7e234` |
| `HU200-v055-three-seed-blend.average.gz.part-006` | 651787431 | 914,259,030 | `b42a0481b18060731347f93b1808461d72d7e368a08c9383ab15cc9fd6bbb2cf` |
| `INSTALL.md` | 651795552 | 4,210 | `c1951542386748e16558b8d84a57a54b10f594cacb5a21619d4067949cef6673` |
| `MODEL_CARD.md` | 651795654 | 5,266 | `ce39fb961e18128ef6fce9d109721eaaeb8184d295b229ef238c2a48a8f9a134` |
| `RELEASE_NOTES.md` | 651795750 | 4,516 | `e1a61e4b9e334e3b1230ffe47f4033f193534c0ba9193ff061d7fa10e1bdd818` |
| `SHA256SUMS` | 651795857 | 1,339 | `2e49ef325ef387ac0c00d480bb9cd36c7cd0a52d3ef1bdf07e961a5991674710` |
| `flop-k50.bin` | 651796012 | 12,867,944 | `084e243ded9fe93ad03cd59601f22f16c3210592f51e1e3646a60983b572c111` |
| `release-manifest.json` | 651796227 | 3,964 | `68358cd51f1b486188bb67d0d650bb5f4ad690fb05180f49aec5ef75a63ae71d` |
| `river-k50.bin` | 651801465 | 1,231,562,564 | `70c1cb5ecf4cd292e4c89dc2200f7c8381100be3b0288ceeb0a12a3e83977629` |
| `turn-k50.bin` | 651812701 | 139,600,524 | `c0bc6a8aa0535553118109d18a32d3b4dc6880e937c263cdc87472b1ae9f168f` |
| `verify_hu200_bundle.py` | 651814127 | 15,892 | `c77f41bab0292ef4d63a914c930b9468816d411b2085c6285edde35a59855d29` |

### hu200-frozen-20b-seeds — research pre-release

| Asset | GitHub asset ID | Bytes | SHA256 |
| --- | ---: | ---: | --- |
| `HU200-frozen-20B-seed-2026101302.average.gz.part-001` | 651818836 | 1,073,741,824 | `2da17aa40a102550a61e7a202bc2802d8d2e3a8eb2166acf4178ca38f14bd023` |
| `HU200-frozen-20B-seed-2026101302.average.gz.part-002` | 651831751 | 1,073,741,824 | `338a7c0a02de3646360ae0b015ad8819bc358e949756414c3e5ecc29b094c8fe` |
| `HU200-frozen-20B-seed-2026101302.average.gz.part-003` | 651844306 | 1,017,080,327 | `c509b4d09865fda1cea57b027dfa5b50e0b4aec779a1b0694af49635bd04c85e` |
| `HU200-frozen-20B-seed-2026101302.checkpoint.gz.part-001` | 651855567 | 1,073,741,824 | `6062a9aff01516d40aced04855b135febf881e6abcee3e78da9ab0090a96978c` |
| `HU200-frozen-20B-seed-2026101302.checkpoint.gz.part-002` | 651867833 | 1,073,741,824 | `eeeff90989c8c4fa471672c08d5f004b39cab8740682a099b33060553f86ddaa` |
| `HU200-frozen-20B-seed-2026101302.checkpoint.gz.part-003` | 651879121 | 1,073,741,824 | `eea280841dc4d056484786967bf05377652f3adeba804f0742a94612cb0b0219` |
| `HU200-frozen-20B-seed-2026101302.checkpoint.gz.part-004` | 651890614 | 1,073,741,824 | `cac42f19e48a230ee84bc53b38e03acde96d72e3342a30caf2e4c5c5373c0f1e` |
| `HU200-frozen-20B-seed-2026101302.checkpoint.gz.part-005` | 651901862 | 665,877,290 | `c73cdb577604c65044346c5531e251402317fd29e40be8f3032ca8c5991ffc4c` |
| `HU200-frozen-20B-seed-2026101421.average.gz.part-001` | 651912218 | 1,073,741,824 | `c9cde6eae7388094b33e6fea5e1e6fdc3bcb84a0a5090155581d08967a91da98` |
| `HU200-frozen-20B-seed-2026101421.average.gz.part-002` | 651925092 | 1,073,741,824 | `3905f8d432064e04a36a6f35c7145a37138f0294d5e85e756a15f3d7c70f4647` |
| `HU200-frozen-20B-seed-2026101421.average.gz.part-003` | 651938924 | 1,015,187,432 | `1347c0aa1464543a88b2bbd4de74f7630535bd990c56c7d2d70e1a8e16dc09a8` |
| `HU200-frozen-20B-seed-2026101421.checkpoint.gz.part-001` | 651950998 | 1,073,741,824 | `ecd3f7906d7b91e8a5eb69946085e5c8e690e72648613c65c1cc413d6948f89c` |
| `HU200-frozen-20B-seed-2026101421.checkpoint.gz.part-002` | 651964866 | 1,073,741,824 | `9cf6002080d68f35bde854ed91889a9dd79585f5139b5a64a235d02249e84cc6` |
| `HU200-frozen-20B-seed-2026101421.checkpoint.gz.part-003` | 651980017 | 1,073,741,824 | `35582d7ca24e5908f45eaf06974a98196a5b3e6123986edfef65dbd9e83653bf` |
| `HU200-frozen-20B-seed-2026101421.checkpoint.gz.part-004` | 651992627 | 1,073,741,824 | `17d16166a71670935cb66667162f4fd56b1ee9c134c2d2854bc0035b581b93f5` |
| `HU200-frozen-20B-seed-2026101421.checkpoint.gz.part-005` | 652004457 | 662,785,369 | `3b2bf9ecb02be53acabb6c47a13ff5564b3abbd58e779ba76539c7f5b501c843` |
| `HU200-frozen-20B-seed-2026101422.average.gz.part-001` | 652014236 | 1,073,741,824 | `fad472eec4aff2f5919d823906873a61f26e8ddda5535f07a870dfa97486a63d` |
| `HU200-frozen-20B-seed-2026101422.average.gz.part-002` | 652027794 | 1,073,741,824 | `3f5fdf3b2ceb65501db38cb5820ad820f9d883f1d14f2c2e19d96c3b5796f4fa` |
| `HU200-frozen-20B-seed-2026101422.average.gz.part-003` | 652040427 | 1,014,580,954 | `0aacfe6254d31644981276cfd8782ec394d827f04a12fae0ee8bdb60b1165dc6` |
| `HU200-frozen-20B-seed-2026101422.checkpoint.gz.part-001` | 652052829 | 1,073,741,824 | `d68f98fa1d7c52fcac47a733dbc61607cf8fe73d037d9ada25735aa27bedb5c6` |
| `HU200-frozen-20B-seed-2026101422.checkpoint.gz.part-002` | 652066173 | 1,073,741,824 | `785ffcbd3e85001d6d733ec38033fd908da8ca6720e29b7ac69ba11476a47789` |
| `HU200-frozen-20B-seed-2026101422.checkpoint.gz.part-003` | 652078505 | 1,073,741,824 | `4fd5bb7ce9a4349f2d4fd5e322494d9806ecd8fe7fe3001aaec629068dc3e169` |
| `HU200-frozen-20B-seed-2026101422.checkpoint.gz.part-004` | 652091599 | 1,073,741,824 | `a28a39c274e774ef62bca03102610d4e8c6595e651dcf9ae8863f0f0765a3bda` |
| `HU200-frozen-20B-seed-2026101422.checkpoint.gz.part-005` | 652102827 | 662,349,332 | `39b5de10154b94534da25e43e85387281d2ddb0dc26d08aea9335f77bc587b37` |
| `INSTALL.md` | 652107732 | 3,463 | `9c6da3b99d06a3c5475c3373897c8515581ad2acda6f82cf72ac5f07cd54fa81` |
| `MODEL_CARD.md` | 652107810 | 3,754 | `1ef43b419f7d0405f37a0f433d6878ada3690c7b533ef3d9dfdb00ff6e146267` |
| `RELEASE_NOTES.md` | 652107879 | 2,206 | `9ff34d955dcc202eed029725e3933ac523dfcee144c81eb61607e7dcb64bee1f` |
| `SHA256SUMS` | 652107939 | 3,640 | `3db49f97528a8c4f46c8128ca65b0d73170906ce1d6de581a543f46510956047` |
| `blend-config.json` | 652108034 | 8,498 | `83c72410433ef57904fbf97829a84ecb3dae7a74132e48fb87dad3f0b909a47f` |
| `flop-k50.bin` | 652108233 | 12,867,944 | `084e243ded9fe93ad03cd59601f22f16c3210592f51e1e3646a60983b572c111` |
| `release-manifest.json` | 652108482 | 10,273 | `f268e1374b117c7d951471d37c5c15840d1afdd0bc0728ec942da9f9fae0ac3e` |
| `river-k50.bin` | 652114669 | 1,231,562,564 | `70c1cb5ecf4cd292e4c89dc2200f7c8381100be3b0288ceeb0a12a3e83977629` |
| `turn-k50.bin` | 652126514 | 139,600,524 | `c0bc6a8aa0535553118109d18a32d3b4dc6880e937c263cdc87472b1ae9f168f` |
| `verify_hu200_bundle.py` | 652127771 | 15,892 | `c77f41bab0292ef4d63a914c930b9468816d411b2085c6285edde35a59855d29` |

## Research collection and installation

The research pre-release contains all three 20B averages and raw checkpoints,
including seed 2026101302, the original candidate. That recipe did not qualify
under its declared first protocol; the original failure stands. Its Slumbot results,
card-luck analysis and exact reconstruction instructions are in the research
[model card](../hu200-frozen-20b-seeds/MODEL_CARD.md) and
[install guide](../hu200-frozen-20b-seeds/INSTALL.md). All rebuild inputs are public
GitHub assets; Drive access is unnecessary for that reconstruction.

For HU200 human play and the spectator, follow [INSTALL.md](INSTALL.md).
The evidence archives and retained partials are indexed in
[RESULTS_INDEX](../../../RESULTS_INDEX.md#pr319--hu200-v055-release-packaging-verification).
Older release assets and the HU20 default are unchanged.
