"""PR367: fixed fresh acceptance, never training, selecting or retrying models."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import statistics
import subprocess
import sys
import time

from scripts import nplayer_bb100_continuation as diagnostic
from scripts import nplayer_bb100_overnight as generic
from scripts import nplayer_inference_validation as io
from scripts import nplayer_pruning_strength as thermal

SOURCE = Path(__file__).resolve().parents[1]
MODULE = 'scripts.nplayer_v06_acceptance'
SEEDS = (2026101935003, 202610200601, 202610200602)
SIZING = 'configs/research/nplayer-v06-acceptance-sizing.json'
INPUTS = 'configs/research/nplayer-v06-acceptance-inputs.json'
BINARY_NAMES = ('nplayer_inference', 'nplayer_continuation_arena', 'nplayer_arena')
FAMILY = 30


def matrix(smoke=False):
    rows = []
    templates = {c.get('opponent'): c['players'][1:] for c in diagnostic.cases(True) if c.get('opponent')}
    for i, gate in enumerate(io.load(SOURCE/SIZING)['rows']):
        common = dict(gate=gate['gate'], seed=int(gate['seed']), blocks=2 if smoke else gate['blocks'],
                      root=(20261020367901 if smoke else 20261020367001)+i)
        seed = common['seed']
        if gate['gate'] == 'script-profit':
            rows.append(dict(common, name=f'{seed}-{gate["name"]}', opponent=gate['name'],
                             players=['candidate']+templates[gate['name']], phase=f'own-{seed}'))
        elif gate['gate'] == 'direct':
            for n, players in enumerate((['candidate','baseline','baseline'], ['baseline','candidate','candidate'])):
                rows.append(dict(common, name=f'{seed}-direct-{n}', players=players, phase=f'own-{seed}'))
        elif gate['gate'] == 'cross':
            other = int(gate['name'])
            for alias in ('candidate', 'baseline'):
                rows.append(dict(common, name=f'cross-{seed}-{alias}', opponent_seed=other,
                    singleton=f'{alias}-{seed}', pair=f'baseline-{other}', phase=f'cross-{seed}-{alias}'))
        else:
            raise ValueError('unknown gate')
    return rows


def phases(smoke=False):
    rows = matrix(smoke)
    names = [f'own-{s}' for s in SEEDS]
    names += [f'cross-{s}-{a}' for s in SEEDS for a in ('candidate','baseline')]
    return [(name, [r for r in rows if r['phase'] == name]) for name in names]


def source_pins():
    deployed = SOURCE/'.acceptance-source-pins.json'
    if deployed.exists():
        return {p:io.sha(SOURCE/p) for p in io.load(deployed)}
    paths = subprocess.check_output(['git','ls-files','scripts','src','native/hu20-trainer','native/hu20-buckets',
        'requirements.txt','tests/test_nplayer_v06_acceptance.py',SIZING,INPUTS,'docs/nplayer-v06-acceptance.md'],cwd=SOURCE,text=True).splitlines()
    return {p:io.sha(SOURCE/p) for p in paths}


def validate_config(c):
    if (c['authorization'] != 'owner-20261020-fresh-v06-acceptance' or c['cases'] != matrix(c['smoke'])
            or c['threads'] != 8 or c['family'] != FAMILY or c['cross_margin_bb100'] != -5
            or c['resource_policy'] != thermal.RESOURCE_POLICY or c['source_files'] != source_pins()):
        raise ValueError('frozen protocol/source/configuration differs')
    if not c['smoke'] and c['catalog'] != io.load(SOURCE/INPUTS):
        raise ValueError('frozen model catalog changed')
    for name, pin in c['binaries'].items():
        if name not in BINARY_NAMES or io.sha(pin['path']) != pin['sha256']:
            raise ValueError('frozen native binary changed')
    if set(c['binaries']) != set(BINARY_NAMES):
        raise ValueError('missing native binary')
    if thermal.python_environment(Path(c['python']))[1] != c['environment']:
        raise ValueError('qualified Python environment changed')
    if not c['smoke']:
        q = c['qualification']
        if io.sha(q['path']) != q['sha256']:
            raise ValueError('fixture proof changed')
        f = Path(q['path']).parent
        fc, result = io.load(f/'config.json'), io.load(q['path'])
        if (not fc['smoke'] or fc['source_files'] != c['source_files'] or fc['binaries'] != c['binaries']
                or fc['environment'] != c['environment'] or result['status'] != 'settled'
                or result['initial_hands'] != 432 or len(result['gates']) != 30
                or io.load(f/'status.json')['status'] != 'complete' or (f/'failure.json').exists()):
            raise ValueError('full36-case fixture not qualified')


def log(root, name, value):
    with (root/name).open('a') as f:
        f.write(json.dumps(value,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())


def owned_stage(root, cache, paths):
    """Copy unique new data, or release a verified restored duplicate to its cache.

    Only this study's paths may be replaced. Original research inputs are never
    selected. Existing cache bytes must match; partial/different destinations stop.
    """
    root,cache=Path(root).absolute(),Path(cache).absolute()
    if root==cache or root in cache.parents or cache in root.parents:
        raise ValueError('owned cache must be a separate directory')
    for p in map(Path,paths):
        p=p.absolute();relative=p.relative_to(root);dest=cache/relative
        if not p.parent.resolve().is_relative_to(root.resolve()):
            raise ValueError('staging source escapes owned root')
        if p.is_symlink():
            if p.resolve()!=dest.resolve() or not dest.is_file():raise ValueError('foreign/broken staging link')
            continue
        if not dest.exists():
            diagnostic_stage(root,cache,p)
            continue
        if not dest.parent.resolve().is_relative_to(cache.resolve()):
            raise ValueError('cache destination escapes owned cache')
        before=p.stat();pin=io.sha(p)
        if not dest.is_file() or dest.is_symlink() or dest.stat().st_size!=before.st_size or io.sha(dest)!=pin:
            raise ValueError('existing cache/partial differs; retain both')
        if p.stat().st_mtime_ns!=before.st_mtime_ns or io.sha(p)!=pin:
            raise ValueError('restored working copy changed')
        log(root,'relocations.jsonl',dict(source=str(p),destination=str(dest),sha256=pin,bytes=before.st_size,
            at=time.time(),reused_verified_cache=True,drive_accepted=False))
        link=p.with_name(p.name+'.staged-link');os.symlink(dest,link);os.replace(link,p)
        sync_directory(p.parent)


def diagnostic_stage(root,cache,p):
    from scripts.nplayer_bb100_confirmation import stage_files
    stage_files(root,cache,[p])


def sync_directory(path):
    fd=os.open(path,os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def restore_owned(root, paths, models):
    """Rehydrate only this run's staged model paths, preserving cached originals."""
    for name in paths:
        model=models[name];p=Path(model['path'])
        if not p.is_symlink():
            if io.sha(p)!=model['sha256']:raise ValueError('working derivative changed')
            continue
        source=p.resolve();cache=Path(io.load(root/'config.json')['cache']).resolve()
        if not source.is_relative_to(cache):raise ValueError('restore link outside owned cache')
        tmp=p.with_name(p.name+'.restoring')
        io.copy_pinned(source,tmp,model['sha256'])
        os.replace(tmp,p);sync_directory(p.parent)
        log(root,'restorations.jsonl',dict(path=str(p),cache=str(source),sha256=model['sha256'],at=time.time()))


