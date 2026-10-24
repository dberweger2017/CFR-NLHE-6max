"""One prospective500M/250M six-player comparison, never an automatic follow-up."""
import argparse
import fcntl
import json
import math
import os
from pathlib import Path
import signal
import statistics
import subprocess
import sys
import time
from scripts import nplayer_six_player_candidate as six
from scripts import nplayer_five_player_candidate as prior
from scripts import nplayer_bb200_feasibility as base
from scripts import nplayer_bb200_model_campaign as mature
from scripts import nplayer_four_player_feasibility as four
from scripts import nplayer_paired_evidence as evidence
from scripts import nplayer_shared_observations as shared

SOURCE=Path(__file__).resolve().parents[1]
MODULE='scripts.nplayer_six_player_capacity'
PROPOSAL='configs/research/nplayer-six-player-capacity.json'
PRIOR_ROOT=Path('/home/dberweger/nplayer-six-player-candidate-20261023')
PRIOR_RESULT_SHA='361e40b70f195d578592d1155738340917d753fdd2cbd3866236adee3bd3e5c1'
NAMES=six.NAMES
load=prior.load
write=prior.write
sha=prior.sha


def fixed(smoke=False):
    return dict(format='nplayer-six-player-capacity-v1',players=6,stack_bb=100,
        seed=2026102461991 if smoke else 2026102361001,target=200000 if smoke else 10000000000,
        cap=20000 if smoke else 500000000,control_cap=10000 if smoke else 250000000,
        threads=16,roots_per_seat=8,last_average_street=3,pruning=False,freeze_at_cap=True,fast_gzip=True,
        smoke=smoke,fresh_candidate=True,schedule=six.SCHEDULE,blocks=2 if smoke else 4096,
        root_base=20261024659901 if smoke else 20261024650001,
        fields=[dict(name=n,opponents=['peer' if s=='baseline' else s for s in specs]) for n,specs in six.FIELDS],
        shared_models=['control','candidate'],shared_weighting='All focal decision occurrences from both arms; source-arm strata; no dedup or outcome/status/action filtering.',
        interval_family='8one-sided95Studentt/Bonferroni,trainedlower>0,otherslower>-5',
        resource_stops='CPU90/Thermistor15-100/missing-nonfinite;ownerSTOP/mutex/correctness',no_time_rss_disk_swap_stop=True,
        incomplete_policy='Terminal; preserve partials; no automatic science retry/recovery/extension',cleanup='owner-managed-only')


def source():
    if subprocess.check_output(['git','status','--porcelain'],cwd=SOURCE,text=True).strip():raise ValueError('clean committed source required')
    paths=subprocess.check_output(['git','ls-files','native','scripts','src','configs/research','tests/test_nplayer_six_player_capacity.py','tests/test_nplayer_shared_observations.py','docs/nplayer-six-player-capacity.md'],cwd=SOURCE,text=True).splitlines()
    return dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip(),files={p:sha(SOURCE/p) for p in paths})


def protected_models():
    root=PRIOR_ROOT/'main-v1';s=load(root/'status.json');v=load(root/'evaluation-verified.json')
    if s['status']!='complete' or s['result_sha256']!=PRIOR_RESULT_SHA or sha(root/'results.json')!=PRIOR_RESULT_SHA or (root/'failure.json').exists() or v['status']!='passed' or any(z['returncode']!=0 for z in load(root/'stage-costs.json')):raise ValueError('completed protected PR417 proofs required')
    r=load(root/'results.json')
    if r['status']!='settled-development':raise ValueError('protected PR417 result not settled')
    expected=load(SOURCE/'docs/reports/nplayer-six-player-candidate/results.json')
    models={'control':r['models']['10b'],'peer':r['models']['3b']}
    for alias,tag in [('control','10b'),('peer','3b')]:
        if models[alias]!=expected['models'][tag] or models[alias]['audit']['status']!='passed' or models[alias]['binary_audit']['status']!='passed':raise ValueError('protected control/peer pins differ')
    return models


