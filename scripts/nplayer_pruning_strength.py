"""Issue351: prepare and run a two-stage pruning cost/strength screen explicitly.

Building or configuring never starts training. The owner reviews the PR and
configuration before an explicit `run`. Existing PR350 inputs remain read-only.
"""
import argparse
import fcntl
import gzip
import io
import json
import math
import os
from pathlib import Path
import signal
import statistics
import subprocess
import tarfile
import time

from scripts import nplayer_bb100_overnight as bounded
from scripts import run_nplayer_storage_benchmark as guard
from scripts.nplayer_overnight import BOTS, load

LIBRARY_COMMIT = 'b9882e7e728847a58691995e64eabd4563ea0991'
SEED = 2026101935003
NODE_TARGET = 3_000_000_000
ACTIVE_TARGET = 630.740595090997
BASELINE_NODES = 3_000_011_203
BASELINE_ITERATION = 212132
PRUNING = dict(bb=0.05, after=200)
BLOCKS = 8192
RESOURCE_POLICY = dict(cpu_stop_c=90, thermistor15_stop_c=100,
    runtime_limit_seconds=None, rss_limit_bytes=None, address_limit_bytes=None,
    disk_check_enabled=False, swap_check_enabled=False)
BASELINE_ROOT = '/mnt/data2tb/research-cloud/PR-350-nplayer-bb100/bounded-20261019-v3'
BASELINE_CHECKPOINT_SHA = 'ea0c7dca97ae627b08a39d4196cdd824d6e0767d85ca64c829eae5dcceb2da6b'
BASELINE_POLICY_SHA = 'c602c3727df28160a9807716d3c9211d988e420c33ed7b0c04c2fd899afef06b'
SOURCE = Path(__file__).resolve().parents[1]


def baseline():
    folder = Path(BASELINE_ROOT)/'calibration-continuation'
    return dict(checkpoint=str(folder/'3000000000.gz'), checkpoint_sha256=BASELINE_CHECKPOINT_SHA,
                path=str(folder/'3000000000-average.gz'), sha256=BASELINE_POLICY_SHA,
                strategy='average', scope=3)


def cases(phase):
    if phase not in ('nodes', 'clock'):
        raise ValueError('unknown comparison phase')
    # Separate from every PR350 development, calibration and held-out root.
    start = 20261019351101 if phase == 'nodes' else 20261019351201
    rows = [dict(name='direct-'+str(i), group='direct', root=start, blocks=BLOCKS,
                 singleton='candidate' if i == 0 else 'baseline',
                 pair='baseline' if i == 0 else 'candidate') for i in (0, 1)]
    for i, bot in enumerate(BOTS, 1):
        for model in ('candidate', 'baseline'):
            rows.append(dict(name=bot+'-'+model, group='bot', bot=bot, root=start+i,
                             blocks=BLOCKS, singleton=model, pair='bot='+bot))
    return rows


def next_clock_action(endpoints):
    node = endpoints.get('nodes')
    if node is None:
        raise ValueError('missing 3B endpoint')
    if 'clock' in endpoints:
        return 'reuse'
    if node['active_seconds'] >= ACTIVE_TARGET:
        raise ValueError('missed the equal-time checkpoint during node training')
    return 'continue'


