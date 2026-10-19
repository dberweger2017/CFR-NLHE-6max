"""Owner-authorized proposal345: frozen three-seed overnight continuations."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import fcntl
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import time

from scripts import run_nplayer_storage_benchmark as guard
from scripts.overnight_tensorboard import Scalars

SEEDS = (2026101541, 2026101542, 2026101543)
BOTS = ('random', 'check-call', 'tight-aggressive', 'pot-pressure')
TARGETS = (10_000_000_000, 20_000_000_000, 30_000_000_000)
MAX_SECONDS = 10 * 3600
TMP_BUDGET = 48 * guard.GIB
CACHE_BUDGET = 100_000_000_000


def load(path):
    return json.loads(Path(path).read_text())


def cases(smoke=False):
    rows = []
    index = 0
    for group in ('same', 'cross'):
        for i, seed in enumerate(SEEDS):
            other = seed if group == 'same' else SEEDS[(i+1) % 3]
            for reverse in (False, True):
                a, b = f'final-{seed}', f'anchor-{other}'
                rows.append(dict(name=f'{group}-{seed}-{int(reverse)}', group=group, seed=seed,
                    root=(20261018347001 if smoke else 20261018346001)+index,
                    blocks=2 if smoke else 8192, singleton=b if reverse else a, pair=a if reverse else b))
            index += 1
    for seed in SEEDS:
        for bot in BOTS:
            for anchor in (False, True):
                rows.append(dict(name=f'bot-{seed}-{bot}-{int(anchor)}', group='bot', seed=seed, bot=bot,
                    root=(20261018347001 if smoke else 20261018346001)+index,
                    blocks=2 if smoke else 8192, singleton=f'{"anchor" if anchor else "final"}-{seed}', pair='bot='+bot))
            index += 1
    return rows


def preserve(root, cache, names):
    """Retain verified copies only; never unlink or overwrite an earlier copy."""
    receipt = []
    for name in names:
        source = root / name
        files = [source] if source.is_file() else sorted(p for p in source.rglob('*') if p.is_file())
        for path in files:
            relative = path.relative_to(root)
            dest = cache / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            digest = guard.sha(path)
            if dest.exists():
                if not path.samefile(dest) and guard.sha(dest) != digest:
                    raise ValueError('preservation destination changed: '+str(relative))
            else:
                with path.open('rb') as src, dest.open('xb') as out:
                    shutil.copyfileobj(src, out, 4*1024**2)
                    out.flush(); os.fsync(out.fileno())
                if guard.sha(dest) != digest:
                    raise ValueError('preservation copy mismatch')
            receipt.append(dict(path=str(relative), bytes=path.stat().st_size, sha256=digest))
    return receipt


class Supervisor(guard.Supervisor):
    def __init__(self, root, cache, lock, remaining, logs):
        guard.BUDGET = TMP_BUDGET
        guard.FLOOR = 2 * guard.GIB  # tmpfs reservation; physical disks checked separately.
        super().__init__(root, lock, cpus=range(16), max_seconds=remaining,
                         rss_limit=80*guard.GIB, cpu_limit=90, thermistor_limit=95,
                         swap_limit_bytes=None)
        self.cache, self.logs, self.seed = cache, logs, 0
        self.last_log = 0
        self.initial_cache_bytes = guard.tree_bytes(cache)

    def sample(self, process, phase, target):
        row = super().sample(process, phase, target)
        try:
            for path, label in [('/home/dberweger', 'nvme'), (str(self.cache), 'hdd')]:
                disk = os.statvfs(path)
                row[label+'_free_bytes'] = disk.f_bavail * disk.f_frsize
                if row[label+'_free_bytes'] < 50_000_000_000:
                    raise RuntimeError(label+'50GB floor stop')
            if guard.tree_bytes(self.cache)-self.initial_cache_bytes > CACHE_BUDGET:
                raise RuntimeError('owned100GB preservation budget stop')
        except RuntimeError as error:
            error.resource_sample = row
            raise
        if time.monotonic()-self.last_log >= 30:
            for k in ('rss_bytes', 'available_ram_bytes', 'swap_used_bytes', 'swap_growth_bytes', 'nvme_free_bytes', 'hdd_free_bytes'):
                self.logs.add('resources/'+k, row[k], int(time.time()))
            for k,v in row['temperatures_c'].items():
                self.logs.add('temperature/'+k, v, int(time.time()))
            self.last_log = time.monotonic()
        return row

    def event(self, line):
        event = guard.json_event_original(line)
        if event is None:
            return None
        seed = self.seed
        step = event.get('nodes', 0)
        if event.get('event') in ('progress','trained'):
            for key in ('nodes','entries','active_seconds','monitor_seconds','nodes_per_second'):
                if key in event:
                    self.logs.add(f'{seed}/training/{key}', event[key], step)
            if event.get('active_seconds',0)>100 and event.get('monitor_seconds',0)>event['active_seconds']*.10:
                raise RuntimeError('monitoring overhead exceeds10%')
        if event.get('event')=='probe':
            for row in event['results']:
                values=row['block_bb100']; mean=statistics.mean(values)
                # Exactly128 independent blocks: t(.975,127)=1.9788195347.
                width=1.9788195347*statistics.stdev(values)/math.sqrt(len(values))
                for key,val in [('bb100',mean),('lower95',mean-width),('upper95',mean+width)]:
                    self.logs.add(f'{seed}/monitor/{row["bot"]}/{key}',val,step)
        return event


def case_run(task):
    from scripts.check_nplayer_policy_replay import check
    case,m,root=task
    folder=Path(root)/'evaluation'/case['name'];folder.mkdir(parents=True,exist_ok=False)
    def spec(name):
        if name.startswith('bot='):return name
        model=m['models'][name]
        return 'policy='+model['path']+'@'+model['sha256']
    command=[m['arena'],m['tables'],str(case['blocks']),str(case['root'])]
    coverage=[]
    for repeat in (0,1):
        trace=folder/f'play-{repeat}.jsonl'
        with (folder/f'play-{repeat}.log').open('x') as out:
            subprocess.run(command+[str(trace),spec(case['singleton']),spec(case['pair'])],stdout=out,stderr=subprocess.STDOUT,check=True)
        coverage.append(load(folder/f'play-{repeat}.log'))
    a,b=folder/'play-0.jsonl',folder/'play-1.jsonl'
    digest=guard.sha(a)
    if guard.sha(b)!=digest:raise ValueError('reproduction differs')
    replay=check(a)
    if replay['status']!='passed' or replay['hands']!=case['blocks']*6 or replay['trace_sha256']!=digest:
        raise ValueError('replay mismatch')
    with a.open() as stream:header=json.loads(next(stream))
    if header['seed']!=case['root'] or header['blocks']!=case['blocks']:
        raise ValueError('trace root/count mismatch')
    expected=[m['models'][name]['sha256'] if not name.startswith('bot=') else None
              for name in (case['singleton'],case['pair'],case['pair'])]
    if [p.get('sha256') for p in header['policies']]!=expected:raise ValueError('trace model mismatch')
    result=dict(status='passed',case=case,trace_sha256=digest,hands=replay['hands'],coverage=coverage)
    guard.write(folder/'replay.json',replay);guard.write(folder/'result.json',result)
    return result


def evaluation_directory(root, m):
    if 'evaluation_directory' in m:
        # Large final traces can live directly in the owned retained cache.
        directory=Path(m['evaluation_directory'])
        expected=Path(load(root/'config.json')['cache'])/'evaluation'
        if directory!=expected or not directory.is_absolute():
            raise ValueError('evaluation directory must be the owned cache/evaluation')
        directory.mkdir(exist_ok=False)
        (root/'evaluation').symlink_to(directory,target_is_directory=True)
    else:
        (root/'evaluation').mkdir(exist_ok=False)


def batch(root):
    from scripts.check_nplayer_parity import engine_identity
    engine_identity()
    m=load(root/'evaluation-manifest.json')
    if m['cases']!=cases(m['smoke']):raise ValueError('changed frozen matrix')
    for path,digest in [(m['arena'],m['arena_sha256'])]+[(v['path'],v['sha256']) for v in m['models'].values()]:
        if guard.sha(path)!=digest:raise ValueError('evaluation input mismatch')
    evaluation_directory(root,m)
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(case_run,(case,m,str(root))) for case in m['cases']]
        for i,future in enumerate(as_completed(futures),1):
            future.result();print(json.dumps(dict(event='progress',completed=i,total=len(futures))),flush=True)
    guard.write(root/'evaluation-verified.json',dict(status='passed',manifest_sha256=guard.sha(root/'evaluation-manifest.json'),
        cases=len(m['cases']),hands=sum(c['blocks']*6 for c in m['cases'])))


def read(root, matrix=None):
    matrix = cases() if matrix is None else matrix
    from scipy.stats import t
    from scripts.read_nplayer_fast_study import paired_blocks
    from scripts.analyze_nplayer_arena import interval
    if (root/'failure.json').exists() or load(root/'status.json')['status']!='verified-readout-ready':
        raise ValueError('global barrier not ready')
    m=load(root/'evaluation-manifest.json');verified=load(root/'evaluation-verified.json')
    if m['cases']!=matrix or verified!=dict(status='passed',manifest_sha256=guard.sha(root/'evaluation-manifest.json'),cases=36,hands=1769472):
        raise ValueError('verification identity mismatch')
    for c in matrix:
        d=root/'evaluation'/c['name'];result=load(d/'result.json');replay=load(d/'replay.json')
        if result['status']!='passed' or result['case']!=c or result['hands']!=49152 or replay['status']!='passed':raise ValueError('unverified case')
        if len({result['trace_sha256'],replay['trace_sha256'],guard.sha(d/'play-0.jsonl'),guard.sha(d/'play-1.jsonl')})!=1:
            raise ValueError('trace proof differs')
    rows=[]
    for a,b in zip(matrix[::2],matrix[1::2]):
        values=list(paired_blocks(root/'evaluation'/a['name']/'play-0.jsonl',root/'evaluation'/b['name']/'play-0.jsonl',a['root']))
        if len(values)!=8192:raise ValueError('statistical block count')
        key='advantage' if a['group']!='bot' else 'fast_singleton'
        data=[v[key] if a['group']!='bot' else v['fast_singleton']-v['production_singleton'] for v in values]
        score=interval(data)
        if a['group']=='bot':
            width=float(t.ppf(1-.05/(2*12),len(data)-1))*statistics.stdev(data)/math.sqrt(len(data))
            score.update(lower_family95=statistics.mean(data)-width,upper_family95=statistics.mean(data)+width)
        detail={key:[interval([v[key][i] for v in values]) for i in range(3)] for key in
                ('fast_by_seat','production_by_seat','fast_by_position','production_by_position')}
        rows.append(dict(group=a['group'],seed=a['seed'],bot=a.get('bot'),root=a['root'],score=score,**detail))
    result=dict(status='settled',rows=rows,models=m['models'],final_hands=1769472,reproduction_hands=1769472,
        consistent_gain=all(r['score']['lower95_bb100']>0 for r in rows if r['group']=='same'),
        cross_noninferiority=all(r['score']['lower95_bb100']>-5 for r in rows if r['group']=='cross'))
    guard.write(root/'results.json',result)
    print(json.dumps(dict(event='complete',status='settled')),flush=True)


def verify_one(task):
    import hashlib
    from scripts.check_nplayer_policy_replay import check
    row,c,root=task
    directory=Path(root)/'probe-proof'/row['bot'];directory.mkdir(parents=True,exist_ok=False)
    model=c['anchors'][str(SEEDS[0])];trace=directory/'reference.jsonl'
    command=[c['arena'],c['tables'],'128',str(row['root']),str(trace),
             'policy='+model['path']+'@'+model['sha256'],'bot='+row['bot']]
    subprocess.run(command,stdout=(directory/'play.log').open('x'),stderr=subprocess.STDOUT,check=True)
    digest=hashlib.sha256();values=[];current=[];decisions=[0]*4;missing=[0]*4
    with trace.open() as stream:
        next(stream)
        for line in stream:
            hand=json.loads(line)
            body=[hand['block'],hand['permutation'],hand['actors'],hand['actions'],hand['rewards']]
            digest.update((json.dumps(body,separators=(',',':'))+'\n').encode())
            current.append(hand['rewards'][hand['identities'].index(0)])
            if hand['permutation']==5:values.append(sum(current)/6);current=[]
    if digest.hexdigest()!=row['play_sha256'] or values!=row['block_bb100']:
        raise ValueError('in-memory/reference played path differs')
    replay=check(trace)
    if replay['status']!='passed' or replay['hands']!=768:raise ValueError('probe replay failed')
    guard.write(directory/'replay.json',replay)
    return dict(bot=row['bot'],play_sha256=digest.hexdigest(),hands=768,status='passed')


def verify(root):
    c=load(root/'config.json')
    result=load(root/'measurements/qualification-monitored/result.json')
    events=[e for e in result['events'] if e.get('event')=='probe']
    if len(events)!=1:raise ValueError('missing qualification probe')
    with ProcessPoolExecutor(max_workers=4) as pool:
        proof=list(pool.map(verify_one,[(row,c,str(root)) for row in events[0]['results']]))
    guard.write(root/'probe-proof.json',dict(status='passed',results=proof))
    print(json.dumps(dict(event='complete',status='passed',hands=3072)),flush=True)


def run(root):
    c=load(root/'config.json');cache=Path(c['cache']);launch=load(root/'launch.json')
    with Path('/tmp/cfr-nplayer-overnight.lock').open('a') as own,Path('/tmp/cfr-cygnus-exclusive.lock').open('a') as legacy:
        for lock in (own,legacy):fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        logs=Scalars(root/'tensorboard')
        s=Supervisor(root,cache,own.fileno(),launch['epoch']+MAX_SECONDS-time.time(),logs)
        guard.json_event_original=guard.json_event;guard.json_event=s.event
        sample=s.sample(None,'admission',0)
        if sample['temperatures_c']['Package id 0']>=70 or sample['temperatures_c']['Thermistor 15']>=80:raise RuntimeError('thermal admission')
        for name,digest in c['source_files'].items():
            if guard.sha(root/'source'/name)!=digest:raise ValueError('source pin mismatch')
        for key in ('legacy_train','policy','arena'):
            if guard.sha(c[key])!=c[key+'_sha256']:raise ValueError('binary pin mismatch')
        for value in c['anchors'].values():
            for path,hashkey in (('checkpoint','checkpoint_sha256'),('path','sha256')):
                if guard.sha(value[path])!=value[hashkey]:raise ValueError('anchor input mismatch')
        guard.write(root/'admission.json',dict(source_commit=c['source_commit'],initial_sample=sample,deadline=launch['epoch']+MAX_SECONDS))
        src=root/'source';env=dict(os.environ,RAYON_NUM_THREADS='16',CARGO_BUILD_JOBS='4',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',CARGO_TARGET_DIR=str(root/'target'))
        env['PATH']='/home/dberweger/.cargo/bin:'+env['PATH']
        def stage(name,cmd,keep_status=False):
            if not keep_status:guard.write(root/'status.json',dict(status=name,at=time.time(),seed=s.seed))
            result=s.execute(name,list(map(str,cmd)),src,env)
            preserve(root,cache,['measurements/'+name])
            return result
        stage('build',['cargo','build','--release','--locked','--offline','--manifest-path',src/'native/hu20-trainer/Cargo.toml','--example','nplayer_overnight'])
        native=root/'target/release/examples/nplayer_overnight'
        guard.write(root/'native-binary.json',dict(path=str(native),sha256=guard.sha(native)))
        stage('native-tests',['cargo','test','--release','--locked','--offline','--manifest-path',src/'native/hu20-trainer/Cargo.toml','--lib','--','--test-threads=1'])
        def train(label,seed,targets,probe_nodes,blocks,input_model,reference=False):
            s.seed=seed
            config=dict(seed=seed,threads=16,tables=c['tables'],input=input_model['checkpoint'],input_sha256=input_model['checkpoint_sha256'],
                out=str(root/label),targets=targets,probe_nodes=probe_nodes,probe_blocks=blocks,probe_root=20261018348001+SEEDS.index(seed)*10,stop_file=str(root/'STOP'))
            if reference:config.update(reference=input_model['path'],reference_sha256=input_model['sha256'])
            path=root/(label+'-config.json');guard.write(path,config)
            result=stage(label,[native,path]);preserve(root,cache,[label,label+'-config.json'])
            return result
        anchor=c['anchors'][str(SEEDS[0])];start=c['anchor_nodes'][str(SEEDS[0])];target=start+200_000_000
        control_path=root/'qualification-control.gz'
        control=stage('qualification-control',[c['legacy_train'],'--players','3','--stack-bb','20',
            '--card-buckets',c['tables'],'--seed',str(SEEDS[0]),'--nodes',str(target),
            '--max-entries','150000000','--last-average-street','3','--max-seconds','600',
            '--fast','--threads','16','--resume',anchor['checkpoint'],'--resume-sha256',anchor['checkpoint_sha256'],
            '--out',control_path])
        preserve(root,cache,[control_path.name])
        monitored=train('qualification-monitored',SEEDS[0],[target],[0],128,anchor,True)
        a=next(e for e in control['events'] if 'sha256' in e and 'stop_reason' in e)
        if a['stop_reason']!='nodes':raise ValueError('legacy qualification stopped early')
        b=next(e for e in monitored['events'] if e.get('event')=='checkpoint')
        if a['sha256']!=b['sha256']:raise ValueError('monitoring changes training state')
        trained=next(e for e in monitored['events'] if e.get('event')=='trained')
        rate=(trained['nodes']-start)/trained['active_seconds']
        active=sum(30_000_000_000-n for n in c['anchor_nodes'].values())/rate
        # Seven probes per seed including the anchor; mature saves get3x allowance.
        monitoring=trained['monitor_seconds']*21
        serialization=b['save_seconds']*27
        projected=1.25*(active+monitoring+serialization)+3600
        estimate=dict(projected_remaining_seconds=projected,nodes_per_second=rate,active_seconds=active,
            monitoring_seconds=monitoring,save_allowance_seconds=serialization,final_allowance_seconds=3600,
            remaining_seconds=launch['epoch']+MAX_SECONDS-time.time())
        guard.write(root/'cost-quote.json',estimate)
        if monitoring/active>.1 or projected>estimate['remaining_seconds']:raise RuntimeError('overnight cost admission refused')
        stage('probe-proof',[c['python'],'-m','scripts.nplayer_overnight','verify',root])
        # Qualify the complete final matrix with two blocks and existing averages only.
        models={f'{label}-{seed}':dict(c['anchors'][str(seed)],strategy='average',scope=3)
                for seed in SEEDS for label in ('final','anchor')}
        smoke=root/'smoke';smoke.mkdir()
        m=dict(arena=c['arena'],arena_sha256=c['arena_sha256'],tables=c['tables'],models=models,smoke=True,cases=cases(True))
        guard.write(smoke/'evaluation-manifest.json',m)
        stage('matrix-smoke',[c['python'],'-m','scripts.nplayer_overnight','batch',smoke])
        preserve(root,cache,['smoke','probe-proof'])
        estimate['remaining_seconds']=launch['epoch']+MAX_SECONDS-time.time()
        guard.write(root/'cost-quote.json',estimate)
        if projected>estimate['remaining_seconds']:raise RuntimeError('post-qualification cost admission refused')
        guard.write(root/'pretraining-freeze.json',dict(status='qualified',seeds=SEEDS,targets=TARGETS,quote=estimate,cases=cases(),source_commit=c['source_commit']))
        for seed in SEEDS:
            result=train(f'training-{seed}',seed,list(TARGETS),[0,5_000_000_000,10_000_000_000,15_000_000_000,20_000_000_000,25_000_000_000,30_000_000_000],128,c['anchors'][str(seed)])
            cp=[e for e in result['events'] if e.get('event')=='checkpoint'][-1]
            output=root/f'final-{seed}-average.gz'
            stage(f'export-{seed}',[c['policy'],'export',cp['path'],cp['sha256'],'average',output])
            stage(f'audit-{seed}',[c['python'],'-m','scripts.audit_nplayer_policy',cp['path'],output])
            models[f'final-{seed}']=dict(path=str(output),sha256=guard.sha(output),strategy='average',scope=3,checkpoint=cp['path'],checkpoint_sha256=cp['sha256'])
            preserve(root,cache,[output.name])
        m.update(smoke=False,cases=cases(),models=models)
        guard.write(root/'evaluation-manifest.json',m)
        stage('final-evaluation',[c['python'],'-m','scripts.nplayer_overnight','batch',root])
        guard.write(root/'status.json',dict(status='verified-readout-ready',at=time.time()))
        stage('readout',[c['python'],'-m','scripts.nplayer_overnight','read',root],keep_status=True)
        guard.write(root/'status.json',dict(status='complete',at=time.time()))
        logs.close()
        preserve(root,cache,['evaluation','tensorboard']+[p.name for p in root.glob('*.json')])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=('run','batch','read','verify'));parser.add_argument('root',type=Path);args=parser.parse_args()
    try:
        globals()[args.mode](args.root)
    except BaseException as error:
        failure=dict(error=repr(error),at=time.time())
        if hasattr(error,'resource_sample'):failure['resource_sample']=error.resource_sample
        guard.write(args.root/'failure.json',failure)
        if args.mode=='run':
            try:
                cache=Path(load(args.root/'config.json')['cache'])
                preserve(args.root,cache,[p.name for p in args.root.iterdir() if p.name not in ('source','target')])
            except BaseException as preservation_error:
                guard.write(args.root/'preservation-failure.json',dict(error=repr(preservation_error)))
        raise
