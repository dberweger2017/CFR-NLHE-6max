"""Bounded RunPod controller for docs/neural-six-imitation.md.

Run once in a fresh output directory. No scientific retries or recipe overrides.
T3 scheduled work owns retrieval and provider termination; this process owns
only its subprocess groups and the work deadline.
"""
import argparse
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts import neural_policy_imitation as imitation
from scripts import neural_six_imitation as study
from scripts.runpod_multistreet import _terminate

GIB = 1024 ** 3


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.partial')
    tmp.write_text(json.dumps(value, indent=1, allow_nan=False) + '\n')
    tmp.replace(path)


def resources(root):
    mem = {line.split(':')[0]: int(line.split()[1]) * 1024
           for line in Path('/proc/meminfo').read_text().splitlines()}
    available = mem['MemAvailable']
    limit = Path('/sys/fs/cgroup/memory.max')
    if limit.exists() and limit.read_text().strip() != 'max':
        available = min(available, int(limit.read_text()) - int(limit.with_name('memory.current').read_text()))
    legacy = Path('/sys/fs/cgroup/memory/memory.limit_in_bytes')
    if legacy.exists():
        available = min(available, int(legacy.read_text()) -
                        int(legacy.with_name('memory.usage_in_bytes').read_text()))
    gpu = subprocess.check_output(['nvidia-smi', '--query-gpu=temperature.gpu,memory.used',
                                   '--format=csv,noheader,nounits'], text=True, timeout=10)
    temperatures, gpu_mb = [], []
    for row in gpu.strip().splitlines():
        t, m = map(float, row.split(','))
        temperatures.append(t)
        gpu_mb.append(m)
    if not temperatures:
        raise ValueError('GPU sensor missing')
    return {'at': time.time(), 'available_bytes': available,
            'free_disk_bytes': shutil.disk_usage(root).free,
            'gpu_c': max(temperatures), 'gpu_memory_mb': sum(gpu_mb)}


def stop_reason(snapshot, deadline, now, stop=False):
    if stop:
        return 'STOP file'
    if now >= deadline:
        return 'work deadline'
    if snapshot['available_bytes'] < 4 * GIB:
        return 'memory reserve'
    if snapshot['free_disk_bytes'] < 10 * GIB:
        return 'disk reserve'
    if snapshot['gpu_c'] >= 87:
        return 'GPU temperature'
    return None