def endpoint_models(result, checkpoint_dir):
    if result['returncode'] != 0:
        raise ValueError('training command failed')
    endpoints = {}
    for e in bounded.events(result, 'endpoint'):
        label = e['label']
        cp = next(x for x in bounded.events(result, 'checkpoint') if x['label'] == label)
        exported = bounded.model(result, label)
        clock_path = Path(e['clock_path'])
        if (label not in ('nodes', 'clock') or label in endpoints
                or clock_path != Path(checkpoint_dir)/(label+'-clock.json')
                or guard.sha(clock_path) != e['clock_sha256']):
            raise ValueError('endpoint/clock receipt differs')
        proof = load(clock_path)
        if any(proof[k] != e[k] for k in ('nodes', 'iteration', 'active_seconds', 'pruned_actions', 'last_iteration_seconds')):
            raise ValueError('clock accounting differs')
        if (proof['target_seconds'] != ACTIVE_TARGET or cp['nodes'] != e['nodes']
                or cp['iteration'] != e['iteration'] or proof['checkpoint_sha256'] != cp['sha256']
                or exported['checkpoint_sha256'] != cp['sha256']
                or proof['checkpoint'] != cp['path'] or cp['path'] != str(Path(checkpoint_dir)/(label+'.gz'))
                or not math.isfinite(e['active_seconds'])
                or e['active_seconds'] <= 0):
            raise ValueError('endpoint lineage differs')
        if label == 'nodes' and cp['nodes'] < NODE_TARGET:
            raise ValueError('incomplete node endpoint')
        if label == 'clock' and (e['active_seconds'] < ACTIVE_TARGET
                or not math.isfinite(e['last_iteration_seconds']) or e['last_iteration_seconds'] <= 0
                or e['active_seconds']-ACTIVE_TARGET > e['last_iteration_seconds']+1e-7):
            raise ValueError('incomplete or overrun clock endpoint')
        endpoints[label] = dict(e, model=exported)
    if len(bounded.events(result, 'complete')) != 1:
        raise ValueError('incomplete native trajectory')
    if 'clock' in endpoints and 'nodes' in endpoints:
        clock,node=endpoints['clock'],endpoints['nodes']
        if any(clock[k]>node[k] for k in ('active_seconds','nodes','iteration','pruned_actions')):
            raise ValueError('early clock endpoint follows node endpoint')
    return endpoints


def verify_model(model, pruning, endpoint=None):
    for path, digest in ((model['checkpoint'], model['checkpoint_sha256']), (model['path'], model['sha256'])):
        if guard.sha(path) != digest:
            raise ValueError('model hash differs')
    with gzip.open(model['checkpoint'], 'rt') as f:
        h = json.loads(next(f))
    expected = None if pruning is None else dict(pruning)
    actual = h.get('pruning')
    if actual is not None:
        actual = {k:actual[k] for k in ('bb', 'after')}
    if (h['players'] != 3 or h['game']['stacks'] != [10000]*3 or h['seed'] != SEED
            or h['sampling'] != 'path-v1' or h['roots_per_seat'] != 8
            or h['last_average_street'] != 3 or h['max_entries'] != bounded.CAP
            or not h['freeze_at_cap'] or actual != expected):
        raise ValueError('model recipe differs')
    if pruning is None and (h['counts']['nodes'] != BASELINE_NODES or h['iteration'] != BASELINE_ITERATION):
        raise ValueError('wrong historical baseline')
    if endpoint is not None and (h['counts']['nodes'] != endpoint['nodes'] or h['iteration'] != endpoint['iteration']
            or h.get('pruning', {}).get('pruned_actions', 0) != endpoint['pruned_actions']):
        raise ValueError('checkpoint/clock accounting differs')
    if model.get('strategy') != 'average' or model.get('scope') != 3:
        raise ValueError('full-average model required')
    return h


def build(destination):
    """Compile against the baseline library; exclude PR347 from the timing contrast."""
    destination.mkdir(parents=True, exist_ok=False)
    source = destination/'source';source.mkdir()
    data = subprocess.check_output(['git', 'archive', LIBRARY_COMMIT, 'native/hu20-trainer', 'native/hu20-buckets'], cwd=SOURCE)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        # The members come from a pinned local Git tree, never an input ZIP.
        archive.extractall(source, filter='data')
    overlays = ('native/hu20-trainer/examples/nplayer_pruning_study.rs',
                'native/hu20-trainer/examples/support/nplayer_checkpoint_io.rs')
    for name in overlays:
        output = source/name;output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes((SOURCE/name).read_bytes())
    manifest = {str(p.relative_to(source)):guard.sha(p) for p in source.rglob('*') if p.is_file()}
    target = destination/'target'
    env = dict(os.environ, CARGO_TARGET_DIR=str(target), CARGO_BUILD_JOBS='2')
    command = ['cargo', 'build', '--release', '--locked', '--manifest-path', str(source/'native/hu20-trainer/Cargo.toml'),
               '--example', 'nplayer_pruning_study', '--example', 'nplayer_arena']
    subprocess.run(command, env=env, check=True)
    binaries = {key:str(target/'release/examples'/name) for key,name in
                (('train', 'nplayer_pruning_study'), ('arena', 'nplayer_arena'))}
    receipt = dict(library_source_commit=LIBRARY_COMMIT,
                   harness_source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip(),
                   files=manifest, overlays=list(overlays),
                   **binaries, **{k+'_sha256':guard.sha(v) for k,v in binaries.items()}, command=command)
    guard.write(destination/'build-receipt.json', receipt)


