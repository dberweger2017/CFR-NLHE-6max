"""Fixed four-player development preparation; main requires explicit allocation."""
import argparse
import fcntl
import itertools
import json
import math
import statistics
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from scripts import nplayer_bb200_feasibility as base
from scripts import nplayer_bb200_model_campaign as mature
from scripts import nplayer_four_player_feasibility as four
from scripts import nplayer_paired_evidence as evidence

SOURCE=Path(__file__).resolve().parents[1]
MODULE='scripts.nplayer_four_player_candidate'
PROPOSAL='configs/research/nplayer-four-player-candidate.json'
NAMES=('nplayer_train','nplayer_policy','nplayer_inference','nplayer_paired_arena','nplayer_arena')
SEED=2026102341001
QUAL_SEED=2026102341991
SCHEDULE=[list(row) for row in itertools.permutations(range(4))]
FIELDS=(('trained',['baseline']*3),('random',['bot=random']*3),('check-call',['bot=check-call']*3),
 ('tight-aggressive',['bot=tight-aggressive']*3),('pot-pressure',['bot=pot-pressure']*3),
 ('call-pressure',['bot=check-call','bot=check-call','bot=pot-pressure']),
 ('random-tight',['bot=random','bot=tight-aggressive','bot=tight-aggressive']),
 ('trained-call-pressure',['baseline','bot=check-call','bot=pot-pressure']))


def load(p):return base.read(Path(p))
def write(p,v):base.write(Path(p),v)
def sha(p):return base.sha(p)


def fixed(smoke=False):
    return dict(format='nplayer-four-player-candidate-v1',players=4,stack_bb=100,
        seed=QUAL_SEED if smoke else SEED,targets=[100000,200000] if smoke else [3000000000,10000000000],
        cap=10000 if smoke else 250000000,threads=16,roots_per_seat=8,last_average_street=3,
        pruning=False,freeze_at_cap=True,fast_gzip=True,smoke=smoke,schedule=SCHEDULE,
        blocks=2 if smoke else 4096,root_base=20261023459901 if smoke else 20261023450001,
        fields=[dict(name=name,opponents=field) for name,field in FIELDS],
        resource_stops='CPU90/Thermistor15-100/missing-nonfinite; ownerSTOP/mutex/correctness',
        no_time_rss_disk_swap_stop=True,cleanup='owner-vacuum-cleaner-only')


def source():
    if subprocess.check_output(['git','status','--porcelain'],cwd=SOURCE,text=True).strip():raise ValueError('clean committed source required')
    files=subprocess.check_output(['git','ls-files','native','scripts','src','configs/research','tests/test_nplayer_four_player_candidate.py'],cwd=SOURCE,text=True).splitlines()
    return dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip(),files={n:sha(SOURCE/n) for n in files})


def manifest(root,c,models,phase,*,self_only=False,serial=False,gzip_models=False):
    cases=[]
    fields=[dict(name='self',opponents=['baseline','bot=check-call','bot=pot-pressure'])] if self_only else c['fields']
    for i,f in enumerate(fields):
        name=f['name'];folder=root/f'arena-{phase}';folder.mkdir(exist_ok=True)
        cases.append(dict(name=name,players=4,stack_bb=100,blocks=c['blocks'],root=c['root_base']+i,
            schedule=c['schedule'],focals=['baseline','baseline' if self_only else 'candidate'],opponents=f['opponents'],
            traces=[str(folder/f'{name}-{a}.jsonl') for a in ('a','b')],summary=str(folder/f'{name}-cost.json')))
    if gzip_models:
        models={k:dict(v,path=v['source_policy'],sha256=v['source_policy_sha256']) for k,v in models.items()}
    return dict(format='nplayer-paired-manifest-v1',tables=c['tables'],threads=1 if serial else 8,models=models,cases=cases)


def trace_payload_parity(binary,gzip,models):
    # Headers deliberately pin distinct files. Normalize only the known binary
    # digest to its fully audited source policy; every payload byte must match.
    mapping={v['sha256']:v['source_policy_sha256'] for v in models.values()}
    with Path(binary).open('rb') as a,Path(gzip).open('rb') as b:
        headers=[json.loads(next(f)) for f in (a,b)]
        for header in headers:
            for pin in header['policies']:
                if 'sha256' in pin:pin['sha256']=mapping.get(pin['sha256'],pin['sha256'])
        if headers[0]!=headers[1]:raise ValueError('gzip/binary header identity differs')
        for left,right in itertools.zip_longest(a,b):
            if left!=right:raise ValueError('gzip/binary hand payload differs')


