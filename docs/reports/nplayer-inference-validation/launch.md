# Mature loading validation — running

Owner approved90–150min validation and new-owned output staging. PR359 merged
`fed5f8f9` after all five checks passed at `e942f435`. Draft PR361 follows
[the frozen protocol](../../nplayer-inference-validation.md).

Runtime source `c06fc565`; snapshot6096a8517c93f0204efad6c2859d7d020d2d688b9da07e1efa2103e22038c064.
Full fixture-v1 passes all33stage return codes,216initial hand rows per format
plus reproduction/independent replay, exact full-row/mass/first-action checks
and verified staging. Its generated rows mostly miss actual play; stored-row
exactness is additionally covered by PR359 unit tests. No mature cost claim.

Main launchedOctober20,06:52:34UTC (08:52Madrid), PID622098, root
`bb128:/home/dberweger/nplayer-inference-validation-20261020/main-v1`.
[Compact launch/current resource snapshot](launch.json). All phases advance
automatically; normal mutex held, CPU90/Thermistor15 100 stops, manual resources.
The first gzip job/reproduction/replay finished; latest phase is repeated loads.
No failure/interim winner. Existing PR350/355/357 inputs remain read-only.

New owned completed copies/traces stage with SHA verification and accessible
symlinks into `bb128:/mnt/data2tb/research-cloud/PR-361-nplayer-inference-validation/main-v1`.
Raw models/traces stay there or the NVMe root. Archive/Drive acceptance pending;
no deletion, cleanup, default or additional experiment. PR362 waits behind the
benchmark mutex; all its heavy M1 local qualification has finished.
