"""Owner-authorized PR346 final-seed continuation, without a swap stop."""
import argparse
import fcntl
import os
from pathlib import Path
import time

from scripts import nplayer_overnight as campaign
from scripts.nplayer_overnight_thermal_handoff import ContinuedScalars, ContinuationSupervisor, FROZEN, read_events

SEED=campaign.SEEDS[-1]
MAX_SECONDS=4*3600


def completed_model(checkpoints, exported, audit):
    final=[e for e in checkpoints if e.get('event')=='checkpoint'][-1]
    trained=[e for e in checkpoints if e.get('event')=='trained'][-1]
    if (final['target']!=30_000_000_000 or trained['nodes']<30_000_000_000 or
            audit['status']!='passed' or audit['checkpoint_sha256']!=final['sha256'] or
            audit['policy_sha256']!=exported['sha256'] or audit['strategy']!='average' or
            audit['last_average_street']!=3 or audit['rows']!=trained['entries'] or
            exported['mode']!='average'):
        raise ValueError('completed model proof differs')
    return final


def final_seed_plan(events):
    saves=[e for e in events if e.get('event')=='checkpoint']
    trained=[e for e in events if e.get('event')=='trained']
    if len(saves)!=1 or saves[0]['target']!=10_000_000_000 or len(trained)!=1 or trained[0]['target']!=10_000_000_000:
        raise ValueError('third-seed recovery requires its sole completed10B save')
    return dict(checkpoint=saves[0],trained=trained[0],targets=[20_000_000_000,30_000_000_000],
                probe_nodes=[15_000_000_000,20_000_000_000,25_000_000_000,30_000_000_000])


