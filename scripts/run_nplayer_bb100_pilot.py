"""Measure admission costs for the owner's requested three-player100BB campaign."""
import argparse
import fcntl
import gzip
import json
import os
from pathlib import Path
import time

from scripts import run_nplayer_storage_benchmark as guard

SEED = 2026101935001
TARGETS = (100_000_000, 200_000_000, 500_000_000)
CAP = 150_000_000
MAX_SECONDS = 1200


def command(config, out, target, threads=16, resume=None):
    args = [config['train'], '--players', '3', '--stack-bb', '100',
        '--small-blind', '50', '--big-blind', '100', '--fast', '--threads', str(threads),
        '--roots-per-seat', '8', '--seed', str(SEED), '--nodes', str(target),
        '--last-average-street', '3', '--max-entries', str(CAP), '--max-seconds', '600',
        '--card-buckets', config['tables'], '--out', str(out)]
    if resume:
        args += ['--resume', resume['checkpoint'], '--resume-sha256', resume['sha256']]
    return args


def validate(summary, target):
    identity = summary['identity']
    if (identity['players'] != 3 or identity['stacks'] != [10000] * 3
            or identity['small_blind'] != 50 or identity['big_blind'] != 100
            or identity['menu'] != 'min-pot-conditional-jam-v1'
            or identity['schema'] != 'nplayer-button-live-actor-history-equity-k50-v1'
            or identity['utility_unit'] != 'big-blind'):
        raise ValueError('pilot is not the frozen three-player100BB game')
    counts = summary['counts']
    if (summary['stop_reason'] != 'nodes' or counts['nodes'] < target
            or counts['discarded_keys'] or counts['discarded_visits']
            or summary['entries'] >= CAP or summary['frozen_at'] is not None):
        raise ValueError('incomplete node target or changed capacity behavior')


class PilotSupervisor(guard.Supervisor):
    def sample(self, process, phase, target):
        row = super().sample(process, phase, target)
        row.update(cpu_stop_c=90, thermistor15_stop_c=100, swap_guard_enabled=False)
        disk = os.statvfs('/home/dberweger')
        row['nvme_free_bytes'] = disk.f_bavail * disk.f_frsize
        if row['nvme_free_bytes'] < 50_000_000_000:
            error = RuntimeError('NVMe50GB floor stop')
            error.resource_sample = row
            raise error
        return row


