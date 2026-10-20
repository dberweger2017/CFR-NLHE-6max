"""Owner-approved exact mature inference validation. Never trains or retries science."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import sys
import time

MODULE = 'scripts.nplayer_inference_validation'
SOURCE = Path(__file__).resolve().parents[1]
SEED = 202610200601


def load(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    tmp = path.with_name(path.name+'.writing')
    with tmp.open('w') as f:
        json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def copy_pinned(source, target, expected):
    source,target=Path(source),Path(target)
    target.parent.mkdir(parents=True,exist_ok=True)
    h=hashlib.sha256()
    with source.open('rb') as src,target.open('xb') as dst:
        for b in iter(lambda:src.read(4*1024**2),b''):
            h.update(b);dst.write(b)
        dst.flush();os.fsync(dst.fileno())
    if h.hexdigest()!=expected or sha(target)!=expected:
        raise ValueError('restored input hash differs; partial retained')


def child(folder, command):
    """wait4 gives per-command RSS/faults, rather than cumulative max RSS."""
    folder=Path(folder);start=time.monotonic()
    with (folder/'process.stdout').open('xb') as out,(folder/'process.stderr').open('xb') as err:
        pid=os.posix_spawn(command[0],command,os.environ,file_actions=[
            (os.POSIX_SPAWN_DUP2,out.fileno(),1),(os.POSIX_SPAWN_DUP2,err.fileno(),2)])
        _,status,r=os.wait4(pid,0)
    code=os.waitstatus_to_exitcode(status)
    value=dict(returncode=code,wall_seconds=time.monotonic()-start,cpu_seconds=r.ru_utime+r.ru_stime,
        peak_rss_bytes=r.ru_maxrss if sys.platform=='darwin' else r.ru_maxrss*1024,
        minor_faults=r.ru_minflt,major_faults=r.ru_majflt,inblocks=r.ru_inblock,outblocks=r.ru_oublock)
    write(folder/'process.json',value);print(json.dumps(value),flush=True)
    if code:raise SystemExit(code if code>0 else 128-code)


def same_trace(left,right):
    """Only derivative artifact hashes in the header may differ."""
    with Path(left).open('rb') as a,Path(right).open('rb') as b:
        ha,hb=json.loads(next(a)),json.loads(next(b))
        for header in (ha,hb):
            for pin in header['policies']:pin.pop('sha256',None)
        if ha!=hb:raise ValueError('trace header identity changed')
        count=0
        while True:
            x,y=a.readline(),b.readline()
            if x!=y:raise ValueError(f'hand bytes differ at {count}')
            if not x:break
            count+=1
        if count!=ha['hands']:raise ValueError('trace hand count differs')
    return count


def check_job(root):
    from scripts.nplayer_bb100_continuation import check_case
    root=Path(root);m=load(root/'evaluation-manifest.json')
    with ProcessPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(check_case,[(str(root),case,m) for case in m['cases']]))
    value=dict(status='passed',cases=len(results),hands=sum(r['hands'] for r in results))
    write(root/'evaluation-verified.json',value)
    print(json.dumps(value),flush=True)


def stage(root, cache, files):
    from scripts.nplayer_bb100_confirmation import stage_files
    stage_files(Path(root),Path(cache),[Path(p) for p in files])


def job(root, name, models, tables, cases, keyset):
    folder=root/name;folder.mkdir()
    m=dict(models=models,tables=tables,cases=cases,smoke=False)
    write(folder/'evaluation-manifest.json',m)
    native=dict(tables=tables,threads=8,models=models,cases=[],diagnostics=True,
        keyset_sha256=keyset)
    for case in cases:
        d=folder/'evaluation'/case['name'];d.mkdir(parents=True)
        for repeat in (0,1):
            native['cases'].append(dict(name=f"{case['name']}-{repeat}",players=case['players'],
                blocks=case['blocks'],root=case['root'],trace=str(d/f'play-{repeat}.jsonl'),
                summary=str(d/f'play-{repeat}.json')))
    write(folder/'native.json',native)
    return folder,native


def materialize(root):
    root=Path(root);config=load(root/'config.json')
    for task in config['restore']:
        copy_pinned(task['source'],task['target'],task['sha256'])
    print(json.dumps(dict(status='passed',files=len(config['restore']))))


def run(root):
    from scripts import nplayer_pruning_strength as prior
    from scripts import run_nplayer_storage_benchmark as guard
    from scripts.nplayer_bb100_confirmation import matrix
    root=Path(root).absolute();c=load(root/'config.json')
    if (root/'launch.json').exists():raise ValueError('existing launch; no automatic retry')
    if c['authorization']!='owner-20261020-merge-one-run-two' or c['cases']!=matrix(0,c['smoke']):
        raise ValueError('fixed authorization or matrix changed')
    with Path('/tmp/cfr-nplayer-inference-validation.lock').open('a') as own,Path('/tmp/cfr-cygnus-exclusive.lock').open('a') as normal:
        for f in (own,normal):fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        supervisor=prior.Supervisor(root,own.fileno(),normal.fileno())
        env=dict(os.environ,PYTHONPATH=str(SOURCE),RAYON_NUM_THREADS='8',CARGO_BUILD_JOBS='4')
        def execute(label,command):
            write(root/'status.json',dict(status='running',phase=label,at=time.time()))
            folder=root/'measurements'/label
            supervisor.execute(label,[sys.executable,'-m',MODULE,'child',str(folder),'--',*map(str,command)],str(SOURCE),env)
            value=load(folder/'process.json')
            if value['returncode']!=0:raise ValueError('failed child')
            return value
        def native(label,*args):
            execute(label,[c['inference'],*args])
            return load(root/'measurements'/label/'process.stdout')
        def stage_list(label,files):
            manifest=root/(label+'.json');write(manifest,list(map(str,files)))
            execute(label,[sys.executable,'-m',MODULE,'stage',str(root),c['cache'],str(manifest)])
        try:
            admission=supervisor.sample(None,'admission',0)
            write(root/'admission.json',admission)
            write(root/'launch.json',dict(pid=os.getpid(),at=time.time(),config_sha256=sha(root/'config.json'),source=c['source_commit']))
            execute('build',['/home/dberweger/.cargo/bin/cargo','build','--release','--locked','--manifest-path',str(SOURCE/'native/hu20-trainer/Cargo.toml'),'--example','nplayer_inference','--example','nplayer_continuation_arena'])
            execute('native-qualification',['/home/dberweger/.cargo/bin/cargo','test','--locked','--manifest-path',str(SOURCE/'native/hu20-trainer/Cargo.toml'),'--lib','multi_binary::tests'])
            execute('restore',[sys.executable,'-m',MODULE,'materialize',str(root)])
            write(root/'binary-pins.json',{p:sha(c[p]) for p in ('inference','arena')})
            # Fixed JSON-first whole-job order lowers peak working storage. Both
            # jobs use the same source, matrix, workers, replay and cache policy.
            a,manifest=job(root,'gzip-job',c['models'],c['tables'],c['cases'],c['keyset'])
            execute('gzip-job',[c['arena'],'batch',str(a/'native.json')])
            execute('gzip-job-replay',[sys.executable,'-m',MODULE,'check-job',str(a)])
            stage_list('stage-gzip-job',[Path(row['trace']) for row in manifest['cases']])
            binary_models={};conversions={};audits={};first_actions={};loads=[]
            for alias,model in c['models'].items():
                out=root/'inputs'/f'{alias}.bin'
                conversions[alias]=native('convert-'+alias,'convert',model['path'],model['sha256'],out,'--mass',str(Path(model['mass'])/'receipt.json'),model['mass_sha256'])
                pin=conversions[alias]['sha256']
                binary_models[alias]=dict(model,path=str(out),sha256=pin)
                audits[alias]=native('audit-'+alias,'verify',model['path'],model['sha256'],out,pin,'--mass',str(Path(model['mass'])/'receipt.json'),model['mass_sha256'])
                for i,(name,p) in enumerate([(name,p) for _ in range(3) for name,p in [('gzip-json',model),('binary',binary_models[alias])]]):
                    r=native(f'load-{alias}-{i}','load',p['path'],p['sha256']);loads.append(dict(alias=alias,order=i,**r))
                for name,p in [('gzip-json',model),('binary',binary_models[alias])]:
                    first_actions[alias+'-'+name]=native(f'first-{alias}-{name}','first-action',c['tables'],p['path'],p['sha256'])
                if first_actions[alias+'-gzip-json']['action']!=first_actions[alias+'-binary']['action']:
                    raise ValueError('first action changed')
            profile=native('legacy-profile','load',c['models']['baseline']['path'],c['models']['baseline']['sha256'],'--profile')
            # Only new working copies relocate; original PR357 inputs stay put.
            stage_list('stage-gzip-inputs',[Path(p['path']) for p in c['models'].values()])
            b,bmanifest=job(root,'binary-job',binary_models,c['tables'],c['cases'],c['keyset'])
            execute('binary-job',[c['arena'],'batch',str(b/'native.json')])
            execute('binary-job-replay',[sys.executable,'-m',MODULE,'check-job',str(b)])
            execute('compare-hand-rows',[sys.executable,'-m',MODULE,'compare-jobs',str(a),str(b)])
            stage_list('stage-binary-job',[Path(row['trace']) for row in bmanifest['cases']])
            medians={alias:{fmt:statistics.median(r['total_seconds'] for r in loads if r['alias']==alias and r['format']==fmt)
                for fmt in ('gzip-json','binary')} for alias in c['models']}
            ratios={a:v['gzip-json']/v['binary'] for a,v in medians.items()}
            costs={name:load(root/'measurements'/name/'process.json') for name in ('gzip-job','binary-job','gzip-job-replay','binary-job-replay')}
            walls={fmt:costs[fmt+'-job']['wall_seconds']+costs[fmt+'-job-replay']['wall_seconds'] for fmt in ('gzip','binary')}
            files={a:dict(bytes=Path(m['path']).stat().st_size,allocated_bytes=Path(m['path']).stat().st_blocks*512) for a,m in binary_models.items()}
            result=dict(status='settled',source=c['source_commit'],config_sha256=sha(root/'config.json'),conversions=conversions,
                audits=audits,loads=loads,medians=medians,load_speedups=ratios,first_actions=first_actions,profile=profile,
                complete_job_wall_seconds=walls,costs=costs,binary_files=files,models=binary_models,
                load_gate=all(v>=2 for v in ratios.values()),whole_job_gate=walls['binary']<walls['gzip'],
                parity=load(b/'comparison.json'),completed=time.time(),
                limits='One seed/pair/host, fixed JSON-first order, ordinary caches; conversion/audit and staging separate, no strength claim.')
            write(root/'results.json',result)
            stage_list('stage-final-derivatives',[Path(p['path']) for p in binary_models.values()])
            write(root/'status.json',dict(status='complete',at=time.time(),result_sha256=sha(root/'results.json')))
        except BaseException as error:
            write(root/'failure.json',dict(error=repr(error),at=time.time(),phase=load(root/'status.json') if (root/'status.json').exists() else 'admission'))
            raise


def configure(root, cache, source_commit, smoke=False):
    from scripts.nplayer_bb100_confirmation import matrix
    root=Path(root).absolute();root.mkdir(parents=True,exist_ok=False)
    if smoke:
        return configure_fixture(root,cache,source_commit)
    v=load(SOURCE/'docs/reports/nplayer-bb100-confirmation/results.json')
    endpoints=[e for e in v['endpoints'] if e['seed']==SEED]
    restore=[];models={}
    for endpoint in endpoints:
        alias=endpoint['alias'];old=endpoint['model'];model=dict(old)
        model['path']=str(root/'inputs'/f'{alias}.gz');model['mass']=str(root/'inputs'/f'{alias}-mass')
        restore.append(dict(source=old['path'],target=model['path'],sha256=old['sha256']))
        receipt=next(a for a in v['mass_audits'] if a['seed']==SEED and a['alias']==alias)
        restore.extend([dict(source=str(Path(old['mass'])/name),target=str(Path(model['mass'])/name),sha256=pin)
            for name,pin in [('receipt.json',old['mass_sha256']),('zero-keys.bin',receipt['zero_keys_sha256'])]])
        models[alias]=model
    target=SOURCE/'native/hu20-trainer/target/release/examples'
    write(root/'config.json',dict(authorization='owner-20261020-merge-one-run-two',source_commit=source_commit,
        cache=str(Path(cache).absolute()),models=models,restore=restore,cases=matrix(0),smoke=False,
        keyset='d2e9bbadb39aa5f6504b077cdfd764fd5f41c4407706f9f5b6124325154a10a3',
        tables='/home/dberweger/cygnus-qualification-20261014/tables',inference=str(target/'nplayer_inference'),arena=str(target/'nplayer_continuation_arena')))



def configure_fixture(root,cache,source_commit):
    from scripts.benchmark_nplayer_inference import fixture
    from scripts.nplayer_bb100_confirmation import matrix
    source=root/'fixture-inputs';source.mkdir()
    policy=source/'policy.gz';keys=fixture(policy,1000);pin=sha(policy)
    keyset=hashlib.sha256(b''.join(keys)).hexdigest()
    mass=source/'mass';mass.mkdir();(mass/'zero-keys.bin').write_bytes(b'')
    receipt=dict(format='nplayer-average-mass-v1',status='passed',strategy='average',last_average_street=3,
        checkpoint_sha256='a'*64,policy_sha256=pin,rows=1000,average_rows=1000,current_rows=0,
        zero_mass_rows=0,positive_mass_rows=1000,keyset_sha256=keyset,zero_keys_sha256=sha(mass/'zero-keys.bin'))
    write(mass/'receipt.json',receipt)
    models={};restore=[]
    for alias in ('baseline','candidate'):
        model=dict(path=str(root/'inputs'/f'{alias}.gz'),sha256=pin,mass=str(root/'inputs'/f'{alias}-mass'),
            mass_sha256=sha(mass/'receipt.json'),checkpoint_sha256='a'*64)
        models[alias]=model
        restore.append(dict(source=str(policy),target=model['path'],sha256=pin))
        restore.extend(dict(source=str(mass/name),target=str(Path(model['mass'])/name),sha256=sha(mass/name)) for name in ('receipt.json','zero-keys.bin'))
    target=SOURCE/'native/hu20-trainer/target/release/examples'
    write(root/'config.json',dict(authorization='owner-20261020-merge-one-run-two',source_commit=source_commit,smoke=True,
        cache=str(Path(cache).absolute()),models=models,restore=restore,cases=matrix(0,True),keyset=keyset,
        tables='/home/dberweger/cygnus-qualification-20261014/tables',inference=str(target/'nplayer_inference'),arena=str(target/'nplayer_continuation_arena')))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode');p.add_argument('args',nargs=argparse.REMAINDER);a=p.parse_args();args=a.args
    if a.mode=='configure':configure(*args[:3],smoke=len(args)==4 and args[3]=='--smoke')
    elif a.mode=='run':run(*args)
    elif a.mode=='child':child(args[0],args[2:] if args[1]=='--' else args[1:])
    elif a.mode=='materialize':materialize(*args)
    elif a.mode=='check-job':check_job(*args)
    elif a.mode=='stage':stage(args[0],args[1],load(args[2]))
    elif a.mode=='compare-jobs':
        left,right=map(Path,args);m=load(left/'evaluation-manifest.json')
        rows={c['name']:same_trace(left/'evaluation'/c['name']/'play-0.jsonl',right/'evaluation'/c['name']/'play-0.jsonl') for c in m['cases']}
        write(right/'comparison.json',dict(status='passed',hands=sum(rows.values()),cases=rows))
    else:p.error('unknown mode')


if __name__=='__main__':main()
