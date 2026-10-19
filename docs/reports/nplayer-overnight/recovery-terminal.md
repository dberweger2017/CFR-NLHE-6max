# Overnight recovery: two completed seeds, terminal swap stop

The owner-authorized100°C recovery stopped October19 at01:34:58UTC/03:34:58Madrid during seed2026101543. Seeds2026101541 and2026101542 each reached30B nodes, saved final checkpoints, and completed export and independent audit with returncode0. The third seed's last periodic reading was12,204,443,619nodes; its10B checkpoint is retained. No final held-out arena or global strength readout ran. This is a partial campaign, not a failed strength gate or an established playing-strength improvement.

## Cause and accounting limitation

The exact crossing sample was **269,004,800bytes (256.543MiB) absolute host swap**, exceeding268,435,456bytes (256MiB). The generic guard reports `swap growth stop`, but the recovery had deliberately set its baseline to zero and therefore charged all existing swap. At recovery admission,140,816,384bytes were already used; the increase since that admission was128,188,416bytes (122.25MiB), below256MiB. Thus **the conservative absolute-swap accounting caused this stop**, not a measured256MiB increase during recovery. This stricter implementation was introduced to avoid resetting an unknown original baseline; it should be distinguished from the original growth-only policy in any follow-up protocol.

CPU61°C and Thermistor1594°C were below their90°C/100°C stops. Available RAM was88,448,929,792bytes (82.37GiB); the trainer RSS was7.59GiB. These measurements do not indicate physical RAM exhaustion. They do not establish why Linux swapped those pages. No swap clearing, host change, threshold relaxation or automatic retry followed. At the07:35Madrid status check, the original07:19 deadline had passed; no existing-budget continuation is pending.

## Retained training endpoints

| Seed | Saved endpoint | Entries | Save seconds | Checkpoint SHA256 |
|---|---:|---:|---:|---|
|2026101541|20,000,003,724|93,117,233|317.29|`6fec25f31cb2e2837f8a369985e79d52b728a85578c0e4bb27fc16fa041a21a7`|
|2026101541|30,000,002,144|109,378,727|373.05|`fcfc009ee2ca9d6b5770bbf1f6ac6fb60927f4a9f4a2a7651e9e52cd68775c25`|
|2026101542|10,000,001,942|70,149,792|237.72|`79d2390182d424641b5e2c0a2823037dee35295303c36bddce7b81b8d199b59f`|
|2026101542|20,000,000,158|92,049,398|313.72|`ac47d33bf32e0bdaffe4e399a2fac7d445873f711ace83097a2350482595c1f7`|
|2026101542|30,000,001,659|108,248,711|369.00|`4b166ef2a1d41cef8a9185ff548b42d28e8d8dd654901a644a2aebe10ed98474`|
|2026101543|10,000,002,106|72,241,620|272.36|`424976a1e00e8e2262c3b7b999c3cf9e888a7a7030add20193215d0d0913d472`|

The first seed's original10B recovery input is indexed in the [original terminal report](terminal-stop.md). Resuming it reproduced every retained15B scripted probe result and fingerprint exactly. The first two seeds used roughly108–109M entries at30B, below the150M ceiling. Their sampled training-phase peaks were9.81GiB/9.72GiB and saving peaks10.40GiB/10.29GiB. These are process-family RSS, excluding tmpfs file storage and unrelated processes.

First seed's recovery20B additional nodes took4,356.166active seconds; second seed's~27B additional nodes took5,562.102active seconds. Full stage wall times were5,183.820/6,599.392seconds, including loads/saves/hashes. Separate exports took319.446/317.174seconds and audits712.627/712.854seconds. Complete-stage CPU/resource details and all six checkpoint paths/sizes are in [compact metadata](recovery-terminal.json). These are not total campaign costs: the original failed segment, discarded unsaved work, qualification, preservation and third-seed failed segment must be accounted separately. No complete-campaign speed/strength claim is made.

## Preservation and disposition

Active original files remain under `bb128:/tmp/nplayer-overnight-20261018-resume100-v2`, with retained owned copies in `/mnt/data2tb/research-cloud/PR-346-nplayer-overnight-blueprint/nplayer-overnight-20261018-resume100-v2`. After a current PR346-open check, read-only inspection confirmed matching original/cache sizes for all six recovery checkpoints and both30B average exports, plus a retained root failure. No preservation-failure receipt exists. This is not a new full model hash audit or Drive acceptance claim. The earlier95°C failure and initial recovery setup refusal remain protected. No deletion or cleanup.

Native source4cd199a5 and all input pins/seeds/targets/held-out roots remain unchanged. Neither remaining seed work nor final evaluation was silently reduced to fit the budget. A new compute allocation or changed guard protocol requires explicit owner direction. There is no timer to disable, and no further automatic retry. Research-Cloud archival/acceptance remains pending.

## Subsequent owner instruction

On October19 the owner instructed “Remove the swap guard.” The campaign code now treats swap as telemetry only, preserving independent available-RAM/RSS/thermal/storage/deadline stops. This does not alter the actual cause or evidence of the earlier stop. Twenty-seven focused tests cover the disabled campaign swap condition and unchanged legacy defaults/other stops. The stopped remote attempts retain their frozen code and evidence; no new compute or deadline reset was performed for this amendment.
