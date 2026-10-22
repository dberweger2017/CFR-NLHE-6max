"""One lightweight remote status snapshot; never launches or retries science."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

REMOTE = r'''
from pathlib import Path
import json,time
r=Path('/mnt/data2tb/research-cloud/PR-350-nplayer-bb100/bounded-20261019')
value=dict(root=str(r),epoch=time.time())
for name in ('launch','source-receipt','admission','status','small-qualification','pretraining-freeze','cost-quote','failure','training-progress'):
 p=r/(name+'.json')
 if p.is_file():value[name]=json.loads(p.read_text())
pid=value.get('launch',{}).get('supervisor_pid')
p=Path('/proc')/str(pid)/'cmdline'
value['supervisor_command']=p.read_bytes().replace(b'\x00',b' ').decode() if p.exists() else None
stage=value.get('status',{}).get('status','')
d=r/'measurements'/stage
for name in ('progress','failure'):
 p=d/(name+'.json')
 if p.is_file():
  row=json.loads(p.read_text())
  value['stage_'+name]={k:v for k,v in row.items() if k!='results'}
  if 'results' in row:value['stage_'+name]['probe_bots']=[v['bot'] for v in row['results']]
p=d/'resources.jsonl'
if p.is_file():
 with p.open('rb') as f:
  f.seek(max(0,p.stat().st_size-6000))
  lines=f.read().splitlines()
  if lines:value['last_resource']=json.loads(lines[-1])
if 'failure' in value:
 with (r/'supervisor.log').open('rb') as f:
  f.seek(max(0,(r/'supervisor.log').stat().st_size-8000));value['failure_log_tail']=f.read().decode(errors='replace')
print(json.dumps(value,indent=2))
'''

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('destination', type=Path)
    p.add_argument('--root', default='/mnt/data2tb/research-cloud/PR-350-nplayer-bb100/bounded-20261019')
    args = p.parse_args()
    remote = REMOTE.replace("r=Path('/mnt/data2tb/research-cloud/PR-350-nplayer-bb100/bounded-20261019')", 'r=Path('+repr(args.root)+')')
    args.destination.mkdir(parents=True, exist_ok=False)
    result = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', 'bb128', 'python3 -'],
                            input=remote, text=True, capture_output=True, check=True)
    value = json.loads(result.stdout)
    (args.destination/'snapshot.json').write_text(result.stdout)
    compact = {k:v for k,v in value.items() if k not in ('launch','source-receipt','admission','last_resource','failure_log_tail')}
    if 'last_resource' in value:
        row = value['last_resource']
        compact['resources'] = {k:row[k] for k in ('temperatures_c','rss_bytes','available_ram_bytes','swap_growth_bytes')}
    print(json.dumps(compact, indent=2))
