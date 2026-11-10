"""Fit and report the opt-in M4 estimator qualification; never changes a playing model.

The critic's distinct format and combined-seat inputs are training-only. Import torch only
inside fitting so reporting and protocol tests need neither torch nor an Apple GPU.
"""
import argparse
import hashlib
import json
import math
import random
import statistics
import time
from pathlib import Path

INPUTS = 670
HIDDEN = 64


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def fit(args):
    import numpy as np
    import torch
    start = time.monotonic()
    torch.manual_seed(20261110850003)
    torch.set_num_threads(2)
    if args.device == 'mps':
        torch.mps.set_per_process_memory_fraction(0.10)
    dtype = np.dtype([('features', 'u1', (INPUTS,)), ('action', 'u1'), ('target', '<f4')])
    path = Path(args.data) / 'train.bin'
    if path.stat().st_size % dtype.itemsize:
        raise ValueError('truncated training data')
    rows = np.fromfile(path, dtype=dtype)
    if not len(rows) or not np.isfinite(rows['target']).all() or (rows['action'] >= 6).any():
        raise ValueError('invalid training rows')
    device = torch.device(args.device)
    model = torch.nn.Sequential(torch.nn.Linear(INPUTS, HIDDEN), torch.nn.ReLU(), torch.nn.Linear(HIDDEN, 6)).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
    rng = np.random.default_rng(20261110850003)
    losses = []
    for step in range(1000):
        pick = rng.integers(len(rows), size=512)
        x = torch.from_numpy(rows['features'][pick].astype(np.float32) / 255).to(device)
        a = torch.from_numpy(rows['action'][pick].astype(np.int64)).to(device)
        y = torch.from_numpy(rows['target'][pick].astype(np.float32) / 100).to(device)
        opt.zero_grad(set_to_none=True)
        loss = ((model(x).gather(1, a[:, None]).squeeze(1) - y) ** 2).mean()
        loss.backward()
        opt.step()
        if step % 100 == 0 or step == 999:
            value = float(loss.detach().cpu())
            if not math.isfinite(value):
                raise ValueError('nonfinite critic loss')
            losses.append({'step': step + 1, 'loss': value})
            print(json.dumps(losses[-1]), flush=True)
    layers = [model[0], model[2]]
    weights = [v.detach().cpu().numpy() for layer in layers for v in (layer.weight, layer.bias)]
    if not all(np.isfinite(w).all() for w in weights):
        raise ValueError('nonfinite critic weights')
    layout = json.loads((Path(args.data) / 'summary.json').read_text())['policy_layout']
    critic = {'format': 'variance-probe-critic-v1', 'inputs': INPUTS, 'hidden': HIDDEN,
              'policy_layout': layout, **{k: w.ravel().tolist() for k, w in zip(('w', 'b', 'v', 'c'), weights)}}
    out = Path(args.out)
    out.mkdir(exist_ok=False)
    (out / 'critic.json').write_text(json.dumps(critic, allow_nan=False))
    # Keep the exact inputs/outputs for a native inference parity check.
    x = rows['features'][:32].copy()
    with torch.no_grad():
        pred = model(torch.from_numpy(x.astype(np.float32) / 255).to(device)).cpu().numpy() * 100
    (out / 'parity.json').write_text(json.dumps({'features': x.tolist(), 'values': pred.tolist()}))
    receipt = {'seconds': time.monotonic() - start, 'rows': len(rows), 'steps': 1000,
               'seed': 20261110850003, 'losses': losses, 'device': str(device),
               'data_sha256': sha(path), 'critic_sha256': sha(out / 'critic.json'),
               'mps_driver_bytes': torch.mps.driver_allocated_memory() if args.device == 'mps' else 0}
    (out / 'fit.json').write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt), flush=True)


def quantile(values, fraction):
    values = sorted(values)
    i = (len(values) - 1) * fraction
    lo, hi = math.floor(i), math.ceil(i)
    return values[lo] * (hi - i) + values[hi] * (i - lo) if lo != hi else values[lo]


def root_rows(path, repeats):
    groups = {}
    seen = set()
    for line in Path(path).read_text().splitlines():
        row = json.loads(line)
        key = (row['root'], row['batch'], row['repeat'])
        if key in seen or row['batch'] not in (0, 1) or not 0 <= row['repeat'] < repeats:
            raise ValueError('duplicate/invalid evaluation sample')
        seen.add(key)
        arms = sorted(row['arms'], key=lambda a: a['arm'])
        if [a['arm'] for a in arms] != [0, 1] or arms[0]['legal'] != arms[1]['legal']:
            raise ValueError('evaluation arms differ')
        if arms[0]['nodes'] != arms[1]['nodes']:
            raise ValueError('baseline changed the sampled tree')
        for arm in arms:
            if not all(math.isfinite(v) for v in arm['advantages']) or not math.isfinite(arm['seconds']) or arm['seconds'] <= 0:
                raise ValueError('nonfinite/invalid evaluation')
        groups.setdefault((row['root'], row['batch']), []).append(arms)
    roots = {r for r, _ in groups}
    expected = {f'{family}-{street}-{r}' for family in ('3p100', '4p100', '6p100', '6pmix')
                for street in (1, 2, 3) for r in range(4)}
    if roots != expected or len(groups) != 96 or any(len(a) != repeats for a in groups.values()):
        raise ValueError('incomplete fixed panel')
    return groups


