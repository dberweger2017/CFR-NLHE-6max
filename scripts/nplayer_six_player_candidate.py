"""One fixed six-player100BB lineage, four checkpoints and five paired contrasts."""
import argparse
import fcntl
import itertools
import json
import math
import os
from pathlib import Path
import signal
import statistics
import subprocess
import sys
import time
from scripts import nplayer_five_player_candidate as prior
from scripts import nplayer_bb200_feasibility as base
from scripts import nplayer_bb200_model_campaign as mature
from scripts import nplayer_four_player_feasibility as four
from scripts import nplayer_paired_evidence as evidence

SOURCE=Path(__file__).resolve().parents[1]
MODULE='scripts.nplayer_six_player_candidate'
PROPOSAL='configs/research/nplayer-six-player-candidate.json'
NAMES=prior.NAMES
TAGS=('3b','6b','10b','15b')
CONTRASTS=(('3b','6b'),('6b','10b'),('10b','15b'),('3b','10b'),('3b','15b'))
SCHEDULE=[[(d*s+r)%6 for s in range(6)] for d in (1,-1) for r in range(6)]
FIELDS=(('trained',['baseline']*5),('random',['bot=random']*5),('check-call',['bot=check-call']*5),
 ('tight-aggressive',['bot=tight-aggressive']*5),('pot-pressure',['bot=pot-pressure']*5),
 ('call-pressure',['bot=check-call']*3+['bot=pot-pressure']*2),
 ('random-tight',['bot=random']+['bot=tight-aggressive']*4),
 ('trained-call-pressure',['baseline']+['bot=check-call']*2+['bot=pot-pressure']*2))
load=prior.load
write=prior.write
sha=prior.sha


def fixed(smoke=False):
    return dict(format='nplayer-six-player-candidate-v1',players=6,stack_bb=100,seed=2026102361991 if smoke else 2026102361001,
        targets=[50000,100000,150000,200000] if smoke else [3_000_000_000,6_000_000_000,10_000_000_000,15_000_000_000],
        tags=list(TAGS),contrasts=[list(z) for z in CONTRASTS],cap=10000 if smoke else 250000000,
        threads=16,roots_per_seat=8,last_average_street=3,pruning=False,freeze_at_cap=True,fast_gzip=True,smoke=smoke,
        schedule=SCHEDULE,blocks=2 if smoke else 4096,root_base=20261023659901 if smoke else 20261023650001,
        fields=[dict(name=n,opponents=f) for n,f in FIELDS],interval_family='40 one-sided95 Student-t/Bonferroni; trained lower>0; scripted/mixed lower>-5',
        incomplete_policy='terminal failures; no automatic recovery/retry; partial evidence never reduced acceptance',
        resource_stops='CPU90/Thermistor15-100/missing-nonfinite; ownerSTOP/mutex/correctness',no_time_rss_disk_swap_stop=True,cleanup='owner-vacuum-cleaner-only')


def source():
    if subprocess.check_output(['git','status','--porcelain'],cwd=SOURCE,text=True).strip():raise ValueError('clean committed source required')
    paths=subprocess.check_output(['git','ls-files','native','scripts','src','configs/research','tests/test_nplayer_six_player_candidate.py','tests/test_nplayer_trace_divergence.py','docs/nplayer-six-player-candidate.md'],cwd=SOURCE,text=True).splitlines()
    return dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip(),files={n:sha(SOURCE/n) for n in paths})


def manifest(root,c,models,tag,phase,*,self_only=False,serial=False,gzip_models=False):
    chosen={'baseline':models['3b'],'candidate':models[tag]};cases=[]
    if gzip_models:chosen={k:dict(v,path=v['source_policy'],sha256=v['source_policy_sha256']) for k,v in chosen.items()}
    fields=[dict(name='self',opponents=['baseline']+['bot=check-call']*2+['bot=pot-pressure']*2)] if self_only else c['fields']
    folder=root/f'arena-{tag}-{phase}';folder.mkdir(exist_ok=True)
    for i,f in enumerate(fields):
        cases.append(dict(name=f['name'],players=6,stack_bb=100,blocks=c['blocks'],root=c['root_base']+i,schedule=c['schedule'],
            focals=['baseline','baseline' if self_only else 'candidate'],opponents=f['opponents'],
            traces=[str(folder/(f['name']+'-'+a+'.jsonl')) for a in ('a','b')],summary=str(folder/(f['name']+'-cost.json'))))
    return dict(format='nplayer-paired-manifest-v1',tables=c['tables'],threads=1 if serial else 8,models=chosen,cases=cases)