def verify_mass(model, expected, original_sha):
    folder=Path(model['mass']);r=io.load(folder/'receipt.json')
    # Snapshot may contain explanatory fields absent in native receipts.
    fields=('format','status','checkpoint_sha256','policy_sha256','strategy','last_average_street',
        'rows','average_rows','current_rows','zero_mass_rows','positive_mass_rows','keyset_sha256','zero_keys_sha256')
    if (io.sha(folder/'receipt.json')!=model['mass_sha256'] or any(r[k]!=expected[k] for k in fields)
            or r['policy_sha256']!=original_sha or r['checkpoint_sha256']!=model['checkpoint_sha256']
            or r['rows']!=r['positive_mass_rows']+r['zero_mass_rows'] or r['average_rows']!=r['rows']
            or r['current_rows']!=0 or r['strategy']!='average' or r['last_average_street']!=3
            or (folder/'zero-keys.bin').stat().st_size!=16*r['zero_mass_rows']
            or io.sha(folder/'zero-keys.bin')!=r['zero_keys_sha256']):
        raise ValueError('mass metadata/lineage differs')


def prepare_seed(root,c,seed,execute):
    models=io.load(root/'models.json') if (root/'models.json').exists() else {}
    for alias,x in c['catalog'][str(seed)].items():
        folder=root/'inputs'/str(seed);folder.mkdir(parents=True,exist_ok=True)
        source=x['source'];mass=folder/(alias+'-mass');mass.mkdir()
        for file,pin in [('receipt.json',source['mass_sha256']),('zero-keys.bin',x['mass']['zero_keys_sha256'])]:
            execute(f'mass-{seed}-{alias}-{file}',[sys.executable,'-m',MODULE,'copy',str(Path(source['mass'])/file),str(mass/file),pin])
        model=dict(source,path=str(folder/(alias+'.bin')),mass=str(mass))
        verify_mass(model,x['mass'],source['sha256'])
        if x['binary']:
            audit=x['audit']
            if (audit['status']!='passed' or audit['binary_sha256']!=x['binary']['sha256']
                    or audit['source_policy_sha256']!=source['sha256'] or audit['rows']!=x['mass']['rows']):
                raise ValueError('reused derivative audit differs')
            execute(f'restore-{seed}-{alias}',[sys.executable,'-m',MODULE,'copy',x['binary']['path'],model['path'],x['binary']['sha256']])
            model['sha256']=x['binary']['sha256']
            io.write(folder/(alias+'-audit.json'),dict(audit,reused=True))
        else:
            gz=folder/(alias+'.gz')
            execute(f'restore-{seed}-{alias}',[sys.executable,'-m',MODULE,'copy',source['path'],str(gz),source['sha256']])
            command=[c['binaries']['nplayer_inference']['path'],'convert',str(gz),source['sha256'],model['path'],
                '--mass',str(mass/'receipt.json'),source['mass_sha256']]
            execute(f'convert-{seed}-{alias}',command)
            converted=io.load(root/'measurements'/f'convert-{seed}-{alias}'/'process.stdout')
            model['sha256']=converted['sha256']
            execute(f'audit-{seed}-{alias}',[c['binaries']['nplayer_inference']['path'],'verify',str(gz),source['sha256'],
                model['path'],model['sha256'],'--mass',str(mass/'receipt.json'),source['mass_sha256']])
            audit=io.load(root/'measurements'/f'audit-{seed}-{alias}'/'process.stdout')
            if (audit['status']!='passed' or audit['rows']!=x['mass']['rows']
                    or audit['source_policy_sha256']!=source['sha256'] or audit['binary_sha256']!=model['sha256']):
                raise ValueError('full-row audit failed')
            io.write(folder/(alias+'-audit.json'),audit)
            staging(root,c,execute,f'stage-source-{seed}-{alias}',[gz])
        models[f'{alias}-{seed}']=model
        io.write(root/'models.json',models)
    a,b=(c['catalog'][str(seed)][alias]['mass'] for alias in ('baseline','candidate'))
    if a['keyset_sha256']!=b['keyset_sha256'] or a['rows']!=b['rows']:
        raise ValueError('within-seed membership differs')
    return models


