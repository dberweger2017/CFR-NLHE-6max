"""One-shot, guarded M4 qualification. A failed stage is terminal; no automatic retries."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time

from scripts.deep_cfr_variance_probe import sha
from scripts.nplayer_four_player_feasibility import sample, TABLES
from scripts.support.research_process_guard import run

GIB = 2 ** 30
SOURCE = Path(__file__).resolve().parents[1]


def put(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def resume_queue(path):
    """Resume only the launchers whose PID, command and start time still match our receipt."""
    if path is None:
        return
    receipt = json.loads(Path(path).read_text())
    for row in reversed(receipt['processes']):
        pid = str(row['pid'])
        command = subprocess.check_output(['ps', '-o', 'command=', '-p', pid], text=True).strip()
        started = subprocess.check_output(['ps', '-o', 'lstart=', '-p', pid], text=True).strip()
        if command != row['command'] or started != row['started']:
            raise RuntimeError('queue identity changed; refusing to signal reused PID')
        os.kill(row['pid'], signal.SIGCONT)
    put(Path(path).with_name('queue-resumed.json'), {'epoch': time.time(), 'processes': receipt['processes']})


def execute(args):
    if platform.system() != 'Darwin' or 'Apple M4' not in subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string'], text=True):
        raise ValueError('M4 only')
    root = Path(args.out)
    root.mkdir(exist_ok=False, parents=True)
    locks = []
    # Hold the existing host locks as well as the explicit owner assignment.
    for name in ('.hu20-m4-research.lock', '.hu100-m4-research.lock'):
        lock = (Path.home() / 'Local' / name).open('a+')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        locks.append(lock)
    if 'AC Power' not in subprocess.check_output(['pmset', '-g', 'batt'], text=True):
        raise ValueError('AC power required')
    commands = subprocess.check_output(['ps', '-axo', 'pid=,command='], text=True)
    for line in commands.splitlines():
        if any(needle in line for needle in ('-m scripts.neural_capacity_sweep run', 'nplayer_deep_cfr traverse', 'nplayer_train --')):
            raise ValueError('other research is still running: ' + line)
    paths = [Path(args.binary), Path(args.network), Path(args.thermal)]
    if sha(args.network) != 'd57c79d81cf5656ce5a7c45912e2047817cb1dd715b8c50666accd90df87d9db':
        raise ValueError('not the frozen run-1 advantage network')
    sources = [p for folder in ('native/hu20-trainer/src', 'native/hu20-buckets/src')
               for p in (SOURCE / folder).rglob('*.rs')]
    sources += [SOURCE / p for p in ('native/hu20-trainer/examples/nplayer_variance_probe.rs',
                'scripts/deep_cfr_variance_probe.py', 'scripts/run_deep_cfr_variance_m4.py',
                'docs/deep-cfr-variance-qualification.md')]
    pins = {str(p): sha(p) for p in paths + sources}
    for name, pin in TABLES.items():
        if sha(Path(args.tables) / name) != pin:
            raise ValueError('K50 pin changed: ' + name)
    config = {'pins': pins, 'tables': TABLES, 'network_sha256': sha(args.network),
              'argv': vars(args), 'allocation_seconds': 2700, 'started_epoch': time.time()}
    put(root / 'config.json', config)
    config_pin = sha(root / 'config.json')
    start = time.monotonic()
    active_pid = [None]
    active_name = ['']
    initial_free = __import__('shutil').disk_usage(root).free

    def probe():
        x = sample(root, args.thermal, active_pid[0])
        x['kind'] = 'm4'
        # Reserve 2 GiB for Metal driver allocations during fitting, in addition to RSS.
        # The learner also caps its MPS allocation to 10% of recommended device memory.
        x['metal_reserve_bytes'] = 2 * GIB if active_name[0] == 'fit' else 0
        if x['worker_family_rss_bytes'] + x['metal_reserve_bytes'] > 6 * GIB:
            raise ValueError('6 GiB family/Metal cap')
        if x['available_ram_bytes'] < 2 * GIB or x['disk_free_bytes'] < 2 * GIB:
            raise ValueError('RAM/disk headroom')
        if initial_free - x['disk_free_bytes'] > 5 * GIB:
            raise ValueError('new disk cap')
        if time.monotonic() - start >= 2700:
            raise ValueError('45-minute research allocation exhausted')
        return x

    def stage(name, command):
        active_name[0] = name
        for path, pin in pins.items():
            if sha(path) != pin:
                raise ValueError('pinned input changed: ' + path)
        put(root / 'status.json', {'phase': name, 'status': 'running'})
        receipt = run(command, root / 'stages' / name, probe, stop=root / 'STOP', interval=0.5,
                      unchanged=lambda: sha(root / 'config.json') == config_pin,
                      on_start=lambda pid: active_pid.__setitem__(0, pid))
        active_pid[0] = None
        row = {'name': name, 'seconds': receipt['wall_seconds'], 'returncode': receipt['returncode'],
               'cpu_seconds': receipt['user_cpu_seconds'] + receipt['system_cpu_seconds']}
        with (root / 'stages.jsonl').open('a') as f:
            f.write(json.dumps(row) + '\n')
        return receipt

    common = [args.binary, '--network', args.network, '--sha', config['network_sha256'], '--tables', args.tables]
    try:
        admission = probe()
        # Maximum dataset is 4096 rollouts × 256 decisions × 675 bytes, below 1 GiB.
        if admission['available_ram_bytes'] < 5 * GIB or admission['disk_free_bytes'] < 3 * GIB:
            raise ValueError('forecast: need 3 GiB worker + 2 GiB RAM, 1 GiB output + 2 GiB disk')
        put(root / 'admission.json', admission)
        stage('calibrate', common + ['--mode', 'evaluate', '--samples', '2', '--out', str(root / 'calibration')])
        calibration = json.loads((root / 'calibration' / 'summary.json').read_text())
        # Main has 32 times the calibration work. Allow 4× for critic inference and 5 min
        # for collection/fitting/qualification. Refuse rather than alter the fixed counts.
        quote = calibration['work_seconds'] * 32 * 4 + 300
        remaining = 2700 - (time.monotonic() - start)
        put(root / 'quote.json', {'forecast_seconds': quote, 'remaining_seconds': remaining,
                                 'fixed_counts_admitted': quote < remaining})
        if quote >= remaining:
            raise ValueError('fixed main allocation not admitted')
        stage('collect', common + ['--mode', 'collect', '--samples', '4096', '--out', str(root / 'data')])
        stage('fit', [sys.executable, '-m', 'scripts.deep_cfr_variance_probe', 'fit', '--data', str(root / 'data'),
                      '--out', str(root / 'fit'), '--device', 'mps'])
        critic = root / 'fit' / 'critic.json'
        pins[str(critic)] = sha(critic)
        stage('qualify', common + ['--mode', 'qualify', '--samples', '2', '--critic', str(critic),
                                  '--parity', str(root / 'fit' / 'parity.json'), '--out', str(root / 'qualification')])
        stage('evaluate', common + ['--mode', 'evaluate', '--samples', '64', '--critic', str(critic),
                                   '--out', str(root / 'evaluation')])
        put(root / 'COMPLETE.json', {'seconds': time.monotonic() - start,
                                    'evaluation_sha256': sha(root / 'evaluation' / 'estimates.jsonl')})
        put(root / 'status.json', {'status': 'complete'})
    except BaseException as exc:
        put(root / 'failure.json', {'error': repr(exc), 'seconds': time.monotonic() - start, 'terminal': True})
        raise
    finally:
        for lock in locks:
            lock.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('binary', 'network', 'tables', 'thermal', 'out'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--resume-queue', help='identity-checked queue-hold receipt from the operator')
    args = p.parse_args()
    try:
        execute(args)
    finally:
        resume_queue(args.resume_queue)


if __name__ == '__main__':
    main()
