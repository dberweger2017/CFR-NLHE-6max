"""Fixed M4 engineering qualification using retained PR406/408 fixtures only."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from scripts import nplayer_four_player_feasibility as core
from scripts import nplayer_paired_evidence as evidence

SOURCE=Path(__file__).resolve().parents[1]
HOST=Path('/Users/dberweger/Local/nplayer-paired-arena-20261023')
BASE='4b416074584c7b8229ab1abf41a234fbf4237b18'


def source():
    if subprocess.check_output(['git','status','--porcelain'],cwd=SOURCE,text=True).strip():raise ValueError('clean source required')
    names=subprocess.check_output(['git','ls-files','native','scripts','src','tests/test_nplayer_paired_evidence.py','docs/nplayer-paired-arena.md'],cwd=SOURCE,text=True).splitlines()
    return dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip(),files={n:core.sha(SOURCE/n) for n in names})


def prepare(root,build=None,build_source=None):
    build=build or HOST/'build-dev-v1';build_source=build_source or HOST/'source-dev-v1'
    if root.exists():raise FileExistsError('prepared attempt already exists')
    if core.load(build/'status.json')['status']!='passed' or (build/'failure.json').exists():raise ValueError('native development build/tests not passed')
    for name in subprocess.check_output(['git','ls-files','native'],cwd=SOURCE,text=True).splitlines():
        if core.sha(SOURCE/name)!=core.sha(build_source/name):raise ValueError('native source differs from qualified build')
    models={}
    for n in (4,5,6):
        parent=Path('/Users/dberweger/Local/nplayer-four-player-feasibility-20261022') if n==4 else Path('/Users/dberweger/Local/nplayer-five-six-feasibility-20261023')
        for size in ('tiny','cap'):
            folder=parent/('qualification-v1' if size=='tiny' else 'main-v1')
            if n!=4:folder=folder/f'players{n}'
            if (folder/'failure.json').exists():raise ValueError('fixture input failure')
            for i,label in enumerate(('a','b')):
                name=f'fixture-{label}' if size=='tiny' else f'endpoint{(25000000,50000000)[i]}'
                path=folder/(name+'-average.gz');mass=folder/(name+'-mass');receipt=core.load(mass/'receipt.json')
                if receipt['status']!='passed' or core.sha(path)!=receipt['policy_sha256'] or core.sha(mass/'zero-keys.bin')!=receipt['zero_keys_sha256']:raise ValueError('fixture source/mass changed')
                models[f'p{n}-{size}-{label}']=dict(path=str(path),sha256=receipt['policy_sha256'],mass=str(mass),mass_sha256=core.sha(mass/'receipt.json'))
    binary=build/'target/release/examples/nplayer_paired_arena';legacy=binary.with_name('nplayer_arena')
    tables=Path('/Users/dberweger/Local/overnight-equity-hu100-20261009/stage-a/results/equity-bench/tables')
    for name,pin in core.TABLES.items():
        if core.sha(tables/name)!=pin:raise ValueError('K50 changed')
    thermal=Path('/Users/dberweger/Local/nplayer-four-player-feasibility-20261022/qualification-v1/thermal-state')
    root.mkdir(parents=True,exist_ok=False)
    for size in ('tiny','cap'):
        for run in ('initial','repeat','serial') if size=='tiny' else ('initial','repeat'):
            (root/f'{size}-{run}').mkdir()
    config=dict(source=source(),models=models,tables=str(tables),binary=str(binary),binary_sha256=core.sha(binary),legacy=str(legacy),legacy_sha256=core.sha(legacy),
        thermal=str(thermal),thermal_sha256=core.sha(thermal),python=sys.executable,python_sha256=core.sha(sys.executable),base=BASE,native_build=str(build),native_build_source=str(build_source))
    core.write(root/'config.json',config);core.write(root/'catalog.json',models)
    # Already-measured cap-size work plus explicit streaming-tag audit reserve.
    quote=dict(status='quoted',central_seconds=900,reserved_seconds=1800,scope='Fixed tiny/cap cases, reproduction, tiny serial, legacy regression, independent replay and source-mass tag audit; no training',
        basis='PR406/408 cap-size load/play ~15s per model, six cap models per fresh pass; 360s central serial export/tag audit allowance; existing build costs separate; reserve2x; no elapsed-time stop',
        native_build_already_spent_seconds=sum(x['wall_seconds'] for x in core.load(build/'stage-costs.json')),
        no_arena_started=True,no_training=True)
    core.write(root/'quote.json',quote)
    core.write(root/'status.json',dict(status='prepared',no_arena_started=True))


def manifest(root,c,size,run):
    cases=[]
    for n in (4,5,6):
        a,b=(f'p{n}-{size}-{label}' for label in ('a','b'))
        field=[a]+(['bot=check-call','bot=pot-pressure'] if n==4 else ['bot=check-call','bot=tight-aggressive','bot=pot-pressure','bot=random'][:n-2])
        for i,focals in enumerate(([a,a],[a,b])):
            name=f'p{n}-{("self","changed")[i]}';folder=root/f'{size}-{run}'
            cases.append(dict(name=name,players=n,stack_bb=100,blocks=8 if size=='tiny' else 2,
                root=(20261023410000 if size=='tiny' else 20261023420000)+100*n+i,
                focals=focals,opponents=field,traces=[str(folder/f'{name}-{arm}.jsonl') for arm in ('a','b')],summary=str(folder/f'{name}-cost.json')))
    return dict(format='nplayer-paired-manifest-v1',tables=c['tables'],threads=1 if run=='serial' else 4,models=c['models'],cases=cases)


def validate(c):
    if c['source']!=source():raise ValueError('frozen source changed')
    for name in ('binary','legacy','thermal','python'):
        if core.sha(c[name])!=c[name+'_sha256']:raise ValueError('binary/helper/Python changed')
    for name,pin in core.TABLES.items():
        if core.sha(Path(c['tables'])/name)!=pin:raise ValueError('K50 changed')


def run(root,accepted):
    if accepted!=1800:raise ValueError('explicit1800-second qualification planning allowance required')
    if any((root/p).exists() for p in ('launch.json','failure.json','measurements')):raise ValueError('attempt exists; preserve/no retry')
    c=core.load(root/'config.json');validate(c)
    if core.load(root/'quote.json')['reserved_seconds']!=accepted:raise ValueError('quote changed')
    import psutil
    available=psutil.virtual_memory().available
    # Two JSON weights share one K50 set; this is admission only, not a kill.
    forecast=6*2**30
    if forecast+2**30>available:raise ValueError('two-model admission needs6GiB plus1GiB available headroom')
    core.write(root/'launch.json',dict(pid=os.getpid(),epoch=time.time(),source=c['source']['commit'],accepted_planning_seconds=accepted,quote_sha256=core.sha(root/'quote.json'),available_ram_bytes=available,forecast_peak_rss_bytes=forecast))
    env={**os.environ,'PYTHONPATH':str(SOURCE),'RAYON_NUM_THREADS':'4','RUST_TEST_THREADS':'4','CARGO_BUILD_JOBS':'4','NPLAYER_STOP_FILE':str(root/'STOP')}
    sup=core.Supervisor(root,env,Path(c['thermal']));tick=time.monotonic()
    sup.stage('python-tests',[c['python'],'-m','unittest','tests.test_nplayer_paired_evidence','-q'])
    manifests={}
    for size in ('tiny','cap'):
        for phase in ('initial','repeat','serial') if size=='tiny' else ('initial','repeat'):
            validate(c);m=manifest(root,c,size,phase);path=root/f'{size}-{phase}.json';core.write(path,m);manifests[size,phase]=m
            sup.stage(f'{size}-{phase}',[c['binary'],'batch',path])
    proofs=[];pairs=[];initial_traces=[]
    for size in ('tiny','cap'):
        for i,case in enumerate(manifests[size,'initial']['cases']):
            repeat=manifests[size,'repeat']['cases'][i];replay=[]
            for arm,path in enumerate(case['traces']):
                initial_traces.append(path)
                if core.sha(path)!=core.sha(repeat['traces'][arm]):raise ValueError('reproduction differs')
                if size=='tiny' and core.sha(path)!=core.sha(manifests[size,'serial']['cases'][i]['traces'][arm]):raise ValueError('serial/parallel traces differ')
                name=f'{size}-{case["name"]}-{arm}-replay'
                sup.stage(name,[c['python'],'-m','scripts.nplayer_paired_evidence','replay',path]);receipt=root/'measurements'/name/'stdout.log';replay.append(receipt);proofs.append(core.load(receipt))
            name=f'{size}-{case["name"]}-readout'
            sup.stage(name,[c['python'],'-m','scripts.nplayer_paired_evidence','pair',*case['traces'],*repeat['traces'],*replay])
            pairs.append(dict(size=size,name=case['name'],result=core.load(root/'measurements'/name/'stdout.log')))
    sup.stage('independent-mass-tags',[c['python'],'-m','scripts.nplayer_paired_evidence','coverage',root/'catalog.json',*initial_traces])
    # Compare legacy outputs from exactly the base source, in an owned snapshot.
    base=root/'legacy-base';base.mkdir();archive=subprocess.Popen(['git','archive',BASE,'native'],cwd=SOURCE,stdout=subprocess.PIPE)
    unpack=subprocess.run(['tar','-xf','-','-C',str(base)],stdin=archive.stdout);archive.stdout.close()
    if archive.wait() or unpack.returncode:raise RuntimeError('base source extraction failed')
    env['CARGO_TARGET_DIR']=str(root/'legacy-target')
    sup.stage('legacy-base-build',[str(Path.home()/'.cargo/bin/cargo'),'build','--release','--locked','--offline','--manifest-path',base/'native/hu20-trainer/Cargo.toml','--example','nplayer_arena'])
    for depth in (20,100,200):
        paths=[]
        for label,binary in (('base',root/'legacy-target/release/examples/nplayer_arena'),('current',Path(c['legacy']))):
            path=root/f'legacy-{depth}-{label}.jsonl';paths.append(path)
            sup.stage(f'legacy-{depth}-{label}',[binary,c['tables'],2,20261023430000+depth,path,'bot=check-call','bot=pot-pressure',depth,1])
        if core.sha(paths[0])!=core.sha(paths[1]):raise ValueError('legacy three-player trace bytes changed')
        sup.stage(f'legacy-{depth}-replay',[c['python'],'-m','scripts.check_nplayer_policy_replay',paths[1]])
    validate(c)
    core.write(root/'results.json',dict(status='qualified-engineering-only',source=c['source']['commit'],elapsed_seconds=time.monotonic()-tick,pairs=pairs,
        replay_hands=sum(p['hands'] for p in proofs),mass_tags=core.load(root/'measurements/independent-mass-tags/stdout.log'),costs=sup.costs,
        legacy_three_player_bytes_unchanged=True,no_training=True,no_strength_claim=True,archive='owner-managed pending; originals retained'))
    core.write(root/'status.json',dict(status='complete',result_sha256=core.sha(root/'results.json')))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('prepare','run'));p.add_argument('--root',required=True,type=Path);p.add_argument('--accepted-seconds',type=int);p.add_argument('--build-root',type=Path);p.add_argument('--build-source',type=Path);a=p.parse_args();root=a.root.absolute()
    if sys.platform!='darwin' or subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True).strip()!='Apple M4':raise ValueError('M4 only')
    if 'AC Power' not in subprocess.check_output(['pmset','-g','batt'],text=True):raise ValueError('AC required')
    def stop(sig,frame):raise InterruptedError(f'owner signal{sig}')
    for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,stop)
    with (Path.home()/'Local/.hu20-m4-research.lock').open('a+') as normal,Path('/tmp/cfr-paired-arena-qualification.lock').open('a+') as own:
        for lock in (normal,own):fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if a.mode=='prepare' and root.exists():raise FileExistsError('prepared attempt exists; no overwrite')
        if a.mode=='run' and any((root/p).exists() for p in ('launch.json','failure.json','measurements')):raise FileExistsError('attempt exists; no restart or metadata overwrite')
        try:
            if a.mode=='prepare':prepare(root,a.build_root,a.build_source)
            else:run(root,a.accepted_seconds)
        except BaseException as e:
            if root.exists():core.write(root/'failure.json',dict(error=repr(e),epoch=time.time(),no_automatic_retry=True))
            raise


if __name__=='__main__':main()