def staging(root,c,execute,label,paths):
    selection=root/(label+'.json');io.write(selection,list(map(str,paths)))
    execute(label,[sys.executable,'-m',MODULE,'stage',str(root),str(selection)])


def make_job(root,c,name,rows,models):
    job=root/'jobs'/name;job.mkdir(parents=True)
    own=name.startswith('own-')
    if own:
        seed=rows[0]['seed'];ms={a:models[f'{a}-{seed}'] for a in ('baseline','candidate')}
        keyset=c['catalog'][str(seed)]['baseline']['mass']['keyset_sha256']
    else:
        ms={k:models[k] for k in (rows[0]['singleton'],rows[0]['pair'])};keyset=None
    manifest=dict(models=ms,cases=rows,tables=c['tables'],kind='own' if own else 'cross',keyset_sha256=keyset)
    io.write(job/'evaluation-manifest.json',manifest)
    native=dict(tables=c['tables'],threads=8,cases=[],stack_bb=100,models=ms,diagnostics=True,keyset_sha256=keyset)
    for case in rows:
        folder=job/'evaluation'/case['name'];folder.mkdir(parents=True)
        for repeat in (0,1):
            entry=dict(name=f'{case["name"]}-{repeat}',blocks=case['blocks'],root=case['root'],
                       trace=str(folder/f'play-{repeat}.jsonl'),summary=str(folder/f'play-{repeat}.json'))
            if own:entry['players']=case['players']
            else:
                entry.update(singleton=generic.spec(case['singleton'],ms),pair=generic.spec(case['pair'],ms))
            native['cases'].append(entry)
    io.write(job/'native.json',native)
    return job,manifest


