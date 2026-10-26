"""Approved fixed PR438 panel; native evaluation and proof-gated readout only."""
import argparse
import fcntl
import json
from pathlib import Path
import platform
import resource
import os
import subprocess
import sys
import time

from scripts.calibrate_six_player_counterfactual_m4 import required_source_files, run_guarded
from scripts.nplayer_four_player_feasibility import TABLES, sample, sha, write
from scripts.six_player_counterfactual_m4 import MODEL

SOURCE = Path(__file__).resolve().parents[1]


def source_files():
    return required_source_files() | {
        'scripts/run_six_player_counterfactual_m4.py',
        'scripts/analyze_six_player_counterfactual_m4.py'}


def validate(c):
    if (c['format'] != 'six-player-conditional-main-v1' or c['mode'] != 'main'
            or c['belief_root'] != 20261026437001 or c['threads'] != 2
            or c['model_sha256'] != MODEL or c['discovery_worlds'] != 64
            or c['heldout_worlds'] != 2048):
        raise ValueError('fixed main scope differs')
    if set(c['source_files']) != source_files():
        raise ValueError('source manifest incomplete')
    for name, pin in c['source_files'].items():
        if sha(SOURCE/name) != pin:
            raise ValueError('source changed:'+name)
    for name, pin in TABLES.items():
        if sha(Path(c['tables'])/name) != pin:
            raise ValueError('K50 changed')
    for field in ['binary','model','states','inventory','review_receipt','qualification_receipt','owner_admission','thermal','python']:
        if sha(c[field]) != c[field+'_sha256']:
            raise ValueError('input changed:'+field)
    a=json.loads(Path(c['owner_admission']).read_text())
    if (a['study'] != 'PR438' or a['status'] != 'owner-approved'
            or a['allocation_seconds'] != 900 or a['discovery_worlds'] != 64
            or a['heldout_worlds'] != 2048 or a['repetitions'] != 2
            or a['model_sha256'] != MODEL or a['states_sha256'] != c['states_sha256']):
        raise ValueError('owner approval differs')
    review=json.loads(Path(c['review_receipt']).read_text())
    if not review['resolved'] or not review['main_readout_reviewed']:
        raise ValueError('main readout review unresolved')
    manifest_pin=__import__('hashlib').sha256(json.dumps(c['source_files'],sort_keys=True).encode()).hexdigest()
    if review['source_manifest_sha256'] != manifest_pin:
        raise ValueError('reviewed source differs')
    qualification=json.loads(Path(c['qualification_receipt']).read_text())
    if (qualification['status'] != 'passed' or qualification['binary_sha256'] != c['binary_sha256']
            or not qualification['full_work_fixture_readout_passed']
            or qualification['source_manifest_sha256'] != manifest_pin):
        raise ValueError('source qualification differs')
    inventory=json.loads(Path(c['inventory']).read_text())
    if inventory['roots'] != 36 or inventory['states_sha256'] != c['states_sha256'] or inventory['model_sha256'] != MODEL:
        raise ValueError('frozen panel differs')
    if a['inventory_sha256'] != c['inventory_sha256']:
        raise ValueError('approved inventory differs')


def run(root, c):
    if platform.system() != 'Darwin' or 'Apple M4' not in subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True):
        raise ValueError('M4 only')
    if 'AC Power' not in subprocess.check_output(['pmset','-g','batt'],text=True):
        raise ValueError('AC required')
    root=Path(root);root.mkdir(parents=True,exist_ok=False)
    write(root/'config.json',c)
    locks=[];clock=time.monotonic();before=resource.getrusage(resource.RUSAGE_SELF)
    try:
        for p in [Path.home()/'Local/.hu20-m4-research.lock',root.parent/'.six-player-counterfactual.lock']:
            f=p.open('a+');locks.append(f);fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        validate(c)
        resources=sample(root,c['thermal'])
        raw=Path(c['model']).stat().st_size
        tables=sum((Path(c['tables'])/n).stat().st_size for n in TABLES)
        forecast=raw+tables+2**30
        write(root/'admission.json',dict(sample=resources,forecast_family_rss_bytes=forecast,
              ram_headroom_bytes=2**30,forecast_additional_disk_bytes=2**30,disk_headroom_bytes=4*2**30,
              owner_allocation_seconds=900,no_elapsed_time_cutoff=True))
        if (resources['available_ram_bytes'] < forecast+2**30 or resources['disk_free_bytes'] < 5*2**30
                or resources['thermal_state'] not in ['nominal','fair'] or (root/'STOP').exists()):
            raise ValueError('resource/thermal/STOP admission refused')
        manifest={k:c[k] for k in ['mode','belief_root','threads','model','model_sha256','tables','states','states_sha256',
                                  'discovery_worlds','heldout_worlds','owner_admission','owner_admission_sha256']}
        manifest['out']=str(root/'native')
        stages=[]
        for name,command in [
            ('native-main',[c['binary'],str(root/'manifest.json')]),
            ('readout',[c['python'],'-m','scripts.analyze_six_player_counterfactual_m4',str(root/'native'),c['inventory'],str(root/'readout')])]:
            if (root/'STOP').exists():
                raise RuntimeError('ownerSTOP')
            stage=root/name;stage.mkdir(exist_ok=False)
            write(stage/'config.json',c)
            if name=='native-main':
                write(root/'manifest.json',manifest)
            write(root/'status.json',dict(status='running',phase=name))
            stages.append(run_guarded(stage,c,phase=name,command=command,owner_stop=root/'STOP'))
            write(root/'stage-costs.json',stages)
        validate(c)
        receipt=json.loads((root/'readout/verified.json').read_text())
        if receipt['status'] != 'passed' or receipt['roots'] != 36 or not receipt['no_exclusions'] or receipt['fixture_only']:
            raise ValueError('incomplete main readout')
        write(root/'COMPLETE.json',dict(status='passed',roots=36,readout_verified_sha256=sha(root/'readout/verified.json'),
              results_sha256=sha(root/'readout/results.json'),config_sha256=sha(root/'config.json'),
              owner_admission_sha256=c['owner_admission_sha256'],no_extra_worlds=True,stages=stages))
        write(root/'status.json',dict(status='complete',results_sha256=sha(root/'readout/results.json')))
    except BaseException as e:
        write(root/'failure.json',dict(error=repr(e),terminal=True,no_retry=True))
        raise
    finally:
        after=resource.getrusage(resource.RUSAGE_SELF)
        write(root/'WRAPPER-COST.json',dict(wall_seconds=time.monotonic()-clock,
              parent_user_cpu_seconds=after.ru_utime-before.ru_utime,
              parent_system_cpu_seconds=after.ru_stime-before.ru_stime,
              scope='Whole wrapper incl validation/setup/readout; parent CPU excludes stage children.'))
        for f in reversed(locks):f.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('root',type=Path);p.add_argument('config',type=Path)
    a=p.parse_args();run(a.root,json.loads(a.config.read_text()))

if __name__=='__main__':main()
