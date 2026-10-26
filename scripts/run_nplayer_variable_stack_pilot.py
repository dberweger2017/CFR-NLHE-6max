"""One accepted fixed M4 pilot; no training extension or strength readout."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from scripts.calibrate_six_player_counterfactual_m4 import run_guarded
from scripts.nplayer_four_player_feasibility import sample,sha,write,TABLES
from scripts.nplayer_variable_stack_qualification import source_manifest

SOURCE=Path(__file__).resolve().parents[1]
TARGETS=[5_000_000,25_000_000,100_000_000]
SEED=20261026441011


def validate(c):
    for name in ['binary','qualification','owner_admission','thermal','binary_binding']:
        if sha(c[name])!=c[name+'_sha256']:raise ValueError('input changed:'+name)
    q=json.loads(Path(c['qualification']).read_text())
    owner=json.loads(Path(c['owner_admission']).read_text())
    if q['status']!='passed' or not q['fixture_only'] or not q['no_pilot_started']:
        raise ValueError('qualification incomplete')
    if (owner['status']!='owner-approved' or owner['study']!='PR441' or owner['targets']!=TARGETS
            or owner['seed']!=SEED or owner['max_entries']!=10_000_000
            or owner['allocation_seconds']!=3600 or owner['threads']!=2):
        raise ValueError('accepted fixed allocation differs')
    if source_manifest(SOURCE)!=c['source_manifest']:raise ValueError('source changed')
    original_path=Path(c['qualification']).parent/'config.json'
    if sha(original_path)!=q['config_sha256']:raise ValueError('qualification config changed')
    original=json.loads(original_path.read_text())
    digest=hashlib.sha256(json.dumps(original['source_manifest'],sort_keys=True).encode()).hexdigest()
    if digest!=q['source_manifest_sha256']:raise ValueError('qualification source binding differs')
    if sha(sys.executable)!=c['python_sha256'] or c['python_sha256']!=original['python_sha256']:raise ValueError('qualified Python changed')
    for name,pin in original['source_manifest'].items():
        if name.startswith('native/') and sha(SOURCE/name)!=pin:
            raise ValueError('qualified native source differs:'+name)
    binding=json.loads(Path(c['binary_binding']).read_text())
    if (binding['qualification_sha256']!=c['qualification_sha256'] or binding['source_manifest_sha256']!=q['source_manifest_sha256']
            or sha(c['binary'])!=binding['binary_sha256']):raise ValueError('binary differs from qualified executable')
    for name,pin in TABLES.items():
        if sha(Path(c['tables'])/name)!=pin:raise ValueError('K50 changed')


def run(root,c):
    if 'Apple M4' not in subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True):raise ValueError('M4 only')
    if 'AC Power' not in subprocess.check_output(['pmset','-g','batt'],text=True):raise ValueError('AC required')
    root.mkdir(parents=True,exist_ok=False);write(root/'config.json',c);locks=[];stages=[];clock=time.monotonic()
    try:
        for p in [Path.home()/'Local/.hu20-m4-research.lock',root.parent/'.variable-stack.lock']:
            f=p.open('a+');locks.append(f);fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        validate(c);before=sample(root,c['thermal'])
        write(root/'admission.json',dict(sample=before,forecast_family_rss_bytes=5*2**30,ram_headroom_bytes=2**30,
              forecast_new_disk_bytes=14*2**30,disk_headroom_bytes=4*2**30,planning_allocation_seconds=3600,no_elapsed_time_stop=True))
        if before['available_ram_bytes']<6*2**30 or before['disk_free_bytes']<18*2**30 or before['thermal_state'] not in ['nominal','fair']:
            raise ValueError('pilot forecast/headroom unavailable')
        manifest=dict(mode='pilot',seed=SEED,targets=TARGETS,max_entries=10_000_000,threads=2,
                      owner_admission=c['owner_admission'],tables=c['tables'],out=str(root/'native'))
        write(root/'manifest.json',manifest)
        def stage(name,command):
            if (root/'STOP').exists():raise ValueError('ownerSTOP')
            folder=root/'stages'/name;folder.mkdir(parents=True,exist_ok=False);write(folder/'config.json',c)
            write(root/'status.json',dict(status='running',phase=name))
            stages.append(run_guarded(folder,c,phase=name,command=command,owner_stop=root/'STOP'))
            write(root/'stage-costs.json',stages)
        stage('native-pilot',[c['binary'],'pilot',str(root/'manifest.json')])
        final=json.loads((root/'native/native-complete.json').read_text())
        if (final['status']!='native-complete-proof-pending'
                or [e['target_nodes']for e in final['endpoints']]!=TARGETS
                or any(e['actual_nodes']<e['target_nodes']for e in final['endpoints'])):
            raise ValueError('native endpoint barrier incomplete')
        for target in TARGETS:
            endpoint=root/'native'/str(target)
            for arm in ['initial','repeat']:
                stage(f'replay-{target}-{arm}',[sys.executable,'-m','scripts.check_nplayer_policy_replay',str(endpoint/(arm+'.jsonl'))])
            if sha(endpoint/'initial.jsonl')!=sha(endpoint/'repeat.jsonl'):raise ValueError('reproduction differs')
        validate(c)
        # Return the native measurement/proof pins, not a poker-strength verdict.
        write(root/'COMPLETE.json',dict(status='passed',cost_and_learning_only=True,targets=TARGETS,
          source_manifest_sha256=hashlib.sha256(json.dumps(c['source_manifest'],sort_keys=True).encode()).hexdigest(),
          native_readout_sha256=sha(root/'native/native-complete.json'),stages=stages,no_extra_training=True,wall_seconds=time.monotonic()-clock))
        write(root/'status.json',dict(status='complete',cost_and_learning_only=True))
    except BaseException as e:
        write(root/'failure.json',dict(error=repr(e),terminal=True,no_retry=True));raise
    finally:
        write(root/'WRAPPER-COST.json',dict(wall_seconds=time.monotonic()-clock,scope='Includes child stages; no elapsed-time cutoff'))
        for f in reversed(locks):f.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('config',type=Path)
    a=p.parse_args();run(a.root,json.loads(a.config.read_text()))

if __name__=='__main__':main()
