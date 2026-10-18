"""Owner-authorized PR344 key qualification and fixed-work bb128 comparison."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import statistics
import time

from scripts import run_nplayer_storage_benchmark as guard

SCHEMAS = ('v1', 'compact-blake2b-v2', 'compact-xxh3-v2')
SEED = 2026101832701
THREADS = (1, 2, 4, 8, 16)
TARGETS = (1_000_000_000, 3_000_000_000)
STEADY = 3_200_000_000
MAX_SECONDS = 2 * 3600


def load(path):
    return json.loads(Path(path).read_text())


def checkpoints(result):
    return {event['target']: event for event in result['events'] if event.get('event') == 'checkpoint'}


def trained(result):
    return {event['target']: event for event in result['events'] if event.get('event') == 'trained'}


def same_counts(results):
    reference = next(iter(results.values()))
    for result in results.values():
        if trained(result).keys() != trained(reference).keys():
            raise ValueError('missing matched target')
        for target, event in trained(reference).items():
            other = trained(result)[target]
            for key in ('nodes', 'iteration', 'entries', 'counts'):
                if event[key] != other[key]:
                    raise ValueError(f'cross-schema {key} mismatch at {target}')


def quote(pilots, audit_pilot):
    # Scale traversal by work, serialization by represented rows. The prior
    # measured compact1B load anchors a separate allowance for18 large reloads.
    growth = sum(trained(p)[100_000_000]['seconds'] * 30 for p in pilots.values())
    steady = sum(trained(p)[100_000_000]['seconds'] * 6 for p in pilots.values())
    writing = sum(checkpoints(p)[100_000_000]['save_seconds'] * 212_000_000 /
                  trained(p)[100_000_000]['entries'] for p in pilots.values())
    audit = next(e['seconds'] for e in audit_pilot['events'] if e.get('event') == 'audit-trained') * 32
    audit_write = checkpoints(pilots['v1'])[100_000_000]['save_seconds'] * 46_000_000 / trained(pilots['v1'])[100_000_000]['entries']
    reloads = 18 * 36.83 * 46 / 32.15
    total = 1.25 * (growth + steady + writing + audit + audit_write + reloads) + 300
    return dict(projected_seconds=total, components=dict(growth_seconds=growth,
        steady_seconds=steady, serialization_seconds=writing, audited_training_seconds=audit,
        audit_save_seconds=audit_write, load_allowance_seconds=reloads,
        growth_allowance=1.25, other_seconds=300))


class Supervisor(guard.Supervisor):
    def sample(self, process, phase, target):
        row = super().sample(process, phase, target)
        disk = os.statvfs('/home/dberweger')
        row['home_free_disk_bytes'] = disk.f_bavail * disk.f_frsize
        if row['home_free_disk_bytes'] < 50_000_000_000:
            error = RuntimeError('home NVMe floor stop')
            error.resource_sample = row
            raise error
        return row


def run(root):
    c = load(root / 'config.json')
    started = load(root / 'launch.json')['epoch']
    remaining = started + MAX_SECONDS - time.time()
    if remaining <= 0:
        raise RuntimeError('original compute deadline expired')
    guard.BUDGET = 100_000_000_000
    with Path('/tmp/cfr-nplayer-key-benchmark.lock').open('a') as own, \
            Path('/tmp/cfr-cygnus-exclusive.lock').open('a') as legacy:
        for lock in (own, legacy):
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        supervisor = Supervisor(root, own.fileno(), cpus=range(16), max_seconds=remaining,
            rss_limit=80 * guard.GIB, cpu_limit=90, thermistor_limit=95)
        row = supervisor.sample(None, 'admission', 0)
        if row['temperatures_c']['Package id 0'] >= 70 or row['temperatures_c']['Thermistor 15'] >= 80:
            raise RuntimeError('thermal admission refused')
        for relative, digest in c['source_files'].items():
            if guard.sha(root / 'source' / relative) != digest:
                raise ValueError('source mismatch: ' + relative)
        if guard.sha(c['legacy_train']) != c['legacy_train_sha256']:
            raise ValueError('legacy trainer binary mismatch')
        guard.write(root / 'admission.json', dict(pid=os.getpid(), source_commit=c['source_commit'],
            initial_sample=row, deadline_epoch=started + MAX_SECONDS, schemas=SCHEMAS, cpus=list(range(16))))
        src = root / 'source'
        env = dict(os.environ, RAYON_NUM_THREADS='16', CARGO_BUILD_JOBS='4', OMP_NUM_THREADS='1',
            OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', CARGO_TARGET_DIR=str(root / 'target'),
            NPLAYER_K50_TABLES=c['tables'], PYTHONOPTIMIZE='')
        env['PATH'] = '/home/dberweger/.cargo/bin:' + env['PATH']
        manifest = str(src / 'native/hu20-trainer/Cargo.toml')
        python = c['python']
        guard.write(root / 'status.json', dict(status='build-and-qualification', at=time.time()))
        supervisor.execute('build', ['cargo', 'build', '--release', '--locked', '--manifest-path', manifest,
            '--example', 'nplayer_key_bench', '--example', 'nplayer_train', '--example', 'nplayer_policy', '--example', 'nplayer_arena'], src, env)
        supervisor.execute('native-tests', ['cargo', 'test', '--release', '--locked', '--manifest-path', manifest,
            '--lib', '--example', 'nplayer_key_bench', '--', '--test-threads=1'], src, env)
        binaries = root / 'target/release/examples'
        bench, policy, arena = (str(binaries / name) for name in ('nplayer_key_bench', 'nplayer_policy', 'nplayer_arena'))
        guard.write(root / 'binary-receipts.json', {name: guard.sha(binaries / name)
            for name in ('nplayer_key_bench', 'nplayer_train', 'nplayer_policy', 'nplayer_arena')})

        def stage(label, command):
            return supervisor.execute(label, command, src, env)

        def train(label, schema, targets, threads=16, resume=None):
            pin = '-'
            if resume is not None:
                file = root / (label + '-input.json')
                guard.write(file, dict(path=resume['path'], sha256=resume['sha256']))
                pin = str(file)
            return stage(label, [bench, 'train', c['tables'], str(root / label), schema,
                str(SEED), str(threads), ','.join(map(str, targets)), pin])

        def groups(manifest_path, variants, targets):
            rows = []
            for target in targets:
                row = dict(target=target)
                for schema in SCHEMAS:
                    cp = checkpoints(variants[schema])[target]
                    row[schema] = dict(path=cp['path'], sha256=cp['sha256'])
                rows.append(row)
            guard.write(manifest_path, rows)
            return str(manifest_path)

        fixtures = {}
        for schema in SCHEMAS:
            hashes = []
            for threads in THREADS:
                result = train(f'fixture-{schema}-{threads}', schema, [3_000_000], threads)
                hashes.append(checkpoints(result)[3_000_000]['sha256'])
                if threads == 16:
                    fixtures[schema] = result
            if len(set(hashes)) != 1:
                raise ValueError('thread determinism failed: ' + schema)
            first = train('resume-first-' + schema, schema, [1_000_000])
            resumed = train('resume-final-' + schema, schema, [3_000_000], resume=checkpoints(first)[1_000_000])
            if checkpoints(resumed)[3_000_000]['sha256'] != hashes[0]:
                raise ValueError('resume differs: ' + schema)
        same_counts(fixtures)
        legacy_path = root / 'legacy-fixture.gz'
        stage('legacy-fixture', [c['legacy_train'], '--players', '3', '--stack-bb', '20',
            '--card-buckets', c['tables'], '--nodes', '3000000', '--max-entries', '150000000',
            '--max-seconds', '600', '--last-average-street', '3', '--seed', str(SEED), '--fast',
            '--threads', '16', '--out', str(legacy_path)])
        if guard.sha(legacy_path) != checkpoints(fixtures['v1'])[3_000_000]['sha256']:
            raise ValueError('legacy v1 checkpoint changed')
        stage('fixture-audit', [bench, 'audit', c['tables'], str(root / 'fixture-audit'), 'v1', str(SEED), '16',
            '3000000', groups(root / 'fixture-comparisons.json', fixtures, [3_000_000])])
        exports = {}
        for schema in SCHEMAS:
            cp = checkpoints(fixtures[schema])[3_000_000]
            dest = root / ('fixture-' + schema + '-average.gz')
            stage('export-' + schema, [policy, 'export', cp['path'], cp['sha256'], 'average', str(dest)])
            stage('audit-export-' + schema, [python, '-m', 'scripts.audit_nplayer_policy', cp['path'], str(dest)])
            exports[schema] = 'policy=' + str(dest) + '@' + guard.sha(dest)
        # Compare complete played bodies; headers correctly differ in policy/schema pins.
        traces = []
        for schema in SCHEMAS:
            path = root / ('smoke-' + schema + '.jsonl')
            stage('play-' + schema, [arena, c['tables'], '16', '202610183270101', str(path), exports[schema], exports['v1']])
            stage('replay-' + schema, [python, '-m', 'scripts.check_nplayer_policy_replay', str(path)])
            traces.append(path)
        with traces[0].open('rb') as baseline:
            baseline.readline()
            reference = baseline.read()
        for path in traces[1:]:
            with path.open('rb') as stream:
                stream.readline()
                if stream.read() != reference:
                    raise ValueError('rekeyed policy changes play')
        # Explicitly test mismatched CLI resume before the cost pilot.
        stage('python-qualification', [python, '-m', 'scripts.qualify_nplayer_keys', str(root)])

        pilots = {schema: train('pilot-' + schema, schema, [100_000_000]) for schema in SCHEMAS}
        same_counts(pilots)
        audit_pilot = stage('pilot-audit', [bench, 'audit', c['tables'], str(root / 'pilot-audit'), 'v1',
            str(SEED), '16', '100000000', groups(root / 'pilot-comparisons.json', pilots, [100_000_000])])
        estimate = quote(pilots, audit_pilot)
        guard.write(root / 'cost-quote.json', dict(estimate, remaining_seconds=started + MAX_SECONDS - time.time(), at=time.time()))
        if estimate['projected_seconds'] > started + MAX_SECONDS - time.time():
            raise RuntimeError('measured workload does not fit accepted original two-hour ceiling')
        guard.write(root / 'qualification-passed.json', dict(status='passed', legacy_identity=True,
            cross_thread=list(THREADS), schemas=list(SCHEMAS), source_commit=c['source_commit'], quote=estimate))
        guard.write(root / 'status.json', dict(status='main-growth', at=time.time()))
        growth = {schema: train('growth-' + schema, schema, TARGETS) for schema in SCHEMAS}
        same_counts(growth)
        steady = {schema: [] for schema in SCHEMAS}
        for repeat in range(3):
            for schema in SCHEMAS[repeat:] + SCHEMAS[:repeat]:
                steady[schema].append(train(f'steady-{repeat}-{schema}', schema, [STEADY],
                    resume=checkpoints(growth[schema])[TARGETS[-1]]))
        for schema in SCHEMAS:
            hashes = [checkpoints(result)[STEADY]['sha256'] for result in steady[schema]]
            if len(set(hashes)) != 1:
                raise ValueError('steady repeat differs: ' + schema)
        same_counts({schema: rows[0] for schema, rows in steady.items()})
        rows = load(Path(groups(root / 'main-comparisons.json', growth, TARGETS)))
        extra = root / 'steady-comparisons.json'
        groups(extra, {schema: items[0] for schema, items in steady.items()}, [STEADY])
        guard.write(root / 'main-comparisons.json', rows + load(extra))
        guard.write(root / 'status.json', dict(status='main-canonical-audit', at=time.time()))
        proof = stage('main-audit', [bench, 'audit', c['tables'], str(root / 'main-audit'), 'v1', str(SEED), '16',
            str(STEADY), str(root / 'main-comparisons.json')])
        verified = [e for e in proof['events'] if e.get('event') == 'canonical-verified']
        if len(verified) != 6:
            raise ValueError('incomplete full-row verification')
        result = dict(status='complete-identical', source_commit=c['source_commit'], growth=growth,
            steady=steady, canonical=verified, quote=estimate,
            median_steady_nodes_per_second={schema: statistics.median(trained(r)[STEADY]['nodes_per_second']
                for r in items) for schema, items in steady.items()})
        guard.write(root / 'results.json', result)
        guard.write(root / 'status.json', dict(status='complete-identical', at=time.time()))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path)
    a = p.parse_args()
    try:
        run(a.root)
    except BaseException as error:
        failure = dict(error=repr(error), at=time.time())
        if hasattr(error, 'resource_sample'):
            failure['resource_sample'] = error.resource_sample
        guard.write(a.root / 'failure.json', failure)
        raise