def manifest(root,c,models,phase,diagnostics=True,self_only=False,serial=False,gzip_models=False):
    folder=root/('arena-'+phase);folder.mkdir(exist_ok=True);cases=[]
    fields=[dict(name='self',opponents=['peer']+['bot=check-call']*2+['bot=pot-pressure']*2)] if self_only else c['fields']
    for i,f in enumerate(fields):
        case=dict(name=f['name'],players=6,stack_bb=100,blocks=c['blocks'],root=c['root_base']+i,schedule=c['schedule'],
            focals=['control','control' if self_only else 'candidate'],opponents=f['opponents'],
            traces=[str(folder/(f['name']+'-'+a+'.jsonl')) for a in ('a','b')],summary=str(folder/(f['name']+'-cost.json')))
        if diagnostics:case['shared_models']=c['shared_models']
        cases.append(case)
    chosen=models
    if gzip_models:chosen={k:dict(v,path=v['source_policy'],sha256=v['source_policy_sha256']) for k,v in models.items()}
    return dict(format='nplayer-paired-manifest-v1',tables=c['tables'],threads=1 if serial else 8,models=chosen,cases=cases)


def native(root,c,sup,models,phase,**kw):
    m=manifest(root,c,models,phase,**kw);p=root/(phase+'-manifest.json');write(p,m)
    sup.stage('arena-'+phase,[c['binaries']['nplayer_paired_arena'],'batch',p]);return m


def train(root,c,sup,name,cap,target,parent=None,threads=16):
    if not c['smoke'] and parent is not None:raise ValueError('main candidate must train from scratch')
    path=root/(name+'.gz');cost=sup.stage(name,four.train_command(c,path,target,c['seed'],cap,parent,threads))
    row=load(root/'measurements'/name/'stdout.log');four.checkpoint(row,path,target,c['seed'],cap,6)
    return dict(row,checkpoint=str(path),checkpoint_bytes=path.stat().st_size,active_training_seconds=row['elapsed_seconds']-row['save_seconds'],stage_wall_seconds=cost['wall_seconds'])


