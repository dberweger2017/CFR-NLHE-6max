"""Issue356: two fresh fixed-membership continuations and cyclic cross-seed checks.

Preparation never launches science. Only `run` consumes the owner's explicit
launch authorization. Historical PR350/355 models are read-only references.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import time

from scripts import nplayer_bb100_continuation as old
from scripts import nplayer_bb100_overnight as bounded
from scripts import nplayer_pruning_strength as prior
from scripts import run_nplayer_storage_benchmark as guard
from scripts.nplayer_overnight import load

SOURCE = Path(__file__).resolve().parents[1]
MODULE = 'scripts.nplayer_bb100_confirmation'
SEEDS = (202610200601, 202610200602)
ORIGINAL = 2026101935003
TARGETS = (3_000_000_000, 10_000_000_000)
REFERENCE_ROOT = Path('/home/dberweger/nplayer-bb100-10b-20261019/main-v1')


def matrix(index, smoke=False):
    rows = old.cases(smoke)
    first = (20261020619001 if smoke else 20261020610001) + index * 100
    first_old = rows[0]['root']
    return [dict(r, root=first+r['root']-first_old) for r in rows]


def cross_cases(smoke=False):
    seeds = (ORIGINAL,) + SEEDS
    rows = []
    for i, seed in enumerate(seeds):
        other = seeds[(i+1) % 3]
        for version in ('candidate', 'baseline'):
            rows.append(dict(name=f'cross-{seed}-{version}', group='cross', seed=seed,
                opponent_seed=other, root=(20261020619901 if smoke else 20261020610301)+i,
                blocks=2 if smoke else 8192, singleton=f'{version}-{seed}', pair=f'baseline-{other}'))
    return rows


def expected_loads(rows):
    cache = set()
    count = 0
    for row in rows:
        needed = {row['singleton'], row['pair']}
        for name in (row['singleton'], row['pair']):
            if name not in cache:
                if len(cache) >= 2:
                    cache.intersection_update(needed)
                cache.add(name)
                count += 1
    return count


def checked_endpoint(result, seed, target, cap, parent=None):
    cp = bounded.validate_trajectory(result, cap, target)
    model = bounded.model(result, str(target))
    with gzip.open(model['checkpoint'], 'rt') as f:
        h = json.loads(next(f))
    with gzip.open(model['path'], 'rt') as f:
        p = json.loads(next(f))
    if (h['seed'] != seed or cp['nodes'] != h['counts']['nodes']
            or p['source_checkpoint_sha256'] != model['checkpoint_sha256']
            or p['identity'] != h['game'] or p['strategy'] != 'average'
            or p['last_average_street'] != 3 or p['entries'] != cp['entries']):
        raise ValueError('endpoint seed/export identity differs')
    if parent and any(cp[k] != parent[k] for k in ('entries','keyset_sha256','frozen_at')):
        raise ValueError('within-lineage frozen membership changed')
    return model, cp


def stage_files(root, cache, paths):
    """Owner-authorized relocation of only this new study's completed outputs."""
    root, cache = root.absolute(), cache.absolute()
    if cache == root or root in cache.parents or cache in root.parents:
        raise ValueError('cache must be a separate owned directory')
    cache.mkdir(parents=True, exist_ok=True)
    receipt = root/'relocations.jsonl'
    for item in paths:
        item = Path(item).absolute()
        relative = item.relative_to(root)
        if '..' in relative.parts or not item.parent.resolve().is_relative_to(root.resolve()):
            raise ValueError('staging source escapes the owned root')
        if item.is_symlink():
            destination = cache/relative
            if item.resolve() != destination.resolve():
                raise ValueError('foreign symlink in staging selection')
            continue
        if not item.is_file():
            raise ValueError('staging selection is not a regular file')
        before = item.stat()
        destination = cache/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.parent.resolve().is_relative_to(cache.resolve()):
            raise ValueError('cache destination escapes the owned cache')
        if destination.exists() or destination.is_symlink():
            raise ValueError('cache destination already exists; preserve partials')
        digest = guard.sha(item)
        with item.open('rb') as source, destination.open('xb') as target:
            shutil.copyfileobj(source, target, length=4*1024**2)
            target.flush();os.fsync(target.fileno())
        if (guard.sha(destination) != digest or item.stat().st_size != before.st_size
                or item.stat().st_mtime_ns != before.st_mtime_ns or guard.sha(item) != digest):
            raise ValueError('staging copy/source identity differs')
        fd = os.open(destination.parent, os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
        row = dict(source=str(item), destination=str(destination), bytes=before.st_size,
                   mtime_ns=before.st_mtime_ns, sha256=digest, at=time.time(), drive_accepted=False)
        # Commit the restoration record before replacing the original pathname.
        with receipt.open('a') as f:
            f.write(json.dumps(row, sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
        link = item.with_name(item.name+'.staged-link')
        os.symlink(destination, link)
        os.replace(link, item)
        fd = os.open(item.parent, os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
        print(json.dumps(dict(event='staged', **row)), flush=True)


def stage_selection(root, cache, selection):
    paths = []
    for entry in selection:
        p = root/entry
        paths.extend(sorted(x for x in p.rglob('*') if x.is_file() or x.is_symlink()) if p.is_dir() else [p])
    stage_files(root, cache, paths)


def reference_models(smoke, qualification):
    if smoke:
        return load(qualification)['models']
    if load(REFERENCE_ROOT/'status.json')['status'] != 'complete' or (REFERENCE_ROOT/'failure.json').exists():
        raise ValueError('PR355 reference not complete')
    original = load(REFERENCE_ROOT/'comparison/results.json')['models']
    if original['baseline']['sha256'] != prior.BASELINE_POLICY_SHA or original['candidate']['sha256'] != 'a85364b71c478be213e0356c5201911755228c864472427b64699346191facbd':
        raise ValueError('wrong original lineage policies')
    return original


def configure(root, build, tables, python, qualification, cache, *, smoke=False, fixture=None):
    if root.exists() or cache.exists():
        raise ValueError('fresh main and cache roots required')
    python, environment = prior.python_environment(python)
    b = old.checked_build(build)
    q = load(qualification)
    pins = old.source_pins()
    if (q['status'] != 'passed' or q['source_files'] != pins or q['environment'] != environment
            or q['build_receipt_sha256'] != guard.sha(build/'build-receipt.json')):
        raise ValueError('qualification/source/build/environment differs')
    fixture_pin = None
    if not smoke:
        if fixture is None:
            raise ValueError('complete confirmation fixture required')
        proof = load(fixture/'results.json')
        fc = load(fixture/'config.json')
        if (proof['status'] != 'settled' or load(fixture/'status.json')['status'] != 'complete'
                or (fixture/'failure.json').exists() or not fc['smoke']
                or fc['source_files'] != pins or fc['build_receipt_sha256'] != guard.sha(build/'build-receipt.json')
                or proof['initial_hands'] != 42*2*6):
            raise ValueError('confirmation end-to-end fixture differs')
        fixture_pin = dict(path=str(fixture/'results.json'), sha256=guard.sha(fixture/'results.json'))
    c = dict(smoke=smoke, seeds=list(SEEDS), targets=[100000,200000] if smoke else list(TARGETS),
        cap=10000 if smoke else bounded.CAP, matrices=[matrix(i,smoke) for i in range(2)],
        cross=cross_cases(smoke), reference=reference_models(smoke,qualification), cache=str(cache),
        python=str(python), environment=environment, tables=str(tables), build_root=str(build),
        binaries=b['binaries'], hashes=b['hashes'], build_receipt_sha256=guard.sha(build/'build-receipt.json'),
        qualification=str(qualification), qualification_sha256=guard.sha(qualification), fixture=fixture_pin,
        source_files=pins, resource_policy=prior.RESOURCE_POLICY)
    root.mkdir(parents=True)
    guard.write(root/'config.json', c)


def validate_config(c):
    smoke = c['smoke']
    if (c['seeds'] != list(SEEDS) or c['targets'] != ([100000,200000] if smoke else list(TARGETS))
            or c['cap'] != (10000 if smoke else bounded.CAP)
            or c['matrices'] != [matrix(i,smoke) for i in range(2)] or c['cross'] != cross_cases(smoke)
            or c['source_files'] != old.source_pins() or c['resource_policy'] != prior.RESOURCE_POLICY):
        raise ValueError('frozen confirmation configuration changed')
    b = old.checked_build(Path(c['build_root']))
    q = load(c['qualification'])
    if (c['binaries'] != b['binaries'] or c['hashes'] != b['hashes']
            or c['build_receipt_sha256'] != guard.sha(Path(c['build_root'])/'build-receipt.json')
            or c['qualification_sha256'] != guard.sha(c['qualification']) or q['source_files'] != c['source_files']
            or q['status'] != 'passed' or q['environment'] != c['environment']
            or prior.python_environment(Path(c['python']))[1] != c['environment']):
        raise ValueError('build/qualification/environment changed')
    if c['fixture'] and guard.sha(c['fixture']['path']) != c['fixture']['sha256']:
        raise ValueError('confirmation fixture changed')


def execute(c, root, stage):
    models = {f'{a}-{ORIGINAL}':m for a,m in c['reference'].items()}
    for index, seed in enumerate(SEEDS):
        line = root/f'lineage-{seed}';line.mkdir()
        baseline = checkpoint = None
        for alias, target in zip(old.ALIASES,c['targets']):
            out = line/alias
            conf = old.training_config(c['tables'],out,root/'STOP',model=baseline,
                target=target,cap=c['cap'],seed=seed)
            path = line/(alias+'-training.json');guard.write(path,conf)
            result = stage(f'{seed}-train-{alias}',[c['binaries']['train'],path])
            model, cp = checked_endpoint(result,seed,target,c['cap'],checkpoint)
            if alias == 'baseline':
                checkpoint = cp
            mass = line/(alias+'-mass')
            stage(f'{seed}-audit-{alias}',old.audit_model(c['python'],model,mass))
            model = old.mass_model(model,mass,checkpoint['keyset_sha256'])
            models[f'{alias}-{seed}'] = model
            guard.write(line/(alias+'-endpoint.json'),dict(model=model,checkpoint=cp))
            if alias == 'baseline':
                baseline = model
            else:
                if load(mass/'receipt.json')['zero_mass_rows'] > load(line/'baseline-mass/receipt.json')['zero_mass_rows']:
                    raise ValueError('cumulative mass decreased')
            # A completed checkpoint is no longer being written. Relocate it
            # before the next large save; exports stay on NVMe through this match.
            selection = [str(Path(model['checkpoint']).relative_to(root))]
            file = line/(alias+'-stage.json');guard.write(file,selection)
            stage(f'{seed}-stage-{alias}',[c['python'],'-m',MODULE,'stage',root,'--selection',file])
        comparison = line/'comparison';comparison.mkdir()
        pair = {a:models[f'{a}-{seed}'] for a in old.ALIASES}
        guard.write(comparison/'evaluation-manifest.json',dict(smoke=c['smoke'],models=pair,
            tables=c['tables'],arena=c['binaries']['arena'],arena_sha256=c['hashes']['arena'],
            cases=c['matrices'][index],keyset_sha256=checkpoint['keyset_sha256']))
        stage(f'{seed}-evaluation',[c['python'],'-m',MODULE,'batch',comparison,'--index',index,'--smoke',int(c['smoke'])])
        # No payoff readout here: all lineages and cross-seed checks must verify.
        guard.write(comparison/'status.json',dict(status='verified-readout-ready'))
        selection = [str((line/name).relative_to(root)) for name in ('baseline','candidate','baseline-mass','candidate-mass','comparison/evaluation')]
        file = line/'stage-completed.json';guard.write(file,selection)
        stage(f'{seed}-stage-completed',[c['python'],'-m',MODULE,'stage',root,'--selection',file])
    cross = root/'cross';cross.mkdir()
    guard.write(cross/'evaluation-manifest.json',dict(smoke=c['smoke'],models=models,tables=c['tables'],
        arena=c['binaries']['legacy'],arena_sha256=c['hashes']['legacy'],cases=c['cross']))
    stage('cross-evaluation',[c['python'],'-m',MODULE,'cross',cross,'--smoke',int(c['smoke'])])
    total = sum(x['blocks']*6 for rows in c['matrices']+[c['cross']] for x in rows)
    guard.write(root/'evaluation-verified.json',dict(status='passed',initial_hands=total,reproduction_hands=total,
        manifests={str(p.relative_to(root)):guard.sha(p) for p in root.glob('*/comparison/evaluation-manifest.json')},
        cross_manifest_sha256=guard.sha(cross/'evaluation-manifest.json')))
    guard.write(root/'status.json',dict(status='all-science-verified-readout-ready'))
    stage('global-readout',[c['python'],'-m',MODULE,'read',root])
    guard.write(root/'status.json',dict(status='complete',at=time.time()))


def adjusted(values, family):
    from scripts.analyze_nplayer_arena import interval
    from scipy.stats import t
    if len(values)<2 or not all(math.isfinite(v) for v in values):
        raise ValueError('invalid statistical blocks')
    result = interval(values)
    width = float(t.ppf(1-.05/(2*family),len(values)-1))*statistics.stdev(values)/math.sqrt(len(values))
    result.update(lower_family95=statistics.mean(values)-width,upper_family95=statistics.mean(values)+width,family=family)
    return result


def read(root):
    from scripts.read_nplayer_fast_study import paired_blocks
    c = load(root/'config.json')
    validate_config(c)
    proof = load(root/'evaluation-verified.json')
    expected = sum(x['blocks']*6 for rows in c['matrices']+[c['cross']] for x in rows)
    if ((root/'failure.json').exists() or load(root/'status.json')['status'] != 'all-science-verified-readout-ready'
            or proof['status'] != 'passed' or proof['initial_hands'] != expected or proof['reproduction_hands'] != expected
            or proof['cross_manifest_sha256'] != guard.sha(root/'cross/evaluation-manifest.json')
            or len(proof['manifests']) != 2 or any(guard.sha(root/p) != digest for p,digest in proof['manifests'].items())):
        raise ValueError('global confirmation barrier not ready')
    rows=[];lineages={}
    for index,seed in enumerate(SEEDS):
        folder=root/f'lineage-{seed}'/'comparison'
        old.read(folder,matrix=c['matrices'][index])
        lineages[str(seed)]=load(folder/'results.json')
        for a,b in zip(c['matrices'][index][::2],c['matrices'][index][1::2]):
            blocks=list(paired_blocks(folder/'evaluation'/a['name']/'play-0.jsonl',folder/'evaluation'/b['name']/'play-0.jsonl',a['root']))
            data=[v['advantage'] if a['group']=='direct' else v['fast_singleton']-v['production_singleton'] for v in blocks]
            rows.append(dict(seed=seed,group=a['group'],opponent=a.get('opponent'),score=adjusted(data,2 if a['group']=='direct' else 16)))
    folder=root/'cross'
    m=load(folder/'evaluation-manifest.json');p=load(folder/'evaluation-verified.json')
    if p != dict(status='passed',manifest_sha256=guard.sha(folder/'evaluation-manifest.json'),cases=6,hands=sum(x['blocks']*6 for x in c['cross'])):
        raise ValueError('cross proof changed')
    # Recheck original/reproduction/replay bytes at the final barrier.
    for case in c['cross']:
        d=folder/'evaluation'/case['name'];r=load(d/'result.json');v=load(d/'replay.json');digest=guard.sha(d/'play-0.jsonl')
        if (r['case']!=case or r['status']!='passed' or r['trace_sha256']!=digest
                or v['status']!='passed' or v['trace_sha256']!=digest or v['hands']!=case['blocks']*6
                or guard.sha(d/'play-1.jsonl')!=digest):
            raise ValueError('cross final replay/reproduction proof changed')
    cross=[]
    for a,b in zip(c['cross'][::2],c['cross'][1::2]):
        values=list(paired_blocks(folder/'evaluation'/a['name']/'play-0.jsonl',folder/'evaluation'/b['name']/'play-0.jsonl',a['root']))
        cross.append(dict(seed=a['seed'],opponent_seed=a['opponent_seed'],score=adjusted([v['fast_singleton']-v['production_singleton'] for v in values],3)))
    costs={p.parent.name:{k:load(p)[k] for k in ('wall_seconds','cpu_seconds','sampled_peak_rss_by_phase')} for p in (root/'measurements').glob('*/result.json') if p.parent.name!='global-readout'}
    guard.write(root/'results.json',dict(status='settled',initial_hands=expected,reproduction_hands=expected,
        rows=rows,cross=cross,lineages=lineages,costs=costs,
        repeated_primary_gain=all(x['score']['lower_family95']>0 for x in rows if x['group']=='direct'),
        cross_seed_safeguard=all(x['score']['lower_family95']>-5 for x in cross),
        scripted_safeguard=all(x['score']['lower_family95']>-50 for x in rows if x['group']!='direct'),
        scope='two new fixed seeds plus original-seed cross references; no automatic release/default adoption'))


def run(root):
    if (root/'launch.json').exists():
        raise ValueError('already launched; no automatic retry')
    c=load(root/'config.json');validate_config(c)
    old.supervised(root,lambda stage:execute(c,root,stage),nonblocking=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('configure','run','batch','cross','read','stage'))
    p.add_argument('root',type=Path);p.add_argument('--build',type=Path);p.add_argument('--tables',type=Path)
    p.add_argument('--python',type=Path);p.add_argument('--qualification',type=Path);p.add_argument('--fixture',type=Path)
    p.add_argument('--cache',type=Path);p.add_argument('--smoke',type=int,choices=(0,1),default=0)
    p.add_argument('--index',type=int,choices=(0,1));p.add_argument('--selection',type=Path);a=p.parse_args()
    root=a.root.absolute()
    if a.mode=='configure':
        configure(root,a.build.absolute(),a.tables.absolute(),a.python,a.qualification.absolute(),a.cache.absolute(),smoke=bool(a.smoke),fixture=a.fixture);return
    if a.mode=='batch':old.batch(root,matrix=matrix(a.index,bool(a.smoke)));return
    if a.mode=='cross':bounded.batch(root,matrix=cross_cases(bool(a.smoke)),expected_loads=expected_loads(cross_cases(bool(a.smoke))));return
    if a.mode=='stage':
        c=load(root/'config.json')
        if load(root/'launch.json')['config_sha256'] != guard.sha(root/'config.json'):
            raise ValueError('staging configuration changed')
        stage_selection(root,Path(c['cache']),load(a.selection));return
    globals()[a.mode](root)


if __name__=='__main__':main()