def run(root, config):
    started = time.time()
    root.mkdir(parents=False, exist_ok=False)
    guard.BUDGET = 12_000_000_000
    guard.write(root / 'launch.json', dict(epoch=started, deadline_epoch=started + MAX_SECONDS,
        supervisor_pid=os.getpid(), config=config, targets=TARGETS, entry_cap=CAP,
        cpu_stop_c=90, thermistor15_stop_c=100, swap_guard_enabled=False,
        rss_limit_bytes=32 * guard.GIB, output_growth_bytes=guard.BUDGET))
    try:
        for relative, digest in config['source_files'].items():
            if guard.sha(Path(__file__).parents[1] / relative) != digest:
                raise ValueError('deployed source mismatch: ' + relative)
        if guard.sha(config['train']) != config['train_sha256']:
            raise ValueError('frozen native binary changed')
        with Path('/tmp/cfr-nplayer-bb100.lock').open('a') as own, \
                Path('/tmp/cfr-cygnus-exclusive.lock').open('a') as normal:
            for lock in (own, normal):
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            supervisor = PilotSupervisor(root, own.fileno(), cpus=range(16),
                max_seconds=MAX_SECONDS - (time.time() - started), rss_limit=32 * guard.GIB,
                cpu_limit=90, thermistor_limit=100, swap_limit_bytes=None)
            first = supervisor.sample(None, 'admission', 0)
            if first['temperatures_c']['Package id 0'] >= 70 or first['temperatures_c']['Thermistor 15'] >= 80:
                raise RuntimeError('thermal admission refused')
            guard.write(root / 'admission.json', first)
            env = dict(os.environ, RAYON_NUM_THREADS='16', OMP_NUM_THREADS='1',
                OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
            def stage(name, target, threads=16, resume=None):
                guard.write(root / 'status.json', dict(status=name, at=time.time(), target=target))
                print(json.dumps(dict(event='stage-start', stage=name, target=target)), flush=True)
                output = root / (name + '.gz')
                measurement = supervisor.execute(name, command(config, output, target, threads, resume),
                    Path(__file__).parents[1], env)
                summary = json.loads((root / 'measurements' / name / 'stdout.log').read_text())
                validate(summary, target)
                if guard.sha(output) != summary['sha256']:
                    raise ValueError('checkpoint readback differs')
                with gzip.open(output, 'rt') as stream:
                    header = json.loads(stream.readline())
                if (header['game'] != summary['identity'] or header['players'] != 3
                        or header['max_entries'] != CAP
                        or header.get('sampling') != 'path-v1' or header.get('roots_per_seat') != 8
                        or header['last_average_street'] != 3 or header['seed'] != SEED
                        or header['freeze_at_cap'] or 'pruning' in header):
                    raise ValueError('checkpoint recipe differs')
                supervisor.sample(None, 'checkpoint-readback', target)
                if summary['elapsed_seconds'] <= summary['save_seconds']:
                    raise ValueError('invalid training/save timing')
                record = dict(stage=name, **summary, wall_seconds=measurement['wall_seconds'],
                    child_cpu_seconds=measurement['cpu_seconds'],
                    sampled_peak_rss_bytes=max(measurement['sampled_peak_rss_by_phase'].values()),
                    checkpoint_bytes=output.stat().st_size,
                    training_seconds=summary['elapsed_seconds'] - summary['save_seconds'])
                guard.write(root / (name + '-summary.json'), record)
                print(json.dumps(dict(event='stage-complete', **record)), flush=True)
                return record
            one = stage('fixture-one', 200_000, 1)
            many = stage('fixture-sixteen', 200_000)
            split = stage('fixture-resume', 400_000, resume=one)
            fresh = stage('fixture-fresh', 400_000)
            if one['sha256'] != many['sha256'] or split['sha256'] != fresh['sha256']:
                raise ValueError('100BB thread/resume checkpoint identity failed')
            guard.write(root / 'qualification.json', dict(status='passed',
                fixture_sha256=one['sha256'], resumed_sha256=split['sha256']))
            rows, previous = [], None
            for target in TARGETS:
                previous = stage(f'pilot-{target}', target, resume=previous)
                rows.append(previous)
            slope = (rows[-1]['entries'] - rows[-2]['entries']) / (rows[-1]['counts']['nodes'] - rows[-2]['counts']['nodes'])
            rate = (rows[-1]['counts']['nodes'] - rows[-2]['counts']['nodes']) / rows[-1]['training_seconds']
            result = dict(status='complete-cost-only', rows=rows,
                last_interval_keys_per_node=slope, last_interval_nodes_per_second=rate,
                linear_entries_at_3b=rows[-1]['entries'] + slope * (3_000_000_000 - rows[-1]['counts']['nodes']),
                linear_entries_at_30b=rows[-1]['entries'] + slope * (30_000_000_000 - rows[-1]['counts']['nodes']),
                projection_scope='local linear scenarios, not bounds or saturation forecasts',
                full_campaign_admitted=False, elapsed_seconds=time.time() - started)
            guard.write(root / 'results.json', result)
            guard.write(root / 'status.json', dict(status='complete-cost-only', at=time.time()))
            print(json.dumps(dict(event='complete', **result)), flush=True)
    except BaseException as error:
        failure = dict(error=repr(error), at=time.time())
        if hasattr(error, 'resource_sample'):
            failure['resource_sample'] = error.resource_sample
        guard.write(root / 'failure.json', failure)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    args = parser.parse_args()
    value = json.loads(args.config.read_text())
    run(Path(value['root']), value)