def configure(root, build_root, tables, python):
    receipt = load(build_root/'build-receipt.json')
    if receipt['library_source_commit'] != LIBRARY_COMMIT:
        raise ValueError('baseline library source required')
    for name in receipt['overlays']:
        if guard.sha(SOURCE/name) != receipt['files'][name]:raise ValueError('native harness changed since build')
    for name, digest in receipt['files'].items():
        if guard.sha(build_root/'source'/name) != digest:
            raise ValueError('build source changed')
    for key in ('train', 'arena'):
        if guard.sha(receipt[key]) != receipt[key+'_sha256']:
            raise ValueError('build binary changed')
    paths = subprocess.check_output(['git', 'ls-files', 'scripts', 'src', 'requirements.txt'], cwd=SOURCE, text=True).splitlines()
    root.mkdir(parents=True, exist_ok=False)
    guard.write(root/'config.json', dict(build_receipt=str(build_root/'build-receipt.json'),
        build_receipt_sha256=guard.sha(build_root/'build-receipt.json'),
        **{k:receipt[k] for k in ('train','train_sha256','arena','arena_sha256')},
        python=str(python), tables=str(tables), baseline=baseline(), pruning=PRUNING,
        node_target=NODE_TARGET, active_seconds_target=ACTIVE_TARGET, seed=SEED,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip(),
        source_files={name:guard.sha(SOURCE/name) for name in paths}, resource_policy=RESOURCE_POLICY,
        cases={p:cases(p) for p in ('nodes','clock')}))


def enforce_temperatures(row):
    temperatures=row['temperatures_c']
    limits={'Package id 0':90,'Thermistor 15':100}
    if set(temperatures)!=set(limits):raise RuntimeError('required temperature sensors missing')
    exceeded={name:dict(reading_c=temperatures[name],limit_c=limit) for name,limit in limits.items()
              if not math.isfinite(temperatures[name]) or temperatures[name]>=limit}
    if exceeded:
        error=RuntimeError('thermal stop: '+json.dumps(exceeded,sort_keys=True));error.resource_sample=row;raise error


class Supervisor(guard.Supervisor):
    def __init__(self,root,lock_fd,normal_fd):
        # Reuse process-group ownership/cleanup without the old campaign's
        # resource sampler. The owner requested temperature-only resource stops
        # and manual disk/swap inspection, with no memory or elapsed-time cap.
        self.root=root;self.lock_fd=lock_fd;self.extra_lock_fds=(normal_fd,)
        self.cpus=set(range(16));self.address_limit=None;self.protect_group=True
        self.started=time.monotonic()

    def sample(self,process,phase,target):
        row=dict(at=time.time(),phase=phase,target=target,temperatures_c=guard.sensors(),
                 elapsed_seconds=time.monotonic()-self.started,
                 **(guard.group_metrics(process.pid) if process else dict(rss_bytes=0)))
        enforce_temperatures(row)
        if (self.root/'STOP').exists():
            error=RuntimeError('owner stop file');error.resource_sample=row;raise error
        return row


def training_config(c, root, mode, node=None):
    value = dict(mode=mode, seed=SEED, threads=16, tables=c['tables'], max_entries=bounded.CAP,
        node_target=NODE_TARGET, active_seconds_target=ACTIVE_TARGET, reference_iteration=BASELINE_ITERATION,
        pruning=PRUNING, out=str(root/('candidate-nodes' if mode == 'nodes' else 'candidate-clock')),
        stop_file=str(root/'STOP'))
    if node is not None:
        value.update(input=node['model']['checkpoint'], input_sha256=node['model']['checkpoint_sha256'],
                     input_clock=node['clock_path'], input_clock_sha256=node['clock_sha256'])
    return value


