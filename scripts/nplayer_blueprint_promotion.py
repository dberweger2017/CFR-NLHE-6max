"""Fixed PR341 proposal: fresh promotion matches for the existing PR340 averages."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import signal
import time

from scripts import run_nplayer_storage_benchmark as guard
from scripts.analyze_nplayer_arena import interval, sha
from scripts.read_nplayer_fast_study import paired_blocks

SEEDS = (2026101541, 2026101542, 2026101543)
SOURCE = Path(__file__).resolve().parents[1]
INPUTS = SOURCE / 'docs/nplayer-blueprint-promotion-inputs.json'
WORKERS = 6
FINAL_HANDS = 589824
BUDGET = 5_000_000_000
MAX_SECONDS = 90 * 60


def load(path):
    return json.loads(Path(path).read_text())


def cases(smoke=False):
    rows = []
    for group in ('same', 'cross'):
        for i, seed in enumerate(SEEDS):
            opponent = seed if group == 'same' else SEEDS[(i + 1) % 3]
            fast, production = f'fast-{seed}-clock', f'production-{opponent}-1b'
            index = i + (0 if group == 'same' else 3)
            for reverse in (False, True):
                rows.append(dict(name=f'{group}-{seed}-' + ('reverse' if reverse else 'forward'),
                    group=group, seed=seed, opponent_seed=opponent,
                    root=(20261018345001 if smoke else 20261018345101) + index,
                    blocks=2 if smoke else 8192,
                    singleton=production if reverse else fast, pair=fast if reverse else production))
    return rows


def manifest(smoke=False):
    pins = load(INPUTS)
    return dict(format='nplayer-blueprint-promotion-v1', smoke=smoke,
        cases=cases(smoke), workers=WORKERS,
        **{key: pins[key] for key in ('models', 'arena', 'arena_sha256', 'tables')})


def validate_manifest(value, smoke=False):
    if value != manifest(smoke):
        raise ValueError('changed frozen promotion matrix or input pins')


def check_header(path, case, models):
    with path.open() as f:
        header = json.loads(next(f))
    expected = [models[name]['sha256'] for name in (case['singleton'], case['pair'], case['pair'])]
    if (header['seed'] != case['root'] or header['blocks'] != case['blocks']
            or header['hands'] != 6 * case['blocks']
            or [p['sha256'] for p in header['policies']] != expected
            or any(p['strategy'] != 'average' or p['average_scope'] != 3 for p in header['policies'])):
        raise ValueError('trace model/root/size identity mismatch')


def batch(root, smoke=False):
    # case_run preserves the qualified native play/replay path; this campaign owns its matrix.
    from scripts.run_nplayer_fast_evaluation import case_run
    from scripts.check_nplayer_parity import engine_identity
    engine_identity()
    m = load(root / 'evaluation-manifest.json')
    validate_manifest(m, smoke)
    for path, digest in [(m['arena'], m['arena_sha256'])] + [
            (p['path'], p['sha256']) for p in m['models'].values()]:
        if sha(Path(path)) != digest:
            raise ValueError('binary/model input hash mismatch: ' + path)
    (root / 'evaluation').mkdir(exist_ok=False)
    pool = ProcessPoolExecutor(max_workers=WORKERS)
    try:
        futures = [pool.submit(case_run, (case, m, str(root))) for case in m['cases']]
        results = []
        for future in as_completed(futures):
            result = future.result()
            check_header(root / 'evaluation' / result['case']['name'] / 'play-0.jsonl', result['case'], m['models'])
            results.append(result)
            progress = dict(event='progress', completed=len(results), total=len(m['cases']))
            guard.write(root / 'evaluation-progress.json', progress)
            print(json.dumps(progress), flush=True)
        pool.shutdown()
        hands = sum(6 * c['blocks'] for c in m['cases'])
        if len(results) != 12 or sum(r['hands'] for r in results) != hands:
            raise ValueError('incomplete promotion matrix')
        verified = dict(status='passed', cases=12, final_hands=hands,
            reproduction_hands=hands, manifest_sha256=sha(root / 'evaluation-manifest.json'))
        guard.write(root / 'evaluation-verified.json', verified)
        print(json.dumps(dict(event='complete', **verified)), flush=True)
    except BaseException as error:
        guard.write(root / 'evaluation-failure.json', dict(error=repr(error), at=time.time()))
        # Supervisor puts this batch and its workers in a fresh process group.
        os.killpg(os.getpgrp(), signal.SIGTERM)
        raise


def global_gate(root):
    if any(root.glob('*failure.json')):
        raise ValueError('campaign failed; no outcome readout')
    if load(root / 'status.json')['status'] not in ('verified-readout-ready', 'complete'):
        raise ValueError('global verification barrier not passed')
    m = load(root / 'evaluation-manifest.json')
    validate_manifest(m)
    v = load(root / 'evaluation-verified.json')
    if v != dict(status='passed', cases=12, final_hands=FINAL_HANDS,
            reproduction_hands=FINAL_HANDS, manifest_sha256=sha(root / 'evaluation-manifest.json')):
        raise ValueError('global verification identity mismatch')
    for case in m['cases']:
        folder = root / 'evaluation' / case['name']
        r, replay = load(folder / 'result.json'), load(folder / 'replay.json')
        if (r['case'] != case or r['status'] != 'passed' or r['hands'] != 49152
                or replay['status'] != 'passed' or replay['hands'] != 49152
                or len(r['operations']) != 2 or any(o['returncode'] for o in r['operations'])):
            raise ValueError('unverified promotion case')
        digests = {r['trace_sha256'], replay['trace_sha256']}
        for repeat in (0, 1):
            path = folder / f'play-{repeat}.jsonl'
            digests.add(sha(path))
            check_header(path, case, m['models'])
        if len(digests) != 1:
            raise ValueError('trace verification mismatch')
    return m


def decision(rows):
    if len(rows) != 6 or {(r['group'], r['seed']) for r in rows} != {
            (group, seed) for group in ('same', 'cross') for seed in SEEDS}:
        raise ValueError('incomplete decision family')
    primary = all(r['advantage']['lower95_bb100'] > 0 for r in rows if r['group'] == 'same')
    secondary = all(r['advantage']['lower95_bb100'] > -5 for r in rows if r['group'] == 'cross')
    return dict(consistent_improvement_passed=primary,
        cross_seed_noninferiority_passed=secondary, promotion_gate_passed=primary and secondary)


def read(root):
    m = global_gate(root)
    rows = []
    matrix = cases()
    for left, right in zip(matrix[::2], matrix[1::2]):
        values = list(paired_blocks(root / 'evaluation' / left['name'] / 'play-0.jsonl',
            root / 'evaluation' / right['name'] / 'play-0.jsonl', left['root']))
        if len(values) != 8192:
            raise ValueError('wrong independent block count')
        detail = {key: [interval([b[key][i] for b in values]) for i in range(3)]
            for key in ('fast_by_seat', 'production_by_seat', 'fast_by_position', 'production_by_position')}
        rows.append(dict(group=left['group'], seed=left['seed'], opponent_seed=left['opponent_seed'],
            root=left['root'], blocks=len(values),
            **{key: interval([b[key] for b in values]) for key in
                ('advantage', 'fast_singleton', 'production_singleton')}, **detail))
    return dict(status='settled', rows=rows, **decision(rows), final_hands=FINAL_HANDS,
        reproduction_hands=FINAL_HANDS, models=m['models'],
        manifest_sha256=sha(root / 'evaluation-manifest.json'))


def run(root):
    launch = load(root / 'launch.json')
    deadline = launch['epoch'] + MAX_SECONDS
    remaining = deadline - time.time()
    if remaining < 30 * 60:
        raise RuntimeError('insufficient original campaign time remaining')
    guard.BUDGET = BUDGET
    with Path('/tmp/cfr-blueprint-promotion.lock').open('a') as own, \
            Path('/tmp/cfr-cygnus-exclusive.lock').open('a') as legacy:
        for lock in (own, legacy):
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        supervisor = guard.Supervisor(root, own.fileno(), cpus=range(16), max_seconds=remaining,
            rss_limit=80 * guard.GIB, cpu_limit=90, thermistor_limit=95)
        row = supervisor.sample(None, 'admission', 0)
        if row['temperatures_c']['Package id 0'] >= 70 or row['temperatures_c']['Thermistor 15'] >= 80:
            raise RuntimeError('temperature admission refused')
        for relative, digest in launch['source_files'].items():
            if sha(SOURCE / relative) != digest:
                raise ValueError('source bundle mismatch: ' + relative)
        guard.write(root / 'admission.json', dict(pid=os.getpid(), initial_sample=row,
            cpus=list(range(16)), workers=WORKERS, deadline_epoch=deadline,
            source_commit=launch['source_commit'], source_files=launch['source_files']))
        pins = load(INPUTS)
        env = dict(os.environ, RAYON_NUM_THREADS='16', OMP_NUM_THREADS='1',
            OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
        python = pins['python']
        smoke = root / 'smoke'
        smoke.mkdir()
        guard.write(smoke / 'evaluation-manifest.json', manifest(True))
        guard.write(root / 'status.json', dict(status='qualification', at=time.time()))
        measured = supervisor.execute('qualification', [python, '-m',
            'scripts.nplayer_blueprint_promotion', 'batch', str(smoke), '--smoke'], SOURCE, env)
        verified = load(smoke / 'evaluation-verified.json')
        if verified['status'] != 'passed' or verified['final_hands'] != 144:
            raise ValueError('qualification did not verify')
        # The previous same-sized matrix took 331s. Allow 4x plus measured smoke cost.
        quote = 4 * 331.353 + measured['wall_seconds'] + 120
        if quote > deadline - time.time():
            raise RuntimeError('qualified workload does not fit original deadline')
        guard.write(root / 'evaluation-manifest.json', manifest())
        guard.write(root / 'pre-evaluation-freeze.json', dict(source_commit=launch['source_commit'],
            launch_sha256=sha(root / 'launch.json'), manifest_sha256=sha(root / 'evaluation-manifest.json'),
            qualification=verified, measured_smoke_wall_seconds=measured['wall_seconds'],
            projected_remaining_seconds=quote, deadline_epoch=deadline, at=time.time()))
        guard.write(root / 'status.json', dict(status='final-evaluation', at=time.time()))
        supervisor.execute('final-evaluation', [python, '-m', 'scripts.nplayer_blueprint_promotion',
            'batch', str(root)], SOURCE, env)
        guard.write(root / 'status.json', dict(status='verified-readout-ready', at=time.time()))
        supervisor.execute('verified-readout', [python, '-m', 'scripts.nplayer_blueprint_promotion',
            'read', str(root)], SOURCE, env)
        if load(root / 'results.json')['status'] != 'settled':
            raise ValueError('readout incomplete')
        guard.write(root / 'status.json', dict(status='complete', at=time.time(), utc=datetime.now(timezone.utc).isoformat()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['run', 'batch', 'read'])
    parser.add_argument('root', type=Path)
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    try:
        if args.action == 'run':
            run(args.root)
        elif args.action == 'batch':
            batch(args.root, args.smoke)
        else:
            result = read(args.root)
            with (args.root / 'results.json').open('x') as f:
                json.dump(result, f, indent=2)
                f.write('\n')
            print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'models')}), flush=True)
    except BaseException as error:
        if args.action == 'run':
            failure = dict(error=repr(error), at=time.time())
            if hasattr(error, 'resource_sample'):
                failure['resource_sample'] = error.resource_sample
            guard.write(args.root / 'failure.json', failure)
        raise


if __name__ == '__main__':
    main()