def run_native(sup,c,root,models,phase,**options):
    m=manifest(root,c,models,phase,**options);path=root/(phase+'-manifest.json');write(path,m)
    sup.stage('arena-'+phase,[c['binaries']['nplayer_paired_arena'],'batch',path]);return m


def train(root,c,sup,tag,target,parent=None,threads=16):
    out=root/(tag+'.gz')
    cost=sup.stage(tag,four.train_command(c,out,target,c['seed'],c['cap'],parent,threads))
    x=load(root/'measurements'/tag/'stdout.log');four.checkpoint(x,out,target,c['seed'],c['cap'],4)
    if parent and parent['frozen_at'] is not None and any(x[k]!=parent[k] for k in ('entries','frozen_at')):raise ValueError('frozen marker/count changed')
    return dict(x,checkpoint=str(out),checkpoint_bytes=out.stat().st_size,stage_wall_seconds=cost['wall_seconds'],active_training_seconds=x['elapsed_seconds']-x['save_seconds'])


def verify_case(root,c,sup,left,right):
    receipts=[]
    for arm in range(2):
        path=Path(left['traces'][arm]);other=Path(right['traces'][arm])
        if sha(path)!=sha(other):raise ValueError('reproduction differs')
        name='replay-'+left['name']+'-'+str(arm)
        sup.stage(name,[c['python'],'-m','scripts.nplayer_paired_evidence','replay',path])
        receipts.append(root/'measurements'/name/'stdout.log')
    name='pair-'+left['name']
    sup.stage(name,[c['python'],'-m','scripts.nplayer_paired_evidence','pair',*left['traces'],*right['traces'],*receipts])
    result=load(root/'measurements'/name/'stdout.log')
    if result['blocks']!=c['blocks'] or result['schedule']!=c['schedule'] or result['root']!=left['root']:raise ValueError('paired scope differs')
    return result


def execute(root,c,sup):
    models={};endpoints={};parent=None
    for tag,target in zip(('baseline','candidate'),c['targets']):
        cp=train(root,c,sup,tag+'-train',target,parent)
        models[tag]=mature.convert(root,c,sup.stage,c['seed'],tag,cp);endpoints[tag]=cp;parent=cp
        write(root/'training-endpoints.json',endpoints)
        if c['smoke']:
            ref=train(root,c,sup,'reference-'+tag,target,threads=1 if tag=='baseline' else 16)
            if ref['sha256']!=cp['sha256']:raise ValueError('thread/resume checkpoint parity differs')
    a,b=(models[k]['audit'] for k in ('baseline','candidate'))
    if a['rows']!=b['rows'] or a['keyset_sha256']!=b['keyset_sha256']:raise ValueError('within-lineage membership differs')
    if not c['smoke'] and any(x['frozen_at'] is None for x in endpoints.values()):raise ValueError('main endpoints did not freeze membership')
    write(root/'models.json',models);catalog_sha=sha(root/'models.json')
    initial=run_native(sup,c,root,models,'initial');repeat=run_native(sup,c,root,models,'repeat')
    if sha(root/'models.json')!=catalog_sha:raise ValueError('frozen model catalog changed')
    pairs={}
    for left,right in zip(initial['cases'],repeat['cases']):pairs[left['name']]=verify_case(root,c,sup,left,right)
    if c['smoke']:
        serial=run_native(sup,c,root,models,'serial',serial=True)
        gz=run_native(sup,c,root,models,'gzip',gzip_models=True)
        for i,left in enumerate(initial['cases']):
            for arm,path in enumerate(left['traces']):
                if sha(path)!=sha(serial['cases'][i]['traces'][arm]):raise ValueError('serial/parallel trace parity differs')
                trace_payload_parity(path,gz['cases'][i]['traces'][arm],models)
        own=run_native(sup,c,root,models,'self',self_only=True)
        own_repeat=run_native(sup,c,root,models,'self-repeat',self_only=True)
        self_result=verify_case(root,c,sup,own['cases'][0],own_repeat['cases'][0])
        if not self_result['self_exact_zero']:raise ValueError('self comparison not exactly zero')
        catalog={k:dict(v,path=v['source_policy'],sha256=v['source_policy_sha256']) for k,v in models.items()};write(root/'gzip-catalog.json',catalog)
        sup.stage('independent-mass-tags',[c['python'],'-m','scripts.nplayer_paired_evidence','coverage',root/'gzip-catalog.json',*[p for x in gz['cases'] for p in x['traces']]])
        for depth in (20,100,200):
            paths=[]
            for label,key in (('old','legacy'),('new','nplayer_arena')):
                trace=root/f'legacy-{depth}-{label}.jsonl';paths.append(trace)
                sup.stage(f'legacy-{depth}-{label}',[c['binaries'][key],c['tables'],2,20261023459800+depth,trace,'bot=check-call','bot=pot-pressure',depth,1])
            if sha(paths[0])!=sha(paths[1]):raise ValueError('legacy three-player bytes changed')
            sup.stage(f'legacy-{depth}-replay',[c['python'],'-m','scripts.check_nplayer_policy_replay',paths[1]])
    for p in (root/'measurements').glob('*/receipt.json'):
        if load(p)['returncode']!=0:raise ValueError('failed stage blocks readout')
    if (root/'failure.json').exists():raise ValueError('terminal failure blocks readout')
    write(root/'evaluation-verified.json',dict(status='passed',cases=8,blocks_per_case=c['blocks'],initial_hands=8*c['blocks']*24*2,reproduction_hands=8*c['blocks']*24*2,
        manifests={p:sha(root/(p+'-manifest.json')) for p in ('initial','repeat')},models_sha256=catalog_sha))
    write(root/'verified-summary.json',dict(models=models,endpoints=endpoints,pairs=pairs,qualification_complete=c['smoke']))
    sup.stage('global-readout',[c['python'],'-m',MODULE,'readout','--root',root])


