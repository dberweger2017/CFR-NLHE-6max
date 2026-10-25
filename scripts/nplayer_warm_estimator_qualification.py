"""PR425: fixed warmed-current-policy diagnostic, never a training launcher.

`build` and `prepare` do not load the mature checkpoint. `run` additionally
requires a source-bound independent estimator review and fresh admission.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import itertools
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from scripts.nplayer_bb200_feasibility import Supervisor, read, sha, write

SOURCE = Path(__file__).resolve().parents[1]
REPORT = SOURCE / 'docs/reports/nplayer-four-player-candidate/results.json'
PARENT = Path('/home/dberweger/nplayer-four-player-candidate-20261023/main-v1')
WARM_SHA = '2071d1e7fcbf3294942a978cc01ca8c817b4174f3bdedda072758d68c08bd2a1'
FIELDS = ('check-call', 'call-pressure', 'trained-call-pressure')
SCHEDULE = tuple(itertools.permutations(range(4)))
LEAN = tuple(tuple((start + direction * i) % 4 for i in range(4))
             for direction in (1, -1) for start in range(4))
ARTIFACTS = {'prefix-audit.jsonl', 'summary.json'} | {
    f'{mode}/{name}' for mode in ('reference', 'passive')
    for name in ('roots.jsonl', 'rows.jsonl', 'summary.json')}
SCOPE = dict(format='nplayer-warm-qualification-v1', batches=32, players=4,
             roots_per_seat=8, root_seed=2026102442501, threads=16,
             proposal_passive_fraction=0.25, shadow_new_slots=100000,
             saved_blocks_per_field=64, saved_hands=1536,
             allowance_seconds=3600, new_storage_gib=12,
             training_admitted=False, strength_evaluation_admitted=False)


def source_pins():
    names = subprocess.check_output(['git', 'ls-files', 'native', 'scripts'],
                                    cwd=SOURCE, text=True).splitlines()
    return {n: sha(SOURCE / n) for n in names if (SOURCE / n).is_file()}


def clean_source():
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=SOURCE,
                               text=True).strip():
        raise ValueError('commit the source before preparation')
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE,
                                   text=True).strip()


@contextmanager
def exclusive(root):
    """Never unlink/replace the shared mutex inode or wait for another owner."""
    with open('/tmp/cfr-cygnus-exclusive.lock', 'a+') as normal, \
            open(root / 'study.lock', 'a+') as own:
        fcntl.flock(normal, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(own, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def file_pin(path):
    stat = path.stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def extract_one(source, expected_sha, out, field, *, blocks=64):
    """Hash the WHOLE source; parse only the prospectively selected prefix."""
    before = file_pin(source)
    digest = hashlib.sha256()
    selected = []
    seen = set()
    with source.open('rb') as stream:
        raw = next(stream)
        digest.update(raw)
        header = json.loads(raw)
        if (header.get('format') != 'nplayer-privileged-policy-replay-v1'
                or header.get('schedule') != [list(x) for x in SCHEDULE]
                or header.get('policies', [{}])[0].get('source_checkpoint_sha256') != WARM_SHA
                or header.get('identity', {}).get('players') != 4):
            raise ValueError('historical trace schema/schedule/model differs')
        for index, raw in enumerate(stream):
            digest.update(raw)
            if index >= blocks * len(SCHEDULE):
                continue
            row = json.loads(raw)
            block, permutation = divmod(index, len(SCHEDULE))
            if (row.get('block') != block or row.get('permutation') != permutation
                    or row.get('identities') != list(SCHEDULE[permutation])
                    or row.get('button') != block % 4):
                raise ValueError('historical prefix order/seating/button differs')
            if SCHEDULE[permutation] in LEAN:
                key = (block, permutation)
                if key in seen:
                    raise ValueError('duplicate prefix hand')
                seen.add(key)
                selected.append(dict(field=field, record=row))
    if digest.hexdigest() != expected_sha or before != file_pin(source):
        raise ValueError('historical source hash/stat changed')
    if len(selected) != blocks * len(LEAN):
        raise ValueError('incomplete fixed prefix cohort')
    for row in selected:
        out.write(json.dumps(row, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n')
    return dict(field=field, path=str(source), sha256=expected_sha, hands=len(selected),
                header=header, stat=list(before))


def build(root):
    source = clean_source()
    root.mkdir(parents=True, exist_ok=False)
    env = {**os.environ, 'CARGO_TARGET_DIR': str(root / 'target'), 'CARGO_BUILD_JOBS': '8'}
    with exclusive(root):
        supervisor = Supervisor(root, env)
        cargo = ['cargo', 'test', '--locked', '--manifest-path',
                 str(SOURCE / 'native/hu20-trainer/Cargo.toml')]
        try:
            supervisor.stage('native-library-tests', cargo + ['--lib'])
            supervisor.stage('estimator-fixtures', cargo + ['--example', 'nplayer_warm_estimator'])
            supervisor.stage('release-build', ['cargo', 'build', '--locked', '--release',
                '--manifest-path', str(SOURCE / 'native/hu20-trainer/Cargo.toml'),
                '--example', 'nplayer_warm_estimator'])
            binary = root / 'target/release/examples/nplayer_warm_estimator'
            write(root / 'build-receipt.json', dict(status='passed', source=source,
                source_files=source_pins(), binary=str(binary), binary_sha256=sha(binary),
                native_library_tests_passed=True, estimator_fixtures_passed=True))
            write(root / 'status.json', dict(status='complete-build-only'))
        except BaseException as error:
            write(root / 'failure.json', dict(error=repr(error), no_retry=True))
            raise


def prepare(root, build_receipt, tables):
    source = clean_source()
    build_info = read(build_receipt)
    binary = Path(build_info['binary'])
    if (build_info.get('status') != 'passed' or build_info.get('source') != source
            or build_info.get('source_files') != source_pins()
            or build_info.get('binary_sha256') != sha(binary)
            or not build_info.get('native_library_tests_passed')
            or not build_info.get('estimator_fixtures_passed')):
        raise ValueError('source-bound native build/fixture receipt required')
    root.mkdir(parents=True, exist_ok=False)
    with exclusive(root):
        historical = read(REPORT)
        cohort = root / 'prefix-cohort.jsonl'
        try:
            with cohort.open('x') as out:
                out.write(json.dumps(dict(format='nplayer-warm-prefix-cohort-v1', hands=1536)) + '\n')
                traces = [extract_one(PARENT / f'arena-initial/{field}-b.jsonl',
                    historical['arena_costs']['initial'][field]['trace_sha256'][1], out, field)
                    for field in FIELDS]
            table_hashes = historical['config']['table_sha256s']
            if any(sha(tables / n) != value for n, value in table_hashes.items()):
                raise ValueError('K50 hashes differ')
            config = {**SCOPE, 'source': source, 'source_files': source_pins(),
                'binary': str(binary), 'binary_sha256': sha(binary),
                'python': sys.executable, 'python_sha256': sha(sys.executable),
                'build_receipt': str(build_receipt), 'build_receipt_sha256': sha(build_receipt),
                'checkpoint': str(PARENT / 'candidate-train.gz'), 'checkpoint_sha256': WARM_SHA,
                'tables': str(tables), 'table_sha256s': table_hashes,
                'cohort': str(cohort), 'cohort_sha256': sha(cohort),
                'historical_report_sha256': sha(REPORT), 'cohort_sources': traces}
            write(root / 'config.json', config)
            write(root / 'status.json', dict(status='prepared-not-started',
                config_sha256=sha(root / 'config.json'), review_required=True))
        except BaseException as error:
            write(root / 'failure.json', dict(error=repr(error), no_retry=True))
            raise


def validate(config, review):
    if any(config.get(k) != value for k, value in SCOPE.items()):
        raise ValueError('frozen diagnostic scope changed')
    if (config.get('source_files') != source_pins()
            or config.get('checkpoint_sha256') != WARM_SHA
            or config.get('historical_report_sha256') != sha(REPORT)):
        raise ValueError('source or historical inputs changed')
    if (review.get('status') != 'approved' or review.get('source') != config['source']
            or review.get('binary_sha256') != config['binary_sha256']
            or not review.get('independent_reviewer')
            or review.get('scope') != 'frozen-warm-estimator-and-information-boundary'
            or review.get('unresolved_correctness_questions') != []):
        raise ValueError('independent source-bound estimator review required')


def verify(root):
    manifests = [read(root / p / 'artifacts.json') for p in ('initial', 'repeat')]
    if (any(m.get('format') != 'nplayer-warm-artifact-receipts-v1' for m in manifests)
            or manifests[0] != manifests[1] or set(manifests[0]['files']) != ARTIFACTS):
        raise ValueError('reproduction artifact inventory/hash/length differs')
    for name, entry in manifests[0]['files'].items():
        p = root / 'initial' / name
        if p.stat().st_size != entry['bytes'] or sha(p) != entry['sha256']:
            raise ValueError('initial artifact changed')
        if (root / 'repeat' / name).exists():
            raise ValueError('repeat unexpectedly retained duplicate raw payload')
    for mode in ('reference', 'passive'):
        with (root / 'initial' / mode / 'roots.jsonl').open() as stream:
            header = json.loads(next(stream))
            if any(header.get(k) != value for k, value in dict(
                    format='nplayer-frozen-estimator-roots-v1', mode=mode,
                    root_seed=SCOPE['root_seed'], batches=32, roots_per_seat=8,
                    players=4, source_checkpoint_sha256=WARM_SHA).items()):
                raise ValueError('wrong root inventory identity')
            expected = itertools.product(range(32), range(4), range(8))
            count = 0
            for row, identity in itertools.zip_longest(map(json.loads, stream), expected):
                if row is None or identity is None or tuple(row[k] for k in ('batch', 'traverser', 'root')) != identity:
                    raise ValueError('missing/duplicate/reordered root context')
                count += 1
            if count != 1024:
                raise ValueError('root count differs')
    summary = read(root / 'initial/summary.json')
    if (summary['status'] != 'complete-diagnostic-only'
            or summary['input_checkpoint_sha256'] != WARM_SHA
            or not summary['no_training_or_strength_verdict']):
        raise ValueError('wrong diagnostic completion')
    proof = dict(status='passed', root_contexts_per_mode=1024, modes=2,
                 byte_compared_reproduction=True, no_duplicate_raw_repeat=True,
                 initial_manifest_sha256=sha(root / 'initial/artifacts.json'),
                 summary_sha256=sha(root / 'initial/summary.json'), no_strength_verdict=True)
    write(root / 'verified.json', proof)
    return proof


def settle(root):
    proof = verify(root)
    summary = read(root / 'initial/summary.json')
    prefixes = {}
    with (root / 'initial/prefix-audit.jsonl').open() as stream:
        next(stream)
        for row in map(json.loads, stream):
            item = prefixes.setdefault(row['key'], dict(street=row['street'], family=row['family'],
                                       observed_prefixes=0, positive_target_prefixes=0))
            if (item['street'], item['family']) != (row['street'], row['family']):
                raise ValueError('watch key street/family changed')
            item['observed_prefixes'] += 1
            item['positive_target_prefixes'] += int(row['target_counterfactual_prefix'] > 0)
    modes = {}
    for mode in ('reference', 'passive'):
        native = summary[mode]['summary']
        groups = native['by_street_family']
        targeted = {str(street): sum(g['replicated_positive_learning_proxy'] for g in groups
                     if g['street'] == street and g['family'] in ('P0', 'P1', 'P2'))
                     for street in (2, 3)}
        watched = []
        with (root / 'initial' / mode / 'rows.jsonl').open() as stream:
            for row in map(json.loads, stream):
                if row['key'] in prefixes:
                    watched.append(dict(key=row['key'], **prefixes[row['key']],
                        encountered=row['first_batch'] is not None,
                        admitted=row['admitted_batch'] is not None,
                        potential=row['potential'], retained=row['retained']))
        if {r['key'] for r in watched} != set(prefixes):
            raise ValueError('watch keys dropped from ledger')
        modes[mode] = dict(targeted_turn_river_replicated_rows=targeted,
            targeted_replicated_per_million_nodes={s: n * 1e6 / native['nodes'] for s,n in targeted.items()},
            targeted_replicated_per_1000_roots={s: n * 1000 / native['roots'] for s,n in targeted.items()},
            watched=watched, full_summary=summary[mode])
    evidence = all(modes['passive']['targeted_turn_river_replicated_rows'][str(s)] > 0 for s in (2,3))
    result = dict(status='settled-diagnostic-only', proof=proof, modes=modes,
        interpretation='replicated learning in both targeted streets; next experiment needs a separate quote' if evidence
        else 'replicated-learning requirement not demonstrated in both targeted streets; distinguish observed zero prefixes from inadequate stochastic coverage',
        zero_reach_limit='Exact zeros describe retained observed prefixes only; they do not prove an abstract information key unreachable for every compatible hidden state.',
        no_strength_verdict=True, no_automatic_training=True, no_scientific_retry=True)
    write(root / 'readout.json', result)
    return result


def run(root, review_path, accepted_seconds):
    if accepted_seconds != SCOPE['allowance_seconds']:
        raise ValueError('accept the fixed 3600-second planning allocation; no elapsed-time kill')
    config = read(root / 'config.json')
    review = read(review_path)
    validate(config, review)
    prepared = read(root / 'status.json')
    if (root / 'failure.json').exists() or prepared.get('status') != 'prepared-not-started':
        raise ValueError('not an untouched prepared run; no retry')
    if prepared.get('config_sha256') != sha(root / 'config.json'):
        raise ValueError('prepared config changed')
    with exclusive(root):
        # Admission only: there is no disk/RSS/swap/time cutoff during traversal.
        free = shutil.disk_usage(root).free
        if free < SCOPE['new_storage_gib'] * 2**30:
            raise ValueError('fresh 12GiB new-space admission not met')
        for path, digest in [(config['binary'], config['binary_sha256']),
                (config['cohort'], config['cohort_sha256']),
                (config['checkpoint'], WARM_SHA),
                (config['python'], config['python_sha256']),
                (config['build_receipt'], config['build_receipt_sha256'])] + [
                (str(Path(config['tables']) / name), digest)
                for name, digest in config['table_sha256s'].items()]:
            if sha(path) != digest:
                raise ValueError('frozen input/build changed')
        launch = dict(pid=os.getpid(), epoch=time.time(), source=config['source'],
                      config_sha256=sha(root / 'config.json'), review_sha256=sha(review_path),
                      nvme_free_bytes=free, meminfo=Path('/proc/meminfo').read_text(),
                      planning_allowance_seconds=accepted_seconds)
        with (root / 'launch.json').open('x') as out:
            json.dump(launch, out, indent=2)
        supervisor = Supervisor(root, dict(os.environ))
        try:
            for phase in ('initial', 'repeat'):
                command = [config['binary'], 'run', config['checkpoint'], WARM_SHA,
                    config['tables'], config['cohort'], config['cohort_sha256'],
                    str(root / phase), str(config['threads'])]
                if phase == 'repeat':
                    command.append(str(root / 'initial'))
                supervisor.stage(phase, command)
            validate(config, read(review_path))
            if (sha(root / 'config.json') != launch['config_sha256']
                    or sha(review_path) != launch['review_sha256']
                    or sha(config['binary']) != config['binary_sha256']
                    or any(sha(Path(config['tables']) / n) != h
                           for n, h in config['table_sha256s'].items())):
                raise ValueError('frozen config/review/binary/K50 changed during run')
            supervisor.stage('verification-and-readout', [config['python'], '-m',
                'scripts.nplayer_warm_estimator_qualification', 'settle', str(root)])
            proof = read(root / 'verified.json')
            write(root / 'status.json', dict(status='complete-diagnostic-only',
                  verified_sha256=sha(root / 'verified.json'), no_followup_started=True))
            return proof
        except BaseException as error:
            write(root / 'failure.json', dict(error=repr(error), no_retry=True,
                  resource_sample=getattr(error, 'resource_sample', None)))
            write(root / 'status.json', dict(status='terminal-failure'))
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build'); b.add_argument('root', type=Path)
    p = sub.add_parser('prepare'); p.add_argument('root', type=Path)
    p.add_argument('--build-receipt', type=Path, required=True)
    p.add_argument('--tables', type=Path, required=True)
    r = sub.add_parser('run'); r.add_argument('root', type=Path)
    r.add_argument('--review', type=Path, required=True)
    r.add_argument('--accept-seconds', type=int, required=True)
    v = sub.add_parser('verify'); v.add_argument('root', type=Path)
    s = sub.add_parser('settle'); s.add_argument('root', type=Path)
    args = parser.parse_args()
    root = args.root.absolute()
    if args.command == 'build': build(root)
    elif args.command == 'prepare': prepare(root, args.build_receipt.absolute(), args.tables.absolute())
    elif args.command == 'run': print(json.dumps(run(root, args.review, args.accept_seconds)))
    elif args.command == 'verify': print(json.dumps(verify(root)))
    else: print(json.dumps({'status': settle(root)['status']}))


if __name__ == '__main__':
    main()
