"""PR350: qualify, then run the owner-authorized capped100BB campaign once.

Raw checkpoints and traces remain in the fresh owned HDD root. The source and
all numerical choices are pinned before qualification. No failed stage is retried.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import fcntl
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import time

from scripts import run_nplayer_storage_benchmark as guard
from scripts.nplayer_overnight import BOTS, load, read as legacy_read
from scripts.overnight_tensorboard import Scalars

SEEDS = (202610193501, 202610193502, 202610193503)
CALIBRATION_SEED = 2026101935003
FIXTURE_SEED = 2026101935004
CAP = 250_000_000
TARGETS = (1_000_000_000, 3_000_000_000, 10_000_000_000)
QUAL_SECONDS = 2 * 3600
MAIN_SECONDS = 8 * 3600
OUTPUT_BUDGET = 600_000_000_000


def cases(smoke=False):
    rows = []
    index = 0
    for group in ('same', 'cross'):
        for i, seed in enumerate(SEEDS):
            other = seed if group == 'same' else SEEDS[(i+1) % 3]
            for reverse in (False, True):
                a, b = f'final-{seed}', f'anchor-{other}'
                rows.append(dict(name=f'{group}-{seed}-{int(reverse)}', group=group, seed=seed,
                    root=(20261019355101 if smoke else 20261019355001)+index,
                    blocks=2 if smoke else 8192, singleton=b if reverse else a, pair=a if reverse else b))
            index += 1
    for seed in SEEDS:
        for bot in BOTS:
            for anchor in (False, True):
                rows.append(dict(name=f'bot-{seed}-{bot}-{int(anchor)}', group='bot', seed=seed, bot=bot,
                    root=(20261019355101 if smoke else 20261019355001)+index,
                    blocks=2 if smoke else 8192, singleton=f'{"anchor" if anchor else "final"}-{seed}', pair='bot='+bot))
            index += 1
    return rows


def execution_order(rows):
    return ([r for seed in SEEDS for r in rows if r['seed'] == seed and r['group'] != 'cross']
            + [r for r in rows if r['group'] == 'cross'])


def spec(name, models):
    if name.startswith('bot='):
        return name
    row = models[name]
    return 'policy='+row['path']+'@'+row['sha256']


def check_case(task):
    from scripts.check_nplayer_policy_replay import check
    case, manifest, root = task
    folder = Path(root)/'evaluation'/case['name']
    a, b = folder/'play-0.jsonl', folder/'play-1.jsonl'
    digest = guard.sha(a)
    if guard.sha(b) != digest:
        raise ValueError('reproduction differs: '+case['name'])
    coverage = [load(folder/f'play-{i}.json') for i in (0, 1)]
    fields = ('status', 'blocks', 'hands', 'decisions_by_identity_street',
              'misses_by_identity_street', 'trace_sha256')
    if any(coverage[0][k] != coverage[1][k] for k in fields):
        raise ValueError('coverage reproduction differs')
    with a.open() as stream:
        header = json.loads(next(stream))
    expected = [manifest['models'][n]['sha256'] if not n.startswith('bot=') else None
                for n in (case['singleton'], case['pair'], case['pair'])]
    if (header['seed'] != case['root'] or header['blocks'] != case['blocks']
            or header['identity']['stacks'] != [10000]*3
            or [p.get('sha256') for p in header['policies']] != expected):
        raise ValueError('trace identity differs')
    replay = check(a)
    if replay['status'] != 'passed' or replay['hands'] != case['blocks']*6 or replay['trace_sha256'] != digest:
        raise ValueError('replay proof differs')
    result = dict(status='passed', case=case, trace_sha256=digest, hands=replay['hands'], coverage=coverage)
    guard.write(folder/'replay.json', replay)
    guard.write(folder/'result.json', result)
    return result


def batch(root):
    from scripts.check_nplayer_parity import engine_identity
    engine_identity()
    m = load(root/'evaluation-manifest.json')
    if m['cases'] != cases(m['smoke']):
        raise ValueError('changed frozen matrix')
    def verify_inputs():
        for path, digest in [(m['arena'], m['arena_sha256'])]+[(v['path'], v['sha256']) for v in m['models'].values()]:
            if guard.sha(path) != digest:
                raise ValueError('evaluation input changed')
    verify_inputs()
    (root/'evaluation').mkdir(exist_ok=False)
    native = dict(tables=m['tables'], threads=16, stack_bb=100, cases=[])
    for c in execution_order(m['cases']):
        folder = root/'evaluation'/c['name']
        folder.mkdir(exist_ok=False)
        for repeat in (0, 1):
            native['cases'].append(dict(name=c['name']+f'-{repeat}', blocks=c['blocks'], root=c['root'],
                trace=str(folder/f'play-{repeat}.jsonl'), summary=str(folder/f'play-{repeat}.json'),
                singleton=spec(c['singleton'], m['models']), pair=spec(c['pair'], m['models'])))
    guard.write(root/'native-evaluation-manifest.json', native)
    # This child inherits the guarded batch process group; never starts a new PG.
    subprocess.run([m['arena'], 'batch', str(root/'native-evaluation-manifest.json')], check=True)
    verify_inputs()
    with ProcessPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(check_case, (c, m, str(root))) for c in m['cases']]
        for i, f in enumerate(as_completed(futures), 1):
            f.result()
            print(json.dumps(dict(event='progress', replayed_cases=i, total=len(futures))), flush=True)
    guard.write(root/'evaluation-verified.json', dict(status='passed',
        manifest_sha256=guard.sha(root/'evaluation-manifest.json'), cases=len(m['cases']),
        hands=sum(c['blocks']*6 for c in m['cases'])))


def read(root):
    # Keep the reviewed statistics and global barrier with this explicit matrix.
    legacy_read(root, matrix=cases())
    result = load(root/'results.json')
    result['severe_scripted_regression'] = any(
        r['score']['upper_family95'] < -10 for r in result['rows'] if r['group'] == 'bot')
    result['scope'] = '100BB frozen250M; singleton-oriented contrasts, not pooled player returns'
    guard.write(root/'results.json', result)


def decompressed_sha(path):
    value = hashlib.sha256()
    with gzip.open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(4*1024**2), b''):
            value.update(chunk)
    return value.hexdigest()


def events(result, event):
    return [e for e in result['events'] if e.get('event') == event]


def model(result, label):
    row = next(e for e in events(result, 'exported') if e['label'] == label)
    return dict(path=row['path'], sha256=row['sha256'], checkpoint=row['checkpoint'],
                checkpoint_sha256=row['checkpoint_sha256'], strategy='average', scope=3)


def validate_trajectory(result, cap, endpoint, require_frozen=True):
    checkpoints = events(result, 'checkpoint')
    if not checkpoints or checkpoints[-1]['nodes'] < endpoint or len(events(result, 'complete')) != 1:
        raise ValueError('incomplete trajectory')
    frozen = [c for c in checkpoints if c['frozen_at'] is not None]
    if require_frozen and not frozen:
        raise ValueError('capacity was not reached at the fixed qualification endpoint')
    if frozen and (len({c['keyset_sha256'] for c in frozen}) != 1
                   or len({c['entries'] for c in frozen}) != 1):
        raise ValueError('frozen membership changed')
    for c in checkpoints:
        if guard.sha(c['path']) != c['sha256']:
            raise ValueError('checkpoint readback differs')
        with gzip.open(c['path'], 'rt') as stream:
            h = json.loads(next(stream))
        if (h['game']['stacks'] != [10000]*3 or h['players'] != 3 or h['max_entries'] != cap
                or not h['freeze_at_cap'] or h['sampling'] != 'path-v1' or h['roots_per_seat'] != 8
                or h['last_average_street'] != 3 or 'pruning' in h or h['counts'] != c['counts']):
            raise ValueError('checkpoint recipe/accounting differs')
        if c['frozen_at'] is None and (c['counts']['discarded_keys'] or c['counts']['discarded_visits']):
            raise ValueError('unexpected pre-freeze discard')
    if frozen and checkpoints[-1]['counts']['discarded_keys'] == 0:
        raise ValueError('missing post-freeze discard accounting')
    for e in events(result, 'exported'):
        if guard.sha(e['path']) != e['sha256']:
            raise ValueError('export readback differs')
    return checkpoints[-1]


class Supervisor(guard.Supervisor):
    def __init__(self, root, lock, logs):
        guard.BUDGET = OUTPUT_BUDGET
        guard.FLOOR = 50_000_000_000
        super().__init__(root, lock, cpus=range(16), max_seconds=QUAL_SECONDS,
            rss_limit=80*guard.GIB, cpu_limit=90, thermistor_limit=100,
            swap_limit_bytes=None, address_limit=96*guard.GIB)
        self.logs, self.seed, self.last_log = logs, 0, 0
        self.parse = guard.json_event

    def sample(self, process, phase, target):
        row = super().sample(process, phase, target)
        disk = os.statvfs('/home/dberweger')
        row['nvme_free_bytes'] = disk.f_bavail*disk.f_frsize
        row['cpu_stop_c'], row['thermistor15_stop_c'], row['swap_guard_enabled'] = 90, 100, False
        if row['nvme_free_bytes'] < 50_000_000_000:
            error = RuntimeError('NVMe50GB floor stop')
            error.resource_sample = row
            raise error
        if time.monotonic()-self.last_log >= 30:
            step = int(time.time())
            for key in ('rss_bytes', 'available_ram_bytes', 'swap_used_bytes', 'swap_growth_bytes', 'free_disk_bytes'):
                self.logs.add('resources/'+key, row[key], step)
            for key, value in row['temperatures_c'].items():
                self.logs.add('temperature/'+key, value, step)
            self.last_log = time.monotonic()
        return row

    def event(self, line):
        e = self.parse(line)
        if e is None:
            return None
        if e.get('event') in ('progress', 'trained'):
            for key in ('nodes', 'entries', 'active_seconds', 'monitor_seconds', 'nodes_per_second'):
                if isinstance(e.get(key), (int, float)):
                    self.logs.add(f'{self.seed}/training/{key}', e[key], e.get('nodes', 0))
            for key, value in e.get('allocation_bytes', {}).items():
                self.logs.add(f'{self.seed}/allocation/{key}', value, e['nodes'])
        if e.get('active_seconds', 0) > 100 and e.get('monitor_seconds', 0) > .1*e['active_seconds']:
            raise RuntimeError('monitoring overhead exceeds10%')
        if e.get('event') == 'probe':
            for row in e['results']:
                values = row['block_bb100']
                mean = statistics.mean(values)
                width = 1.9788195347*statistics.stdev(values)/math.sqrt(len(values))
                for key, value in [('bb100', mean), ('lower95', mean-width), ('upper95', mean+width)]:
                    self.logs.add(f'{self.seed}/monitor/{row["bot"]}/{key}', value, e['nodes'])
        return e


def run(root):
    c = load(root/'config.json')
    src = Path(__file__).parents[1]
    for name, digest in c['source_files'].items():
        if guard.sha(src/name) != digest:
            raise ValueError('source pin mismatch: '+name)
    for key in ('train', 'legacy_train', 'policy', 'arena', 'legacy_arena'):
        if guard.sha(c[key]) != c[key+'_sha256']:
            raise ValueError('binary pin mismatch: '+key)
    if (root/'launch.json').exists():
        raise ValueError('this run was already launched')
    started = time.time()
    guard.write(root/'launch.json', dict(epoch=started, supervisor_pid=os.getpid(),
        qualification_deadline_epoch=started+QUAL_SECONDS, main_maximum_seconds=MAIN_SECONDS,
        seeds=SEEDS, targets=TARGETS, cap=CAP, output_reservation_bytes=OUTPUT_BUDGET,
        rss_limit_bytes=80*guard.GIB, address_limit_bytes=96*guard.GIB,
        cpu_stop_c=90, thermistor15_stop_c=100, swap_guard_enabled=False,
        source_commit=c['source_commit'], source_manifest_sha256=guard.sha(root/'config.json')))
    with Path('/tmp/cfr-nplayer-bb100.lock').open('a') as own, Path('/tmp/cfr-cygnus-exclusive.lock').open('a') as normal:
        for lock in (own, normal):
            fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        logs = Scalars(root/'tensorboard')
        s = Supervisor(root, own.fileno(), logs)
        guard.json_event = s.event
        first = s.sample(None, 'admission', 0)
        if first['temperatures_c']['Package id 0'] >= 70 or first['temperatures_c']['Thermistor 15'] >= 80:
            raise RuntimeError('thermal admission refused')
        guard.write(root/'admission.json', first)
        env = dict(os.environ, RAYON_NUM_THREADS='16', OMP_NUM_THREADS='1',
            OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', NPLAYER_STOP_FILE=str(root/'STOP'))
        def stage(name, command, keep_status=False):
            s.sample(None, 'stage-admission', 0)
            if not keep_status:
                guard.write(root/'status.json', dict(status=name, at=time.time(), seed=s.seed))
            print(json.dumps(dict(event='stage-start', stage=name)), flush=True)
            value = s.execute(name, list(map(str, command)), src, env)
            print(json.dumps(dict(event='stage-complete', stage=name, wall_seconds=value['wall_seconds'])), flush=True)
            return value
        def train(name, seed, targets, cap=100_000, parallel=False, input_model=None, probes=(), reference=None):
            s.seed = seed
            config = dict(seed=seed, threads=16, stack_bb=100, max_entries=cap, freeze_at_cap=True,
                parallel_gzip=parallel, tables=c['tables'], out=str(root/name), targets=list(targets),
                probe_nodes=list(probes), probe_blocks=128 if probes else 0,
                probe_root=20261019355201 if seed == FIXTURE_SEED else 20261019355301+(SEEDS.index(seed)*10 if seed in SEEDS else 40),
                stop_file=str(root/'STOP'), save_anchor=True, export_final=True)
            if input_model:
                config.update(input=input_model['checkpoint'], input_sha256=input_model['checkpoint_sha256'])
            if reference:
                config.update(reference=reference['path'], reference_sha256=reference['sha256'])
            path = root/(name+'-config.json')
            guard.write(path, config)
            result = stage(name, [c['train'], path])
            validate_trajectory(result, cap, targets[-1])
            return result
        def audit(name, m, parallel=True):
            module = 'scripts.audit_nplayer_policy_parallel' if parallel else 'scripts.audit_nplayer_policy'
            result = stage(name, [c['python'], '-m', module, m['checkpoint'], m['path']])
            value = load(root/'measurements'/name/'stdout.log')
            if value['status'] != 'passed' or value['policy_sha256'] != m['sha256']:
                raise ValueError('independent audit failed')
            return result, value
        def cli(name, threads):
            path = root/(name+'.gz')
            result = stage(name, [c['legacy_train'], '--players', '3', '--stack-bb', '100', '--fast',
                '--threads', str(threads), '--roots-per-seat', '8', '--seed', str(FIXTURE_SEED), '--nodes', '3000000',
                '--max-entries', '100000', '--freeze-at-cap', '--last-average-street', '3', '--max-seconds', '300',
                '--card-buckets', c['tables'], '--out', path])
            summary = load(root/'measurements'/name/'stdout.log')
            if summary['stop_reason'] != 'nodes':
                raise ValueError('CLI fixture incomplete')
            return guard.sha(path)
        one, many = cli('fixture-cli-one', 1), cli('fixture-cli-sixteen', 16)
        fixture = train('fixture-host', FIXTURE_SEED, [1_000_000, 3_000_000], probes=[0, 1_000_000, 3_000_000])
        if one != many or events(fixture, 'checkpoint')[-1]['sha256'] != one:
            raise ValueError('CLI/thread/host fixture differs')
        base = model(fixture, '3000000')
        resumed = train('fixture-resume', FIXTURE_SEED, [5_000_000], input_model=base, probes=[0], reference=base)
        fresh = train('fixture-fresh', FIXTURE_SEED, [5_000_000])
        parallel = train('fixture-parallel-gzip', FIXTURE_SEED, [3_000_000], parallel=True)
        parallel_base = model(parallel, '3000000')
        parallel_resume = train('fixture-parallel-resume', FIXTURE_SEED, [5_000_000], input_model=parallel_base)
        if len({events(r, 'checkpoint')[-1]['sha256'] for r in (resumed, fresh, parallel_resume)}) != 1:
            raise ValueError('resume/compression recovery differs')
        if decompressed_sha(base['checkpoint']) != decompressed_sha(parallel_base['checkpoint']):
            raise ValueError('parallel compression changes checkpoint')
        exported = root/'fixture-separate-export.gz'
        stage('fixture-separate-export', [c['policy'], 'export', base['checkpoint'], base['checkpoint_sha256'], 'average', exported])
        if guard.sha(exported) != base['sha256']:
            raise ValueError('direct/separate export differs')
        _, serial_audit = audit('fixture-serial-audit', base, False)
        _, parallel_audit = audit('fixture-parallel-audit', base)
        if serial_audit != parallel_audit:
            raise ValueError('serial/parallel independent audits differ')
        def arena(name, blocks, root_seed, singleton, pair, stack=100, threads=16, old=False):
            path = root/(name+'.jsonl')
            args = [c['legacy_arena'] if old else c['arena'], c['tables'], blocks, root_seed, path, singleton, pair]
            if not old:
                args += [stack, threads]
            stage(name, args)
            return path, load(root/'measurements'/name/'stdout.log')
        policy_spec = spec('p', {'p': base})
        a, _ = arena('fixture-arena-one', 2, 20261019355401, policy_spec, 'bot=random', threads=1)
        b, _ = arena('fixture-arena-sixteen', 2, 20261019355401, policy_spec, 'bot=random')
        if guard.sha(a) != guard.sha(b):
            raise ValueError('parallel arena changes trace')
        old, _ = arena('fixture-old20', 2, 20261019355402, 'bot=random', 'bot=pot-pressure', old=True)
        new, _ = arena('fixture-new20', 2, 20261019355402, 'bot=random', 'bot=pot-pressure', stack=20)
        if guard.sha(old) != guard.sha(new):
            raise ValueError('old20BB arena trace changed')
        for name, path in [('fixture-replay', a), ('fixture-old20-replay', new)]:
            stage(name, [c['python'], '-m', 'scripts.check_nplayer_policy_replay', path])
        # Check complete in-memory probe paths against the independently replayed exported policy.
        probe = events(resumed, 'probe')[0]
        for row in probe['results']:
            path, _ = arena('probe-'+row['bot'], 128, row['root'], policy_spec, 'bot='+row['bot'])
            value = hashlib.sha256(); values = []; rewards = []
            with path.open() as stream:
                next(stream)
                for line in stream:
                    h = json.loads(line)
                    value.update((json.dumps([h[k] for k in ('block','permutation','actors','actions','rewards')], separators=(',', ':'))+'\n').encode())
                    rewards.append(h['rewards'][h['identities'].index(0)])
                    if h['permutation'] == 5:
                        values.append(sum(rewards)/6); rewards = []
            if value.hexdigest() != row['play_sha256'] or values != row['block_bb100']:
                raise ValueError('probe/export played path differs')
            stage('probe-replay-'+row['bot'], [c['python'], '-m', 'scripts.check_nplayer_policy_replay', path])
        smoke = root/'smoke'; smoke.mkdir(exist_ok=False)
        m = dict(arena=c['arena'], arena_sha256=c['arena_sha256'], tables=c['tables'], smoke=True,
            cases=cases(True), models={f'{label}-{seed}':base for seed in SEEDS for label in ('anchor','final')})
        guard.write(smoke/'evaluation-manifest.json', m)
        stage('matrix-smoke', [c['python'], '-m', 'scripts.nplayer_bb100_overnight', 'batch', smoke])
        guard.write(root/'small-qualification.json', dict(status='passed', cli_checkpoint_sha256=one,
            resume_checkpoint_sha256=events(fresh,'checkpoint')[-1]['sha256'], probe_hands=3072, smoke_hands=432))
        calibration = train('calibration', CALIBRATION_SEED, [1_000_000_000, 2_000_000_000], cap=CAP, parallel=True,
                            probes=[1_000_000_000, 2_000_000_000])
        anchor, final = model(calibration, 'anchor'), model(calibration, '2000000000')
        audit_a, _ = audit('calibration-anchor-audit', anchor)
        audit_b, _ = audit('calibration-final-audit', final)
        pair0, pair_summary = arena('calibration-pair', 128, 20261019355403,
                                   spec('a', {'a':final}), spec('b', {'b':anchor}))
        pair1, _ = arena('calibration-pair-repeat', 128, 20261019355403,
                         spec('a', {'a':final}), spec('b', {'b':anchor}))
        if guard.sha(pair0) != guard.sha(pair1):
            raise ValueError('mature reproduction differs')
        replay = stage('calibration-pair-replay', [c['python'], '-m', 'scripts.check_nplayer_policy_replay', pair0])
        quote = cost_quote(calibration, audit_a, audit_b, pair_summary, replay,
                           load(root/'measurements/calibration-pair/result.json'))
        guard.write(root/'cost-quote.json', quote)
        if (quote['total_seconds_with_allowance'] > MAIN_SECONDS or quote['peak_rss_with_allowance_bytes'] > 80*guard.GIB
                or quote['monitoring_fraction'] > .1):
            raise RuntimeError('measured overnight admission refused; no final seed started')
        s.sample(None, 'qualified', 0)
        # A prospective main deadline, distinct from the fixed qualification budget.
        # Neither deadline is extended on failure or restart.
        main_epoch = time.time()
        s.max_seconds = time.monotonic()-s.started+MAIN_SECONDS
        guard.write(root/'pretraining-freeze.json', dict(status='qualified', epoch=main_epoch,
            deadline_epoch=main_epoch+MAIN_SECONDS, quote=quote, seeds=SEEDS, targets=TARGETS, cap=CAP,
            cases=cases(), source_commit=c['source_commit'], source_manifest_sha256=guard.sha(root/'config.json')))
        models = {}
        for seed in SEEDS:
            result = train(f'training-{seed}', seed, TARGETS, cap=CAP, parallel=True,
                           probes=range(1_000_000_000, 10_000_000_001, 1_000_000_000))
            for label, export_label in [('anchor','anchor'), ('final','10000000000')]:
                v = model(result, export_label)
                audit(f'audit-{label}-{seed}', v)
                models[f'{label}-{seed}'] = v
            guard.write(root/'training-progress.json', dict(completed_seed=seed, completed_seeds=len(models)//2, models=models))
        m.update(smoke=False, cases=cases(), models=models)
        guard.write(root/'evaluation-manifest.json', m)
        stage('final-evaluation', [c['python'], '-m', 'scripts.nplayer_bb100_overnight', 'batch', root])
        guard.write(root/'status.json', dict(status='verified-readout-ready', at=time.time()))
        stage('readout', [c['python'], '-m', 'scripts.nplayer_bb100_overnight', 'read', root], keep_status=True)
        guard.write(root/'status.json', dict(status='complete', at=time.time()))
        logs.close()


def cost_quote(calibration, audit_a, audit_b, pair, replay, pair_measurement):
    frozen = events(calibration, 'frozen')[0]
    done = events(calibration, 'complete')[0]
    rate = (done['nodes']-frozen['nodes'])/(done['active_seconds']-frozen['active_seconds'])
    growth = frozen['active_seconds']
    training = 3*(growth+(10_000_000_000-frozen['nodes'])/rate)
    checkpoints = events(calibration, 'checkpoint')
    exports = events(calibration, 'exported')
    # Four saves and two exports per final seed; source readbacks and hashes get
    # explicit allowances from measured whole-stage overhead, not training rate.
    saving = 12*max(e['save_seconds'] for e in checkpoints)
    exporting = 6*max(e['export_seconds'] for e in exports)
    auditing = 3*(audit_a['wall_seconds']+audit_b['wall_seconds'])
    monitoring = done['monitor_seconds']*15  # two calibration probes ->30 final probes.
    # Persistent batches retain two tables: six own-seed + six cyclic cross loads.
    loading = 6*pair['load_seconds']
    playing = pair['play_seconds']*(1769472*2/(128*6))
    replaying = replay['wall_seconds']*(1769472/(128*6))/8
    remainder = max(0, calibration['wall_seconds']-done['active_seconds']-done['monitor_seconds']
                    -sum(e['save_seconds'] for e in checkpoints)-sum(e['export_seconds'] for e in exports))
    verification = remainder*4 + 900
    peak = max(max(calibration['sampled_peak_rss_by_phase'].values()),
               max(pair_measurement['sampled_peak_rss_by_phase'].values()), CAP*224+4*guard.GIB)
    total = sum((training, saving, exporting, auditing, monitoring, loading, playing, replaying, verification))
    return dict(training_seconds=training, saving_seconds=saving, export_seconds=exporting,
        audit_seconds=auditing, monitoring_seconds=monitoring, model_load_seconds=loading,
        play_seconds=playing, replay_seconds=replaying, verification_allowance_seconds=verification,
        total_seconds_with_allowance=1.25*total, post_freeze_nodes_per_second=rate,
        peak_rss_with_allowance_bytes=1.25*peak, monitoring_fraction=monitoring/training,
        cap=CAP, final_seeds=SEEDS, final_hands=1769472, reproduction_hands=1769472,
        scope='one calibration trajectory; fixed matrix, no strength-based selection')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('run', 'batch', 'read'))
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    try:
        globals()[args.mode](args.root)
    except BaseException as error:
        failure = dict(error=repr(error), at=time.time())
        if hasattr(error, 'resource_sample'):
            failure['resource_sample'] = error.resource_sample
        guard.write(args.root/'failure.json', failure)
        raise
