"""Owner-authorized PR362 study, queued behind PR361's exclusive timing run."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

SOURCE=Path(__file__).resolve().parents[1]
MODULE='scripts.run_matched_regression_study'
DEPENDENCY=Path('/home/dberweger/nplayer-inference-validation-20261020/main-v1')
SEEDS=(202610200601,202610200602)


def load(path):return json.loads(Path(path).read_text())
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(path,v):Path(path).write_text(json.dumps(v,indent=2)+'\n')


def copy_pin(source,target,pin):
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if sha(target)!=pin:raise ValueError('owned restored file changed')
        return
    h=hashlib.sha256()
    with Path(source).open('rb') as a,target.open('xb') as b:
        for chunk in iter(lambda:a.read(4*1024**2),b''):h.update(chunk);b.write(chunk)
        b.flush();os.fsync(b.fileno())
    if h.hexdigest()!=pin or sha(target)!=pin:raise ValueError('restored input differs; partial retained')


def configure(root,cache,source_commit):
    root=Path(root).absolute();root.mkdir(parents=True,exist_ok=False)
    v=load(SOURCE/'docs/reports/nplayer-bb100-confirmation/results.json')
    c=dict(authorization='owner-20261020-merge-one-run-two',source_commit=source_commit,seeds=SEEDS,
        dependency=str(DEPENDENCY),dependency_source='c06fc565',cache=str(Path(cache).absolute()),models={},traces={},
        tables='/home/dberweger/cygnus-qualification-20261014/tables',discovery_worlds=32,heldout_worlds=512)
    for seed in SEEDS:
        c['models'][str(seed)]={}
        for e in v['endpoints']:
            if e['seed']==seed:
                model=dict(e['model']);audit=next(a for a in v['mass_audits'] if a['seed']==seed and a['alias']==e['alias'])
                model['zero_keys_sha256']=audit['zero_keys_sha256'];c['models'][str(seed)][e['alias']]=model
        c['traces'][str(seed)]=[]
        for field in ('random','random-tight'):
            for reached in ('baseline','candidate'):
                suffix=f'/lineage-{seed}/comparison/evaluation/{field}-{reached}/play-0.jsonl'
                p=next(p for p in v['relocations'] if p['source'].endswith(suffix))
                # These are the exact frozen PR357 roots, not hidden action seeds.
                # Matrix roots: direct first, random +1, random-tight +8.
                root_seed=20261020610001+(seed-SEEDS[0])*100+(1 if field=='random' else 8)
                c['traces'][str(seed)].append(dict(path=p['source'],sha256=p['sha256'],seed=seed,field=field,reached=reached,root=root_seed))
    write(root/'config.json',c)


def restore(root,seed):
    root=Path(root);c=load(root/'config.json');folder=root/f'lineage-{seed}';folder.mkdir(exist_ok=True)
    traces=[]
    for task in c['traces'][str(seed)]:
        out=folder/'trace-inputs'/f"{task['field']}-{task['reached']}.jsonl"
        copy_pin(task['path'],out,task['sha256']);traces.append(dict(task,path=str(out)))
    write(folder/'trace-inputs.json',traces)
    models={}
    dependency=load(Path(c['dependency'])/'results.json')
    for alias,original in c['models'][str(seed)].items():
        model=dict(original);mass=folder/'inputs'/f'{alias}-mass'
        for name,pin in [('receipt.json',model['mass_sha256']),('zero-keys.bin',model['zero_keys_sha256'])]:
            copy_pin(Path(original['mass'])/name,mass/name,pin)
        model['mass']=str(mass)
        if seed==SEEDS[0]:
            source=dependency['models'][alias]
            if dependency['conversions'][alias]['source_policy_sha256']!=original['sha256'] or dependency['audits'][alias]['status']!='passed':raise ValueError('dependency model source differs')
            out=folder/'inputs'/f'{alias}.bin';copy_pin(source['path'],out,source['sha256']);model.update(path=str(out),sha256=source['sha256'])
        else:
            out=folder/'inputs'/f'{alias}.gz';copy_pin(original['path'],out,original['sha256']);model['path']=str(out)
        models[alias]=model
    write(folder/'models.json',models)


def fixture_states(root):
    from scripts.nplayer_matched_regression import legal_state
    root=Path(root);c=load(root/'config.json');out=root/'fixture-states.jsonl'
    rows=[]
    for task in c['traces'][str(SEEDS[0])]:
        if task['reached']!='baseline':continue
        # Verified inputs have already restored into the owned root.
        path=root/f'lineage-{SEEDS[0]}'/'trace-inputs'/f"{task['field']}-baseline.jsonl"
        with path.open() as f:
            next(f)
            for line in f:
                r=json.loads(line);indices=[i for i,a in enumerate(r['actors']) if r['identities'][a]==0]
                if not indices:continue
                s=legal_state(r,indices[-1],seed=task['seed'],field=task['field'],reached=task['reached'],root=task['root'])
                s['split']='discovery';rows.append(s);break
    if len(rows)!=2:raise ValueError('two fixture fields required')
    with out.open('x') as f:
        for r in rows:f.write(json.dumps(r)+'\n')


def staging(root,seed):
    from scripts.nplayer_bb100_confirmation import stage_files
    root=Path(root);c=load(root/'config.json');folder=root/f'lineage-{seed}'
    files=[p for p in folder.rglob('*') if p.is_file() and not p.is_symlink() and p.name not in ('results.json','manifest.json','models.json','native-result.json','extraction.json','trace-inputs.json')]
    stage_files(root,Path(c['cache']),files)


def run(root):
    from scripts.nplayer_pruning_strength import Supervisor
    root=Path(root).absolute();c=load(root/'config.json')
    if (root/'launch.json').exists():raise ValueError('existing launch; no scientific retry')
    if c['authorization']!='owner-20261020-merge-one-run-two' or c['seeds']!=list(SEEDS) or Path(c['dependency'])!=DEPENDENCY:raise ValueError('fixed authorization/input family changed')
    with Path('/tmp/cfr-nplayer-matched-regression.lock').open('a') as own,Path('/tmp/cfr-cygnus-exclusive.lock').open('a') as normal:
        fcntl.flock(own,fcntl.LOCK_EX|fcntl.LOCK_NB)
        write(root/'launch.json',dict(pid=os.getpid(),at=time.time(),source=c['source_commit'],config_sha256=sha(root/'config.json'),science_started=False))
        write(root/'status.json',dict(status='queued',dependency=c['dependency']))
        # Blocking on the existing benchmark mutex consumes no science compute.
        fcntl.flock(normal,fcntl.LOCK_EX)
        supervisor=Supervisor(root,own.fileno(),normal.fileno())
        env=dict(os.environ,PYTHONPATH=str(SOURCE),RAYON_NUM_THREADS='8',CARGO_BUILD_JOBS='4')
        def execute(label,command):
            write(root/'status.json',dict(status='running',phase=label,at=time.time()))
            return supervisor.execute(label,list(map(str,command)),str(SOURCE),env)
        def self_command(label,*args):return execute(label,[sys.executable,'-m',MODULE,*args])
        try:
            if (DEPENDENCY/'failure.json').exists() or load(DEPENDENCY/'status.json')['status']!='complete':raise ValueError('loader dependency did not complete cleanly; no regression science started')
            d=load(DEPENDENCY/'results.json')
            if d['status']!='settled' or d['source']!=c['dependency_source'] or d['parity']['status']!='passed' or d['parity']['hands']!=884736:raise ValueError('loader dependency parity proof differs')
            write(root/'dependency-verified.json',dict(result_sha256=sha(DEPENDENCY/'results.json'),source=d['source'],parity=d['parity']))
            write(root/'admission.json',supervisor.sample(None,'admission',0))
            cargo='/home/dberweger/.cargo/bin/cargo';manifest=SOURCE/'native/hu20-trainer/Cargo.toml'
            execute('build',[cargo,'build','--release','--locked','--manifest-path',manifest,'--example','nplayer_matched_regression','--example','nplayer_inference'])
            execute('qualification',[cargo,'test','--locked','--manifest-path',manifest,'--lib','multi_counterfactual::tests'])
            native=SOURCE/'native/hu20-trainer/target/release/examples/nplayer_matched_regression';converter=native.with_name('nplayer_inference')
            self_command('restore-first-inputs','restore',root,SEEDS[0])
            self_command('prepare-real-fixture','fixture-states',root)
            fixture=root/'fixture-v1'
            execute('fixture-create',[native,'fixture',c['tables'],root/'fixture-states.jsonl',fixture])
            execute('fixture-play',[native,fixture/'manifest.json'])
            execute('fixture-read',[sys.executable,'-m','scripts.nplayer_matched_regression','read',fixture])
            fr=load(fixture/'results.json')
            if fr['status']!='settled' or fr['native']['selected']!=2:raise ValueError('complete real-K50 fixture failed')
            write(root/'calibration.json',dict(selected_states=2,qualified=True,
                projected_max_counterfactual_seconds=fr['native']['counterfactual_seconds']*16,
                observed_load_cost_source=str(DEPENDENCY/'results.json'),scope='Synthetic changed rows; qualification, no strength result'))
            write(root/'science-started.json',dict(at=time.time(),source=c['source_commit'],qualification_result_sha256=sha(fixture/'results.json')))
            panels=[]
            for seed in SEEDS:
                folder=root/f'lineage-{seed}'
                if seed!=SEEDS[0]:self_command(f'restore-{seed}','restore',root,seed)
                models=load(folder/'models.json')
                if seed!=SEEDS[0]:
                    for alias,model in models.items():
                        out=folder/'inputs'/f'{alias}.bin'
                        stage=execute(f'convert-{seed}-{alias}',[converter,'convert',model['path'],model['sha256'],out,'--mass',Path(model['mass'])/'receipt.json',model['mass_sha256']])
                        converted=next(v for v in stage['events'] if v.get('status')=='converted')
                        execute(f'audit-{seed}-{alias}',[converter,'verify',model['path'],model['sha256'],out,converted['sha256'],'--mass',Path(model['mass'])/'receipt.json',model['mass_sha256']])
                        models[alias]=dict(model,path=str(out),sha256=converted['sha256'])
                execute(f'extract-{seed}',[sys.executable,'-m','scripts.nplayer_matched_regression','extract',folder])
                m=dict(threads=8,models=models,tables=c['tables'],states=str(folder/'legal-states.jsonl'),states_sha256=sha(folder/'legal-states.jsonl'),
                    discovery_worlds=32,heldout_worlds=512,belief_root=20261020362001+(seed-SEEDS[0]),
                    **{k:str(folder/v) for k,v in [('matched','matched.jsonl'),('selected','selected.jsonl'),('values','values.jsonl'),('result','native-result.json')]})
                write(folder/'manifest.json',m)
                execute(f'evaluate-{seed}',[native,folder/'manifest.json'])
                execute(f'readout-{seed}',[sys.executable,'-m','scripts.nplayer_matched_regression','read',folder])
                result=load(folder/'results.json')
                if result['status']!='settled' or result['native']['states']!=load(folder/'extraction.json')['states'] or result['native']['selected']>16:raise ValueError('lineage readout/counts not settled')
                panels.append(dict(seed=seed,result_sha256=sha(folder/'results.json'),native=result['native'],selected_panels=len(result['panel'])))
                self_command(f'stage-{seed}','stage',root,seed)
            write(root/'results.json',dict(status='settled',source=c['source_commit'],config_sha256=sha(root/'config.json'),lineages=panels,
                dependency_result_sha256=sha(DEPENDENCY/'results.json'),completed=time.time(),limitations='Conditional selected-state Monte Carlo investigation, not a population strength or mechanism claim.'))
            write(root/'status.json',dict(status='complete',at=time.time()))
        except BaseException as error:
            write(root/'failure.json',dict(error=repr(error),at=time.time(),phase=load(root/'status.json')));raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode');p.add_argument('args',nargs=argparse.REMAINDER);a=p.parse_args()
    if a.mode=='configure':configure(*a.args)
    elif a.mode=='run':run(*a.args)
    elif a.mode=='restore':restore(a.args[0],int(a.args[1]))
    elif a.mode=='fixture-states':fixture_states(*a.args)
    elif a.mode=='stage':staging(a.args[0],int(a.args[1]))
    else:p.error('unknown mode')


if __name__=='__main__':main()