class Runner:
    def __init__(self, args):
        self.a = args
        self.root = args.out.resolve()
        self.root.mkdir(parents=True, exist_ok=False)
        (self.root / 'logs').mkdir()
        self.python = sys.executable
        self.started = time.time()
        self.current = None
        self.index = 0

    def status(self, state, **extra):
        save(self.root / 'status.json', {'state': state, 'stage': self.current,
             'at': datetime.now(timezone.utc).isoformat(), 'started_epoch': self.started,
             'work_deadline_epoch': self.a.deadline, **extra})

    def run(self, label, command):
        self.current = label
        self.status('running')
        reason = stop_reason(resources(self.root), self.a.deadline, time.time(), (self.root / 'STOP').exists())
        if reason:
            raise RuntimeError(reason)
        self.index += 1
        start = time.time()
        record = {'stage': label, 'argv': list(map(str, command)), 'started': start}
        with (self.root / 'stages.jsonl').open('a') as f:
            f.write(json.dumps(record) + '\n')
        log = self.root / 'logs' / f'{self.index:03}-{label}.log'
        with log.open('xb') as output:
            child = subprocess.Popen(list(map(str, command)), stdout=output, stderr=subprocess.STDOUT,
                                     start_new_session=True)
            try:
                while child.poll() is None:
                    snap = resources(self.root)
                    with (self.root / 'resources.jsonl').open('a') as f:
                        f.write(json.dumps(snap | {'stage': label}) + '\n')
                    reason = stop_reason(snap, self.a.deadline, time.time(), (self.root / 'STOP').exists())
                    if reason:
                        raise RuntimeError(reason)
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        pass
                if child.returncode:
                    raise RuntimeError(f'{label}: exit {child.returncode}; see {log.name}')
            finally:
                # Also kills leaked descendants in this owned group after a successful parent exit.
                _terminate(child, grace_seconds=10)
        save(self.root / 'logs' / f'{self.index:03}-{label}.json', record | {'seconds': time.time() - start, 'exit': 0})

    def module(self, label, module, *args):
        self.run(label, [self.python, '-m', module, *map(str, args)])

    def evaluate(self, folder, seed, smoke=False):
        folder.mkdir(parents=True)
        out = folder / 'out'
        write = study.write_json
        write(folder / 'models.json', study.catalog(self.a.inputs))
        common = ['--out', out, '--seed-run', str(seed), '--tables', self.a.tables,
                  '--threads', str(self.a.threads)] + (['--smoke'] if smoke else [])
        self.module(f'eval{seed}-manifest' + ('-smoke' if smoke else ''), 'scripts.neural_six_imitation',
                    'manifest', *common, '--models', folder / 'models.json', '--networks', self.root / 'networks.json')
        for bank in range(1 if smoke or seed > 1 else 4):
            self.run(f'eval{seed}-arena-b{bank}' + ('-smoke' if smoke else ''),
                     [self.a.binary / 'nplayer_paired_arena', 'batch', out / f'arena-manifest-b{bank}.json'])
            self.module(f'eval{seed}-scan-b{bank}', 'scripts.neural_six_imitation',
                        'scan', *common, '--workers', self.a.workers)
            if bank == 0:
                self.module(f'eval{seed}-replay', 'scripts.neural_six_imitation',
                            'replay', *common, '--workers', self.a.workers)
            # Scan receipts retain the full hand ledger needed by the report. Preserve raw traces
            # compressed, just as step 4 does; a partial gzip is a plumbing failure.
            for path in sorted((out / 'arena' / f'b{bank}').glob('*/*.jsonl')):
                self.run(f'eval{seed}-gzip-{bank}-{path.stem}', ['gzip', '-1', path])
        self.module(f'eval{seed}-equity', 'scripts.neural_six_imitation', 'equity', *common,
                    '--binary', self.a.binary / 'nplayer_allin_equity')
        self.module(f'eval{seed}-report', 'scripts.neural_six_imitation', 'report', *common,
                    '--results', folder / 'results')

    def execute(self):
        a, w = self.a, self.root
        save(w / 'host.json', {'platform': platform.platform(), 'python': sys.version,
             'threads': a.threads, 'workers': a.workers, 'cpu_count': os.cpu_count(),
             'source': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
             'cpu_temperature': 'not exposed/qualified by this container controller'})
        # Qualification on the actual host, before any main scientific work.
        self.run('native-tests', ['cargo', 'test', '--release', '--locked', '--manifest-path',
                                 'native/hu20-trainer/Cargo.toml', '--lib'])
        self.run('host-tests', ['cargo', 'test', '--release', '--locked', '--manifest-path',
                               'native/hu20-trainer/Cargo.toml', '--example', 'nplayer_paired_arena'])
        self.module('python-tests', 'pytest', '-q', 'tests/test_neural_six_imitation.py',
                    'tests/test_neural_policy_imitation.py', 'tests/test_neural_policy_everywhere.py',
                    'tests/test_neural_policy_samples.py')
        self.module('gpu', 'scripts.check_gpu', '--require', 'cuda', '--quick')
        study.catalog(a.inputs)
        q = w / 'qualification'
        self.module('qualification-manifest', 'scripts.neural_six_imitation', 'export-manifest',
                    '--out', q, '--inputs', a.inputs, '--tables', a.tables, '--threads', a.threads,
                    '--qualification', '--manifest', q / 'manifest.json')
        self.run('qualification-export', [a.binary / 'nplayer_features', q / 'manifest.json'])
        summaries = [json.loads(p.read_text()) for p in sorted(q.glob('*.summary.json'))]
        if len(summaries) != 2 or summaries[0]['records_sha256'] != summaries[1]['records_sha256']:
            raise ValueError('export thread determinism failed')
        # Conservative admission from the mixed qualification workload: 2x measured sample density,
        # plus an equally sized array cache, 20 GiB for traces/builds and the 10 GiB reserve.
        measured = sum(p.stat().st_size for p in q.glob('*.npfeat')) / 4000
        projected = 4 * measured * 2520000 + 30 * GIB
        free = shutil.disk_usage(w).free
        save(q / 'admission.json', {'bytes_per_hand': measured, 'required_free_bytes': projected, 'free_bytes': free})
        if free < projected:
            raise RuntimeError('fixed export cannot fit disk admission; do not reduce the recipe')
        data = w / 'data'
        self.module('data-manifest', 'scripts.neural_six_imitation', 'export-manifest',
                    '--out', data, '--inputs', a.inputs, '--tables', a.tables, '--threads', a.threads,
                    '--manifest', data / 'manifest.json')
        self.run('data-export', [a.binary / 'nplayer_features', data / 'manifest.json'])
        train = sorted((data / 'train').glob('*.npfeat'))
        heldout = sorted((data / 'heldout').glob('*.npfeat'))
        if len(train) != 6 or len(heldout) != 6:
            raise ValueError('export fields missing')
        networks = {}
        for seed in (1, 2, 3):
            model, cache = w / 'models' / f'seed{seed}', w / 'array-cache'
            self.module(f'train{seed}', 'scripts.neural_policy_imitation', 'train', '--data', *train,
                        '--seed', seed, '--out', model, '--array-cache', cache)
            # This is a reproducible working cache, not original evidence.
            shutil.rmtree(cache)
            meta = json.loads((model / 'model.json').read_text())
            if not all(__import__('math').isfinite(h['loss']) for h in meta['history']):
                raise ValueError('nonfinite training loss')
            for split, paths, limit in [('heldout', heldout, 0), ('train-prefix', train, 2000)]:
                self.module(f'fidelity{seed}-{split}', 'scripts.neural_six_imitation', 'diagnostics',
                            '--model', model, '--data', *paths, '--limit', limit,
                            '--out', w / 'fidelity' / f'seed{seed}-{split}.json')
            net = w / 'networks' / f'net{seed}.npnet'
            net.parent.mkdir(exist_ok=True)
            self.module(f'export{seed}', 'scripts.neural_policy_imitation', 'export', '--model', model, '--out', net)
            fixture = q / f'parity{seed}.dat'
            self.module(f'parity-fixture{seed}', 'scripts.neural_policy_imitation', 'parity',
                        '--model', model, '--data', heldout[0], '--count', 10000, '--out', fixture)
            pin = imitation.sha_file(net)
            self.run(f'parity{seed}', [a.binary / 'nplayer_network_parity', net, pin, fixture, '1e-5'])
            networks[f'net{seed}'] = {'path': str(net), 'sha256': pin}
        study.write_json(w / 'networks.json', networks)
        self.evaluate(w / 'smoke', 1, True)
        for seed in (1, 2, 3):
            self.evaluate(w / 'main' / f'run{seed}', seed)
        self.module('decision', 'scripts.neural_six_imitation', 'decide', '--results',
                    *(w / 'main' / f'run{s}' / 'results' / 'results.json' for s in (1, 2, 3)),
                    '--out', w / 'decision.json')
        self.status('completed')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--tables', type=Path, required=True)
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--threads', type=int, required=True)
    p.add_argument('--workers', type=int, required=True)
    p.add_argument('--deadline', type=float, required=True, help='absolute UTC epoch, rental + 10.5 hours')
    a = p.parse_args()
    if min(a.threads, a.workers) < 1 or a.deadline <= time.time():
        p.error('positive workers/threads and a future deadline required')
    runner = Runner(a)
    def interrupted(signum, _frame):
        raise RuntimeError(f'controller signal {signum}')
    for signum in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, interrupted)
    try:
        runner.execute()
    except BaseException as error:
        runner.status('failed', error=str(error))
        raise


if __name__ == '__main__':
    main()