def verify_job(job):
    m=io.load(job/'evaluation-manifest.json');native=io.load(job/'native.json')
    summaries=[io.load(x['summary']) for x in native['cases']]
    if (sum(x['new_weight_tables'] for x in summaries)!=2
            or any(x['resident_weight_tables']!=2 or x['resident_card_table_sets']!=1 for x in summaries)):
        raise ValueError('two-model residency/load count differs')
    with ProcessPoolExecutor(max_workers=8) as pool:
        fn=diagnostic.check_case if m['kind']=='own' else generic.check_case
        tasks=[(str(job),r,m) if m['kind']=='own' else (r,m,str(job)) for r in m['cases']]
        futures=[pool.submit(fn,t) for t in tasks]
        for i,future in enumerate(as_completed(futures),1):
            try:future.result()
            except BaseException:
                print(json.dumps(dict(event='fatal',error='reproduction/replay/lookup proof failed')),flush=True);raise
            print(json.dumps(dict(event='progress',verified=i,total=len(tasks))),flush=True)
    io.write(job/'evaluation-verified.json',dict(status='passed',manifest_sha256=io.sha(job/'evaluation-manifest.json'),
        cases=len(m['cases']),hands=sum(r['blocks']*6 for r in m['cases']),
        native_load_seconds=sum(x['load_seconds'] for x in summaries),native_play_seconds=sum(x['play_seconds'] for x in summaries),
        trace_bytes=sum(Path(x['trace']).stat().st_size for x in native['cases'])))


def verify_barrier(root,c):
    if (root/'failure.json').exists():raise ValueError('terminal failure; no settled readout')
    proofs={};coverage={}
    for name,rows in phases(c['smoke']):
        job=root/'jobs'/name;m=io.load(job/'evaluation-manifest.json');proof=io.load(job/'evaluation-verified.json')
        if (m['cases']!=rows or proof['status']!='passed' or proof['cases']!=len(rows)
                or proof['hands']!=sum(r['blocks']*6 for r in rows)
                or proof['manifest_sha256']!=io.sha(job/'evaluation-manifest.json')):
            raise ValueError('global verified manifest/count barrier differs')
        for case in rows:
            folder=job/'evaluation'/case['name'];r=io.load(folder/'result.json');p=io.load(folder/'replay.json')
            digest=io.sha(folder/'play-0.jsonl')
            if (r['status']!='passed' or r['case']!=case or r['hands']!=case['blocks']*6 or r['trace_sha256']!=digest
                    or p['status']!='passed' or p['hands']!=case['blocks']*6 or p['trace_sha256']!=digest
                    or io.sha(folder/'play-1.jsonl')!=digest):
                raise ValueError('global trace/reproduction/replay barrier differs')
            coverage[case['name']]=io.load(folder/'play-0.json')
        proofs[name]=proof
    for folder in (root/'measurements').iterdir():
        if folder.name=='global-readout':continue
        if io.load(folder/'process.json')['returncode']!=0 or io.load(folder/'result.json')['returncode']!=0:
            raise ValueError('failed/unsettled prior stage')
    return proofs,coverage


def lower_bound(values,margin,family=FAMILY):
    from scipy.stats import t
    from scripts.analyze_nplayer_arena import interval
    if len(values)<2 or not all(math.isfinite(v) for v in values):raise ValueError('invalid statistical blocks')
    score=interval(values);critical=float(t.ppf(1-.05/family,len(values)-1))
    lower=score['mean_bb100']-critical*score['standard_error_bb100']
    return dict(score,blocks=len(values),family=family,lower_simultaneous95_bb100=lower,margin_bb100=margin,passed=lower>margin)