def finish(original, previous, root):
    with Path('/tmp/cfr-nplayer-overnight.lock').open('a') as own,Path('/tmp/cfr-cygnus-exclusive.lock').open('a') as legacy:
        for lock in (own,legacy):fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if root.exists():raise ValueError('finish root already exists; no duplicate/retry')
        c=campaign.load(original/'config.json')
        if c['source_commit']!=FROZEN or campaign.load(original/'pretraining-freeze.json')['status']!='qualified':
            raise ValueError('original qualification/source mismatch')
        failed=campaign.load(previous/'failure.json')
        if failed['error']!="RuntimeError('swap growth stop')":raise ValueError('unexpected previous failure')
        plan=final_seed_plan(read_events(previous/f'measurements/training-{SEED}/stdout.log'))
        cp=plan['checkpoint']
        if Path(cp['path'])!=previous/f'training-{SEED}/10000000000.gz':raise ValueError('unexpected checkpoint path')
        finals={}
        for seed in campaign.SEEDS[:2]:
            label=f'training-{seed}'+('-thermal100' if seed==campaign.SEEDS[0] else '')
            proofs={stage:campaign.load(previous/'measurements'/name/'result.json') for stage,name in
                    [('training',label),('export',f'export-{seed}'),('audit',f'audit-{seed}')]}
            if any(p['returncode']!=0 for p in proofs.values()):raise ValueError('incomplete finished model')
            exported=campaign.load(previous/f'measurements/export-{seed}/stdout.log')
            audit=campaign.load(previous/f'measurements/audit-{seed}/stdout.log')
            final=completed_model(proofs['training']['events'],exported,audit)
            finals[str(seed)]=dict(path=str(previous/f'final-{seed}-average.gz'),sha256=exported['sha256'],
                checkpoint=final['path'],checkpoint_sha256=final['sha256'],strategy='average',scope=3)
        rate=campaign.load(previous/f'measurements/training-{SEED}/progress.json')['nodes_per_second']
        all_results=[campaign.load(previous/'measurements'/name/'result.json') for name in ('training-2026101541-thermal100','training-2026101542')]
        saves=[e['save_seconds'] for p in all_results for e in p['events'] if e.get('event')=='checkpoint']
        export=max(campaign.load(previous/f'measurements/export-{s}/result.json')['wall_seconds'] for s in campaign.SEEDS[:2])
        audit_time=max(campaign.load(previous/f'measurements/audit-{s}/result.json')['wall_seconds'] for s in campaign.SEEDS[:2])
        forecast=1.25*((30_000_000_000-plan['trained']['nodes'])/min(rate,4_590_000)+2*max(saves)+export+audit_time)+3600
        if forecast>MAX_SECONDS:raise RuntimeError('remaining-work cost admission refused')
        cache_parent=Path(c['cache']);cache=cache_parent/root.name
        launch=time.time();deadline=launch+MAX_SECONDS
        root.mkdir();cache.mkdir(exist_ok=False)
        c=dict(c,cache=str(cache));campaign.guard.write(root/'config.json',c)
        for name in ('source','target','tensorboard'):(root/name).symlink_to(original/name,target_is_directory=True)
        campaign.guard.write(root/'launch.json',dict(epoch=launch,deadline_epoch=deadline,max_seconds=MAX_SECONDS,
            supervisor_pid=os.getpid(),
            owner_authorization='please resume the run; swap guard removed',native_source_commit=FROZEN,
            original_root=str(original),previous_root=str(previous),original_expired_deadline=1792387148.4860098))
        campaign.guard.write(root/'remaining-cost-quote.json',dict(projected_remaining_seconds=forecast,
            remaining_training_nodes=30_000_000_000-plan['trained']['nodes'],max_seconds=MAX_SECONDS,
            final_allowance_seconds=3600,completed_models_reused=finals))
        logs=ContinuedScalars(root/'tensorboard',plan['trained'],seed=SEED)
        retained=[original,previous,Path('/tmp/nplayer-overnight-20261018-resume100')]
        s=ContinuationSupervisor(root,cache,own.fileno(),deadline-time.time(),logs,origin=original,
            retained_roots=retained,cache_parent=cache_parent)
        s.seed=SEED;s.thermistor_limit=100
        if s.swap_limit_bytes is not None:raise ValueError('swap guard was not removed in deployed controller')
        sample=s.sample(None,'resume-admission',10_000_000_000)
        if sample['temperatures_c']['Package id 0']>=70 or sample['temperatures_c']['Thermistor 15']>=80:
            raise RuntimeError('thermal admission')
        # Reserve future checkpoint/export bytes separately from HDD-only final traces.
        expected_model_bytes=11_700_000_000
        if s.remaining<expected_model_bytes:raise RuntimeError('remaining tmpfs model reservation refused')
        campaign.guard.json_event_original=campaign.guard.json_event;campaign.guard.json_event=s.event
        for name,digest in c['source_files'].items():
            if campaign.guard.sha(original/'source'/name)!=digest:raise ValueError('frozen source changed')
        native_info=campaign.load(original/'native-binary.json');native=Path(native_info['path'])
        if campaign.guard.sha(native)!=native_info['sha256']:raise ValueError('native binary changed')
        models={f'anchor-{seed}':dict(c['anchors'][str(seed)],strategy='average',scope=3) for seed in campaign.SEEDS}
        models.update({f'final-{seed}':model for seed,model in finals.items()})
        pinned=[(cp['path'],cp['sha256'])]+[(c[k],c[k+'_sha256']) for k in ('policy','arena')]
        for model in models.values():
            pinned.append((model['path'],model['sha256']))
            if 'checkpoint' in model:pinned.append((model['checkpoint'],model['checkpoint_sha256']))
        for path,digest in pinned:
            if campaign.guard.sha(path)!=digest:raise ValueError('input model/binary SHA mismatch')
        s.sample(None,'resume-inputs-verified',10_000_000_000)
        campaign.guard.write(root/'active.json',dict(status='active',at=time.time(),supervisor_pid=os.getpid(),
            cpu_stop_c=90,thermistor15_stop_c=100,swap_guard_enabled=False,deadline_epoch=deadline,
            resumed_seed=SEED,checkpoint=cp,reused_models=finals,native_sha256=native_info['sha256'],
            controller_hashes={p.name:campaign.guard.sha(p) for p in Path(__file__).parent.glob('*.py')}))
        campaign.preserve(root,cache,['launch.json','active.json','remaining-cost-quote.json','config.json'])
        src=root/'source';env=dict(os.environ,RAYON_NUM_THREADS='16',CARGO_BUILD_JOBS='4',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        env['PATH']='/home/dberweger/.cargo/bin:'+env['PATH']
        def stage(name,cmd,keep=False):
            if not keep:campaign.guard.write(root/'status.json',dict(status=name,at=time.time(),seed=SEED))
            result=s.execute(name,list(map(str,cmd)),src,env)
            campaign.preserve(root,cache,['measurements/'+name]);return result
        label=f'training-{SEED}-noswap'
        cfg=dict(seed=SEED,threads=16,tables=c['tables'],input=cp['path'],input_sha256=cp['sha256'],out=str(root/label),
            targets=plan['targets'],probe_nodes=plan['probe_nodes'],probe_blocks=128,probe_root=20261018348021,stop_file=str(root/'STOP'))
        path=root/(label+'-config.json');campaign.guard.write(path,cfg)
        result=stage(label,[native,path]);campaign.preserve(root,cache,[label,path.name])
        final=[e for e in result['events'] if e.get('event')=='checkpoint'][-1]
        if final['target']!=30_000_000_000:raise ValueError('missing final checkpoint')
        output=root/f'final-{SEED}-average.gz'
        stage(f'export-{SEED}',[c['policy'],'export',final['path'],final['sha256'],'average',output])
        stage(f'audit-{SEED}',[c['python'],'-m','scripts.audit_nplayer_policy',final['path'],output])
        models[f'final-{SEED}']=dict(path=str(output),sha256=campaign.guard.sha(output),strategy='average',scope=3,
            checkpoint=final['path'],checkpoint_sha256=final['sha256'])
        campaign.preserve(root,cache,[output.name])
        manifest=dict(arena=c['arena'],arena_sha256=c['arena_sha256'],tables=c['tables'],models=models,smoke=False,
            cases=campaign.cases(),evaluation_directory=str(cache/'evaluation'))
        campaign.guard.write(root/'evaluation-manifest.json',manifest)
        stage('final-evaluation',[c['python'],'-m','scripts.nplayer_overnight','batch',root])
        campaign.guard.write(root/'status.json',dict(status='verified-readout-ready',at=time.time()))
        stage('readout',[c['python'],'-m','scripts.nplayer_overnight','read',root],keep=True)
        campaign.guard.write(root/'status.json',dict(status='complete',at=time.time()))
        logs.close();campaign.preserve(root,cache,['evaluation','tensorboard']+[p.name for p in root.glob('*.json')])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('original',type=Path);p.add_argument('previous',type=Path);p.add_argument('root',type=Path);a=p.parse_args()
    try:finish(a.original,a.previous,a.root)
    except BaseException as error:
        active=a.root/'launch.json'
        # A duplicate invocation must not alter another supervisor's evidence.
        if active.exists():
            owner=campaign.load(active)['supervisor_pid']
            if owner==os.getpid():
                failure=dict(error=repr(error),at=time.time())
                if hasattr(error,'resource_sample'):failure['resource_sample']=error.resource_sample
                campaign.guard.write(a.root/'failure.json',failure)
                try:
                    cache=Path(campaign.load(a.root/'config.json')['cache'])
                    campaign.preserve(a.root,cache,[p.name for p in a.root.iterdir() if p.name not in ('source','target','tensorboard')])
                except BaseException as e:campaign.guard.write(a.root/'preservation-failure.json',dict(error=repr(e)))
        raise
