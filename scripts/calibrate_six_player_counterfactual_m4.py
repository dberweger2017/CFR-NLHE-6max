"""Guarded fixed-work PR438 mature cost calibration; never enables the main panel."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import platform
import resource
import signal
import time
import subprocess
import sys

from scripts.nplayer_four_player_feasibility import TABLES, sample, sha, write
from scripts.six_player_counterfactual_m4 import MODEL, quote

SOURCE=Path(__file__).resolve().parents[1]


def required_source_files():
    files=set()
    for directory in ['native/hu20-trainer/src','native/hu20-buckets/src']:
        files.update(str(p.relative_to(SOURCE)) for p in (SOURCE/directory).rglob('*') if p.is_file())
    files.update(['native/hu20-trainer/examples/six_player_counterfactual.rs',
                  'native/hu20-trainer/Cargo.toml','native/hu20-trainer/Cargo.lock',
                  'native/hu20-buckets/Cargo.toml',
                  'scripts/calibrate_six_player_counterfactual_m4.py',
                  'scripts/six_player_counterfactual_m4.py',
                  'scripts/nplayer_four_player_feasibility.py',
                  'scripts/support/m4_thermal_state.swift',
                  'docs/six-player-counterfactual-m4.md'])
    return files


def validate_config(c):
    if c['format']!='six-player-conditional-calibration-v1' or c['mode']!='calibrate' or c['belief_root']!=20261026437002 or c['threads']!=2 or c['model_sha256']!=MODEL:
        raise ValueError('fixed calibration scope differs')
    if not c['independent_review']['resolved'] or not c['independent_review']['receipt_sha256']:
        raise ValueError('independent review unresolved')
    if set(c['source_files']) != required_source_files():raise ValueError('source manifest incomplete')
    for name,pin in c['source_files'].items():
        if sha(SOURCE/name)!=pin:raise ValueError('source changed: '+name)
    for name,pin in TABLES.items():
        if sha(Path(c['tables'])/name)!=pin:raise ValueError('K50 changed')
    for name,pin in [('binary','binary_sha256'),('model','model_sha256'),('states','states_sha256'),('inventory','inventory_sha256'),('review_receipt','review_receipt_sha256'),('thermal','thermal_sha256')]:
        if sha(c[name])!=c[pin]:raise ValueError(name+' changed')
    if c['review_receipt_sha256']!=c['independent_review']['receipt_sha256']:
        raise ValueError('review receipt binding differs')
    inventory=json.loads(Path(c['inventory']).read_text())
    if inventory['states_sha256']!=c['states_sha256'] or inventory['model_sha256']!=MODEL or not 1<=inventory['roots']<=36:
        raise ValueError('frozen panel inventory differs')


def run_guarded(root, config, *, phase="mature-calibration", command=None, owner_stop=None):
    """Supervise only this child/process group; preserve every terminal failure."""
    folder = root/'measurements'/phase
    folder.mkdir(parents=True, exist_ok=False)
    config_pin = sha(root/'config.json')
    command = command or [config['binary'], str(root/'manifest.json')]
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    tick = time.monotonic();peak = 0;child = None
    try:
        with (folder/'stdout.log').open('x') as out, (folder/'stderr.log').open('x') as err:
            write(root/'status.json', dict(status='running', phase=phase))
            child = subprocess.Popen(command, cwd=SOURCE, env=dict(os.environ, RAYON_NUM_THREADS='2'),
                                     stdout=out, stderr=err, start_new_session=True)
            with (root/'resources.jsonl').open('x') as log:
                while child.poll() is None:
                    x = sample(root, config['thermal'], child.pid)
                    peak = max(peak, x['worker_family_rss_bytes'])
                    log.write(json.dumps(x)+'\n');log.flush()
                    if (x['thermal_state'] not in ('nominal','fair') or (root/'STOP').exists() or (owner_stop is not None and owner_stop.exists())
                            or sha(root/'config.json') != config_pin):
                        raise RuntimeError('thermal/STOP/config terminal stop')
                    # Prospective protective floors, distinct from admission
                    # forecast headroom. No run-time elapsed/RSS/swap limit.
                    if x['available_ram_bytes'] < 512*2**20 or x['disk_free_bytes'] < 256*2**20 or x['pressure'] >= 4:
                        raise RuntimeError('resource protection terminal stop')
                    time.sleep(1)
            code = child.wait()
            if code:raise RuntimeError(f'calibration failed:{code}; no automatic retry')
    except BaseException:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(child.pid, signal.SIGKILL);child.wait()
        raise
    finally:
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        cost = dict(phase=phase,command=command,
                    returncode=child.returncode if child is not None else None,
                    pid=child.pid if child is not None else None,
                    wall_seconds=time.monotonic()-tick,
                    user_cpu_seconds=after.ru_utime-before.ru_utime,
                    system_cpu_seconds=after.ru_stime-before.ru_stime,
                    sampled_peak_rss_bytes=peak)
        write(folder/'receipt.json',cost)
        write(root/'stage-costs.json',[cost])
    return cost


def calibrate(root, config):
    if platform.system()!='Darwin' or 'Apple M4' not in subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True):
        raise ValueError('M4 only')
    if 'AC Power' not in subprocess.check_output(['pmset','-g','batt'],text=True):raise ValueError('AC required')
    root=Path(root);root.mkdir(parents=True,exist_ok=False)
    write(root/'config.json',config)
    locks=[]
    try:
        for path in [Path.home()/'Local/.hu20-m4-research.lock',root.parent/'.six-player-counterfactual.lock']:
            f=path.open('a+');locks.append(f);fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        validate_config(config)
        # Raw binary already exists. The eager reader streams it into its row
        # and float vectors; include K50 file bytes plus1GiB allocator/buffer
        # reserve. Compressed transfer bytes never stand in for resident memory.
        raw=Path(config['model']).stat().st_size
        tables=sum((Path(config['tables'])/n).stat().st_size for n in TABLES)
        forecast=raw+tables+2**30
        before=sample(root,config['thermal'])
        admission=dict(sample=before,raw_binary_bytes=raw,table_bytes=tables,
                       forecast_family_rss_bytes=forecast,ram_headroom_bytes=2**30,
                       forecast_additional_disk_bytes=2**30,disk_headroom_bytes=4*2**30,
                       main_started=False)
        write(root/'admission.json',admission)
        if before['available_ram_bytes']<forecast+2**30 or before['disk_free_bytes']<5*2**30:
            raise ValueError('calibration forecast + headroom unavailable')
        if before['thermal_state'] not in ['nominal','fair'] or (root/'STOP').exists():raise ValueError('thermal/ownerSTOP')
        manifest={k:config[k] for k in ['mode','belief_root','threads','model','model_sha256','tables','states','states_sha256']}
        manifest['out']=str(root/'native')
        write(root/'manifest.json',manifest)
        cost=run_guarded(root,config)
        validate_config(config)
        v=json.loads((root/'native/verified.json').read_text())
        if v['roots']!=json.loads(Path(config['inventory']).read_text())['roots'] or v['model_sha256']!=MODEL:
            raise ValueError('calibration did not retain every fixed root')
        pricing=quote(v)
        pricing['calibration_costs']=[cost]
        pricing['admission']=admission
        pricing['after']=sample(root,config['thermal'])
        pricing['review_receipt_sha256']=config['review_receipt_sha256']
        write(root/'quote.json',pricing)
        write(root/'COMPLETE.json',dict(status='passed',main_started=False,quote_sha256=sha(root/'quote.json'),native_receipt_sha256=sha(root/'native/verified.json'),config_sha256=sha(root/'config.json')))
        write(root/'status.json',dict(status='complete',main_started=False))
    except BaseException as e:
        write(root/'failure.json',dict(error=repr(e),no_retry=True));raise
    finally:
        for f in reversed(locks):f.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('root',type=Path);p.add_argument('config',type=Path)
    a=p.parse_args();calibrate(a.root,json.loads(a.config.read_text()))

if __name__=='__main__':main()
