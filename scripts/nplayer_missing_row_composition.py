"""Fixed arena-only experiment. Same-source qualification and accepted quote first."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import socket
import sys
import time
from scripts import nplayer_bb200_feasibility as tools
from scripts import nplayer_paired_evidence as evidence
from scripts import qualify_nplayer_composition as small

SOURCE=Path(__file__).resolve().parents[1]
PROPOSAL=SOURCE/'configs/research/nplayer-missing-row-composition.json'
PARENT=Path('/home/dberweger/nplayer-six-player-capacity-20261024/main-v1')
RESULT='c12ec77d688db05cbdcb1ce64c603d1914169a3cb4ce992e2748e7710057684a'
MODULE='scripts.nplayer_missing_row_composition'


def fixed():
    return dict(format='nplayer-missing-positive-experiment-v1',players=6,stack_bb=100,blocks=4096,threads=8,root_base=20261024750001,schedule=small.SCHEDULE,fields=[dict(name=n,opponents=o) for n,o in small.FIELDS],focals=['control','augmented'],composition='nplayer-missing-positive-v1',no_training_or_exports=True,no_extension=True)


def qualification(path):
    status=tools.read(path/'status.json');q=tools.read(path/'results.json')
    if (path/'failure.json').exists() or status['status']!='complete' or tools.sha(path/'results.json')!=status['result_sha256'] or q['status']!='qualified-engineering':raise ValueError('completed qualification required')
    for flag in ['all_initial_replayed','exact_original_zero_mass_precedence','identity_composition_rng_parity','composition_self_exact_zero','diagnostics_rng_parity','serial_parallel_parity','old_ordinary_arena_byte_parity','corrupted_selection_refused']:
        if q.get(flag) is not True:raise ValueError('qualification proof missing')
    return q


def protected_models():
    s=tools.read(PARENT/'status.json');r=tools.read(PARENT/'results.json')
    if s['status']!='complete' or s['result_sha256']!=RESULT or tools.sha(PARENT/'results.json')!=RESULT or (PARENT/'failure.json').exists() or tools.read(PARENT/'evaluation-verified.json')['status']!='passed':raise ValueError('completed PR419 required')
    models={alias:r['models'][source] for alias,source in [('control','control'),('donor','candidate'),('peer','peer')]}
    if any(m['audit']['status']!='passed' or m['binary_audit']['status']!='passed' or m['scope']!=3 or m['strategy']!='average' for m in models.values()):raise ValueError('audited full-average source required')
    return models


def metadata(models):
    return {alias:{'path':m['path'],'resolved':str(Path(m['path']).resolve()),'size':Path(m['path']).stat().st_size,'mtime_ns':Path(m['path']).stat().st_mtime_ns,'mass_receipt_sha256':tools.sha(Path(m['mass'])/'receipt.json')} for alias,m in models.items()}


def validate(c):
    if c['fixed']!=fixed() or c['proposal_sha256']!=tools.sha(PROPOSAL):raise ValueError('fixed scope/quote changed')
    owner=tools.read(Path(c['owner']));quote=tools.read(PROPOSAL)
    if tools.sha(c['owner'])!=c['owner_sha256'] or owner.get('approved_scope')!=fixed() or owner.get('approved_quote_sha256')!=c['proposal_sha256'] or owner.get('accepted_planning_seconds')!=quote['proposed_planning_seconds'] or owner.get('manual_resources_reviewed') is not True:raise ValueError('accepted exact owner scope/quote required')
    q=qualification(Path(c['qualification']))
    if tools.sha(Path(c['qualification'])/'results.json')!=c['qualification_sha256'] or q['source']!=c['source'] or q['binary_sha256']!=tools.sha(c['binary']):raise ValueError('same-source Linux qualification/binary changed')
    m4=tools.read(Path(c['m4_qualification']))
    if tools.sha(c['m4_qualification'])!=c['m4_qualification_sha256'] or m4['status']!='qualified-engineering' or m4['source']!=q['source']:raise ValueError('same-source M4 qualification changed')
    for p,digest in c['source']['files'].items():
        if tools.sha(SOURCE/p)!=digest:raise ValueError('frozen source changed')
    if protected_models()!=c['models'] or metadata(c['models'])!=c['model_metadata']:raise ValueError('protected source metadata changed')
    if tools.sha(c['python'])!=c['python_sha256']:raise ValueError('Python changed')
    for name,digest in c['table_sha256s'].items():
        if tools.sha(Path(c['tables'])/name)!=digest:raise ValueError('K50 changed')


def configure(a):
    if a.root.exists():raise FileExistsError('attempt root exists')
    q=qualification(a.qualification);old=tools.read(PARENT/'config.json');models=protected_models()
    c=dict(fixed=fixed(),source=q['source'],proposal_sha256=tools.sha(PROPOSAL),owner=str(a.owner.absolute()),owner_sha256=tools.sha(a.owner),qualification=str(a.qualification.absolute()),qualification_sha256=tools.sha(a.qualification/'results.json'),m4_qualification=str(a.m4_qualification.absolute()),m4_qualification_sha256=tools.sha(a.m4_qualification),binary=str((a.qualification/'build/release/examples/nplayer_paired_arena').absolute()),models=models,model_metadata=metadata(models),tables=old['tables'],table_sha256s=old['table_sha256s'],python=old['python'],python_sha256=old['python_sha256'])
    validate(c);a.root.mkdir(parents=True);tools.write(a.root/'config.json',c);os.chmod(a.root/'config.json',0o444);tools.write(a.root/'status.json',dict(status='prepared'))


def manifest(root,c,phase):
    m=small.manifest(root,c['models'],c['tables'],phase,threads=8)
    for i,case in enumerate(m['cases']):case['blocks']=4096;case['root']=20261024750001+i
    return m


def execute(root,c,sup):
    manifests=[]
    for phase in ['initial','repeat']:
        m=manifest(root,c,phase);p=root/(phase+'-manifest.json');tools.write(p,m);sup.stage('arena-'+phase,[c['binary'],'batch',p]);manifests.append(m)
    pairs={};selection={};proofs={}
    for left,right in zip(*(m['cases'] for m in manifests)):
        name=left['name'];receipts=[]
        for arm in range(2):
            if tools.sha(left['traces'][arm])!=tools.sha(right['traces'][arm]):raise ValueError('reproduction differs')
            stage='replay-'+name+'-'+str(arm);sup.stage(stage,[c['python'],'-m','scripts.nplayer_paired_evidence','replay',left['traces'][arm]]);receipts.append(root/'measurements'/stage/'stdout.log')
        sup.stage('pair-'+name,[c['python'],'-m','scripts.nplayer_paired_evidence','pair',*left['traces'],*right['traces'],*receipts]);pairs[name]=tools.read(root/'measurements'/('pair-'+name)/'stdout.log')
        sup.stage('selector-'+name,[c['python'],'-m','scripts.nplayer_composition_evidence','structural',left['traces'][1]]);selection[name]=tools.read(root/'measurements'/('selector-'+name)/'stdout.log')
        p=pairs[name]
        if p['blocks']!=4096 or p['root']!=left['root'] or p['schedule']!=small.SCHEDULE or p['hands_per_arm']!=49152:raise ValueError('paired scope incomplete')
        if selection[name]['hands']!=49152 or selection[name]['decisions']!=sum(sum(row) for row in p['coverage'][1]['by_identity'][0]):raise ValueError('composed decisions excluded')
        proofs[name]=dict(initial=[tools.sha(p) for p in left['traces']],reproduction=[tools.sha(p) for p in right['traces']],replay=[tools.sha(p) for p in receipts],pair=tools.sha(root/'measurements'/('pair-'+name)/'stdout.log'),selector=tools.sha(root/'measurements'/('selector-'+name)/'stdout.log'))
    if len(pairs)!=8 or any(s['returncode']!=0 for s in sup.costs):raise ValueError('global field/stage barrier')
    tools.write(root/'evaluation-verified.json',dict(status='passed',fields=8,initial_hands=786432,reproduction_hands=786432,proofs=proofs,all_initial_independently_replayed=True,no_exclusions=True))
    tools.write(root/'verified-summary.json',dict(pairs=pairs,selection=selection,proofs=proofs))
    sup.stage('global-readout',[c['python'],'-m',MODULE,'readout','--root',root])


def readout(root):
    c=tools.read(root/'config.json');validate(c)
    if (root/'failure.json').exists() or (root/'results.json').exists() or tools.read(root/'evaluation-verified.json')['status']!='passed' or any(s['returncode']!=0 for s in tools.read(root/'stage-costs.json')):raise ValueError('global proof/stage barrier')
    data=tools.read(root/'verified-summary.json');pairs=data['pairs'];selection=data['selection'];proofs=data['proofs']
    if len(pairs)!=8 or len(selection)!=8 or len(proofs)!=8:raise ValueError('incomplete readout')
    for model in c['models'].values():
        if tools.sha(model['path'])!=model['sha256']:raise ValueError('final model bytes changed')
    for phase in ['initial','repeat']:
        m=tools.read(root/(phase+'-manifest.json'))
        for case in m['cases']:
            expected=proofs[case['name']]['initial' if phase=='initial' else 'reproduction']
            if [tools.sha(p) for p in case['traces']]!=expected:raise ValueError('final trace bytes changed')
    # Only now calculate/report any scientific outcomes.
    from scipy.stats import t
    from scripts.nplayer_six_player_candidate import absolute_blocks
    gates=[];absolute={};tails={};initial=tools.read(root/'initial-manifest.json')
    for name,pair in pairs.items():
        case=next(x for x in initial['cases'] if x['name']==name)
        arms=[absolute_blocks(p,12) for p in case['traces']]
        if any(abs(b-a-v)>1e-8 for a,b,v in zip(*arms,pair['block_values_bb100'])):raise ValueError('absolute/paired accounting differs')
        absolute[name]={a:evidence.interval(v) for a,v in zip(['control','composed'],arms)}
        z=pair['contrast'];margin=0 if name=='trained' else -5
        lower=z['mean_bb100']-float(t.ppf(1-.05/8,4095))*z['standard_error_bb100']
        gates.append(dict(field=name,**z,lower_family95_bb100=lower,margin_bb100=margin,passed=lower>margin))
        values=pair['block_values_bb100'];squares=[(v-z['mean_bb100'])**2 for v in values];total=sum(squares)
        tails[name]=dict(top10_squared_deviation_share=sum(sorted(squares,reverse=True)[:10])/total if total else 0,largest_positive=[dict(block=i,value_bb100=values[i]) for i in sorted(range(len(values)),key=values.__getitem__,reverse=True)[:5]],largest_negative=[dict(block=i,value_bb100=values[i]) for i in sorted(range(len(values)),key=values.__getitem__)[:5]],no_exclusions=True)
    tools.write(root/'results.json',dict(status='settled-development',config_sha256=tools.sha(root/'config.json'),models=c['models'],pairs=pairs,selection=selection,gates=gates,absolute_returns=absolute,tails=tails,all_eight_gates_passed=all(g['passed'] for g in gates),decision='Consider independent confirmation only if useful gain and all safeguards pass; otherwise no promotion. No automatic extension or tuning.',no_release_acceptance=True))


def run(root):
    if any((root/p).exists() for p in ['launch.json','failure.json','measurements','results.json']):raise FileExistsError('attempt exists; no retry')
    c=tools.read(root/'config.json');validate(c);pin=tools.sha(root/'config.json');env=dict(os.environ,NPLAYER_STOP_FILE=str(root/'STOP'),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1');sup=tools.Supervisor(root,env);original=sup.stage
    def stage(name,args):
        validate(c)
        if tools.sha(root/'config.json')!=pin:raise ValueError('config changed')
        return original(name,args)
    sup.stage=stage;tools.write(root/'launch.json',dict(pid=os.getpid(),epoch=time.time(),config_sha256=pin))
    try:execute(root,c,sup);validate(c);tools.write(root/'status.json',dict(status='complete',epoch=time.time(),result_sha256=tools.sha(root/'results.json')))
    except BaseException as e:tools.write(root/'failure.json',dict(error=repr(e),no_automatic_retry=True));tools.write(root/'status.json',dict(status='failed'));raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['configure','run','readout']);p.add_argument('--root',type=Path,required=True)
    for flag in ['qualification','m4-qualification','owner']:p.add_argument('--'+flag,type=Path)
    a=p.parse_args()
    if sys.platform!='linux' or socket.gethostname()!='cygnus-x1':raise ValueError('mature experiment is bb128-only')
    if a.mode=='readout':readout(a.root.absolute());return
    if a.mode=='configure' and any(getattr(a,k) is None for k in ['qualification','m4_qualification','owner']):raise ValueError('qualification/M4 proof/accepted owner receipt required')
    def stopped(sig,frame):raise InterruptedError(f'owner signal{sig}')
    for sig in [signal.SIGTERM,signal.SIGINT]:signal.signal(sig,stopped)
    with open('/tmp/cfr-cygnus-exclusive.lock','a+') as normal,open('/tmp/cfr-nplayer-composition.lock','a+') as own:
        for lock in [normal,own]:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if a.mode=='configure':configure(a)
        else:run(a.root.absolute())


if __name__=='__main__':main()
