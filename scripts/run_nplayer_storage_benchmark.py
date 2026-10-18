"""Run the fixed PR331/PR333 engineering comparison under bb128 supervision."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import selectors
import signal
import subprocess
import time

GIB = 1024**3
BUDGET = 20_000_000_000
FLOOR = 50_000_000_000
TARGETS = [1_100_000_000, 1_200_000_000, 1_300_000_000]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024**2), b''):
            h.update(b)
    return h.hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def memory():
    return {s.split(':')[0]: int(s.split()[1]) * 1024
            for s in Path('/proc/meminfo').read_text().splitlines()}


def sensors():
    result = {}
    for p in Path('/sys/class/hwmon').glob('hwmon*/temp*_label'):
        name = p.read_text().strip()
        if name in ('Package id 0', 'Thermistor 15'):
            result[name] = int(p.with_name(p.name.replace('_label', '_input')).read_text()) / 1000
    if set(result) != {'Package id 0', 'Thermistor 15'}:
        raise RuntimeError('required temperature sensors missing')
    return result


def fan_rpm():
    for p in Path('/sys/class/hwmon').glob('hwmon*/temp*_label'):
        if p.read_text().strip() == 'Thermistor 15':
            fan = p.parent / 'fan1_input'
            return int(fan.read_text()) if fan.exists() else None
    return None


def tree_bytes(root):
    total = 0
    for folder, _, files in os.walk(root):
        for name in files:
            try:
                total += (Path(folder) / name).stat().st_size
            except FileNotFoundError:
                pass
    return total


def group_rss(pgid):
    total = 0
    for p in Path('/proc').glob('[0-9]*'):
        try:
            fields = (p / 'stat').read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) == pgid:
                status = (p / 'status').read_text().splitlines()
                total += next((int(s.split()[1]) * 1024 for s in status
                               if s.startswith('VmRSS:')), 0)
        except (OSError, ValueError):
            continue
    return total


def enforce(row, remaining, elapsed):
    t = row['temperatures_c']
    if t['Package id 0'] >= 80 or t['Thermistor 15'] >= 85:
        raise RuntimeError('thermal stop')
    if row['available_ram_bytes'] < 8 * GIB or row['rss_bytes'] > 24 * GIB:
        raise RuntimeError('memory stop')
    if row['swap_growth_bytes'] > 256 * 1024**2:
        raise RuntimeError('swap growth stop')
    if remaining < 0 or row['free_disk_bytes'] < FLOOR + remaining:
        raise RuntimeError('disk reservation stop')
    if elapsed >= 4 * 3600:
        raise RuntimeError('four-hour malfunction fail-safe')


class Supervisor:
    def __init__(self, root, lock_fd):
        self.root = root
        self.lock_fd = lock_fd
        self.started = time.monotonic()
        m = memory()
        self.swap = m['SwapTotal'] - m['SwapFree']
        self.initial_bytes = tree_bytes(root)
        self.last_tree = 0
        self.remaining = BUDGET

    def sample(self, process, phase, target):
        if time.monotonic() - self.last_tree >= 10:
            self.remaining = BUDGET - (tree_bytes(self.root) - self.initial_bytes)
            self.last_tree = time.monotonic()
        m = memory()
        disk = os.statvfs(self.root)
        row = dict(at=time.time(), phase=phase, target=target,
                   temperatures_c=sensors(), available_ram_bytes=m['MemAvailable'],
                   fan1_rpm=fan_rpm(),
                   swap_growth_bytes=m['SwapTotal'] - m['SwapFree'] - self.swap,
                   free_disk_bytes=disk.f_bavail * disk.f_frsize,
                   remaining_output_reservation_bytes=self.remaining,
                   rss_bytes=group_rss(process.pid) if process else 0)
        enforce(row, self.remaining, time.monotonic() - self.started)
        return row

    def execute(self, label, command, cwd, env, reference=None):
        folder = self.root / 'measurements' / label
        folder.mkdir(parents=True, exist_ok=False)
        write(folder / 'command.json', dict(command=command, cwd=str(cwd),
                                          rayon_threads=env['RAYON_NUM_THREADS']))
        def limits():
            import ctypes
            if ctypes.CDLL(None).prctl(1, signal.SIGTERM) != 0:
                raise RuntimeError('cannot set parent-death signal')
            os.sched_setaffinity(0, {0, 1, 2, 3})
            os.nice(10)
            resource.setrlimit(resource.RLIMIT_AS, (48 * GIB,) * 2)
        child = None
        events, peaks = [], {}
        phase, target = 'startup', 0
        cpu_before = resource.getrusage(resource.RUSAGE_CHILDREN)
        start = time.monotonic()
        try:
            with (folder / 'stdout.log').open('x') as out, \
                    (folder / 'resources.jsonl').open('x') as trace:
                child = subprocess.Popen(command, cwd=cwd, env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    start_new_session=True, preexec_fn=limits, bufsize=0,
                    pass_fds=(self.lock_fd,))
                selector = selectors.DefaultSelector()
                selector.register(child.stdout, selectors.EVENT_READ)
                last_sample = 0
                eof = False
                pending = b''
                while not (eof and child.poll() is not None):
                    if time.monotonic() - last_sample >= .5:
                        row = self.sample(child, phase, target)
                        trace.write(json.dumps(row) + '\n'); trace.flush()
                        key = f'{phase}/{target}'
                        peaks[key] = max(peaks.get(key, 0), row['rss_bytes'])
                        last_sample = time.monotonic()
                    for _, _ in selector.select(timeout=.1):
                        chunk = os.read(child.stdout.fileno(), 65536)
                        if not chunk:
                            selector.unregister(child.stdout); eof = True
                            continue
                        pending += chunk
                        while b'\n' in pending:
                            raw, pending = pending.split(b'\n', 1)
                            line = raw.decode(errors='replace')
                            out.write(line + '\n'); out.flush()
                            if line.startswith('{'):
                                event = json.loads(line)
                                events.append(event)
                                if event.get('event') == 'phase':
                                    phase, target = event['phase'], event['target']
                                if reference is not None:
                                    check_event(reference, event)
                                write(folder / 'progress.json', event)
                if pending:
                    out.write(pending.decode(errors='replace'))
                selector.close()
                code = child.wait()
            cpu_after = resource.getrusage(resource.RUSAGE_CHILDREN)
            result = dict(returncode=code, wall_seconds=time.monotonic() - start,
                cpu_seconds=cpu_after.ru_utime + cpu_after.ru_stime
                    - cpu_before.ru_utime - cpu_before.ru_stime,
                sampled_peak_rss_by_phase=peaks, events=events)
            write(folder / 'result.json', result)
            if code:
                raise RuntimeError(f'{label} failed with exit {code}')
            return result
        except BaseException as error:
            if child is not None and child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL); child.wait()
            write(folder / 'failure.json', dict(error=repr(error), phase=phase,
                                               target=target))
            raise


def check_event(reference, event):
    name = event.get('event')
    if name not in ('trained', 'verified'):
        return
    expected = next((e for e in reference['events']
                     if e.get('event') == name and e['target'] == event['target']), None)
    fields = ('target', 'nodes', 'iteration', 'entries') if name == 'trained' else ('target', 'sha256')
    if expected is None or [expected[k] for k in fields] != [event[k] for k in fields]:
        raise ValueError(f'cross-arm {name} identity mismatch at {event["target"]}')


def compare(reference, candidate):
    for name in ('trained', 'verified'):
        left = [e for e in reference['events'] if e.get('event') == name]
        right = [e for e in candidate['events'] if e.get('event') == name]
        if len(left) != 3 or len(right) != 3:
            raise ValueError('missing milestone events')
        fields = ('target', 'nodes', 'iteration', 'entries') if name == 'trained' else ('target', 'sha256')
        if [[e[k] for k in fields] for e in left] != [[e[k] for k in fields] for e in right]:
            raise ValueError(f'cross-arm {name} identity mismatch')


def run(root):
    config = json.loads((root / 'config.json').read_text())
    with Path('/tmp/cfr-cygnus-exclusive.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.sched_setaffinity(0, {7})
        supervisor = Supervisor(root, lock.fileno())
        row = supervisor.sample(None, 'admission', 0)
        if row['temperatures_c']['Package id 0'] >= 70 or row['temperatures_c']['Thermistor 15'] >= 80:
            raise RuntimeError('temperature admission refused')
        write(root / 'admission.json', dict(pid=os.getpid(), config=config,
            initial_sample=row, cpus=[0, 1, 2, 3], rayon_threads=4,
            lock='/tmp/cfr-cygnus-exclusive.lock'))
        env = dict(os.environ, RAYON_NUM_THREADS='4', CARGO_BUILD_JOBS='2',
                   OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
                   NPLAYER_K50_TABLES=config['tables'])
        # Same flag strings and a single owned target directory for all builds.
        env['CARGO_TARGET_DIR'] = str(root / 'target')
        env['CARGO_ENCODED_RUSTFLAGS'] = '\x1f'.join([
            '--remap-path-prefix=' + str(root) + '=benchmark',
            '--remap-path-prefix=' + str(Path.home() / '.cargo') + '=cargo-home'])
        receipts = []
        for arm in config['arms']:
            source = root / 'sources' / arm
            build = ['cargo', 'build', '--release', '--locked', '--offline',
                '--manifest-path', str(source / 'native/hu20-trainer/Cargo.toml'),
                '--example', 'nplayer_storage_bench', '--example', 'nplayer_train']
            supervisor.execute('build-' + arm, build, source, env)
            supervisor.execute('library-tests-' + arm,
                ['cargo', 'test', '--release', '--locked', '--offline',
                 '--manifest-path', str(source / 'native/hu20-trainer/Cargo.toml'),
                 '--lib', '--', '--test-threads=1'], source, env)
            dest = root / 'binaries' / arm
            dest.mkdir(parents=True, exist_ok=False)
            for name in ('nplayer_storage_bench', 'nplayer_train'):
                import shutil
                shutil.copy2(root / 'target/release/examples' / name, dest / name)
            receipts.append(dict(arm=arm, binaries={n:sha(dest/n)
                for n in ('nplayer_storage_bench', 'nplayer_train')}))
        write(root / 'binary-receipts.json', receipts)
        (root / 'outputs').mkdir(exist_ok=False)
        (root / 'qualification').mkdir(exist_ok=False)
        fixture_reference = None
        for arm in config['arms']:
            directory = root / 'qualification' / arm
            directory.mkdir()
            fixture = directory / '200k.gz'
            train = root / 'binaries' / arm / 'nplayer_train'
            supervisor.execute('fixture-' + arm, [str(train), '--players', '3',
                '--stack-bb', '20', '--seed', '2026101541', '--nodes', '200000',
                '--last-average-street', '3', '--max-entries', '150000000',
                '--max-seconds', '300', '--card-buckets', config['tables'],
                '--out', str(fixture)], root, env)
            digest = sha(fixture)
            result = supervisor.execute('qualification-' + arm,
                [str(root / 'binaries' / arm / 'nplayer_storage_bench'), config['tables'],
                 str(fixture), digest, str(directory / 'continued'), '300000,400000,500000'],
                root, env, reference=fixture_reference)
            if fixture_reference is None:
                fixture_reference = result
                fixture_sha = digest
            elif digest != fixture_sha:
                raise ValueError('qualification fresh checkpoint mismatch')
            else:
                compare(fixture_reference, result)
        write(root / 'qualification-passed.json', dict(status='passed',
            fixture_targets=[200000, 300000, 400000, 500000]))
        if sha(config['input']) != config['input_sha256']:
            raise ValueError('input checkpoint mismatch')
        baseline = None
        for arm in config['arms']:
            binary = root / 'binaries' / arm / 'nplayer_storage_bench'
            result = supervisor.execute('arm-' + arm, [str(binary), config['tables'],
                config['input'], config['input_sha256'], str(root / 'outputs' / arm),
                ','.join(map(str, TARGETS))], root, env, reference=baseline)
            if baseline is None:
                baseline = result
            else:
                compare(baseline, result)
            write(root / 'status.json', dict(status='arm-verified', arm=arm))
        write(root / 'status.json', dict(status='complete-identical',
            elapsed_seconds=time.monotonic() - supervisor.started))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    try:
        run(args.root.resolve())
    except BaseException as error:
        write(args.root / 'failure.json', dict(error=repr(error), at=time.time()))
        raise


if __name__ == '__main__':
    main()