def summarize(groups, batches=(0, 1), street=None):
    rows = []
    for root in sorted({r for r, _ in groups}):
        parts = root.split('-')
        if street is not None and int(parts[1]) != street:
            continue
        samples = [sample for b in batches for sample in groups[root, b]]
        legal = [a for a in range(6) if samples[0][0]['legal'] >> a & 1]
        if len(legal) < 2:
            raise ValueError('root requires alternatives')
        var = [statistics.mean(statistics.variance(s[arm]['advantages'][a] for s in samples)
                               for a in legal) for arm in (0, 1)]
        seconds = [sum(s[arm]['seconds'] for s in samples) for arm in (0, 1)]
        rows.append({'root': root, 'stratum': '-'.join(parts[:2]), 'variance': var, 'seconds': seconds})
    return rows


def ratios(rows, overhead, resamples=10000):
    def calc(items):
        v = [statistics.mean(r['variance'][a] for r in items) for a in (0, 1)]
        t = [sum(r['seconds'][a] for r in items) for a in (0, 1)]
        if v[0] <= 0 or t[0] <= 0:
            raise ValueError('zero control variance/time: no identifiable gain')
        ratio = v[1] / v[0]
        return ratio, ratio * (t[1] + overhead) / t[0]
    plain, cost = calc(rows)
    strata = {}
    for row in rows:
        strata.setdefault(row['stratum'], []).append(row)
    rng = random.Random(20261110850004)
    boot = [calc([rng.choice(group) for group in strata.values() for _ in group]) for _ in range(resamples)]
    return {'variance_ratio': plain, 'variance_interval': [quantile([b[0] for b in boot], q) for q in (.025, .975)],
            'cost_ratio': cost, 'cost_interval': [quantile([b[1] for b in boot], q) for q in (.025, .975)],
            'control_seconds': sum(r['seconds'][0] for r in rows),
            'candidate_seconds': sum(r['seconds'][1] for r in rows), 'overhead_seconds': overhead}


def verdict(pooled, batches, streets):
    if any(s['cost_interval'][0] > 1 for s in streets):
        return 'reject: established street harm'
    if pooled['cost_interval'][1] < .75 and all(b['cost_ratio'] < .75 for b in batches):
        return 'advance'
    if pooled['cost_interval'][0] >= .75:
        return 'reject: does not meet the cost-adjusted improvement requirement'
    return 'inconclusive'


def report(args):
    groups = root_rows(Path(args.evaluation) / 'estimates.jsonl', 64)
    stages = [json.loads(line) for line in Path(args.stages).read_text().splitlines()]
    overhead = sum(s['seconds'] for s in stages if s['name'] in ('collect', 'fit'))
    if not {'collect', 'fit', 'evaluate'}.issubset({s['name'] for s in stages}) or any(s['returncode'] for s in stages):
        raise ValueError('missing or failed research stages')
    pooled = ratios(summarize(groups), overhead)
    # Allocate fixed collection/fit cost over the fixed workload; do not charge it twice.
    batches = [ratios(summarize(groups, (b,)), overhead / 2) for b in (0, 1)]
    streets = [ratios(summarize(groups, street=s), overhead / 3) for s in (1, 2, 3)]
    result = {'verdict': verdict(pooled, batches, streets), 'pooled': pooled,
              'batches': batches, 'streets': dict(zip(('flop', 'turn', 'river'), streets)),
              'roots': summarize(groups), 'evaluation_sha256': sha(Path(args.evaluation) / 'estimates.jsonl'),
              'limitations': ['One frozen policy and one critic fit; not a training or playing-strength test.',
                              'Action-sampling variance conditional on complete deals; no card-variance claim.',
                              'Root bootstrap conditions on observed timing; timing uncertainty not included.']}
    Path(args.out).write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: result[k] for k in ('verdict', 'pooled', 'batches', 'streets')}, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    f = sub.add_parser('fit')
    f.add_argument('--data', required=True)
    f.add_argument('--out', required=True)
    f.add_argument('--device', choices=('cpu', 'mps'), default='mps')
    r = sub.add_parser('report')
    r.add_argument('--evaluation', required=True)
    r.add_argument('--stages', required=True)
    r.add_argument('--out', required=True)
    args = p.parse_args()
    {'fit': fit, 'report': report}[args.command](args)


if __name__ == '__main__':
    main()