def native(root,c,sup,models,tag,phase,**kw):
    m=manifest(root,c,models,tag,phase,**kw);p=root/f'{tag}-{phase}-manifest.json';write(p,m)
    sup.stage('arena-'+tag+'-'+phase,[c['binaries']['nplayer_paired_arena'],'batch',p]);return m


def train(root,c,sup,name,target,parent=None,threads=16):
    out=root/(name+'.gz');cost=sup.stage(name,four.train_command(c,out,target,c['seed'],c['cap'],parent,threads))
    x=load(root/'measurements'/name/'stdout.log');four.checkpoint(x,out,target,c['seed'],c['cap'],6)
    if parent and parent['frozen_at'] is not None and any(x[k]!=parent[k] for k in ('entries','frozen_at')):raise ValueError('frozen membership count/marker changed')
    return dict(x,checkpoint=str(out),checkpoint_bytes=out.stat().st_size,stage_wall_seconds=cost['wall_seconds'],active_training_seconds=x['elapsed_seconds']-x['save_seconds'])


def verify_case(root,c,sup,left,right,prefix):
    proofs=[]
    for arm,path in enumerate(left['traces']):
        if sha(path)!=sha(right['traces'][arm]):raise ValueError('reproduction differs')
        name='replay-'+prefix+'-'+str(arm);sup.stage(name,[c['python'],'-m','scripts.nplayer_paired_evidence','replay',path]);proofs.append(str(root/'measurements'/name/'stdout.log'))
    return dict(initial=left,repeat=right,proofs=proofs)


def cross_case(field,left,right):
    def arm(record):
        return 0 if record['tag']=='3b' else 1
    a,b=arm(left),arm(right)
    return dict(name=field,traces=[left['record']['initial']['traces'][a],right['record']['initial']['traces'][b]],
        repeats=[left['record']['repeat']['traces'][a],right['record']['repeat']['traces'][b]],
        proofs=[left['record']['proofs'][a],right['record']['proofs'][b]])