def read(root):
    from scripts.read_nplayer_fast_study import paired_blocks
    from scripts.analyze_nplayer_arena import interval
    c=io.load(root/'config.json');validate_config(c)
    if io.load(root/'status.json')['phase']!='global-readout':raise ValueError('global readout stage not entered')
    proofs,coverage=verify_barrier(root,c)
    rows=matrix(c['smoke']);gates=[]
    def trace(case):return root/'jobs'/case['phase']/'evaluation'/case['name']/'play-0.jsonl'
    for i,g in enumerate(io.load(SOURCE/SIZING)['rows']):
        seed=int(g['seed']);selected=[r for r in rows if r['seed']==seed and r['gate']==g['gate']
            and (g['gate']!='script-profit' or r.get('opponent')==g['name'])]
        a=selected[0];b=selected[-1]
        values=list(paired_blocks(trace(a),trace(b),a['root']))
        if len(values)!=a['blocks']:raise ValueError('statistical unit count differs')
        field={'script-profit':'fast_singleton','direct':'advantage','cross':None}[g['gate']]
        data=[v[field] if field else v['fast_singleton']-v['production_singleton'] for v in values]
        detail={}
        for tag in ('seat','position'):
            detail[tag]=[interval([v['fast_by_'+tag][j] if g['gate']=='script-profit' else
                (v['fast_by_'+tag][j]-v['production_by_'+tag][j])/(2 if g['gate']=='direct' else 1)
                for v in values]) for j in range(3)]
        gates.append(dict(index=i,seed=seed,gate=g['gate'],opponent=g['name'],root=a['root'],cases=[r['name'] for r in selected],
                          score=lower_bound(data,g['margin']),descriptive=detail))
    hands=sum(r['blocks']*6 for r in rows)
    costs={p.parent.name:io.load(p) for p in (root/'measurements').glob('*/process.json') if p.parent.name!='global-readout'}
    io.write(root/'evaluation-verified.json',dict(status='passed',initial_hands=hands,reproduction_hands=hands,
        jobs={k:io.sha(root/'jobs'/k/'evaluation-verified.json') for k in proofs}))
    io.write(root/'results.json',dict(status='settled',config_sha256=io.sha(root/'config.json'),initial_hands=hands,
        reproduction_hands=hands,gates=gates,acceptance=all(r['score']['passed'] for r in gates),models=io.load(root/'models.json'),
        coverage=coverage,proofs=proofs,costs=costs,completed=time.time(),
        old_evidence='PR357 relative script/mixed safeguard remains failed/unresolved. Fresh absolute-profit acceptance is a different prospective criterion.',
        limits='Three fixed lineages, one host, conditional power estimates; no Nash, universal strength, human/external strength, release or default claim.'))


