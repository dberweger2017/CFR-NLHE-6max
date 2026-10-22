"""PR404 fixed owner-accepted200BB campaign. No cleanup, staging or uploads."""
import argparse
import fcntl
import gzip
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from scripts import nplayer_bb200_feasibility as base
from scripts import nplayer_v06_acceptance as acceptance
from scripts import nplayer_inference_validation as io

SOURCE=Path(__file__).resolve().parents[1]
MODULE='scripts.nplayer_bb200_model_campaign'
PROPOSAL='configs/research/nplayer-bb200-model-campaign-proposal.json'
SEEDS=(2026102240001,2026102261001,2026102261002)
FIXTURE_SEEDS=(2026102269901,2026102269902,2026102269903)
PARENT_SHA='55d89c553ba1756eac1af117847b30e8b18e4f901afba942ee5a906bc00249ad'
PRIOR=Path('/home/dberweger/nplayer-bb200-feasibility-20261022')
PARENT=Path('/home/dberweger/nplayer-bb200-maturity-20261022/main-v1/continuation-1b.gz')
NAMES=('nplayer_train','nplayer_policy','nplayer_arena','nplayer_inference','nplayer_continuation_arena')
ALLOWED_NATIVE_CHANGE='native/hu20-trainer/examples/nplayer_continuation_arena.rs'


def proposal():return io.load(SOURCE/PROPOSAL)


def source_pins():
    names=subprocess.check_output(['git','ls-files','scripts','src','native','configs/research',
        'tests/test_nplayer_bb200_model_campaign.py','docs/nplayer-bb200-model-campaign.md'],cwd=SOURCE,text=True).splitlines()
    return {n:io.sha(SOURCE/n) for n in names if (SOURCE/n).is_file()}


def committed():
    if subprocess.check_output(['git','status','--porcelain'],cwd=SOURCE,text=True).strip():
        raise ValueError('committed clean campaign source required')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip()


def sizing(smoke=False):
    rows=proposal()['rows']
    if not smoke:return rows
    mapping=dict(zip(SEEDS,FIXTURE_SEEDS))
    return [dict(r,seed=str(mapping[int(r['seed'])]),
        name=str(mapping[int(r['name'])]) if r['gate']=='cross' else r['name'],
        blocks=2,root=20261022629901+i) for i,r in enumerate(rows)]


def matrix(smoke=False):
    templates={c.get('opponent'):c['players'][1:] for c in acceptance.diagnostic.cases(True) if c.get('opponent')}
    result=[]
    for g in sizing(smoke):
        seed=int(g['seed']);common=dict(seed=seed,gate=g['gate'],blocks=g['blocks'],root=g['root'])
        if g['gate']=='script-profit':
            result.append(dict(common,name=f'{seed}-{g["name"]}',opponent=g['name'],
                players=['candidate']+templates[g['name']],phase=f'own-{seed}'))
        elif g['gate']=='direct':
            for i,players in enumerate((['candidate','baseline','baseline'],['baseline','candidate','candidate'])):
                result.append(dict(common,name=f'{seed}-direct-{i}',players=players,phase=f'own-{seed}'))
        elif g['gate']=='cross':
            other=int(g['name'])
            for alias in ('candidate','baseline'):
                result.append(dict(common,name=f'cross-{seed}-{alias}',opponent_seed=other,
                    singleton=f'{alias}-{seed}',pair=f'baseline-{other}',phase=f'cross-{seed}-{alias}'))
        else:raise ValueError('unknown gate')
    return result


def phases(smoke=False):
    seeds=FIXTURE_SEEDS if smoke else SEEDS;rows=matrix(smoke)
    names=[f'own-{s}' for s in seeds]+[f'cross-{s}-{a}' for s in seeds for a in ('candidate','baseline')]
    return [(n,[r for r in rows if r['phase']==n]) for n in names]


class Supervisor(base.Supervisor):
    def __init__(self,root,env,config_sha=None):
        super().__init__(root,env);self.config_sha=config_sha
    def stage(self,name,command,**kwargs):
        if self.config_sha is not None and io.sha(self.root/'config.json')!=self.config_sha:
            raise ValueError('frozen config mutated')
        row=super().stage(name,command,**kwargs)
        record=dict(row,cpu_seconds=row['user_cpu_seconds']+row['system_cpu_seconds'],
            sampled_peak_rss_by_phase={name:row['sampled_peak_rss_bytes']})
        for file in ('process.json','result.json'):io.write(self.root/'measurements'/name/file,record)
        return row