def execute(root,c,sup):
    models={};endpoints={};parent=None
    for tag,target in zip(TAGS,c['targets']):
        cp=train(root,c,sup,tag+'-train',target,parent);models[tag]=mature.convert(root,c,sup.stage,c['seed'],tag,cp);endpoints[tag]=cp;parent=cp
        write(root/'training-endpoints.json',endpoints)
        if c['smoke']:
            ref=train(root,c,sup,'reference-'+tag,target,threads=1)
            if ref['sha256']!=cp['sha256']:raise ValueError('thread/resume checkpoint parity differs')
    first=models['3b']['audit']
    for model in models.values():
        if any(model['audit'][k]!=first[k] for k in ('rows','keyset_sha256')):raise ValueError('within-lineage keyset differs')
    if not c['smoke'] and any(z['frozen_at'] is None for z in endpoints.values()):raise ValueError('main membership not frozen')
    write(root/'models.json',models);catalog=sha(root/'models.json');records={};manifests={};baseline_hashes={}
    for tag in TAGS[1:]:
        initial=native(root,c,sup,models,tag,'initial');repeat=native(root,c,sup,models,tag,'repeat');manifests[tag]=dict(initial=initial,repeat=repeat);records[tag]={}
        for left,right in zip(initial['cases'],repeat['cases']):
            field=left['name'];records[tag][field]=verify_case(root,c,sup,left,right,tag+'-'+field)
            h=sha(left['traces'][0]);old=baseline_hashes.setdefault(field,h)
            if h!=old:raise ValueError('cross-job3B trace differs')
        if c['smoke']:
            for phase,kw in (('serial',dict(serial=True)),('gzip',dict(gzip_models=True))):
                extra=native(root,c,sup,models,tag,phase,**kw)
                for left,other in zip(initial['cases'],extra['cases']):
                    for arm,path in enumerate(left['traces']):
                        if phase=='serial':
                            if sha(path)!=sha(other['traces'][arm]):raise ValueError('serial/parallel bytes differ')
                        else:prior.trace_payload_parity(path,other['traces'][arm],{'baseline':models['3b'],'candidate':models[tag]})
    if c['smoke']:
        own=native(root,c,sup,models,'6b','self',self_only=True);rep=native(root,c,sup,models,'6b','self-repeat',self_only=True)
        z=verify_case(root,c,sup,own['cases'][0],rep['cases'][0],'self')
        result=evidence.verified_pair(*z['initial']['traces'],*z['repeat']['traces'],*z['proofs'])
        if not result['self_exact_zero']:raise ValueError('self contrast not exactly zero')
        gzip_catalog={k:dict(v,path=v['source_policy'],sha256=v['source_policy_sha256']) for k,v in {'baseline':models['3b'],'candidate':models['15b']}.items()};write(root/'gzip-catalog.json',gzip_catalog)
        sup.stage('independent-mass-tags',[c['python'],'-m','scripts.nplayer_paired_evidence','coverage',root/'gzip-catalog.json',*[p for z in manifest(root,c,models,'15b','gzip',gzip_models=True)['cases'] for p in z['traces']]])
        for depth in (20,100,200):
            paths=[]
            for label,key in (('old','legacy'),('new','nplayer_arena')):
                path=root/f'legacy-{depth}-{label}.jsonl';paths.append(path);sup.stage(f'legacy-{depth}-{label}',[c['binaries'][key],c['tables'],2,20261023659800+depth,path,'bot=check-call','bot=pot-pressure',depth,1])
            if sha(paths[0])!=sha(paths[1]):raise ValueError('legacy3P bytes changed')
            sup.stage(f'legacy-{depth}-replay',[c['python'],'-m','scripts.check_nplayer_policy_replay',paths[1]])
    pairs={};jobs={}
    for a,b in CONTRASTS:
        label=a+'-'+b;pairs[label]={};jobs[label]={}
        for f in c['fields']:
            name=f['name'];left=records['6b' if a=='3b' else a][name];right=records[b][name];job=cross_case(name,dict(tag=a,record=left),dict(tag=b,record=right));jobs[label][name]=job
            stage='pair-'+label+'-'+name;sup.stage(stage,[c['python'],'-m','scripts.nplayer_paired_evidence','pair',*job['traces'],*job['repeats'],*job['proofs']]);p=load(root/'measurements'/stage/'stdout.log')
            if p['blocks']!=c['blocks'] or p['schedule']!=c['schedule'] or p['root']!=c['root_base']+c['fields'].index(f):raise ValueError('paired scope differs')
            pairs[label][name]=p
    if sha(root/'models.json')!=catalog or (root/'failure.json').exists() or any(z['returncode']!=0 for z in load(root/'stage-costs.json')):raise ValueError('global successful stage/catalog barrier')
    write(root/'evaluation-verified.json',dict(status='passed',fields=8,contrasts=5,blocks_per_field=c['blocks'],physical_initial_hands=8*c['blocks']*12*2*3,reproduction_hands=8*c['blocks']*12*2*3,unique_initial_hands=8*c['blocks']*12*4,models_sha256=catalog,baseline_cross_job_trace_identity=True,manifests={tag:{p:sha(root/f'{tag}-{p}-manifest.json') for p in ('initial','repeat')} for tag in TAGS[1:]}))
    write(root/'verified-summary.json',dict(models=models,endpoints=endpoints,pairs=pairs,jobs=jobs,is_qualification_fixture=c['smoke']))
    sup.stage('global-readout',[c['python'],'-m',MODULE,'readout','--root',root])


