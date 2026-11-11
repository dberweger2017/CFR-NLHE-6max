"""Bound the one-off Runpod pilot and preserve resource/exit receipts on its network volume."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True)
    p.add_argument('command', nargs=argparse.REMAINDER)
    args = p.parse_args()
    if not args.command:
        p.error('a command is required')
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    stopped = None
    with (out / 'resources.jsonl').open('w') as resources, (out / 'job.log').open('w') as log:
        child = subprocess.Popen(args.command, start_new_session=True, stdout=log, stderr=subprocess.STDOUT)
        while child.poll() is None:
            mem = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
            available = int(mem['MemAvailable'].split()[0]) * 1024
            free = shutil.disk_usage(out).free
            gpu = subprocess.run(['nvidia-smi', '--query-gpu=temperature.gpu,memory.used,utilization.gpu',
                                  '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=10)
            fields = gpu.stdout.strip().split(',')
            row = {'seconds': time.monotonic() - start, 'available_bytes': available,
                   'disk_free_bytes': free, 'gpu': gpu.stdout.strip(), 'gpu_query_exit': gpu.returncode}
            resources.write(json.dumps(row) + '\n')
            resources.flush()
            if row['seconds'] >= 2700:
                stopped = '45-minute experiment timeout'
            elif available < 1 << 30 or free < 1 << 30:
                stopped = 'memory/disk headroom below 1 GiB'
            elif gpu.returncode or len(fields) != 3:
                stopped = 'GPU telemetry failed'
            elif float(fields[0]) >= 87:
                stopped = 'GPU temperature >=87 C'
            if stopped:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                break
            time.sleep(5)
        code = child.wait()
    (out / 'exit.json').write_text(json.dumps({'returncode': code, 'stop_reason': stopped,
                                             'seconds': time.monotonic() - start}, indent=2) + '\n')
    raise SystemExit(0 if code == 0 and stopped is None else 1)


if __name__ == '__main__':
    main()