def run(root):
    c=io.load(root/'config.json');validate_config(c)
    if (root/'launch.json').exists():raise ValueError('already launched; no automatic retry')
    def interrupt(signum,frame):raise InterruptedError(f'owner signal {signum}')
    signal.signal(signal.SIGTERM,interrupt);signal.signal(signal.SIGINT,interrupt)
    with Path('/tmp/cfr-nplayer-v06-acceptance.lock').open('a') as own,Path('/tmp/cfr-cygnus-exclusive.lock').open('a') as normal:
        for lock in (own,normal):fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        supervisor=thermal.Supervisor(root,own.fileno(),normal.fileno())
        env=dict(os.environ,PYTHONPATH=str(SOURCE),RAYON_NUM_THREADS='8',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
        def execute(label,command):
            if io.load(root/'launch.json')['config_sha256']!=io.sha(root/'config.json'):
                raise ValueError('frozen run configuration changed')
            supervisor.sample(None,label,0)
            io.write(root/'status.json',dict(status='running',phase=label,at=time.time()))
            folder=root/'measurements'/label
            supervisor.execute(label,[sys.executable,'-m','scripts.nplayer_inference_validation','child',str(folder),'--',*map(str,command)],str(SOURCE),env)
            if io.load(folder/'process.json')['returncode']!=0:raise ValueError('failed child')
        try:
            io.write(root/'launch.json',dict(pid=os.getpid(),at=time.time(),config_sha256=io.sha(root/'config.json'),source=c['source_commit']))
            io.write(root/'admission.json',supervisor.sample(None,'admission',0))
            for seed in SEEDS:
                models=prepare_seed(root,c,seed,execute)
                name=f'own-{seed}';rows=next(r for n,r in phases(c['smoke']) if n==name)
                job,_=make_job(root,c,name,rows,models)
                execute(name,[c['binaries']['nplayer_continuation_arena']['path'],'batch',str(job/'native.json')])
                execute(name+'-verify',[sys.executable,'-m',MODULE,'verify-job',str(job)])
                files=[p for p in (job/'evaluation').rglob('*') if p.is_file()]
                files += [Path(models[f'{a}-{seed}']['path']) for a in ('baseline','candidate')]
                staging(root,c,execute,name+'-stage',files)
            for name,rows in phases(c['smoke'])[3:]:
                needed=[rows[0]['singleton'],rows[0]['pair']]
                execute(name+'-restore',[sys.executable,'-m',MODULE,'restore',str(root),*needed])
                job,_=make_job(root,c,name,rows,models)
                execute(name,[c['binaries']['nplayer_arena']['path'],'batch',str(job/'native.json')])
                execute(name+'-verify',[sys.executable,'-m',MODULE,'verify-job',str(job)])
                files=[p for p in (job/'evaluation').rglob('*') if p.is_file()]+[Path(models[n]['path']) for n in needed]
                staging(root,c,execute,name+'-stage',files)
            # All stages and every case must finish before the first payoff read.
            execute('global-readout',[sys.executable,'-m',MODULE,'read',str(root)])
            io.write(root/'status.json',dict(status='complete',at=time.time(),result_sha256=io.sha(root/'results.json')))
        except BaseException as error:
            value=dict(error=repr(error),at=time.time(),phase=io.load(root/'status.json') if (root/'status.json').exists() else 'admission')
            if hasattr(error,'resource_sample'):value['resource_sample']=error.resource_sample
            io.write(root/'failure.json',value);raise


def configure(root,build,cache,python,source_commit,qualification=None,fixture_catalog=None):
    smoke=fixture_catalog is not None
    root.mkdir(parents=True,exist_ok=False)
    if cache.exists():raise ValueError('fresh owned cache required')
    python,environment=thermal.python_environment(python)
    c=dict(authorization='owner-20261020-fresh-v06-acceptance',smoke=smoke,cases=matrix(smoke),threads=8,family=30,
        cross_margin_bb100=-5,resource_policy=thermal.RESOURCE_POLICY,source_files=source_pins(),source_commit=source_commit,
        cache=str(cache),python=str(python),environment=environment,
        tables='/home/dberweger/cygnus-qualification-20261014/tables',
        binaries={name:dict(path=str(build/name),sha256=io.sha(build/name)) for name in BINARY_NAMES},
        catalog=io.load(fixture_catalog) if smoke else io.load(SOURCE/INPUTS),
        qualification=None if smoke else dict(path=str(qualification),sha256=io.sha(qualification)))
    validate_config(c);io.write(root/'config.json',c)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('configure','run','copy','stage','restore','verify-job','read'))
    p.add_argument('paths',nargs='+',type=Path);p.add_argument('--build',type=Path);p.add_argument('--cache',type=Path)
    p.add_argument('--python',type=Path);p.add_argument('--source-commit');p.add_argument('--qualification',type=Path);p.add_argument('--fixture-catalog',type=Path)
    a=p.parse_args();root=a.paths[0].absolute()
    if a.mode=='configure':configure(root,a.build.absolute(),a.cache.absolute(),a.python,a.source_commit,a.qualification,a.fixture_catalog)
    elif a.mode=='copy':io.copy_pinned(a.paths[0],a.paths[1],str(a.paths[2]))
    elif a.mode=='stage':
        c=io.load(root/'config.json')
        if io.load(root/'launch.json')['config_sha256']!=io.sha(root/'config.json'):raise ValueError('staging config changed')
        owned_stage(root,Path(c['cache']),io.load(a.paths[1]))
    elif a.mode=='restore':restore_owned(root,[str(x) for x in a.paths[1:]],io.load(root/'models.json'))
    elif a.mode=='verify-job':verify_job(root)
    else:globals()[a.mode](root)


if __name__=='__main__':main()