def absolute_blocks(path,seatings):
    stream=evidence.rows(path);h=next(stream);values=[];part=[]
    for row in stream:
        focal=row['identities'].index(0);part.append(row['rewards'][focal]*100/h['identity']['big_blind'])
        if len(part)==seatings:values.append(statistics.mean(part));part=[]
    if part or len(values)!=h['blocks']:raise ValueError('absolute block counts differ')
    return values


def summarize(root):
    c=load(root/'config.json');validate(c)
    if (root/'failure.json').exists() or (root/'results.json').exists():raise ValueError('failed or already read out')
    data=load(root/'verified-summary.json');v=load(root/'evaluation-verified.json')
    if v['status']!='passed' or v['models_sha256']!=sha(root/'models.json') or any(z['returncode']!=0 for z in load(root/'stage-costs.json')):raise ValueError('global proof differs')
    if v['fields']!=8 or v['contrasts']!=5 or v['blocks_per_field']!=c['blocks'] or v['physical_initial_hands']!=8*c['blocks']*12*2*3 or set(data['pairs'])!={a+'-'+b for a,b in CONTRASTS}:raise ValueError('frozen global count/contrast inventory differs')
    baseline_hashes={}
    for tag in TAGS[1:]:
        for phase in ('initial','repeat'):
            p=root/f'{tag}-{phase}-manifest.json'
            if sha(p)!=v['manifests'][tag][phase] or load(p)!=manifest(root,c,data['models'],tag,phase):raise ValueError('frozen manifest differs')
        initial=load(root/f'{tag}-initial-manifest.json');repeat=load(root/f'{tag}-repeat-manifest.json')
        for left,right in zip(initial['cases'],repeat['cases']):
            for arm,path in enumerate(left['traces']):
                proof=load(root/'measurements'/f"replay-{tag}-{left['name']}-{arm}"/'stdout.log')
                if proof['status']!='passed' or proof['hands']!=c['blocks']*12 or proof['trace_sha256']!=sha(path) or sha(path)!=sha(right['traces'][arm]):raise ValueError('physical initial replay/reproduction differs')
                if arm==0 and baseline_hashes.setdefault(left['name'],proof['trace_sha256'])!=proof['trace_sha256']:raise ValueError('final cross-job baseline differs')
    for model in data['models'].values():
        for key,pin in (('path','sha256'),('checkpoint','checkpoint_sha256'),('source_policy','source_policy_sha256')):
            if sha(model[key])!=model[pin]:raise ValueError('final model hash differs')
        if sha(Path(model['mass'])/'receipt.json')!=model['mass_sha256'] or sha(Path(model['mass'])/'zero-keys.bin')!=model['audit']['zero_keys_sha256']:raise ValueError('final mass hash differs')
    absolute={};gates=[];tails={};supports={};from scipy.stats import t
    for label,pairs in data['pairs'].items():
        a,b=label.split('-');tails[label]={};supports[label]=prior.support_changes({'baseline':data['models'][a],'candidate':data['models'][b]},pairs)
        for name,pair in pairs.items():
            job=data['jobs'][label][name]
            for path,repeat,proof in zip(job['traces'],job['repeats'],job['proofs']):
                p=load(proof)
                if p['status']!='passed' or p['hands']!=c['blocks']*12 or p['trace_sha256']!=sha(path) or sha(path)!=sha(repeat):raise ValueError('final replay/reproduction differs')
            arms=[absolute_blocks(p,12) for p in job['traces']];values=pair['block_values_bb100']
            if len(values)!=c['blocks'] or any(not math.isclose(y-x,z,abs_tol=1e-9) for x,y,z in zip(*arms,values)):raise ValueError('absolute/paired contrast differs')
            group=absolute.setdefault(name,{})
            for tag,arm in zip((a,b),arms):
                z=evidence.interval(arm)
                if tag in group and group[tag]!=z:raise ValueError('cross-contrast absolute result differs')
                group[tag]=z
            mean=statistics.mean(values);squares=[(x-mean)**2 for x in values];total=sum(squares)
            tails[label][name]=dict(top10_squared_deviation_share=sum(sorted(squares,reverse=True)[:10])/total if total else 0,largest_positive=[dict(block=i,value_bb100=values[i]) for i in sorted(range(len(values)),key=values.__getitem__,reverse=True)[:5]],largest_negative=[dict(block=i,value_bb100=values[i]) for i in sorted(range(len(values)),key=values.__getitem__)[:5]],no_exclusions=True)
            if not c['smoke']:
                score=pair['contrast'];margin=0 if name=='trained' else -5;lower=score['mean_bb100']-float(t.ppf(1-.05/40,c['blocks']-1))*score['standard_error_bb100']
                gates.append(dict(contrast=label,field=name,mean_bb100=score['mean_bb100'],standard_error_bb100=score['standard_error_bb100'],lower_family95_bb100=lower,margin_bb100=margin,passed=lower>margin))
    for field in c['fields']:
        f=field['name'];p=data['pairs'];adj=[p[k][f]['block_values_bb100'] for k in ('3b-6b','6b-10b','10b-15b')];direct=p['3b-15b'][f]['block_values_bb100']
        if any(not math.isclose(sum(parts),z,abs_tol=1e-8) for parts,z in zip(zip(*adj),direct)):raise ValueError('adjacent/direct block additivity differs')
    if len(data['pairs'])!=5 or len(gates)!=(0 if c['smoke'] else 40):raise ValueError('incomplete contrast family')
    write(root/'results.json',dict(status='qualified-engineering' if c['smoke'] else 'settled-development',config_sha256=sha(root/'config.json'),**data,absolute_returns=absolute,gates=gates,tails=tails,support=supports,adjacent_direct_additivity=True,no_release_acceptance=True,no_extension=True,decision='report-development-trajectory-and-exploitation-support-tradeoff; no automatic follow-up or selected release winner'))
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
        if (q/'failure.json').exists() or s['status']!='complete' or sha(q/'results.json')!=s['result_sha256'] or result['status']!='qualified-engineering' or result.get('is_qualification_fixture') is not True or not qc['smoke'] or qc['source']!=c['source'] or result['config_sha256']!=sha(q/'config.json') or sha(q/'results.json')!=c['qualification_sha256']:raise ValueError('same-source bb128 qualification required')
        if c['accepted_seconds']!=load(SOURCE/PROPOSAL)['accepted_planning_seconds']:raise ValueError('accepted complete allocation required')
        diagnosis=Path(c['diagnosis']);owner=Path(c['owner_authorization'])
        if (sha(diagnosis/'results.json')!=c['diagnosis_sha256'] or load(diagnosis/'source.json')!=c['source'] or load(diagnosis/'status.json')['status']!='complete' or (diagnosis/'failure.json').exists()):raise ValueError('same-source completed diagnosis changed')
        if sha(owner)!=c['owner_authorization_sha256'] or load(owner).get('start_during_space_arrangement') is not True:raise ValueError('owner authorization changed')