def build(root):
    source=committed();root.mkdir(parents=True,exist_ok=False)
    with open('/tmp/cfr-cygnus-exclusive.lock','a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        old=io.load(PRIOR/'build-v1/build-receipt.json');current={k:v for k,v in source_pins().items() if k.startswith('native/')}
        if {k:v for k,v in current.items() if k!=ALLOWED_NATIVE_CHANGE}!={k:v for k,v in old['native_files'].items() if k!=ALLOWED_NATIVE_CHANGE}:
            raise ValueError('unreviewed native change beyond diagnostic depth admission')
        if not old['native_library_tests_passed'] or not old['arena_example_tests_passed']:raise ValueError('prior build unqualified')
        env={**os.environ,'CARGO_TARGET_DIR':str(root/'target'),'CARGO_BUILD_JOBS':'4','RAYON_NUM_THREADS':'4',
            'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
        sup=Supervisor(root,env);cargo=str(Path.home()/'.cargo/bin/cargo')
        manifest=['--release','--locked','--offline','--manifest-path',str(SOURCE/'native/hu20-trainer/Cargo.toml')]
        sup.stage('native-build',[cargo,'build',*manifest,'--example','nplayer_inference','--example','nplayer_continuation_arena'])
        sup.stage('native-tests',[cargo,'test',*manifest,'--lib','--example','nplayer_inference','--example','nplayer_continuation_arena','--example','nplayer_arena'])
        oldconfig=io.load(PRIOR/'main-v1/config.json');binaries={n:oldconfig['binaries'][n] for n in NAMES[:3]}
        for n in NAMES[:3]:
            if io.sha(binaries[n])!=oldconfig['binary_sha256s'][n]:raise ValueError('qualified old binary changed')
        binaries.update({n:str(root/'target/release/examples'/n) for n in NAMES[3:]})
        io.write(root/'build-receipt.json',dict(status='passed',source=source,native_files=current,
            binaries=binaries,sha256s={n:io.sha(p) for n,p in binaries.items()},native_tests_passed=True))


def validate_config(c):
    if (c['format']!='nplayer-bb200-model-campaign-v1' or c['accepted_seconds']!=64800
            or c['proposal_sha256']!=io.sha(SOURCE/PROPOSAL) or c['cases']!=matrix(c['smoke'])
            or c['seeds']!=list(FIXTURE_SEEDS if c['smoke'] else SEEDS)
            or c['targets']!=([100000,200000] if c['smoke'] else [3000000000,10000000000])
            or c['max_entries']!=(10000 if c['smoke'] else 250000000)
            or c['resource_policy']!=acceptance.thermal.RESOURCE_POLICY or c['source_files']!=source_pins()
            or c['source']!=committed() or c['stack_bb']!=200 or c['threads']!=16
            or c['cleanup_staging_uploads']!='owner-vacuum-cleaner-only'):
        raise ValueError('accepted fixed campaign configuration/source differs')
    build=io.load(c['build_receipt'])
    if io.sha(c['build_receipt'])!=c['build_receipt_sha256'] or build['source']!=c['source'] or not build['native_tests_passed']:
        raise ValueError('qualified build receipt differs')
    if set(c['binaries'])!=set(NAMES):raise ValueError('native binary missing')
    for name,path in c['binaries'].items():
        if path!=build['binaries'][name] or io.sha(path)!=build['sha256s'][name]:raise ValueError('native binary changed')
    if io.sha(c['python'])!=c['python_sha256']:raise ValueError('managed Python changed')
    if acceptance.thermal.python_environment(Path(c['python']))[1]!=c['environment']:
        raise ValueError('qualified engine/Python/SciPy environment changed')
    for name,digest in c['table_sha256s'].items():
        if io.sha(Path(c['tables'])/name)!=digest:raise ValueError('K50 changed')
    if not c['smoke']:
        q=Path(c['qualification']);result=io.load(q/'results.json')
        qc=io.load(q/'config.json');proof=io.load(q/'qualification.json')
        if (io.sha(q/'qualification.json')!=c['qualification_sha256'] or (q/'failure.json').exists()
                or proof['status']!='passed' or proof['result_sha256']!=io.sha(q/'results.json')
                or result['config_sha256']!=io.sha(q/'config.json') or not qc['smoke'] or qc['cases']!=matrix(True)
                or io.load(q/'status.json')['status']!='complete'
                or result['status']!='settled' or result['initial_hands']!=432 or len(result['gates'])!=30
                or io.load(q/'config.json')['source_files']!=c['source_files']):
            raise ValueError('full200BB qualification missing or changed')


def configure(root,build_receipt,smoke,qualification,accepted_seconds):
    if accepted_seconds!=64800:raise ValueError('owner accepted18h allocation required')
    source=committed();build=io.load(build_receipt);old=io.load(PRIOR/'main-v1/config.json')
    _,environment=acceptance.thermal.python_environment(Path(old['python']))
    c=dict(old,format='nplayer-bb200-model-campaign-v1',source=source,source_files=source_pins(),
        proposal_sha256=io.sha(SOURCE/PROPOSAL),accepted_seconds=64800,smoke=smoke,cases=matrix(smoke),
        seeds=list(FIXTURE_SEEDS if smoke else SEEDS),targets=[100000,200000] if smoke else [3000000000,10000000000],
        max_entries=10000 if smoke else 250000000,binaries=build['binaries'],build_receipt=str(build_receipt),
        build_receipt_sha256=io.sha(build_receipt),resource_policy=acceptance.thermal.RESOURCE_POLICY,
        cleanup_staging_uploads='owner-vacuum-cleaner-only',qualification=str(qualification) if qualification else None,
        qualification_sha256=io.sha(qualification/'qualification.json') if qualification else None,environment=environment)
    root.mkdir(parents=True,exist_ok=False);io.write(root/'config.json',c);validate_config(c)


def convert(root,c,stage,seed,alias,checkpoint):
    name=f'{seed}-{alias}';policy,digest,audit=base.export_model(root,c,stage,name,checkpoint)
    mass=root/(name+'-mass');path=root/(name+'.bin');receipt=mass/'receipt.json';mass_sha=io.sha(receipt)
    if audit['rows']!=checkpoint['entries'] or audit['checkpoint_sha256']!=checkpoint['sha256']:
        raise ValueError('checkpoint/export binding differs')
    stage(name+'-convert',[c['binaries']['nplayer_inference'],'convert',policy,digest,path,'--mass',receipt,mass_sha])
    converted=io.load(root/'measurements'/(name+'-convert')/'stdout.log');binary_sha=converted['sha256']
    stage(name+'-binary-audit',[c['binaries']['nplayer_inference'],'verify',policy,digest,path,binary_sha,'--mass',receipt,mass_sha])
    proof=io.load(root/'measurements'/(name+'-binary-audit')/'stdout.log')
    if (proof['status']!='passed' or proof['rows']!=audit['rows'] or proof['binary_sha256']!=binary_sha
            or proof['source_policy_sha256']!=digest):raise ValueError('binary parity audit differs')
    return dict(path=str(path),sha256=binary_sha,mass=str(mass),mass_sha256=mass_sha,
        checkpoint=checkpoint['checkpoint'],checkpoint_sha256=checkpoint['sha256'],strategy='average',scope=3,
        source_policy=str(policy),source_policy_sha256=digest,audit=audit,binary_audit=proof)


def freeze_models(root,models):
    if len(models)!=6:raise ValueError('six frozen endpoints required')
    if any((root/p).exists() for p in ('models.json','evaluation-freeze.json','evaluation-launch.json')):
        raise FileExistsError('model catalog already frozen; preserve it')
    io.write(root/'models.json',models)
    with (root/'evaluation-freeze.json').open('x') as stream:
        json.dump(dict(models_sha256=io.sha(root/'models.json'),models=models,epoch=time.time()),stream,indent=2)
    with (root/'evaluation-launch.json').open('x') as stream:
        json.dump(dict(freeze_sha256=io.sha(root/'evaluation-freeze.json')),stream)


def verify_freeze(root):
    freeze=io.load(root/'evaluation-freeze.json');launch=io.load(root/'evaluation-launch.json')
    if launch['freeze_sha256']!=io.sha(root/'evaluation-freeze.json') or freeze['models_sha256']!=io.sha(root/'models.json'):
        raise ValueError('frozen model catalog mutated')
    return freeze['models']


def verify_job(job):
    native=io.load(job/'native.json')
    if native['stack_bb']!=200:raise ValueError('not200BB job')
    for case in native['cases']:
        with Path(case['trace']).open() as stream:header=json.loads(next(stream))
        if header['identity']['stacks']!=[20000]*3:raise ValueError('trace depth differs')
    acceptance.verify_job(job)


def read(root):
    c=io.load(root/'config.json');models=verify_freeze(root)
    for model in models.values():
        for path,pin in ((model['path'],model['sha256']),(model['checkpoint'],model['checkpoint_sha256']),
                (model['source_policy'],model['source_policy_sha256']),
                (Path(model['mass'])/'receipt.json',model['mass_sha256']),
                (Path(model['mass'])/'zero-keys.bin',model['audit']['zero_keys_sha256'])):
            if io.sha(path)!=pin:raise ValueError('final retained model/mass bytes differ')
    acceptance.read(root,sizing=sizing(c['smoke']),cases=c['cases'],phase_rows=phases(c['smoke']),config_validator=validate_config)
    result=io.load(root/'results.json');result.update(training_endpoints=io.load(root/'training-endpoints.json'),
        proposal_sha256=c['proposal_sha256'],no_further_cost_pilot=True,cleanup_staging_uploads='owner-vacuum-cleaner-only',
        limits='Three fixed200BBlineages/onehost/cappedmembership; conditional100BBpower scenarios only; no Nash/universal/human strength or automatic release.')
    io.write(root/'results.json',result)


def execute(root,c,sup):
    models={};endpoints={};targets=c['targets'];cap=c['max_entries']
    for seed in c['seeds']:
        parent=None
        if not c['smoke'] and seed==SEEDS[0]:
            parent=io.load(SOURCE/'docs/reports/nplayer-bb200-maturity/results.json')['endpoint']
            if parent['checkpoint']!=str(PARENT) or parent['sha256']!=PARENT_SHA or io.sha(PARENT)!=PARENT_SHA:
                raise ValueError('verified1B parent changed')
        for alias,target in zip(('baseline','candidate'),targets):
            row=base.train_endpoint(root,c,sup.stage,f'{seed}-{alias}-train',target,parent=parent,seed=seed,cap=cap)
            if row['frozen_at'] is None:raise ValueError('declared endpoint did not freeze membership')
            model=convert(root,c,sup.stage,seed,alias,row);models[f'{alias}-{seed}']=model
            endpoints[f'{alias}-{seed}']=row;parent=row
            io.write(root/'training-endpoints.json',endpoints)
            if c['smoke'] and seed==FIXTURE_SEEDS[0]:
                reference=base.train_endpoint(root,c,sup.stage,'fixture-reference-'+alias,target,seed=seed,
                    threads=1 if alias=='baseline' else 16,cap=cap)
                if reference['sha256']!=row['sha256']:raise ValueError('thread/resume checkpoint parity failed')
        a,b=(models[f'{alias}-{seed}']['audit'] for alias in ('baseline','candidate'))
        if a['rows']!=b['rows'] or a['keyset_sha256']!=b['keyset_sha256']:raise ValueError('within-lineage membership differs')
    freeze_models(root,models)
    catalog={str(seed):{alias:dict(mass=models[f'{alias}-{seed}']['audit']) for alias in ('baseline','candidate')} for seed in c['seeds']}
    for name,rows in phases(c['smoke']):
        verify_freeze(root)
        job,_=acceptance.make_job(root,dict(c,catalog=catalog),name,rows,models,stack_bb=200)
        binary='nplayer_continuation_arena' if name.startswith('own-') else 'nplayer_arena'
        sup.stage(name,[c['binaries'][binary],'batch',job/'native.json'])
        sup.stage(name+'-verify',[c['python'],'-m',MODULE,'verify-job','--root',job])
    sup.stage('global-readout',[c['python'],'-m',MODULE,'read','--root',root])


def run(root):
    c=io.load(root/'config.json');validate_config(c)
    if any((root/p).exists() for p in ('launch.json','failure.json','status.json','measurements')):
        raise ValueError('attempt exists; no restart/retry')
    with open('/tmp/cfr-cygnus-exclusive.lock','a+') as normal,open('/tmp/cfr-nplayer-bb200-model-campaign.lock','a+') as own:
        for lock in (normal,own):fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        config_sha=io.sha(root/'config.json');env={**os.environ,'PYTHONPATH':str(SOURCE),'RAYON_NUM_THREADS':'16',
            'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NPLAYER_STOP_FILE':str(root/'STOP')}
        sup=Supervisor(root,env,config_sha)
        try:
            io.write(root/'launch.json',dict(pid=os.getpid(),epoch=time.time(),source=c['source'],config_sha256=config_sha,
                accepted_planning_seconds=64800,smoke=c['smoke'],no_time_memory_disk_swap_stop=True))
            execute(root,c,sup)
            io.write(root/'status.json',dict(status='complete',epoch=time.time(),result_sha256=io.sha(root/'results.json')))
            if c['smoke']:
                io.write(root/'qualification.json',dict(status='passed',source=c['source'],result_sha256=io.sha(root/'results.json'),
                    initial_hands=432,reproduction_hands=432,cases=36,source_files=c['source_files']))
        except BaseException as error:
            io.write(root/'failure.json',dict(error=repr(error),epoch=time.time(),resource_sample=getattr(error,'resource_sample',None),
                originals_retained=True,no_automatic_retry=True));raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('build','configure','run','verify-job','read'))
    p.add_argument('--root',type=Path,required=True);p.add_argument('--build-receipt',type=Path)
    p.add_argument('--smoke',action='store_true');p.add_argument('--qualification',type=Path)
    p.add_argument('--accepted-planning-seconds',type=int);a=p.parse_args();root=a.root.absolute()
    if a.mode in ('run','build'):
        def interrupted(signum,frame):raise InterruptedError(f'owner signal {signum}')
        signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    if a.mode=='configure':configure(root,a.build_receipt.absolute(),a.smoke,a.qualification.absolute() if a.qualification else None,a.accepted_planning_seconds)
    else:globals()[a.mode.replace('-','_')](root)


if __name__=='__main__':main()