def cost_summary(root, endpoints):
    stages={}
    for path in sorted((root/'measurements').glob('*/result.json')):
        value=load(path)
        stages[path.parent.name]={k:value[k] for k in ('wall_seconds','cpu_seconds','sampled_peak_rss_by_phase') if k in value}
    train=[]
    for name in ('train-nodes','train-continue-clock'):
        path=root/'measurements'/name/'result.json'
        if path.exists():train.append(load(path))
    landmarks=[e for row in train for e in bounded.events(row,'iteration-landmark')]
    artifacts=[e for row in train for e in row['events'] if e.get('event') in ('checkpoint','exported')]
    load_events=[e for row in train for e in row['events'] if e.get('event') in ('tables-loaded','checkpoint-loaded')]
    active=endpoints['nodes']['active_seconds']
    peak=max((v for row in stages.values() for v in row.get('sampled_peak_rss_by_phase',{}).values()),default=0)
    return dict(baseline_active_seconds=ACTIVE_TARGET,pruned_3b_active_seconds=active,
        active_seconds_saved_at_3b=ACTIVE_TARGET-active,active_time_saving_fraction_at_3b=1-active/ACTIVE_TARGET,
        active_training_speedup_at_3b=ACTIVE_TARGET/active,
        matched_clock_actual_seconds=endpoints['clock']['active_seconds'],
        matched_clock_nodes=endpoints['clock'].get('nodes'),
        baseline_3b_nodes=BASELINE_NODES,baseline_3b_iterations=BASELINE_ITERATION,
        same_iteration_landmark=landmarks[0] if landmarks else None,
        pruning_exercised=endpoints['nodes'].get('pruned_actions',0)>0,
        training_stages_wall_seconds=sum(v['wall_seconds'] for v in train),
        training_stages_cpu_seconds=sum(v['cpu_seconds'] for v in train),
        sampled_family_peak_rss_bytes=peak,stages=stages,artifact_costs=artifacts,load_events=load_events,
        historical_baseline_training_stage_wall_seconds=3053.4585111550114,
        wall_speedup_comparable=False,
        limitation='historical timing, one host/seed, different save/resume cadence; no end-to-end wall speedup claim')


def run(root):
    def interrupted(signum, frame):raise InterruptedError('owner/supervisor signal '+str(signum))
    signal.signal(signal.SIGTERM, interrupted);signal.signal(signal.SIGINT, interrupted)
    c = load(root/'config.json')
    if (c['pruning'] != PRUNING or c['seed'] != SEED or c['node_target'] != NODE_TARGET
            or c['active_seconds_target'] != ACTIVE_TARGET or c['baseline'] != baseline()
            or c['resource_policy'] != RESOURCE_POLICY or c['cases'] != {p:cases(p) for p in ('nodes','clock')}):
        raise ValueError('changed frozen study')
    if (root/'launch.json').exists():raise ValueError('study already launched')
    required={'scripts/nplayer_pruning_strength.py','scripts/nplayer_bb100_overnight.py',
              'scripts/run_nplayer_storage_benchmark.py','scripts/guarded_process_group.py',
              'scripts/check_nplayer_policy_replay.py','scripts/audit_nplayer_policy_parallel.py','requirements.txt'}
    if not required.issubset(c['source_files']):raise ValueError('incomplete controller source pins')
    for name,digest in c['source_files'].items():
        if guard.sha(SOURCE/name) != digest:raise ValueError('controller source changed')
    if guard.sha(c['build_receipt']) != c['build_receipt_sha256']:raise ValueError('build receipt changed')
    for key in ('train','arena'):
        if guard.sha(c[key]) != c[key+'_sha256']:raise ValueError('native binary changed')
    with Path('/tmp/cfr-nplayer-pruning-strength.lock').open('a') as own, Path('/tmp/cfr-cygnus-exclusive.lock').open('a') as normal:
        for lock in (own,normal):fcntl.flock(lock,fcntl.LOCK_EX)
        epoch=time.time();guard.write(root/'launch.json',dict(epoch=epoch,deadline_epoch=None,resource_policy=RESOURCE_POLICY,pid=os.getpid(),
            source_commit=c['source_commit'],config_sha256=guard.sha(root/'config.json')))
        s=Supervisor(root,own.fileno(),normal.fileno())
        first=s.sample(None,'admission',0)
        guard.write(root/'admission.json',first)
        env=dict(os.environ,RAYON_NUM_THREADS='16',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',
                 NPLAYER_STOP_FILE=str(root/'STOP'))
        def stage(name,cmd):
            s.sample(None,'stage-admission',0);guard.write(root/'status.json',dict(status=name,at=time.time()))
            return s.execute(name,list(map(str,cmd)),SOURCE,env)
        execute_study(c,root,stage)


