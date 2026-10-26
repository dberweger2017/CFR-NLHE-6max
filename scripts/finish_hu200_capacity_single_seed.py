"""Owner-scoped PR301 final queue, seed1302 only, within the existing evaluation clock."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

from scripts import schedule_hu200_capacity as q
from scripts import continue_hu200_capacity as storage
from scripts import evaluate_hu200_capacity as evaluation
from scripts import pilot_hu200_capacity as pilot
from scripts.run_hu200_capacity_training import pin, put
from src.blueprint import policy_cache
from src.policies.files import file_hash

PHASE='evaluation-single-seed-20261018'
COLD=storage.HDD/'research/PR-301-hu200-capacity-cygnus'/PHASE
STEPS=('20B-play','20B-replay','20B-reproduce','20B-verify','offload-20B',
       'restore-5B','cache-5B','admit-5B','5B-play','5B-replay','5B-reproduce',
       '5B-verify','global-barrier','readout')
RESERVE={name:(18_500_000_000 if name=='cache-5B' else 5_600_000_000 if name=='restore-5B'
              else 1_300_000_000 if name.endswith(('-play','-reproduce')) else 64_000_000) for name in STEPS}


def config(base,kind):
    return base/PHASE/('config-'+kind+'.json')


def guard_stop(stop):
    if stop.exists():raise RuntimeError('Guard requested stop; no retry')


def restore(base, spec, stop):
    storage.mount_checked()
    target=Path(spec['path'])
    source=storage.HDD/'research/PR-301-hu200-capacity-cygnus/inactive-models-20261017'/target.relative_to(base)
    if target.exists() or target.is_symlink():raise ValueError('Fresh NVMe restore target required')
    pilot.intact(source,spec);before=source.stat()
    target.parent.mkdir(parents=True,exist_ok=True)
    with source.open('rb') as incoming,target.open('xb') as outgoing:
        while block:=incoming.read(4*1024**2):
            guard_stop(stop);outgoing.write(block)
        outgoing.flush();os.fsync(outgoing.fileno())
    os.utime(target,ns=(before.st_atime_ns,before.st_mtime_ns))
    pilot.intact(target,spec);storage.sync_dir(target.parent)
    if (source.stat().st_size,source.stat().st_mtime_ns)!=(before.st_size,before.st_mtime_ns):
        raise ValueError('HDD source changed')
    put(base/PHASE/'restore-5B.json',dict(status='verified',source=str(source),source_retained=True,destination=pin(target)))


def worker(base,name,stop):
    guard_stop(stop)
    cfg20=evaluation.checked_config(config(base,'20B'))
    cfg5=evaluation.checked_config(config(base,'5B'))
    if name=='offload-20B':
        for parent in [COLD,*COLD.parents]:
            if parent.is_symlink():raise ValueError('Symlink cold destination')
        spec=cfg20['specs'][0];folder=policy_cache.folder(Path(cfg20['cache']),spec['sha256'],spec['abstraction'])
        manifest=q.read(folder/'manifest.json');items=[]
        for key,expected in manifest['files'].items():
            p=folder/(key+'.npy');item=pin(p)
            if (item['bytes'],item['sha256'])!=(expected['bytes'],expected['sha256']):raise ValueError('Cache changed')
            items.append(item)
        items += [pin(folder/'manifest.json'),pin(Path(spec['path']))]
        if items[-1]['sha256']!=spec['sha256']:raise ValueError('Model changed')
        journal=base/PHASE/'offload-journal.jsonl';rows=[]
        for item in items:
            src=Path(item['path']);dst=COLD/src.relative_to(base)
            rows.append(storage.relocate_one(src,dst,item,stop,journal))
        folder.rmdir()
        put(base/PHASE/'offload-20B.json',dict(status='verified',files=rows,cache_build_once_retained=True))
        return
    if name=='restore-5B':restore(base,cfg5['specs'][0],stop);return
    if name=='admit-5B':
        row=storage.sample(base);remaining=q.read(base/'evaluation-clock.json')['deadline_epoch']-time.time()
        if (remaining<4000 or row['free_disk_bytes']<q.FLOOR+1_300_000_000
                or row['package_c']>=68 or row['vrm_c']>=83):raise ValueError('Fresh5B fixed-work admission failed')
        pilot.intact(Path(cfg5['specs'][0]['path']),cfg5['specs'][0])
        put(Path(cfg5['final_admission']),dict(status='admitted',config_sha256=file_hash(config(base,'5B')),
            roots_fresh=True,pr_description_readback_verified=True,resources=row,
            original_declaration=q.read(base/PHASE/'admission-20B.json'),deadline_unchanged=True))
        return
    command=[sys.executable,'-m','scripts.evaluate_hu200_capacity']
    if name=='cache-5B':command+=['cache','--config',str(config(base,'5B')),'--index','0']
    elif name=='global-barrier':command+=['barrier-single-seed-1302','--configs',str(config(base,'20B')),str(config(base,'5B')),'--out',str(base/PHASE/'global-barrier.json')]
    elif name=='readout':command+=['readout','--barrier',str(base/PHASE/'global-barrier.json'),'--out',str(base/PHASE/'readout.json')]
    else:
        kind,action=name.split('-',1);command+=[action,'--config',str(config(base,kind))]
    proc=subprocess.Popen(command)
    while proc.poll() is None:
        if stop.exists():
            proc.terminate()
            try:proc.wait(timeout=30)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
            raise RuntimeError('Owned final stage stopped; partials retained, no retry')
        time.sleep(.25)
    if proc.returncode:raise RuntimeError(f'{name} failed exit{proc.returncode}; no automatic retry')


class Finish(q.Queue):
    def __init__(self,base):
        self.base=base;self.phase=base/PHASE;evaluation.single_seed_scope()
        self.clock=q.read(base/'evaluation-clock.json');self.deadline=self.clock['deadline_epoch']
        if self.deadline!=1792354954.5604858:raise ValueError('Existing evaluation deadline changed')
        self.admission=q.read(base/'admission.json')
        a=q.read(self.phase/'admission-20B.json')
        if a['status']!='admitted' or a['deadline_epoch']!=self.deadline:raise ValueError('Pre-final admission missing')
        for kind in ('20B','5B'):evaluation.checked_config(config(base,kind))
        self.root=base/'guards'/PHASE;self.root.mkdir(exist_ok=False)
        self.active,self.done,self.tasks={},set(),{}
        self.next_counter,self.last_counter=0,None;self.cpu_deltas,self.disk_busy_ms,self.last_disk={},0,None
        deps=[]
        for name in STEPS:self.task(name,'train',deps,seed=2026101302);deps=[name]

    def launch(self,task,row,totals):
        if self.active or row['package_c']>=68 or row['vrm_c']>=83:return False
        name=task['name'];reserve=RESERVE[name]
        if not pilot.evaluation_fits(totals,row['free_disk_bytes'],0,reserve):return False
        stop=self.phase/(name+'.stop')
        if stop.exists():raise ValueError('Stage already stopped; no retry')
        io=name in ('offload-20B','restore-5B');cpus=[6] if io else [0,1]
        command=[sys.executable,'-m','scripts.finish_hu200_capacity_single_seed','step','--base',str(self.base),'--name',name]
        plan=dict(name=name,kind='single-seed-'+name,cpus=cpus,rss_gib=.5 if io else 38,
                  stop_file=str(stop),command=command,reserve_bytes=reserve,original_deadline=self.deadline)
        put(self.root/(name+'.plan.json'),plan);log=(self.root/(name+'.log')).open('x')
        threads=str(len(cpus));env=dict(os.environ,OMP_NUM_THREADS=threads,MKL_NUM_THREADS=threads,
            OPENBLAS_NUM_THREADS=threads,RAYON_NUM_THREADS=threads,MKL_CBWR='AVX2,STRICT',PYTHONUNBUFFERED='1')
        before=q.owned_bytes(self.base)
        proc=subprocess.Popen(['taskset','-c',','.join(map(str,cpus)),*command],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        self.active[name]=dict(**plan,proc=proc,identity=q.process(proc.pid)['start'],log=log,
            started=time.monotonic(),folder=self.base,before_bytes=before)
        print(json.dumps(dict(event='started',job=plan,pid=proc.pid)),flush=True);return True

    finish=pilot.Pilot.finish
    decide_batch=pilot.Pilot.decide_batch
    publish=pilot.Pilot.publish

    def complete(self):
        sealed=q.read(self.phase/'global-barrier.json')
        if sealed['primary_hands']!=983040 or not sealed['exactly_reproduced']:raise ValueError('Global selected barrier incomplete')
        put(self.phase/'evaluation-complete.json',dict(status='single-seed-evaluation-complete',seed=2026101302,
            deferred_seeds=[2026101421,2026101422],barrier=pin(self.phase/'global-barrier.json'),
            readout=pin(self.phase/'readout.json'),finished_utc=storage.now(),clock=self.clock))


def notify(base,event):
    payload=dict(event=event,experiment='PR301',observed_utc=storage.now())
    for attempt in range(6):
        request=urllib.request.Request((base/'campaign-events-url.txt').read_text().strip(),data=json.dumps(payload).encode(),
            headers={'Content-Type':'application/json','User-Agent':'T3Code-HU200Capacity-Observer/1.0'},method='POST')
        try:
            with urllib.request.urlopen(request,timeout=10) as response:code=response.status
            put(base/PHASE/'event-delivery.json',dict(payload=payload,http_status=code,delivery_attempt=attempt+1));return
        except Exception as exc:
            print(json.dumps(dict(event='metadata_delivery_failed',error_type=type(exc).__name__,http_status=getattr(exc,'code',None))),flush=True)
            if attempt<5:time.sleep(10)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('run','step'));p.add_argument('--base',type=Path,required=True);p.add_argument('--name',choices=STEPS);a=p.parse_args()
    if a.base!=q.BASE or os.uname().nodename!='cygnus-x1':raise ValueError('Only owned PR301 on cygnus-x1')
    if a.mode=='step':worker(a.base,a.name,a.base/PHASE/(a.name+'.stop'));return
    with Path('/tmp/cfr-cygnus-exclusive.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:Finish(a.base).run()
        except BaseException as exc:
            put(a.base/PHASE/'evaluation-failed.json',dict(status='failed',error=repr(exc),automatic_retry=False,utc=storage.now()))
            notify(a.base,'evaluation_failed');raise
        notify(a.base,'single_seed_evaluation_complete')


if __name__=='__main__':main()
