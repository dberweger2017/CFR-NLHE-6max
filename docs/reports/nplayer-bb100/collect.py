"""Print compact completion evidence on bb128; leave checkpoints and raw traces there.

Run only after the pilot exits. Example from a fresh ignored local directory:
ssh bb128 python3 - /mnt/data2tb/research-cloud/PR-350-nplayer-bb100/pilot-20261019 < collect.py > receipt.json
"""
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
if not (root / 'results.json').exists() and not (root / 'failure.json').exists():
    raise ValueError('pilot has not reached a terminal state')
files = ('launch', 'admission', 'status', 'qualification', 'results')
receipt = {name: json.loads((root / (name + '.json')).read_text())
           if (root / (name + '.json')).exists() else None for name in files}
receipt['root'] = str(root)
receipt['results_sha256'] = (hashlib.sha256((root / 'results.json').read_bytes()).hexdigest()
                             if receipt['results'] is not None else None)
receipt['failures'] = {str(p.relative_to(root)): json.loads(p.read_text())
                       for p in root.rglob('failure.json')}
receipt['measurements'] = {}
for folder in sorted((root / 'measurements').iterdir()):
    if not folder.is_dir():
        continue
    entry = {name: json.loads((folder / (name + '.json')).read_text())
             if (folder / (name + '.json')).exists() else None
             for name in ('command', 'result')}
    resources = dict(samples=0, peak_rss_bytes=0, cpu_max_c=0, thermistor15_max_c=0,
                     available_ram_min_bytes=None, swap_used_max_bytes=0, swap_growth_max_bytes=0,
                     nvme_free_min_bytes=None, hdd_free_min_bytes=None)
    with (folder / 'resources.jsonl').open() as stream:
        for line in stream:
            row = json.loads(line)
            resources['samples'] += 1
            for key, value in [('peak_rss_bytes', row['rss_bytes']),
                               ('cpu_max_c', row['temperatures_c']['Package id 0']),
                               ('thermistor15_max_c', row['temperatures_c']['Thermistor 15']),
                               ('swap_used_max_bytes', row['swap_used_bytes']),
                               ('swap_growth_max_bytes', row['swap_growth_bytes'])]:
                resources[key] = max(resources[key], value)
            for key, value in [('available_ram_min_bytes', row['available_ram_bytes']),
                               ('nvme_free_min_bytes', row['nvme_free_bytes']),
                               ('hdd_free_min_bytes', row['free_disk_bytes'])]:
                resources[key] = value if resources[key] is None else min(resources[key], value)
            resources['last_sample'] = row
    entry['resources'] = resources
    summary = root / (folder.name + '-summary.json')
    entry['summary'] = json.loads(summary.read_text()) if summary.exists() else None
    receipt['measurements'][folder.name] = entry
print(json.dumps(receipt, indent=2))