def fixture_models(root,c,sup):
    models={}
    for name,target,cap in [('peer',50000,c['control_cap']),('control',c['target'],c['control_cap']),('candidate',c['target'],c['cap'])]:
        cp=train(root,c,sup,name+'-train',cap,target)
        models[name]=mature.convert(root,c,sup.stage,c['seed'],name,cp)
        ref=train(root,c,sup,name+'-reference',cap,target,threads=1)
        if cp['sha256']!=ref['sha256']:raise ValueError('same-cap thread parity differs')
        if name=='candidate':
            half=train(root,c,sup,'candidate-half',cap,target//2)
            resume=train(root,c,sup,'candidate-resume',cap,target,half)
            if cp['sha256']!=resume['sha256']:raise ValueError('same-cap resume parity differs')
    return models


def execute(root,c,sup):
    if c['smoke']:models=fixture_models(root,c,sup);endpoint=None
    else:
        models=protected_models()
        endpoint=train(root,c,sup,'candidate-train',c['cap'],c['target'])
        if endpoint['frozen_at'] is None or endpoint['entries']<c['cap']:raise ValueError('candidate did not reach/freeze declared capacity')
        models['candidate']=mature.convert(root,c,sup.stage,c['seed'],'candidate',endpoint)
        if models['candidate']['audit']['rows']<=models['control']['audit']['rows']:raise ValueError('larger capacity has no larger retained table')
    write(root/'models.json',models);catalog=sha(root/'models.json')
    initial=native(root,c,sup,models,'initial');repeat=native(root,c,sup,models,'repeat');records={}
    for left,right in zip(initial['cases'],repeat['cases']):
        records[left['name']]=six.verify_case(root,c,sup,left,right,left['name'])
    if c['smoke']:
        off=native(root,c,sup,models,'diagnostics-off',diagnostics=False)
        serial=native(root,c,sup,models,'serial',serial=True)
        legacy=manifest(root,c,models,'legacy-paired',diagnostics=False);write(root/'legacy-paired-manifest.json',legacy)
        sup.stage('legacy-paired',[c['binaries']['legacy_paired'],'batch',root/'legacy-paired-manifest.json'])
        for now,old in zip(off['cases'],legacy['cases']):
            if any(sha(x)!=sha(y) for x,y in zip(now['traces'],old['traces'])):raise ValueError('ordinary paired traces changed from PR417')
        zipped=native(root,c,sup,models,'gzip',gzip_models=True)
        for left,other,one,gzip in zip(initial['cases'],off['cases'],serial['cases'],zipped['cases']):
            for arm in range(2):
                shared.ordinary_payload_parity(left['traces'][arm],other['traces'][arm])
                if sha(left['traces'][arm])!=sha(one['traces'][arm]):raise ValueError('shared serial/parallel trace differs')
                # Model digest pins change with encoding; payloads and shared queries may not.
                trace_encoding_parity(left['traces'][arm],gzip['traces'][arm])
        self_a=native(root,c,sup,models,'self',self_only=True);self_b=native(root,c,sup,models,'self-repeat',self_only=True)
        z=six.verify_case(root,c,sup,self_a['cases'][0],self_b['cases'][0],'self')
        pair=evidence.verified_pair(*z['initial']['traces'],*z['repeat']['traces'],*z['proofs'])
        if not pair['self_exact_zero']:raise ValueError('shared identical-policy contrast not exact zero')
        write(root/'shared-source-catalog.json',{a:models[a] for a in c['shared_models']})
        sup.stage('shared-source-audit',[c['python'],'-m','scripts.nplayer_shared_observations','source',root/'shared-source-catalog.json',*[p for z in initial['cases'] for p in z['traces']]])
        for depth in (20,100,200):
            paths=[]
            for label,key in [('old','legacy'),('new','nplayer_arena')]:
                path=root/f'legacy-{depth}-{label}.jsonl';paths.append(path);sup.stage(f'legacy-{depth}-{label}',[c['binaries'][key],c['tables'],2,20261024659800+depth,path,'bot=check-call','bot=pot-pressure',depth,1])
            if sha(paths[0])!=sha(paths[1]):raise ValueError('legacy3P trace changed')
            sup.stage(f'legacy-{depth}-replay',[c['python'],'-m','scripts.check_nplayer_policy_replay',paths[1]])
    pairs={};diagnostics={}
    for case in initial['cases']:
        name=case['name'];z=records[name];paths=[*z['initial']['traces'],*z['repeat']['traces'],*z['proofs']]
        sup.stage('pair-'+name,[c['python'],'-m','scripts.nplayer_paired_evidence','pair',*paths]);pairs[name]=load(root/'measurements'/('pair-'+name)/'stdout.log')
        sup.stage('shared-'+name,[c['python'],'-m','scripts.nplayer_shared_observations','pair',*paths]);diagnostics[name]=load(root/'measurements'/('shared-'+name)/'stdout.log')
        if pairs[name]['blocks']!=c['blocks'] or pairs[name]['root']!=case['root'] or pairs[name]['schedule']!=c['schedule']:raise ValueError('frozen paired scope differs')
        expected=sum(sum(row) for arm in pairs[name]['coverage'] for row in arm['by_identity'][0])
        if diagnostics[name]['observations']!=expected:raise ValueError('shared observations exclude focal decisions')
    if sha(root/'models.json')!=catalog or any(z['returncode']!=0 for z in load(root/'stage-costs.json')):raise ValueError('global model/stage barrier')
    write(root/'evaluation-verified.json',dict(status='passed',models_sha256=catalog,pair_receipts={f['name']:sha(root/'measurements'/('pair-'+f['name'])/'stdout.log') for f in c['fields']},shared_receipts={f['name']:sha(root/'measurements'/('shared-'+f['name'])/'stdout.log') for f in c['fields']},fields=8,blocks_per_field=c['blocks'],initial_hands=8*c['blocks']*12*2,reproduction_hands=8*c['blocks']*12*2,all_focal_observations_included=True,manifests={phase:sha(root/(phase+'-manifest.json')) for phase in ['initial','repeat']}))
    write(root/'verified-summary.json',dict(models=models,endpoint=endpoint,pairs=pairs,shared_observations=diagnostics,records=records))
    sup.stage('global-readout',[c['python'],'-m',MODULE,'readout','--root',root])


def trace_encoding_parity(a,b):
    streams=[evidence.rows(p) for p in (a,b)];headers=[next(s) for s in streams]
    for h in headers:
        for p in h['policies']:
            if 'sha256' in p:p.pop('sha256')
        for p in h['shared_models']:p['pin'].pop('sha256')
    if headers[0]!=headers[1]:raise ValueError('gzip/binary header payload differs')
    count=0
    for count,pair in enumerate(__import__('itertools').zip_longest(*streams),1):
        if None in pair or pair[0]!=pair[1]:raise ValueError('gzip/binary shared payload differs')
    if count!=headers[0]['hands']:raise ValueError('gzip/binary incomplete inventory')


def summarize(root):
    c=load(root/'config.json');validate(c)
    if (root/'failure.json').exists() or (root/'results.json').exists():raise ValueError('failed/already read out')
    data=load(root/'verified-summary.json');v=load(root/'evaluation-verified.json')
    if v['status']!='passed' or v['models_sha256']!=sha(root/'models.json') or any(z['returncode']!=0 for z in load(root/'stage-costs.json')):raise ValueError('final proof/catalog barrier')
    for phase in ['initial','repeat']:
        if sha(root/(phase+'-manifest.json'))!=v['manifests'][phase] or load(root/(phase+'-manifest.json'))!=manifest(root,c,data['models'],phase):raise ValueError('final frozen manifest differs')
    for model in data['models'].values():
        for path,digest in [('path','sha256'),('checkpoint','checkpoint_sha256'),('source_policy','source_policy_sha256')]:
            if sha(model[path])!=model[digest]:raise ValueError('final model pin changed')
        if sha(Path(model['mass'])/'receipt.json')!=model['mass_sha256']:raise ValueError('final mass receipt differs')
    gates=[];absolute={};tails={}
    for field in c['fields']:
        name=field['name'];pair=data['pairs'][name];record=data['records'][name]
        pp=root/'measurements'/('pair-'+name)/'stdout.log';sp=root/'measurements'/('shared-'+name)/'stdout.log'
        if sha(pp)!=v['pair_receipts'][name] or sha(sp)!=v['shared_receipts'][name] or load(pp)!=pair or load(sp)!=data['shared_observations'][name]:raise ValueError('final paired/shared summaries changed')
        for trace,repeat,proof in zip(record['initial']['traces'],record['repeat']['traces'],record['proofs']):
            p=load(proof)
            if p['status']!='passed' or p['hands']!=c['blocks']*12 or sha(trace)!=p['trace_sha256'] or sha(trace)!=sha(repeat):raise ValueError('final physical replay/reproduction differs')
        arms=[six.absolute_blocks(p,12) for p in record['initial']['traces']];values=pair['block_values_bb100']
        if len(values)!=c['blocks'] or any(not math.isclose(b-a,x,abs_tol=1e-9) for a,b,x in zip(*arms,values)):raise ValueError('final absolute/paired returns differ')
        absolute[name]={tag:evidence.interval(v) for tag,v in zip(['control','candidate'],arms)}
        mean=statistics.mean(values);squared=[(x-mean)**2 for x in values];total=sum(squared)
        tails[name]=dict(top10_squared_deviation_share=sum(sorted(squared,reverse=True)[:10])/total if total else 0,largest_positive=[dict(block=i,value_bb100=values[i]) for i in sorted(range(len(values)),key=values.__getitem__,reverse=True)[:5]],largest_negative=[dict(block=i,value_bb100=values[i]) for i in sorted(range(len(values)),key=values.__getitem__)[:5]],no_exclusions=True)
        if not c['smoke']:
            from scipy.stats import t
            score=pair['contrast'];margin=0 if name=='trained' else -5;lower=score['mean_bb100']-float(t.ppf(1-.05/8,c['blocks']-1))*score['standard_error_bb100']
            gates.append(dict(field=name,**score,lower_family95_bb100=lower,margin_bb100=margin,passed=lower>margin))
    if len(data['pairs'])!=8 or len(data['shared_observations'])!=8 or len(gates)!=(0 if c['smoke'] else 8):raise ValueError('incomplete capacity family')
    write(root/'results.json',dict(status='qualified-engineering' if c['smoke'] else 'settled-development',config_sha256=sha(root/'config.json'),**data,absolute_returns=absolute,gates=gates,tails=tails,no_release_acceptance=True,no_extension=True,decision='Report one-seed capacity/support/exploitation/cost tradeoff; no automatic follow-up'))


def validate(c):
    if c['fixed']!=fixed(c['fixed']['smoke']) or any(c.get(k)!=v for k,v in c['fixed'].items()):raise ValueError('frozen capacity scope changed')
    if c['source']!=source() or sha(SOURCE/PROPOSAL)!=c['proposal_sha256']:raise ValueError('source/proposal changed')
    build=load(c['build'])
    if sha(c['build'])!=c['build_sha256'] or build['source']!=c['source'] or not build['tests_passed'] or not build['trainer_unchanged']:raise ValueError('exact source build proof changed')
    for name,path in c['binaries'].items():
        if path!=build['binaries'][name] or sha(path)!=build['sha256s'][name]:raise ValueError('binary changed')
    if sha(c['python'])!=c['python_sha256'] or mature.acceptance.thermal.python_environment(Path(c['python']))[1]!=c['environment']:raise ValueError('pinned Python environment changed')
    for name,digest in c['table_sha256s'].items():
        if sha(Path(c['tables'])/name)!=digest:raise ValueError('K50 changed')
    if not c['smoke']:
        q=Path(c['qualification']);qc=load(q/'config.json');qs=load(q/'status.json');qr=load(q/'results.json')
        if (q/'failure.json').exists() or qs['status']!='complete' or sha(q/'results.json')!=qs['result_sha256'] or sha(q/'results.json')!=c['qualification_sha256'] or qr['status']!='qualified-engineering' or qc['source']!=c['source'] or not qc['smoke']:raise ValueError('same-source completed capacity qualification required')
        owner=load(c['owner']);quote=load(SOURCE/PROPOSAL)
        if sha(c['owner'])!=c['owner_sha256'] or owner.get('approved_quote_sha256')!=c['proposal_sha256'] or owner.get('approved_scope')!=fixed() or owner.get('accepted_planning_seconds')!=quote['proposed_planning_seconds'] or owner.get('manual_resources_reviewed') is not True:raise ValueError('accepted exact quote/scope and manual resource review required')
        if c['protected_models']!=protected_models():raise ValueError('protected control/peer changed')


def configure(root,build_path,smoke=False,qualification=None,owner=None):
    if root.exists():raise FileExistsError('attempt root exists; no overwrite')
    if not smoke and (owner is None or qualification is None):raise ValueError('owner accepted quote and qualification required before main')
    old=load('/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/config.json');scope=fixed(smoke);build=load(build_path)
    c=dict(scope,fixed=scope,source=source(),proposal_sha256=sha(SOURCE/PROPOSAL),build=str(build_path),build_sha256=sha(build_path),binaries=build['binaries'],python=old['python'],python_sha256=old['python_sha256'],tables=old['tables'],table_sha256s=old['table_sha256s'],environment=mature.acceptance.thermal.python_environment(Path(old['python']))[1],qualification=str(qualification) if qualification else None,qualification_sha256=sha(qualification/'results.json') if qualification else None,owner=str(owner) if owner else None,owner_sha256=sha(owner) if owner else None,protected_models=None if smoke else protected_models())
    validate(c);root.mkdir(parents=True,exist_ok=False);write(root/'config.json',c);write(root/'status.json',dict(status='prepared'))


def build(root):
    if root.exists():raise FileExistsError('build exists; no overwrite')
    pins=source();oldbuild=load(PRIOR_ROOT/'build-v1/build-receipt.json')
    allowed={'native/hu20-trainer/examples/support/nplayer_paired_host.rs','native/hu20-trainer/examples/support/nplayer_shared_observation.rs'}
    oldnative={k:v for k,v in oldbuild['source']['files'].items() if k.startswith('native/') and k not in allowed};newnative={k:v for k,v in pins['files'].items() if k.startswith('native/') and k not in allowed}
    if oldnative!=newnative:raise ValueError('native trainer or unrelated source changed')
    root.mkdir(parents=True,exist_ok=False);env={**os.environ,'CARGO_TARGET_DIR':str(root/'target'),'CARGO_BUILD_JOBS':'4','RAYON_NUM_THREADS':'4'};sup=base.Supervisor(root,env);cargo=str(Path.home()/'.cargo/bin/cargo');args=['--release','--locked','--offline','--manifest-path',str(SOURCE/'native/hu20-trainer/Cargo.toml')]
    try:
        sup.stage('native-tests',[cargo,'test',*args,'--lib','--example','nplayer_paired_arena','--example','nplayer_arena'])
        sup.stage('native-build',[cargo,'build',*args,*[a for n in NAMES for a in ['--example',n]]])
        old=load('/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/config.json');binaries={n:str(root/'target/release/examples'/n) for n in NAMES};binaries['legacy']=old['binaries']['nplayer_arena'];binaries['legacy_paired']=oldbuild['binaries']['nplayer_paired_arena']
        if sha(binaries['legacy_paired'])!=oldbuild['sha256s']['nplayer_paired_arena']:raise ValueError('protected PR417paired binary changed')
        if sha(binaries['legacy'])!=old['binary_sha256s']['nplayer_arena']:raise ValueError('protected legacy binary changed')
        sup.stage('focused-python',[sys.executable,'-m','unittest','tests.test_nplayer_six_player_capacity','tests.test_nplayer_shared_observations','tests.test_nplayer_paired_evidence','-q'])
        write(root/'build-receipt.json',dict(status='passed',source=pins,tests_passed=True,trainer_unchanged=True,binaries=binaries,sha256s={n:sha(p) for n,p in binaries.items()}));write(root/'status.json',dict(status='passed'))
    except BaseException as e:write(root/'failure.json',dict(error=repr(e),no_automatic_retry=True));raise


def run(root):
    if any((root/p).exists() for p in ['launch.json','failure.json','measurements']):raise FileExistsError('attempt exists; no retry')
    c=load(root/'config.json');validate(c);env={**os.environ,'NPLAYER_STOP_FILE':str(root/'STOP'),'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'};sup=base.Supervisor(root,env);original=sup.stage;pin=sha(root/'config.json')
    def stage(name,args):
        validate(c)
        if sha(root/'config.json')!=pin:raise ValueError('config changed')
        return original(name,args)
    sup.stage=stage;write(root/'launch.json',dict(pid=os.getpid(),epoch=time.time(),source=c['source']['commit'],config_sha256=pin))
    try:execute(root,c,sup);validate(c);write(root/'status.json',dict(status='complete',epoch=time.time(),result_sha256=sha(root/'results.json')))
    except BaseException as e:
        failure=dict(error=repr(e),epoch=time.time(),no_automatic_retry=True)
        if hasattr(e,'resource_sample'):failure['resource_sample']=e.resource_sample
        write(root/'failure.json',failure);write(root/'status.json',dict(status='failed',**failure));raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['build','configure','run','readout']);p.add_argument('--root',required=True,type=Path);p.add_argument('--build',type=Path);p.add_argument('--smoke',action='store_true');p.add_argument('--qualification',type=Path);p.add_argument('--owner',type=Path);a=p.parse_args()
    if sys.platform!='linux' or __import__('socket').gethostname()!='cygnus-x1':raise ValueError('bb128 only')
    if a.mode=='readout':summarize(a.root.absolute());return
    def stopped(sig,frame):raise InterruptedError(f'owner signal{sig}')
    for sig in [signal.SIGTERM,signal.SIGINT]:signal.signal(sig,stopped)
    with open('/tmp/cfr-cygnus-exclusive.lock','a+') as normal,open('/tmp/cfr-six-player-capacity.lock','a+') as own:
        for lock in [normal,own]:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if a.mode=='build':build(a.root.absolute())
        elif a.mode=='configure':configure(a.root.absolute(),a.build,a.smoke,a.qualification,a.owner)
        else:run(a.root.absolute())


if __name__=='__main__':main()
