"""Issue354: explicitly prepare, qualify and run the fixed 3B→10B continuation.

Build/configuration/fixture qualification never launch the main experiment.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import fcntl
import gzip
import io
import json
import os
from pathlib import Path
import signal
import statistics
import subprocess
import tarfile
import time

from scripts import nplayer_bb100_overnight as bounded
from scripts import nplayer_pruning_strength as prior
from scripts import run_nplayer_storage_benchmark as guard
from scripts.nplayer_overnight import load

SOURCE = Path(__file__).resolve().parents[1]
LIBRARY_COMMIT = prior.LIBRARY_COMMIT
SEED = prior.SEED
TARGET = 10_000_000_000
ENTRIES = 250_000_475
KEYSET = 'a83858109eed965e73acd76787761d9353f2a66cccb482c0271173e3ff731425'
LABELS = ('positive_mass', 'zero_mass', 'missing')
ALIASES = ('baseline', 'candidate')
BINARY_NAMES = dict(train='nplayer_bounded', reference='nplayer_reference_bounded',
                    legacy='nplayer_arena', arena='nplayer_continuation_arena')
RESOURCE_POLICY = prior.RESOURCE_POLICY


def cases(smoke=False):
    first = 20261019354901 if smoke else 20261019354101
    blocks = 2 if smoke else 8192
    rows = [dict(name='direct-'+str(i), group='direct', root=first, blocks=blocks,
                 players=['candidate', 'baseline', 'baseline'] if i == 0 else ['baseline', 'candidate', 'candidate'])
            for i in range(2)]
    opponents = [(bot, ['bot='+bot]*2, 'script') for bot in bounded.BOTS]
    opponents += [('trained-call', ['baseline', 'bot=check-call'], 'mixed-trained'),
                  ('trained-pressure', ['baseline', 'bot=pot-pressure'], 'mixed-trained'),
                  ('call-pressure', ['bot=check-call', 'bot=pot-pressure'], 'mixed-script'),
                  ('random-tight', ['bot=random', 'bot=tight-aggressive'], 'mixed-script')]
    for i, (name, pair, group) in enumerate(opponents, 1):
        for model in ('candidate', 'baseline'):
            rows.append(dict(name=name+'-'+model, group=group, opponent=name,
                             root=first+i, blocks=blocks, players=[model]+pair))
    return rows


def build(destination):
    destination.mkdir(parents=True, exist_ok=False)
    source = destination/'source'
    source.mkdir()
    data = subprocess.check_output(['git', 'archive', LIBRARY_COMMIT, 'native/hu20-trainer', 'native/hu20-buckets'], cwd=SOURCE)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        archive.extractall(source, filter='data')
    base = source/'native/hu20-trainer/examples'
    (base/'nplayer_reference_bounded.rs').write_bytes((base/'nplayer_bounded.rs').read_bytes())
    overlays = ('native/hu20-trainer/examples/nplayer_bounded.rs',
                'native/hu20-trainer/examples/support/nplayer_checkpoint_io.rs',
                'native/hu20-trainer/examples/nplayer_continuation_arena.rs',
                'native/hu20-trainer/examples/support/nplayer_mass_metadata.rs')
    for name in overlays:
        p = source/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((SOURCE/name).read_bytes())
    files = {str(p.relative_to(source)):guard.sha(p) for p in source.rglob('*') if p.is_file()}
    command = ['cargo', 'build', '--release', '--locked', '--manifest-path', str(source/'native/hu20-trainer/Cargo.toml')]
    for name in BINARY_NAMES.values():
        command += ['--example', name]
    subprocess.run(command, env=dict(os.environ, CARGO_BUILD_JOBS='2', CARGO_TARGET_DIR=str(destination/'target')), check=True)
    binaries = {k:str(destination/'target/release/examples'/v) for k, v in BINARY_NAMES.items()}
    guard.write(destination/'build-receipt.json', dict(library_source_commit=LIBRARY_COMMIT,
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip(),
        files=files, overlays=list(overlays), binaries=binaries,
        hashes={k:guard.sha(v) for k, v in binaries.items()}))


def checked_build(path):
    receipt = load(path/'build-receipt.json')
    if receipt['library_source_commit'] != LIBRARY_COMMIT or set(receipt['binaries']) != set(BINARY_NAMES):
        raise ValueError('historical library/build identity differs')
    for name, digest in receipt['files'].items():
        if guard.sha(path/'source'/name) != digest:
            raise ValueError('deployed build source changed')
    for name in receipt['overlays']:
        if guard.sha(SOURCE/name) != receipt['files'][name]:
            raise ValueError('native harness changed after build')
    for name, binary in receipt['binaries'].items():
        if guard.sha(binary) != receipt['hashes'][name]:
            raise ValueError('native binary changed')
    return receipt


def source_pins():
    names = subprocess.check_output(['git', 'ls-files', 'scripts', 'src', 'requirements.txt'], cwd=SOURCE, text=True).splitlines()
    # New modules may be staged but not yet committed during local qualification.
    names += ['scripts/nplayer_bb100_continuation.py']
    return {name:guard.sha(SOURCE/name) for name in sorted(set(names))}


def training_config(tables, out, stop, *, model=None, target=TARGET, cap=bounded.CAP, seed=SEED):
    return dict(seed=seed, threads=16, tables=str(tables), stack_bb=100, max_entries=cap,
                freeze_at_cap=True, parallel_gzip=True, input=model['checkpoint'] if model else None,
                input_sha256=model['checkpoint_sha256'] if model else None, out=str(out), targets=[target],
                stop_file=str(stop), save_anchor=False, export_final=True, probe_nodes=[], probe_blocks=0,
                probe_root=0, reference=None)


def verify_model(model, candidate=False):
    for path, digest in [(model['checkpoint'], model['checkpoint_sha256']), (model['path'], model['sha256'])]:
        if guard.sha(path) != digest:
            raise ValueError('model checksum differs')
    with gzip.open(model['checkpoint'], 'rt') as f:
        h = json.loads(next(f))
    with gzip.open(model['path'], 'rt') as f:
        p = json.loads(next(f))
    if (h['players'] != 3 or h['game']['stacks'] != [10000]*3 or h['seed'] != SEED
            or h['max_entries'] != bounded.CAP or not h['freeze_at_cap'] or h['frozen_at'] is None
            or h['entries'] != ENTRIES or h['sampling'] != 'path-v1' or h['roots_per_seat'] != 8
            or h['last_average_street'] != 3 or 'pruning' in h
            or p['identity'] != h['game'] or p['source_checkpoint_sha256'] != model['checkpoint_sha256']
            or p['strategy'] != 'average' or p['last_average_street'] != 3 or p['entries'] != ENTRIES):
        raise ValueError('checkpoint/export recipe differs')
    if candidate:
        if h['counts']['nodes'] < TARGET or h['iteration'] <= prior.BASELINE_ITERATION:
            raise ValueError('candidate has not reached10B')
    elif h['counts']['nodes'] != prior.BASELINE_NODES or h['iteration'] != prior.BASELINE_ITERATION:
        raise ValueError('baseline endpoint differs')
    return h


def audit_model(python, model, folder):
    return [python, '-m', 'scripts.audit_nplayer_policy_parallel', model['checkpoint'], model['path'], '--lookup-out', str(folder)]


def mass_model(model, folder, keyset=None):
    r = load(folder/'receipt.json')
    if (r['status'] != 'passed' or r['format'] != 'nplayer-average-mass-v1'
            or r['checkpoint_sha256'] != model['checkpoint_sha256'] or r['policy_sha256'] != model['sha256']
            or r['strategy'] != 'average' or r['last_average_street'] != 3
            or r['rows'] != r['positive_mass_rows']+r['zero_mass_rows']
            or r['average_rows'] != r['rows'] or r['current_rows'] != 0
            or keyset is not None and r['keyset_sha256'] != keyset
            or guard.sha(folder/'zero-keys.bin') != r['zero_keys_sha256']
            or (folder/'zero-keys.bin').stat().st_size != 16*r['zero_mass_rows']):
        raise ValueError('mass metadata proof differs')
    return dict(model, mass=str(folder), mass_sha256=guard.sha(folder/'receipt.json'))


def configure(root, build_root, tables, python, qualification):
    python, environment = prior.python_environment(python)
    b = checked_build(build_root)
    q = load(qualification)
    pins = source_pins()
    if (q['status'] != 'passed' or q['build_receipt_sha256'] != guard.sha(build_root/'build-receipt.json')
            or q['source_files'] != pins or q['environment'] != environment):
        raise ValueError('qualification/source/environment differs')
    root.mkdir(parents=True, exist_ok=False)
    guard.write(root/'config.json', dict(build_root=str(build_root), build_receipt_sha256=guard.sha(build_root/'build-receipt.json'),
        binaries=b['binaries'], hashes=b['hashes'], python=str(python), environment=environment, tables=str(tables),
        baseline=prior.baseline(), target=TARGET, seed=SEED, entries=ENTRIES, keyset=KEYSET,
        cases=cases(), resource_policy=RESOURCE_POLICY, source_files=pins,
        qualification=str(qualification), qualification_sha256=guard.sha(qualification)))


def check_config(c):
    if (c['target'] != TARGET or c['seed'] != SEED or c['entries'] != ENTRIES or c['keyset'] != KEYSET
            or c['baseline'] != prior.baseline() or c['cases'] != cases() or c['resource_policy'] != RESOURCE_POLICY
            or c['source_files'] != source_pins()):
        raise ValueError('frozen scientific/source configuration changed')
    b=checked_build(Path(c['build_root']))
    if c['binaries']!=b['binaries'] or c['hashes']!=b['hashes']:
        raise ValueError('configured binary paths/hashes differ from build')
    if guard.sha(Path(c['build_root'])/'build-receipt.json') != c['build_receipt_sha256']:
        raise ValueError('build receipt changed')
    q = load(c['qualification'])
    if (guard.sha(c['qualification']) != c['qualification_sha256'] or q['status'] != 'passed'
            or q['source_files'] != c['source_files'] or q['environment'] != c['environment']
            or q['build_receipt_sha256'] != c['build_receipt_sha256']):
        raise ValueError('qualification changed')
    if prior.python_environment(Path(c['python']))[1] != c['environment']:
        raise ValueError('qualified Python changed')


def supervised(root, callback):
    def interrupted(signum, frame):
        raise InterruptedError('owner/supervisor signal '+str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    with Path('/tmp/cfr-nplayer-bb100-10b.lock').open('a') as own, Path('/tmp/cfr-cygnus-exclusive.lock').open('a') as normal:
        for lock in (own, normal):
            fcntl.flock(lock, fcntl.LOCK_EX)
        if (root/'launch.json').exists():
            raise ValueError('root already launched; no automatic retry')
        guard.write(root/'launch.json', dict(pid=os.getpid(), at=time.time(), resource_policy=RESOURCE_POLICY,
            config_sha256=guard.sha(root/'config.json') if (root/'config.json').exists() else None,
            source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip()))
        s = prior.Supervisor(root, own.fileno(), normal.fileno())
        env = dict(os.environ, RAYON_NUM_THREADS='16', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
                   MKL_NUM_THREADS='1', NPLAYER_STOP_FILE=str(root/'STOP'))
        def stage(name, command):
            s.sample(None, name, 0)
            guard.write(root/'status.json', dict(status=name, at=time.time()))
            return s.execute(name, list(map(str, command)), SOURCE, env)
        try:
            guard.write(root/'admission.json', s.sample(None, 'admission', 0))
            callback(stage)
        except BaseException as error:
            value=dict(error=repr(error),at=time.time())
            if hasattr(error,'resource_sample'):value['resource_sample']=error.resource_sample
            guard.write(root/'failure.json',value)
            raise


def execute(c, root, stage):
    verify_model(c['baseline'])
    stage('baseline-audit', audit_model(c['python'], c['baseline'], root/'baseline-mass'))
    baseline = mass_model(c['baseline'], root/'baseline-mass', KEYSET)
    conf = training_config(c['tables'], root/'candidate', root/'STOP', model=c['baseline'])
    guard.write(root/'training-config.json', conf)
    result = stage('continue-10b', [c['binaries']['train'], root/'training-config.json'])
    bounded.validate_trajectory(result, bounded.CAP, TARGET)
    cp = bounded.events(result, 'checkpoint')[-1]
    if cp['keyset_sha256'] != KEYSET or cp['entries'] != ENTRIES or cp['frozen_at'] is None:
        raise ValueError('continuation changed fixed membership')
    candidate = bounded.model(result, str(TARGET))
    verify_model(candidate, True)
    guard.write(root/'endpoint.json', dict(model=candidate, checkpoint=cp,
        trained=bounded.events(result, 'trained')[-1], complete=bounded.events(result, 'complete')[-1]))
    stage('candidate-audit', audit_model(c['python'], candidate, root/'candidate-mass'))
    candidate = mass_model(candidate, root/'candidate-mass', KEYSET)
    folder = root/'comparison'
    folder.mkdir(exist_ok=False)
    guard.write(folder/'evaluation-manifest.json', dict(smoke=False, models=dict(baseline=baseline, candidate=candidate),
        tables=c['tables'], arena=c['binaries']['arena'], arena_sha256=c['hashes']['arena'], cases=cases(),
        keyset_sha256=KEYSET))
    stage('evaluation', [c['python'], '-m', 'scripts.nplayer_bb100_continuation', 'batch', folder])
    # Global payoff barrier: the complete matrix must replay/reproduce before readout.
    guard.write(folder/'status.json', dict(status='verified-readout-ready'))
    stage('readout', [c['python'], '-m', 'scripts.nplayer_bb100_continuation', 'read', folder])
    results = load(folder/'results.json')
    stages = {p.parent.name:load(p) for p in (root/'measurements').glob('*/result.json')}
    guard.write(root/'results.json', dict(status='settled', results=results, endpoint=load(root/'endpoint.json'),
        costs={k:{f:v[f] for f in ('wall_seconds', 'cpu_seconds', 'sampled_peak_rss_by_phase')} for k,v in stages.items()},
        evaluation_cost=load(folder/'evaluation-cost.json'), scope='one fixed training seed; no automatic adoption'))
    guard.write(root/'status.json', dict(status='complete', at=time.time()))


def verify_inputs(m):
    if guard.sha(m['arena']) != m['arena_sha256']:
        raise ValueError('arena changed')
    for model in m['models'].values():
        if guard.sha(model['path']) != model['sha256']:
            raise ValueError('policy changed')
        actual = mass_model(model, Path(model['mass']), m['keyset_sha256'])
        if actual != model:
            raise ValueError('mass receipt changed')


def native_manifest(root, m, diagnostics=True):
    native = dict(tables=m['tables'], threads=16, models=m['models'], cases=[],
                  keyset_sha256=m['keyset_sha256'], diagnostics=diagnostics)
    for case in m['cases']:
        folder = root/'evaluation'/case['name']
        folder.mkdir(parents=True, exist_ok=False)
        for repeat in (0, 1):
            native['cases'].append(dict(name=case['name']+f'-{repeat}', players=case['players'],
                blocks=case['blocks'], root=case['root'], trace=str(folder/f'play-{repeat}.jsonl'),
                summary=str(folder/f'play-{repeat}.json')))
    return native


def lookup_check(path, case, summary, m):
    """Check diagnostic alignment and reconcile native counters without outcomes."""
    zero = {}
    for alias in ALIASES:
        data = (Path(m['models'][alias]['mass'])/'zero-keys.bin').read_bytes()
        zero[alias] = {data[i:i+16].hex() for i in range(0,len(data),16)}
    counts = [[[[0]*3 for _ in ALIASES] for _ in range(4)] for _ in range(3)]
    decisions = [[0]*4 for _ in range(3)]
    misses = [[0]*4 for _ in range(3)]
    hands = 0
    with path.open() as stream:
        header = json.loads(next(stream))
        pins = [dict(script=n[4:],version='nplayer-scripts-v1') if n.startswith('bot=') else
                dict(sha256=m['models'][n]['sha256'],source_checkpoint_sha256=m['models'][n]['checkpoint_sha256'],
                     strategy='average',average_scope=3) for n in case['players']]
        if (header['seed'] != case['root'] or header['blocks'] != case['blocks']
                or header['policies'] != pins
                or header['lookup_metadata'] != dict(models=list(ALIASES), statuses=list(LABELS),
                    receipts=[m['models'][a]['mass_sha256'] for a in ALIASES])):
            raise ValueError('diagnostic header mismatch')
        for line in stream:
            row = json.loads(line)
            if len(row['lookups']) != len(row['actions']):
                raise ValueError('lookup/action length differs')
            for state, action, lookup in zip(row['states'][:-1], row['actions'], row['lookups']):
                seat = state['actor']
                identity = row['identities'][seat]
                model = case['players'][identity]
                street = ('preflop','flop','turn','river').index(state['street'])
                decisions[identity][street] += 1
                if model.startswith('bot='):
                    if lookup != dict(status='not_applicable'):
                        raise ValueError('script lookup mislabeled')
                    continue
                if (lookup['acting_model'] != model or lookup['seat'] != seat
                        or lookup['position'] != (seat-row['button'])%3 or lookup['street'] != state['street']
                        or lookup['action'] != action or lookup['pot'] != sum(p[2] for p in state['players'])
                        or lookup['live_players'] != sum(not p[3] for p in state['players'])
                        or len(lookup['key']) != 32 or any(c not in '0123456789abcdef' for c in lookup['key'])
                        or len(lookup['statuses']) != 2):
                    raise ValueError('lookup/public state alignment differs')
                missing = [x == 'missing' for x in lookup['statuses']]
                if missing[0] != missing[1]:
                    raise ValueError('matched membership differs')
                for i, alias in enumerate(ALIASES):
                    status = lookup['statuses'][i]
                    if status not in LABELS or ((lookup['key'] in zero[alias]) != (status == 'zero_mass')):
                        raise ValueError('lookup mass label differs')
                    counts[identity][street][i][LABELS.index(status)] += 1
                misses[identity][street] += missing[ALIASES.index(model)]
            hands += 1
    if (hands != case['blocks']*6 or counts != summary['lookup_counts']
            or decisions != summary['decisions_by_identity_street'] or misses != summary['misses_by_identity_street']):
        raise ValueError('diagnostic count reconciliation failed')
    return counts


def check_case(task):
    root, case, m = task
    from scripts.check_nplayer_policy_replay import check
    folder = Path(root)/'evaluation'/case['name']
    a,b = folder/'play-0.jsonl',folder/'play-1.jsonl'
    digest = guard.sha(a)
    summaries = [load(folder/f'play-{i}.json') for i in (0,1)]
    stable = ('status','blocks','hands','trace_sha256','lookup_counts','decisions_by_identity_street','misses_by_identity_street')
    if guard.sha(b) != digest or any(summaries[0][k] != summaries[1][k] for k in stable):
        raise ValueError('exact reproduction differs')
    if summaries[0]['trace_sha256'] != digest or summaries[0]['status'] != 'passed':
        raise ValueError('native proof mismatch')
    lookup_check(a, case, summaries[0], m)
    replay = check(a)
    if replay['hands'] != case['blocks']*6 or replay['trace_sha256'] != digest or replay['status'] != 'passed':
        raise ValueError('independent replay differs')
    guard.write(folder/'replay.json', replay)
    result = dict(status='passed', case=case, hands=replay['hands'], trace_sha256=digest)
    guard.write(folder/'result.json', result)
    return result


def batch(root):
    m = load(root/'evaluation-manifest.json')
    if m['cases'] != cases(m['smoke']):
        raise ValueError('changed fixed matrix')
    from scripts.check_nplayer_parity import engine_identity
    engine_identity()
    tick = time.monotonic()
    verify_inputs(m)
    verification = time.monotonic()-tick
    native = native_manifest(root, m)
    path = root/'native-evaluation-manifest.json'
    guard.write(path,native)
    tick = time.monotonic()
    subprocess.run([m['arena'],'batch',str(path)],check=True)
    native_wall = time.monotonic()-tick
    tick = time.monotonic()
    verify_inputs(m)
    verification += time.monotonic()-tick
    summaries = [load(row['summary']) for row in native['cases']]
    if sum(r['new_weight_tables'] for r in summaries) != 2 or any(
            r['resident_weight_tables'] != 2 or r['resident_card_table_sets'] != 1 for r in summaries):
        raise ValueError('two-model persistent load proof failed')
    tick = time.monotonic()
    with ProcessPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(check_case,(str(root),c,m)) for c in m['cases']]
        for i,f in enumerate(as_completed(futures),1):
            try:
                f.result()
            except BaseException:
                print(json.dumps(dict(event='fatal',error='replay/diagnostic verification failed')),flush=True)
                raise
            print(json.dumps(dict(event='progress',verified_cases=i,total=len(futures))),flush=True)
    guard.write(root/'evaluation-cost.json',dict(native_wall_seconds=native_wall,
        native_load_seconds=sum(r['load_seconds'] for r in summaries), native_play_seconds=sum(r['play_seconds'] for r in summaries),
        replay_wall_seconds=time.monotonic()-tick,input_verification_seconds=verification,policy_loads=2,
        trace_bytes=sum(Path(r['trace']).stat().st_size for r in native['cases'])))
    guard.write(root/'evaluation-verified.json',dict(status='passed',manifest_sha256=guard.sha(root/'evaluation-manifest.json'),
        cases=len(m['cases']),hands=sum(c['blocks']*6 for c in m['cases'])))


def read(root):
    from scripts.analyze_nplayer_arena import interval
    from scripts.read_nplayer_fast_study import paired_blocks
    from scipy.stats import t
    import math
    m=load(root/'evaluation-manifest.json')
    proof=load(root/'evaluation-verified.json')
    if ((root/'failure.json').exists() or load(root/'status.json')['status'] not in ('verified-readout-ready','complete')
            or m['cases'] != cases(m['smoke']) or proof != dict(status='passed',
                manifest_sha256=guard.sha(root/'evaluation-manifest.json'),cases=18,hands=sum(c['blocks']*6 for c in m['cases']))):
        raise ValueError('global replay barrier not ready')
    # Revalidate trace bytes before exposing any payoff. Do not repeat engine play.
    for c in m['cases']:
        folder=root/'evaluation'/c['name'];r=load(folder/'result.json');p=load(folder/'replay.json')
        digest=guard.sha(folder/'play-0.jsonl')
        if (r != dict(status='passed',case=c,hands=c['blocks']*6,trace_sha256=digest)
                or p['status']!='passed' or p['hands']!=c['blocks']*6 or p['trace_sha256']!=digest
                or guard.sha(folder/'play-1.jsonl')!=digest):
            raise ValueError('final trace proof changed')
    verify_inputs(m)
    rows=[]
    for a,b in zip(m['cases'][::2],m['cases'][1::2]):
        values=list(paired_blocks(root/'evaluation'/a['name']/'play-0.jsonl',root/'evaluation'/b['name']/'play-0.jsonl',a['root']))
        if len(values)!=a['blocks']:
            raise ValueError('statistical block count differs')
        data=[v['advantage'] if a['group']=='direct' else v['fast_singleton']-v['production_singleton'] for v in values]
        score=interval(data)
        width=float(t.ppf(1-.05/(2*8),len(data)-1))*statistics.stdev(data)/math.sqrt(len(data))
        if a['group']!='direct':
            score.update(lower_family95=statistics.mean(data)-width,upper_family95=statistics.mean(data)+width)
        rows.append(dict(group=a['group'],opponent=a.get('opponent'),score=score,
            candidate_absolute=interval([v['fast_singleton'] for v in values]),
            baseline_absolute=interval([v['production_singleton'] for v in values]),
            by_seat={tag:[interval([v[key][i] for v in values]) for i in range(3)] for tag,key in
                     [('candidate','fast_by_seat'),('baseline','production_by_seat')]},
            by_position={tag:[interval([v[key][i] for v in values]) for i in range(3)] for tag,key in
                         [('candidate','fast_by_position'),('baseline','production_by_position')]}))
    diagnostic=diagnostic_readout(root,m)
    guard.write(root/'results.json',dict(status='settled',rows=rows,models=m['models'],diagnostics=diagnostic,
        direct_statistic='mean oriented singleton contrast, not pooled individual-player return',
        final_hands=proof['hands'],reproduction_hands=proof['hands'],
        improvement_evidence=rows[0]['score']['lower95_bb100']>0,no_automatic_adoption=True))
    guard.write(root/'status.json',dict(status='complete',at=time.time()))


def diagnostic_readout(root,m):
    from collections import defaultdict
    result={}
    for case in m['cases']:
        folder=root/'evaluation'/case['name']
        counts=load(folder/'play-0.json')['lookup_counts']
        transitions=defaultdict(int);paths=defaultdict(lambda:dict(hands=0,sum_bb100=0.,example=None));reached=defaultdict(lambda:[0,0.]);river=[0,0]
        positions=[[[[0]*3 for _ in range(2)] for _ in range(4)] for _ in range(3)]
        pots=defaultdict(lambda:[0,0.])
        with (folder/'play-0.jsonl').open() as f:
            next(f)
            for line in f:
                row=json.loads(line);seat=row['identities'].index(0);reward=row['rewards'][seat]*100/row['bb']
                own=[e for e in row['history'] if len(e)==5 and e[1]==seat]
                pre='/'.join(e[2] for e in own if e[0]=='preflop') or 'none'
                fold=next((e[0] for e in own if e[2]=='fold'),None)
                end='fold-'+fold if fold else ('showdown' if sum(not p[3] for p in row['states'][-1]['players'])>1 else 'uncontested')
                path=f'{(seat-row["button"])%3}: {pre} -> {end}'
                g=paths[path];g['hands']+=1;g['sum_bb100']+=reward
                if g['example'] is None:g['example']=dict(root=case['root'],hand=row['hand'],block=row['block'],permutation=row['permutation'])
                pot=sum(p[0] for p in row['settlement']['pots'])/row['bb']
                band='<5BB' if pot<5 else '5-20BB' if pot<20 else '20-50BB' if pot<50 else '>=50BB'
                pots[band][0]+=1;pots[band][1]+=reward
                streets=set();had_river=had_two=False
                for state,lookup in zip(row['states'][:-1],row['lookups']):
                    if state['actor']!=seat:continue
                    streets.add(state['street'])
                    if state['street']=='river':
                        had_river=True;had_two|=sum(not p[3] for p in state['players'])==2
                    transitions['/'.join(lookup['statuses'])]+=1
                    for i,label in enumerate(lookup['statuses']):
                        positions[lookup['position']][('preflop','flop','turn','river').index(lookup['street'])][i][LABELS.index(label)]+=1
                for street in streets:
                    reached[street][0]+=1;reached[street][1]+=reward
                river[0]+=had_river;river[1]+=had_two
        result[case['name']]=dict(lookup_counts=counts,matched_status_transitions=dict(transitions),
            singleton_paths=dict(paths),singleton_reached_street=dict(reached),river_hands=river,
            singleton_lookup_by_position_street=positions,singleton_pot_bands=dict(pots),
            source_trace_sha256=load(folder/'result.json')['trace_sha256'],
            return_strata_note='counts and summed BB/100 hand outcomes; reached-street/path conditioning is descriptive')
    return result


def run(root):
    if (root/'launch.json').exists():
        raise ValueError('study already launched; existing root is immutable to relaunch')
    c=load(root/'config.json')
    check_config(c)
    supervised(root,lambda stage:execute(c,root,stage))


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    for name in ('build','run','batch','read'):
        sub.add_parser(name).add_argument('root',type=Path)
    q=sub.add_parser('qualify');q.add_argument('root',type=Path)
    q.add_argument('--build-root',type=Path,required=True);q.add_argument('--tables',type=Path,required=True);q.add_argument('--python',type=Path,required=True)
    c=sub.add_parser('configure');c.add_argument('root',type=Path)
    c.add_argument('--build-root',type=Path,required=True);c.add_argument('--tables',type=Path,required=True)
    c.add_argument('--python',type=Path,required=True);c.add_argument('--qualification',type=Path,required=True)
    a=p.parse_args();root=a.root.absolute()
    if a.mode=='build':build(root);return
    if a.mode=='configure':configure(root,a.build_root.absolute(),a.tables.absolute(),a.python,a.qualification.absolute());return
    if a.mode=='qualify':
        from scripts.qualify_nplayer_bb100_continuation import qualify
        qualify(root,a.build_root.absolute(),a.tables.absolute(),a.python);return
    globals()[a.mode](root)


if __name__=='__main__':main()
