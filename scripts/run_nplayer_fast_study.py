"""Execute the owner-approved PR335 equal-node/equal-time study after qualification."""
import argparse
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import shutil
import time

from scripts import run_nplayer_storage_benchmark as guard
from scripts.run_nplayer_fast_qualification import legacy_holder

SEEDS=[2026101541,2026101542,2026101543]
ROOTS=[20261018335101+i for i in range(6)]


def cases():
    result=[]
    for i,seed in enumerate(SEEDS):
        for j,scope in enumerate(['nodes','clock']):
            f=f'fast-{seed}-{scope}';p=f'production-{seed}-'+('1b' if scope=='nodes' else 'clock')
            for reverse in [False,True]:
                result.append(dict(name=f'{seed}-{scope}-'+('reverse' if reverse else 'forward'),seed=seed,
                    scope=scope,root=ROOTS[2*i+j],blocks=8192,singleton=p if reverse else f,pair=f if reverse else p))
    return result


def run(root):
    c=json.loads((root/'config.json').read_text());q=Path(c['qualification_root'])
    if (q/'failure.json').exists():raise ValueError('qualification failed')
    passed=json.loads((q/'qualification-passed.json').read_text())
    if passed['status']!='passed':raise ValueError('qualification incomplete')
    threads=passed['selected_threads']
    first=json.loads((q/'launch.json').read_text())['utc']
    deadline=datetime.fromisoformat(first).timestamp()+7*3600
    remaining=deadline-time.time()
    if remaining<3*3600:raise RuntimeError('insufficient original campaign time remaining')
    guard.BUDGET=35_000_000_000
    with Path('/tmp/cfr-pr335-compute.lock').open('a') as own,Path('/tmp/cfr-cygnus-exclusive.lock').open('a') as legacy:
        fcntl.flock(own,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:fcntl.flock(legacy,fcntl.LOCK_EX|fcntl.LOCK_NB);background=None
        except BlockingIOError:
            background=legacy_holder()
            if background is None or '/home/dberweger/hu200-capacity-20261015/planning/archive_terminal_closeout_20261018.py run' not in background['command']:
                raise RuntimeError('unknown legacy holder; admission refused')
        supervisor=guard.Supervisor(root,own.fileno(),cpus=range(16),max_seconds=remaining,rss_limit=80*guard.GIB)
        row=supervisor.sample(None,'admission',0)
        if row['temperatures_c']['Package id 0']>=70 or row['temperatures_c']['Thermistor 15']>=80:raise RuntimeError('temperature admission refused')
        med=passed['median_training_seconds'][str(threads)]
        # Threefold extrapolation allowance from the pilot; final clocks are fixed, not extended.
        fast_estimate=max(600,med*50*3)
        quote=3*600+3*fast_estimate+3600
        if quote>remaining:raise RuntimeError('measured workload does not fit original deadline')
        guard.write(root/'admission.json',dict(pid=os.getpid(),initial_sample=row,threads=threads,
            qualification_sha256=guard.sha(q/'qualification-passed.json'),legacy_holder=background,
            original_deadline_epoch=deadline,projected_seconds=quote,source_commit=c['source_commit'],cases=cases()))
        env=dict(os.environ,RAYON_NUM_THREADS=str(threads),CARGO_BUILD_JOBS='4',OMP_NUM_THREADS='1',
            OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NPLAYER_K50_TABLES=c['tables'],CARGO_TARGET_DIR=str(root/'target'))
        env['PATH']='/home/dberweger/.cargo/bin:'+env['PATH']
        env['CARGO_ENCODED_RUSTFLAGS']='\x1f'.join(['--remap-path-prefix='+str(root)+'=strength-study','--remap-path-prefix=/home/dberweger/.cargo=cargo-home'])
        src=root/'source';manifest=str(src/'native/hu20-trainer/Cargo.toml')
        supervisor.execute('build',['cargo','build','--release','--locked','--offline','--manifest-path',manifest,
            '--example','nplayer_fast_strength','--example','nplayer_policy','--example','nplayer_arena'],src,env)
        binaries=root/'binaries';binaries.mkdir()
        for name in ['nplayer_fast_strength','nplayer_policy','nplayer_arena']:shutil.copy2(root/'target/release/examples'/name,binaries/name)
        guard.write(root/'binary-receipts.json',{p.name:guard.sha(p) for p in binaries.iterdir()})
        python=str(root/'venv/bin/python')
        supervisor.execute('environment-create',['python3','-m','venv',str(root/'venv')],root,env)
        supervisor.execute('environment-install',[python,'-m','pip','install','--disable-pip-version-check','numpy==1.26.4','scipy>=1.11,<2',
            'pokers @ git+https://github.com/dberweger2017/pokers.git@5db20e3d5d6862b32a7402035c1340b622d3b005'],root,env)
        inputs=json.loads((root/'input-manifest.json').read_text())
        for m in inputs.values():
            if guard.sha(m['path'])!=m['sha256']:raise ValueError('reference input hash mismatch')
        smoke=root/'harness-smoke'
        result=supervisor.execute('harness-smoke',[str(binaries/'nplayer_fast_strength'),c['tables'],str(smoke),'2026101833500','fast',str(threads),'3000000','0.2'],root,env)
        checkpoints=[e for e in result['events'] if e.get('event')=='checkpoint']
        if sorted(e['label'] for e in checkpoints)!=['clock','nodes'] or not any(e.get('event')=='complete' for e in result['events']):raise ValueError('endpoint smoke failed')
        if next(e for e in checkpoints if e['label']=='nodes')['sha256']!=passed['fast_identity_sha256']:raise ValueError('instrumented node endpoint differs from qualified CLI')
        for label in ['clock','nodes']:
            fixture=smoke/(label+'.gz')
            # Export smoke exercises the same library path; final parents are separately pinned.
            exported=root/('smoke-'+label+'-average.gz')
            supervisor.execute('smoke-export-'+label,[str(binaries/'nplayer_policy'),'export',str(fixture),guard.sha(fixture),'average',str(exported)],root,env)
            supervisor.execute('smoke-audit-'+label,[python,'-m','scripts.audit_nplayer_policy',str(fixture),str(exported)],root,env)
        smoke_root=root/'smoke-evaluation';smoke_root.mkdir()
        smoke_model=dict(path=str(root/'smoke-nodes-average.gz'),sha256=guard.sha(root/'smoke-nodes-average.gz'),strategy='average',scope=3)
        smoke_cases=[dict(case,blocks=2,root=20261018335001+i) for i,case in enumerate(cases())]
        smoke_models={name:smoke_model for case in smoke_cases for name in [case['singleton'],case['pair']]}
        smoke_manifest=root/'smoke-evaluation-manifest.json'
        guard.write(smoke_manifest,dict(format='nplayer-fast-strength-qualification-v1',cases=smoke_cases,models=smoke_models,
            tables=c['tables'],arena=str(binaries/'nplayer_arena'),arena_sha256=guard.sha(binaries/'nplayer_arena')))
        supervisor.execute('smoke-evaluation',[python,'-m','scripts.run_nplayer_fast_evaluation',str(smoke_manifest),str(smoke_root)],root,env)
        if json.loads((smoke_root/'evaluation-verified.json').read_text())['final_hands']!=144:raise ValueError('harness qualification count mismatch')
        guard.write(root/'pretraining-freeze.json',dict(status='qualified',cases=cases(),seed_order=SEEDS,
            threads=threads,roots_per_seat=8,training_seconds=600,node_target=1000000000,
            inputs=inputs,source_commit=c['source_commit'],instrumented_cli_identity='passed',deadline_epoch=deadline))
        outputs=root/'training';outputs.mkdir()
        export_plan=[]
        for seed in SEEDS:
            for recipe in ['fast','production']:
                out=outputs/f'{recipe}-{seed}'
                active=threads if recipe=='fast' else 1
                supervisor.cpus=set(range(16)) if active==16 else set(range(active))
                r=supervisor.execute(f'train-{recipe}-{seed}',[str(binaries/'nplayer_fast_strength'),c['tables'],str(out),str(seed),recipe,str(active),'1000000000','600'],root,env)
                checkpoints=[e for e in r['events'] if e.get('event')=='checkpoint']
                expected={'nodes','clock'} if recipe=='fast' else {'clock'}
                if {e['label'] for e in checkpoints}!=expected or not any(e.get('event')=='complete' for e in r['events']):raise ValueError('missing training endpoint')
                for e in checkpoints:
                    if e['label']=='clock' and not 600<=e['training_seconds']<=610:raise ValueError('clock endpoint missed')
                    if e['label']=='nodes' and not 1000000000<=e['nodes']<1000100000:raise ValueError('node endpoint missed')
                    export_plan.append(dict(id=f"{recipe}-{seed}-{e['label']}",checkpoint=e['checkpoint'],checkpoint_sha256=e['sha256'],export=str(out/(e['label']+'-average.gz'))))
                guard.write(root/'training-progress.json',dict(seed=seed,recipe=recipe,completed_exports=len(export_plan)))
        guard.write(root/'export-plan.json',dict(policy=str(binaries/'nplayer_policy'),models=export_plan))
        supervisor.cpus=set(range(16))
        supervisor.execute('prepare-models',[python,'-m','scripts.prepare_nplayer_fast_models',str(root)],root,env)
        models=json.loads((root/'models-audited.json').read_text())['models'];models.update(inputs)
        evaluation=dict(format='nplayer-fast-strength-evaluation-v1',cases=cases(),models=models,tables=c['tables'],arena=str(binaries/'nplayer_arena'),arena_sha256=guard.sha(binaries/'nplayer_arena'),source_commit=c['source_commit'])
        guard.write(root/'evaluation-manifest.json',evaluation)
        supervisor.execute('final-evaluation',[python,'-m','scripts.run_nplayer_fast_evaluation',str(root/'evaluation-manifest.json'),str(root)],root,env)
        verified=json.loads((root/'evaluation-verified.json').read_text())
        if verified['status']!='passed':raise ValueError('global evaluation barrier failed')
        guard.write(root/'status.json',dict(status='all-science-verified-readout-ready',final_hands=verified['final_hands'],source_commit=c['source_commit'],completed_at=time.time()))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);root=p.parse_args().root.resolve()
    try:run(root)
    except BaseException as error:guard.write(root/'failure.json',dict(error=repr(error),at=time.time()));raise


if __name__=='__main__':main()