def summarize(root):
    c=load(root/'config.json');validate(c)
    if (root/'failure.json').exists() or (root/'results.json').exists():raise ValueError('failed or already read out')
    v=load(root/'evaluation-verified.json');initial=load(root/'initial-manifest.json');repeat=load(root/'repeat-manifest.json');data=load(root/'verified-summary.json')
    if (v['status']!='passed' or v['models_sha256']!=sha(root/'models.json')
            or v['manifests']!={p:sha(root/(p+'-manifest.json')) for p in ('initial','repeat')}
            or initial!=manifest(root,c,data['models'],'initial') or repeat!=manifest(root,c,data['models'],'repeat')
            or set(data['pairs'])!={f['name'] for f in c['fields']}):raise ValueError('global frozen scope/proof differs')
    stages=load(root/'stage-costs.json')
    if not stages or any(x['returncode']!=0 for x in stages):raise ValueError('global successful-stage barrier')
    for model in data['models'].values():
        for key,pin in (('path','sha256'),('checkpoint','checkpoint_sha256'),('source_policy','source_policy_sha256')):
            if sha(model[key])!=model[pin]:raise ValueError('final model input changed')
        if sha(Path(model['mass'])/'receipt.json')!=model['mass_sha256'] or sha(Path(model['mass'])/'zero-keys.bin')!=model['audit']['zero_keys_sha256']:raise ValueError('final mass data changed')
    for left,right in zip(initial['cases'],repeat['cases']):
        for arm,path in enumerate(left['traces']):
            proof=load(root/'measurements'/('replay-'+left['name']+'-'+str(arm))/'stdout.log')
            if proof['status']!='passed' or proof['hands']!=c['blocks']*24 or proof['trace_sha256']!=sha(path) or sha(path)!=sha(right['traces'][arm]):raise ValueError('final replay/reproduction binding changed')
    absolute={};tails={};gates=[]
    from scipy.stats import t
    for case in initial['cases']:
        name=case['name'];pair=data['pairs'][name];arms=[]
        for path in case['traces']:
            stream=evidence.rows(path);header=next(stream);blocks=[];part=[]
            for row in stream:
                focal=row['identities'].index(0);part.append(row['rewards'][focal]*100/header['identity']['big_blind'])
                if len(part)==len(c['schedule']):blocks.append(statistics.mean(part));part=[]
            if part or len(blocks)!=c['blocks']:raise ValueError('absolute block count differs')
            arms.append(blocks)
        values=[b-a for a,b in zip(*arms)]
        if len(values)!=len(pair['block_values_bb100']) or any(not math.isclose(x,y,rel_tol=1e-12,abs_tol=1e-10) for x,y in zip(values,pair['block_values_bb100'])):raise ValueError('absolute and paired block contrasts differ')
        values=pair['block_values_bb100']
        absolute[name]={'3B':evidence.interval(arms[0]),'10B':evidence.interval(arms[1])}
        mean=statistics.mean(values);squares=[(x-mean)**2 for x in values];total=sum(squares);order=sorted(range(len(values)),key=lambda i:abs(values[i]-mean),reverse=True)
        tails[name]=dict(min_block_bb100=min(values),max_block_bb100=max(values),top10_squared_deviation_share=sum(squares[i] for i in order[:10])/total if total else 0,
            largest_positive=[dict(block=i,value_bb100=values[i]) for i in sorted(range(len(values)),key=lambda j:values[j],reverse=True)[:5]],
            largest_negative=[dict(block=i,value_bb100=values[i]) for i in sorted(range(len(values)),key=lambda j:values[j])[:5]],no_exclusions=True)
        if not c['smoke']:
            score=pair['contrast'];lower=score['mean_bb100']-float(t.ppf(1-.05/8,c['blocks']-1))*score['standard_error_bb100'];margin=0 if name=='trained' else -5
            gates.append(dict(name=name,mean_bb100=score['mean_bb100'],standard_error_bb100=score['standard_error_bb100'],lower_family95_bb100=lower,margin_bb100=margin,passed=lower>margin))
    write(root/'results.json',dict(status='qualified-engineering' if c['smoke'] else 'settled-development',config_sha256=sha(root/'config.json'),**data,absolute_returns=absolute,tails=tails,gates=gates,
        all_development_gates_passed=all(x['passed'] for x in gates) if gates else None,no_release_acceptance=True,no_extension=True))


