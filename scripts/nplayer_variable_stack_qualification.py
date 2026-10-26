"""Finite M4 variable-stack fixtures and old-source parity; never starts the pilot."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time

from scripts.calibrate_six_player_counterfactual_m4 import run_guarded
from scripts.nplayer_four_player_feasibility import sample,sha,write,TABLES

SOURCE=Path(__file__).resolve().parents[1]


def source_manifest(root):
    files=[]
    for d in ['native/hu20-trainer/src','native/hu20-trainer/examples','native/hu20-buckets/src']:
        files.extend(p for p in (root/d).rglob('*.rs'))
    files.extend(root/n for n in ['native/hu20-trainer/Cargo.toml','native/hu20-trainer/Cargo.lock','native/hu20-buckets/Cargo.toml'])
    return {str(p.relative_to(root)):sha(p) for p in sorted(files)}


def run(root,baseline,tables,thermal):
    if platform.system()!='Darwin' or 'Apple M4' not in subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True):
        raise ValueError('M4 only')
    if 'AC Power' not in subprocess.check_output(['pmset','-g','batt'],text=True):
        raise ValueError('AC required')
    root.mkdir(parents=True,exist_ok=False);locks=[];clock=time.monotonic()
    stages=[];manifest=source_manifest(SOURCE);old_manifest=source_manifest(baseline)
    config=dict(thermal=str(thermal),python=sys.executable,source_manifest=manifest,baseline_manifest=old_manifest)
    write(root/'config.json',config)
    try:
        for p in [Path.home()/'Local/.hu20-m4-research.lock',root.parent/'.variable-stack.lock']:
            f=p.open('a+');locks.append(f);fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        before=sample(root,thermal)
        write(root/'admission.json',dict(sample=before,fixture_forecast_rss_bytes=3*2**30,ram_headroom_bytes=2**30,
              forecast_new_disk_bytes=4*2**30,disk_headroom_bytes=4*2**30,no_pilot_started=True))
        if before['available_ram_bytes']<4*2**30 or before['disk_free_bytes']<8*2**30 or before['thermal_state'] not in ['nominal','fair']:
            raise ValueError('fixture forecast/headroom unavailable')
        for name,pin in TABLES.items():
            if sha(tables/name)!=pin:raise ValueError('K50 changed')
        os.environ['CARGO_BUILD_JOBS']='2'
        def stage(name,command):
            folder=root/'stages'/name;folder.mkdir(parents=True,exist_ok=False);write(folder/'config.json',config)
            write(root/'status.json',dict(status='running',phase=name))
            stages.append(run_guarded(folder,config,phase=name,command=[str(c) for c in command],owner_stop=root/'STOP'))
            write(root/'stage-costs.json',stages)
        cargo=['cargo','build','--locked','--release','--manifest-path']
        stage('build-new',cargo+[SOURCE/'native/hu20-trainer/Cargo.toml','--example','nplayer_variable_stack','--example','nplayer_train','--example','nplayer_policy','--example','nplayer_parity'])
        stage('build-baseline',cargo+[baseline/'native/hu20-trainer/Cargo.toml','--example','nplayer_train','--example','nplayer_policy'])
        binary=SOURCE/'native/hu20-trainer/target/release/examples'
        old=baseline/'native/hu20-trainer/target/release/examples'
        stage('native-fixtures',[binary/'nplayer_variable_stack','qualify',tables,root/'native'])
        stage('independent-replay',[sys.executable,'-m','scripts.check_nplayer_policy_replay',root/'native/initial.jsonl'])
        stage('repeat-independent-replay',[sys.executable,'-m','scripts.check_nplayer_policy_replay',root/'native/repeat.jsonl'])
        parity=[]
        for schema in ['history','live-order']:
            for version,exe in [('old',old),('new',binary)]:
                out=root/f'{schema}-{version}.gz'
                stage(f'legacy-{schema}-{version}',[exe/'nplayer_train','--players','3','--stack-bb','20',
                  '--small-blind','50','--big-blind','100','--seed','20261026441003','--nodes','100000','--last-average-street','3',
                  '--max-entries','100000','--freeze-at-cap','--fast','--threads','2','--roots-per-seat','8','--max-seconds','1e100',
                  '--card-buckets',tables,'--key-schema',schema,'--out',out])
                stage(f'legacy-export-{schema}-{version}',[exe/'nplayer_policy','export',out,sha(out),'average',root/f'{schema}-{version}-average.gz'])
            if sha(root/f'{schema}-old.gz')!=sha(root/f'{schema}-new.gz') or sha(root/f'{schema}-old-average.gz')!=sha(root/f'{schema}-new-average.gz'):
                raise ValueError('legacy checkpoint/export bytes changed:'+schema)
            parity.append(dict(schema=schema,checkpoint_sha256=sha(root/f'{schema}-new.gz'),average_sha256=sha(root/f'{schema}-new-average.gz')))
        if source_manifest(SOURCE)!=manifest or source_manifest(baseline)!=old_manifest:raise ValueError('source changed during fixtures')
        proof=json.loads((root/'native/verified.json').read_text())
        if proof['status']!='passed' or not proof['no_pilot_started']:raise ValueError('native proof incomplete')
        write(root/'COMPLETE.json',dict(status='passed',fixture_only=True,no_pilot_started=True,native=proof,legacy_byte_parity=parity,
          source_manifest_sha256=__import__('hashlib').sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest(),
          config_sha256=sha(root/'config.json'),stages=stages,wall_seconds=time.monotonic()-clock,after=sample(root,thermal)))
        write(root/'status.json',dict(status='complete',fixture_only=True,no_pilot_started=True))
    except BaseException as e:
        write(root/'failure.json',dict(error=repr(e),terminal=True,no_retry=True));raise
    finally:
        write(root/'WRAPPER-COST.json',dict(wall_seconds=time.monotonic()-clock,scope='Includes child stages; do not add stage walls again'))
        for f in reversed(locks):f.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['root','baseline','tables','thermal']:p.add_argument(n,type=Path)
    a=p.parse_args();run(a.root,a.baseline,a.tables,a.thermal)

if __name__=='__main__':main()
