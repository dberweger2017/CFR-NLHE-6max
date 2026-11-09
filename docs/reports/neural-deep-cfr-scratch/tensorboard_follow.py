"""Mirrors the scratch run's files into TensorBoard scalars, read-only (docs/neural-deep-cfr-scratch.md).

    python tensorboard_follow.py RUN_DIR LOG_DIR

It clears LOG_DIR at start, then every 30 seconds appends what's new in the run's own records, so it
never touches training and can restart at any time. The scalars:
- train/: minutes per iteration, nodes per traversal, the share of traverser decisions sampled past
  the exploration depth, and the advantage network's final loss, by iteration;
- eval/: each table's primary contrast against step 2's net1 (all-in adjusted BB/100), by iteration;
- machine/: CPU, VRM and GPU temperature and memory used, by minute of the run.
"""
import csv
import glob
import json
import shutil
import sys
import time
from pathlib import Path

from tensorboardX import SummaryWriter


def load(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


class Once:
    """Adds each (tag, step) once, so repeated passes over the same records append only news."""

    def __init__(self, writer):
        self.w, self.seen = writer, set()

    def add_scalar(self, tag, value, step, walltime=None):
        if (tag, step) not in self.seen:
            self.seen.add((tag, step))
            self.w.add_scalar(tag, value, step, walltime=walltime)


def write(run, w):
    progress = {}
    if (run / 'progress.csv').exists():
        for row in csv.reader((run / 'progress.csv').open()):
            if len(row) != 5:
                continue
            progress[int(row[0])] = [float(x) for x in row[1:]]
    for t, (t0, _, _, t3) in sorted(progress.items()):
        w.add_scalar('train/minutes_per_iteration', (t3 - t0) / 60, t, walltime=t3)
        it = load(run / 'iterations' / f'it{t}.json')
        if it:
            w.add_scalar('train/nodes_per_traversal', it['nodes'] / it['traversals'], t, walltime=t3)
            explored, sampled = it['advantage_samples'], it.get('sampled_traverser_decisions', 0)
            w.add_scalar('train/sampled_decision_share', sampled / max(1, explored + sampled), t, walltime=t3)
        tr = load(run / 'models' / f'adv{t}.train.json')
        if tr:
            w.add_scalar('train/advantage_loss', tr['final_loss'], t, walltime=t3)
    for res in glob.glob(str(run / 'monitor' / 'it*' / 'results' / 'results.json')):
        t = int(Path(res).parent.parent.name[2:])
        r = load(res)
        for name, e in (r or {}).get('tables', {}).items():
            w.add_scalar(f'eval/{name}', e['fields'][e['primary']]['change']['adjusted']['mean_bb100'], t)
    start = None
    if (run / 'resources.csv').exists():
        for row in csv.reader((run / 'resources.csv').open()):
            try:
                at = time.mktime(time.strptime(row[0], '%Y-%m-%dT%H:%M:%SZ')) - time.timezone
            except ValueError:
                continue
            start = start or at
            step = int((at - start) // 60)
            for i, tag in ((1, 'cpu_c'), (2, 'vrm_c'), (3, 'gpu_c')):
                if row[i]:
                    w.add_scalar(f'machine/{tag}', float(row[i]), step, walltime=at)
            w.add_scalar('machine/ram_used_gb', float(row[4]) / 1024, step, walltime=at)
    w.w.flush()


def main():
    run, log = Path(sys.argv[1]), Path(sys.argv[2])
    shutil.rmtree(log, ignore_errors=True)
    w = Once(SummaryWriter(str(log), flush_secs=30))
    while True:
        write(run, w)
        time.sleep(30)


if __name__ == '__main__':
    main()