def execute_study(c,root,stage):
    def train(mode,node=None):
        conf=training_config(c,root,mode,node);path=root/(mode+'-training-config.json');guard.write(path,conf)
        value=stage('train-'+mode,[c['train'],path])
        return endpoint_models(value,conf['out'])
    def audit(name,endpoint):
        model=endpoint['model']
        path=root/(name+'-verify.json');guard.write(path,dict(model=model,pruning=PRUNING,endpoint=endpoint))
        stage('verify-'+name,[c['python'],'-m','scripts.nplayer_pruning_strength','verify',path])
        value=stage('audit-'+name,[c['python'],'-m','scripts.audit_nplayer_policy_parallel',model['checkpoint'],model['path']])
        proof=load(root/'measurements'/('audit-'+name)/'stdout.log')
        if (value['returncode']!=0 or proof['status']!='passed' or proof['policy_sha256']!=model['sha256']
                or proof['checkpoint_sha256']!=model['checkpoint_sha256']):raise ValueError('average audit differs')
    def compare(phase,endpoint):
        model=endpoint['model']
        audit(phase,endpoint)
        folder=root/('comparison-'+phase);folder.mkdir(exist_ok=False)
        guard.write(folder/'evaluation-manifest.json',dict(smoke=False,phase=phase,tables=c['tables'],
            arena=c['arena'],arena_sha256=c['arena_sha256'],models=dict(candidate=model,baseline=c['baseline']),cases=cases(phase)))
        stage('evaluate-'+phase,[c['python'],'-m','scripts.nplayer_pruning_strength','batch',folder])
        guard.write(folder/'status.json',dict(status='verified-readout-ready'))
        stage('read-'+phase,[c['python'],'-m','scripts.nplayer_pruning_strength','read',folder])
    path=root/'baseline-verify.json';guard.write(path,dict(model=c['baseline'],pruning=None))
    stage('verify-baseline',[c['python'],'-m','scripts.nplayer_pruning_strength','verify',path])
    endpoints=train('nodes');guard.write(root/'endpoints.json',endpoints)
    compare('nodes',endpoints['nodes'])
    # Payoffs never control continuation. Even a poor/inconclusive stage1
    # result continues the predeclared experiment, unless an actual guard fails.
    action=next_clock_action(endpoints)
    if action=='continue':
        extension=train('continue-clock',endpoints['nodes'])
        clock=extension['clock'];node=endpoints['nodes']
        if (abs(clock['active_seconds']-(node['active_seconds']+clock['segment_active_seconds']))>1e-7
                or any(clock[k]<node[k] for k in ('nodes','iteration','pruned_actions'))):
            raise ValueError('continuation lost cumulative training accounting')
        endpoints.update(extension);guard.write(root/'endpoints.json',endpoints)
    compare('clock',endpoints['clock'])
    results={p:load(root/('comparison-'+p)/'results.json') for p in ('nodes','clock')}
    guard.write(root/'results.json',dict(status='settled',comparisons=results,endpoints=endpoints,
        historical_baseline_active_seconds=ACTIVE_TARGET,costs=cost_summary(root,endpoints),
        scope='one fixed seed; timing comparison uses a historical reference'))
    guard.write(root/'status.json',dict(status='complete',at=time.time()))