def configure(root,build_path,smoke,qualification=None,accepted=None,diagnosis=None,owner=None):
    if root.exists():raise FileExistsError('output exists; no overwrite')
    if not smoke and accepted!=43200:raise ValueError('accepted complete allocation required')
    if not smoke:
        if not diagnosis or load(diagnosis/'status.json')['status']!='complete' or load(diagnosis/'status.json')['result_sha256']!=sha(diagnosis/'results.json') or (diagnosis/'failure.json').exists() or load(diagnosis/'results.json')['status']!='complete-descriptive-diagnosis':raise ValueError('completed saved trace diagnosis required')
        if not owner or load(owner).get('start_during_space_arrangement') is not True:raise ValueError('owner storage sequencing authorization required')
    scope=fixed(smoke);build=load(build_path);old=load('/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/config.json')
    c=dict(scope,fixed=scope,source=source(),proposal_sha256=sha(SOURCE/PROPOSAL),binaries=build['binaries'],build=str(build_path),build_sha256=sha(build_path),python=old['python'],python_sha256=old['python_sha256'],tables=old['tables'],table_sha256s=old['table_sha256s'],accepted_seconds=accepted,qualification=str(qualification) if qualification else None,qualification_sha256=sha(qualification/'results.json') if qualification else None,environment=mature.acceptance.thermal.python_environment(Path(old['python']))[1],diagnosis=str(diagnosis) if diagnosis else None,diagnosis_sha256=sha(diagnosis/'results.json') if diagnosis else None,owner_authorization=str(owner) if owner else None,owner_authorization_sha256=sha(owner) if owner else None)
    validate(c);root.mkdir(parents=True,exist_ok=False);write(root/'config.json',c);write(root/'status.json',dict(status='prepared'))