def validate(c):
    if c['fixed']!=fixed(c['fixed']['smoke']) or any(c.get(k)!=v for k,v in c['fixed'].items()):raise ValueError('frozen development scope changed')
    if c['source']!=source() or c['proposal_sha256']!=sha(SOURCE/PROPOSAL):raise ValueError('frozen source/proposal changed')
    build=load(c['build']);
    if sha(c['build'])!=c['build_sha256'] or build['source']!=c['source'] or not build['tests_passed']:raise ValueError('build proof differs')
    for n,p in c['binaries'].items():
        if p!=build['binaries'][n] or sha(p)!=build['sha256s'][n]:raise ValueError('binary changed')
    if sha(c['python'])!=c['python_sha256']:raise ValueError('Python changed')
    if mature.acceptance.thermal.python_environment(Path(c['python']))[1]!=c['environment']:raise ValueError('pinned Python/engine environment changed')
    for n,h in c['table_sha256s'].items():
        if sha(Path(c['tables'])/n)!=h:raise ValueError('K50 changed')
    if not c['smoke']:
        q=Path(c['qualification']);qc=load(q/'config.json');s=load(q/'status.json');result=load(q/'results.json')
        if (q/'failure.json').exists() or s['status']!='complete' or sha(q/'results.json')!=s['result_sha256'] or result['status']!='qualified-engineering' or result.get('qualification_complete') is not True or not qc['smoke'] or qc['source']!=c['source'] or result['config_sha256']!=sha(q/'config.json') or sha(q/'results.json')!=c['qualification_sha256']:raise ValueError('same-source bb128 qualification required')
        if c['accepted_seconds']!=load(SOURCE/PROPOSAL)['proposed_allocation_seconds']:raise ValueError('accepted complete allocation required')


def configure(root,build_path,smoke,qualification=None,accepted=None):
    if root.exists():raise FileExistsError('output exists; no overwrite')
    p=load(SOURCE/PROPOSAL)
    if not smoke and accepted!=p['proposed_allocation_seconds']:raise ValueError('owner complete allocation acceptance required')
    build=load(build_path);scope=fixed(smoke);old=load('/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/config.json')
    c=dict(scope,fixed=scope,source=source(),proposal_sha256=sha(SOURCE/PROPOSAL),binaries=build['binaries'],build=str(build_path),build_sha256=sha(build_path),python=old['python'],python_sha256=old['python_sha256'],tables=old['tables'],table_sha256s=old['table_sha256s'],accepted_seconds=accepted,
        qualification=str(qualification) if qualification else None,qualification_sha256=sha(qualification/'results.json') if qualification else None,environment=mature.acceptance.thermal.python_environment(Path(old['python']))[1])
    validate(c);root.mkdir(parents=True,exist_ok=False);write(root/'config.json',c);write(root/'status.json',dict(status='prepared',no_main_started=True))


