"""Finite real-K50 correctness fixtures for issue354, never the3B→10B run."""
import json
from pathlib import Path
import time

from scripts import nplayer_bb100_continuation as study
from scripts import nplayer_bb100_overnight as bounded
from scripts import nplayer_pruning_strength as prior
from scripts import run_nplayer_storage_benchmark as guard
from scripts.nplayer_overnight import load


def compare_trajectories(left, right, diagnostic=False):
    with Path(left).open() as a, Path(right).open() as b:
        ah,bh=json.loads(next(a)),json.loads(next(b))
        fields=('identity','blocks','hands','seed','policies','distinct_policy_instances')
        if any(ah[k]!=bh[k] for k in fields):raise ValueError('fixture header differs')
        count=0
        from itertools import zip_longest
        for x,y in zip_longest(a,b):
            if x is None or y is None:raise ValueError('fixture trace length differs')
            x,y=json.loads(x),json.loads(y)
            if diagnostic:y.pop('lookups')
            if x!=y:raise ValueError('diagnostics/mixed host changed action/deal/payoff trajectory')
            count+=1
        if count!=ah['hands']:raise ValueError('incomplete fixture')
    return count


def execute(root, receipt, tables, python, environment, stage):
    seed=2026101935401
    config=study.training_config(tables,root/'reference',root/'STOP',target=200000,cap=10000,seed=seed)
    guard.write(root/'reference-config.json',config)
    ref=stage('reference-native',[receipt['binaries']['reference'],root/'reference-config.json'])
    reference=bounded.model(ref,'200000')
    first=study.training_config(tables,root/'first',root/'STOP',target=100000,cap=10000,seed=seed)
    guard.write(root/'first-config.json',first)
    value=stage('first-native',[receipt['binaries']['train'],root/'first-config.json'])
    baseline=bounded.model(value,'100000')
    resumed=study.training_config(tables,root/'resumed',root/'STOP',model=baseline,target=200000,cap=10000,seed=seed)
    guard.write(root/'resumed-config.json',resumed)
    value=stage('resume-native',[receipt['binaries']['train'],root/'resumed-config.json'])
    candidate=bounded.model(value,'200000')
    if any(candidate[k]!=reference[k] for k in ('sha256','checkpoint_sha256')):
        raise ValueError('historical fresh and new resumed checkpoint/export bytes differ')
    cps=[bounded.events(load(root/'measurements'/name/'result.json'),'checkpoint')[-1] for name in ('first-native','resume-native','reference-native')]
    if len({x['keyset_sha256'] for x in cps})!=1 or any(x['frozen_at'] is None for x in cps):
        raise ValueError('qualification did not exercise fixed membership')
    models={}
    for alias,model in [('baseline',baseline),('candidate',candidate)]:
        stage('audit-'+alias,study.audit_model(str(python),model,root/(alias+'-mass')))
        models[alias]=study.mass_model(model,root/(alias+'-mass'),cps[0]['keyset_sha256'])
    folder=root/'comparison';folder.mkdir()
    m=dict(smoke=True,models=models,tables=str(tables),arena=receipt['binaries']['arena'],
           arena_sha256=receipt['hashes']['arena'],cases=study.cases(True),keyset_sha256=cps[0]['keyset_sha256'])
    guard.write(folder/'evaluation-manifest.json',m)
    stage('mixed-diagnostic-fixtures',[str(python),'-m','scripts.nplayer_bb100_continuation','batch',folder])
    guard.write(folder/'status.json',dict(status='verified-readout-ready'))
    stage('read-fixtures',[str(python),'-m','scripts.nplayer_bb100_continuation','read',folder])
    # Repeat just the first pass with diagnostics off to prove no RNG/decision effects.
    native=dict(tables=str(tables),threads=16,models=models,keyset_sha256=cps[0]['keyset_sha256'],diagnostics=False,cases=[])
    out=root/'diagnostics-off';out.mkdir()
    for c in m['cases']:
        native['cases'].append(dict(c,trace=str(out/(c['name']+'.jsonl')),summary=str(out/(c['name']+'.json'))))
    guard.write(root/'diagnostics-off.json',native)
    stage('diagnostics-off',[receipt['binaries']['arena'],'batch',root/'diagnostics-off.json'])
    same=sum(compare_trajectories(out/(c['name']+'.jsonl'),folder/'evaluation'/c['name']/'play-0.jsonl',True) for c in m['cases'])
    legacy=dict(tables=str(tables),threads=16,stack_bb=100,cases=[])
    for c in m['cases']:
        if c['players'][1]!=c['players'][2]:continue
        def spec(name):return bounded.spec(name,models)
        legacy['cases'].append(dict(c,trace=str(out/(c['name']+'-legacy.jsonl')),
            summary=str(out/(c['name']+'-legacy.json')),singleton=spec(c['players'][0]),pair=spec(c['players'][1])))
    guard.write(root/'legacy.json',legacy)
    stage('legacy-host-parity',[receipt['binaries']['legacy'],'batch',root/'legacy.json'])
    old_same=sum(compare_trajectories(row['trace'],folder/'evaluation'/row['name']/'play-0.jsonl',True) for row in legacy['cases'])
    result=dict(status='passed',build_receipt_sha256=guard.sha(Path(receipt['_root'])/'build-receipt.json'),
                source_files=study.source_pins(),environment=environment,fixture=True,
                fixture_hands=same,reproduction_hands=same,legacy_parity_hands=old_same,
                resume_checkpoint_sha256=candidate['checkpoint_sha256'],resume_policy_sha256=candidate['sha256'],
                keyset_sha256=cps[0]['keyset_sha256'],models=models,
                evaluation_cost=load(folder/'evaluation-cost.json'),at=time.time())
    guard.write(root/'qualification.json',result)
    guard.write(root/'status.json',dict(status='qualified',at=time.time()))


def qualify(root, build_root, tables, python):
    python,environment=prior.python_environment(python)
    receipt=study.checked_build(build_root)
    receipt['_root']=str(build_root)
    root.mkdir(parents=True,exist_ok=False)
    study.supervised(root,lambda stage:execute(root,receipt,tables,python,environment,stage))