def run(root):
    if any((root/p).exists() for p in ('launch.json','failure.json','measurements')):raise FileExistsError('attempt exists; no retry')
    c=load(root/'config.json');validate(c);env={**os.environ,'NPLAYER_STOP_FILE':str(root/'STOP'),'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'};sup=base.Supervisor(root,env);original=sup.stage;config_sha=sha(root/'config.json')
    def stage(name,args):
        validate(c)
        if sha(root/'config.json')!=config_sha:raise ValueError('config changed')
        z=original(name,args);write(root/'measurements'/name/'receipt.json',z);return z
    sup.stage=stage;write(root/'launch.json',dict(pid=os.getpid(),epoch=time.time(),source=c['source']['commit'],config_sha256=config_sha))
    try:
        execute(root,c,sup);validate(c);write(root/'status.json',dict(status='complete',epoch=time.time(),result_sha256=sha(root/'results.json')))
    except BaseException as e:
        z=dict(error=repr(e),epoch=time.time(),no_automatic_retry=True)
        if hasattr(e,'resource_sample'):z['resource_sample']=e.resource_sample
        write(root/'failure.json',z);write(root/'status.json',dict(status='failed',**z));raise


def diagnose(root):
    if root.exists():raise FileExistsError('diagnosis root exists')
    root.mkdir(parents=True,exist_ok=False);write(root/'source.json',source());sup=base.Supervisor(root,{**os.environ,'NPLAYER_STOP_FILE':str(root/'STOP')});write(root/'launch.json',dict(pid=os.getpid(),epoch=time.time()))
    try:
        sup.stage('diagnosis',[sys.executable,'-m','scripts.nplayer_trace_divergence','--input-root','/home/dberweger/nplayer-five-player-candidate-20261023/main-v1','--output',root/'results.json'])
        write(root/'status.json',dict(status='complete',result_sha256=sha(root/'results.json'),epoch=time.time()))
    except BaseException as e:write(root/'failure.json',dict(error=repr(e),no_automatic_retry=True));raise
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
        sup.stage('focused-python',[sys.executable,'-m','unittest','tests.test_nplayer_six_player_candidate','tests.test_nplayer_trace_divergence','tests.test_nplayer_paired_evidence','-q'])
        write(root/'build-receipt.json',dict(status='passed',source=pins,tests_passed=True,binaries=binaries,sha256s={n:sha(p) for n,p in binaries.items()}))
        write(root/'status.json',dict(status='passed'))
    except BaseException as e:write(root/'failure.json',dict(error=repr(e),no_automatic_retry=True));raise



def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('build','diagnose','configure','run','readout'));p.add_argument('--root',type=Path,required=True);p.add_argument('--build',type=Path);p.add_argument('--qualification',type=Path);p.add_argument('--diagnosis',type=Path);p.add_argument('--owner',type=Path);p.add_argument('--smoke',action='store_true');p.add_argument('--accepted-seconds',type=int);a=p.parse_args()
    if sys.platform!='linux' or __import__('socket').gethostname()!='cygnus-x1':raise ValueError('bb128 only')
    if a.mode=='readout':summarize(a.root.absolute());return
    def stopped(sig,frame):raise InterruptedError(f'owner signal{sig}')
    for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,stopped)
    with open('/tmp/cfr-cygnus-exclusive.lock','a+') as normal,open('/tmp/cfr-six-player-candidate.lock','a+') as own:
        for lock in (normal,own):fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        root=a.root.absolute()
        if a.mode=='build':build(root)
        elif a.mode=='diagnose':diagnose(root)
        elif a.mode=='configure':configure(root,a.build,a.smoke,a.qualification,a.accepted_seconds,a.diagnosis,a.owner)
        else:run(root)


if __name__=='__main__':main()