def run(root):
    if any((root/p).exists() for p in ('launch.json','failure.json','measurements')):raise FileExistsError('attempt exists; no retry')
    c=load(root/'config.json');validate(c);env={**os.environ,'NPLAYER_STOP_FILE':str(root/'STOP'),'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    sup=base.Supervisor(root,env);config_sha=sha(root/'config.json');original=sup.stage
    def stage(name,args):
        validate(c)
        if sha(root/'config.json')!=config_sha:raise ValueError('frozen config changed')
        row=original(name,args);write(root/'measurements'/name/'receipt.json',row);return row
    sup.stage=stage
    write(root/'launch.json',dict(pid=os.getpid(),epoch=time.time(),source=c['source']['commit'],config_sha256=config_sha))
    try:
        execute(root,c,sup);validate(c)
        write(root/'status.json',dict(status='complete',epoch=time.time(),result_sha256=sha(root/'results.json')))
    except BaseException as e:
        record=dict(error=repr(e),epoch=time.time(),no_automatic_retry=True)
        if hasattr(e,'resource_sample'):record['resource_sample']=e.resource_sample
        write(root/'failure.json',record);write(root/'status.json',dict(status='failed',**record));raise


def build(root):
    if root.exists():raise FileExistsError('build output exists')
    pins=source();root.mkdir(parents=True,exist_ok=False)
    env={**os.environ,'CARGO_TARGET_DIR':str(root/'target'),'CARGO_BUILD_JOBS':'4','RAYON_NUM_THREADS':'4'};sup=base.Supervisor(root,env);cargo=str(Path.home()/'.cargo/bin/cargo')
    args=['--release','--locked','--offline','--manifest-path',str(SOURCE/'native/hu20-trainer/Cargo.toml')]
    try:
        sup.stage('native-tests',[cargo,'test',*args,'--lib','--example','nplayer_paired_arena','--example','nplayer_arena'])
        sup.stage('native-build',[cargo,'build',*args,*[a for n in NAMES for a in ('--example',n)]])
        old=load('/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/config.json')
        binaries={n:str(root/'target/release/examples'/n) for n in NAMES};binaries['legacy']=old['binaries']['nplayer_arena']
        if sha(binaries['legacy'])!=old['binary_sha256s']['nplayer_arena']:raise ValueError('protected legacy binary changed')
        sup.stage('focused-python',[sys.executable,'-m','unittest','tests.test_nplayer_four_player_candidate','tests.test_nplayer_paired_evidence','-q'])
        write(root/'build-receipt.json',dict(status='passed',source=pins,tests_passed=True,binaries=binaries,sha256s={n:sha(p) for n,p in binaries.items()}))
        write(root/'status.json',dict(status='passed'))
    except BaseException as e:write(root/'failure.json',dict(error=repr(e),no_automatic_retry=True));raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('build','configure','run','readout'));p.add_argument('--root',type=Path,required=True);p.add_argument('--build',type=Path);p.add_argument('--qualification',type=Path);p.add_argument('--smoke',action='store_true');p.add_argument('--accepted-seconds',type=int);a=p.parse_args()
    if sys.platform!='linux' or __import__('socket').gethostname()!='cygnus-x1':raise ValueError('bb128 only')
    if a.mode=='readout':
        summarize(a.root.absolute());return
    def stopped(sig,frame):raise InterruptedError(f'owner signal {sig}')
    for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,stopped)
    with open('/tmp/cfr-cygnus-exclusive.lock','a+') as normal,open('/tmp/cfr-four-player-candidate.lock','a+') as own:
        for lock in (normal,own):fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        root=a.root.absolute()
        if a.mode=='build':build(root)
        elif a.mode=='configure':configure(root,a.build,a.smoke,a.qualification,a.accepted_seconds)
        else:run(root)


if __name__=='__main__':main()