def batch(root):
    m=load(root/'evaluation-manifest.json')
    bounded.batch(root,matrix=cases(m['phase']),expected_loads=2)


def read(root):
    m=load(root/'evaluation-manifest.json');matrix=cases(m['phase']);proof=load(root/'evaluation-verified.json')
    if ((root/'failure.json').exists() or load(root/'status.json')['status']!='verified-readout-ready'
            or m['cases']!=matrix or proof!=dict(status='passed',manifest_sha256=guard.sha(root/'evaluation-manifest.json'),
                                               cases=10,hands=10*BLOCKS*6)):
        raise ValueError('phase replay barrier not ready')
    for c in matrix:
        folder=root/'evaluation'/c['name'];result=load(folder/'result.json');replay=load(folder/'replay.json')
        if (result['status']!='passed' or result['case']!=c or result['hands']!=BLOCKS*6
                or replay['status']!='passed' or replay['hands']!=BLOCKS*6
                or len({result['trace_sha256'],replay['trace_sha256'],guard.sha(folder/'play-0.jsonl'),guard.sha(folder/'play-1.jsonl')})!=1):
            raise ValueError('phase trace verification differs')
    from scipy.stats import t
    from scripts.read_nplayer_fast_study import paired_blocks
    from scripts.analyze_nplayer_arena import interval
    rows=[]
    for a,b in zip(matrix[::2],matrix[1::2]):
        values=list(paired_blocks(root/'evaluation'/a['name']/'play-0.jsonl',root/'evaluation'/b['name']/'play-0.jsonl',a['root']))
        if len(values)!=BLOCKS:raise ValueError('block count differs')
        data=[v['advantage'] if a['group']=='direct' else v['fast_singleton']-v['production_singleton'] for v in values]
        score=interval(data)
        # Two primary endpoints and eight scripted contrasts across both phases.
        comparisons=2 if a['group']=='direct' else 8
        width=float(t.ppf(1-.05/(2*comparisons),len(data)-1))*statistics.stdev(data)/math.sqrt(len(data))
        score.update(lower_family95=statistics.mean(data)-width,upper_family95=statistics.mean(data)+width)
        detail={key:[interval([v[key][i] for v in values]) for i in range(3)] for key in
                ('fast_by_seat','production_by_seat','fast_by_position','production_by_position')}
        rows.append(dict(group=a['group'],bot=a.get('bot'),score=score,
            strength_cost_bb100=dict(mean=-score['mean_bb100'],lower95=-score['upper95_bb100'],upper95=-score['lower95_bb100']),**detail))
    guard.write(root/'results.json',dict(status='settled',phase=m['phase'],rows=rows,models=m['models'],
        final_hands=10*BLOCKS*6,reproduction_hands=10*BLOCKS*6,
        statistic='mean oriented singleton contrast, not pooled individual-player return',
        no_automatic_adoption=True))
    print(json.dumps(dict(event='complete',status='settled')),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    for mode in ('run','batch','read','verify'):sub.add_parser(mode).add_argument('root',type=Path)
    sub.add_parser('build').add_argument('root',type=Path)
    prepare=sub.add_parser('configure');prepare.add_argument('root',type=Path)
    prepare.add_argument('--build-root',type=Path,required=True);prepare.add_argument('--tables',type=Path,required=True)
    prepare.add_argument('--python',type=Path,required=True)
    a=p.parse_args()
    if a.mode=='build':build(a.root.resolve());return
    if a.mode=='configure':configure(a.root.resolve(),a.build_root.resolve(),a.tables.resolve(),a.python.resolve());return
    if a.mode=='verify':
        c=load(a.root);verify_model(c['model'],c['pruning'],c.get('endpoint'));return
    try:globals()[a.mode](a.root.resolve())
    except BaseException as e:
        value=dict(error=repr(e),at=time.time())
        if hasattr(e,'resource_sample'):value['resource_sample']=e.resource_sample
        guard.write(a.root/'failure.json',value);raise


if __name__=='__main__':main()
