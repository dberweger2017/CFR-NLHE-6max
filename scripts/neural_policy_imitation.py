"""Imitation of the live widemix by a small network (docs/neural-policy-imitation.md).

    train     --data FILE... --seed S --out DIR      train on teacher 0's positive-mass rows
    evaluate  --model DIR --data FILE... --out JSON  rescue, fidelity and seed-noise measures
    decide    --results JSON...                      the protocol's rule over the training seeds

Samples come from `nplayer_features` files (scripts/neural_policy_samples.py). Teacher 0 is the
live `widemix` (run 1); the others are only read by `evaluate`.
"""
import argparse
import hashlib
import json
import math
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from scripts import neural_policy_samples as nps

HIDDEN = (1024, 1024, 512)
EPOCHS = 4
BATCH = 8192
LR = 1e-3
WEIGHT_DECAY = 1e-4
MARGIN = -0.05
STREETS = ('preflop', 'flop', 'turn', 'river')


def network(torch, features, hidden=HIDDEN):
    nn = torch.nn
    layers, width = [], features
    for h in hidden:
        layers += [nn.Linear(width, h), nn.ReLU()]
        width = h
    layers.append(nn.Linear(width, nps.ACTIONS))
    return nn.Sequential(*layers)


def masked_log_softmax(torch, logits, mask):
    return torch.log_softmax(logits.float().masked_fill(~mask, float('-inf')), dim=1)


def training_arrays(paths):
    """Features, targets and legal masks of every sample where teacher 0 is trained."""
    xs, ps, ms = [], [], []
    layout = None
    for path in paths:
        s = nps.load(path, layout_sha256=layout)
        layout = s.header['layout_sha256']
        p, status = s.teacher(0)
        keep = np.flatnonzero(status == nps.POSITIVE)
        xs.append(np.ascontiguousarray(s.records['features'][keep]))
        ps.append(p[keep])
        ms.append(s.legal(keep))
    return np.concatenate(xs), np.concatenate(ps), np.concatenate(ms), layout


def sha_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 24), b''):
            h.update(block)
    return h.hexdigest()


def train(args, hidden=HIDDEN, epochs=EPOCHS, batch=BATCH):
    import torch
    torch.manual_seed(args.seed)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    start = time.time()
    x, p, m, layout = training_arrays(args.data)
    load_seconds = time.time() - start
    x, p, m = torch.from_numpy(x), torch.from_numpy(p), torch.from_numpy(m)
    if device.type == 'cuda':
        x, p, m = x.pin_memory(), p.pin_memory(), m.pin_memory()
    model = network(torch, x.shape[1], hidden).to(device)
    steps = epochs * math.ceil(len(x) / batch)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    schedule = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=steps)
    amp = device.type == 'cuda'
    scaler = torch.amp.GradScaler('cuda', enabled=amp)
    generator = torch.Generator().manual_seed(args.seed)
    history = []
    for epoch in range(epochs):
        order = torch.randperm(len(x), generator=generator)
        total, count, t0 = 0.0, 0, time.time()
        for i in range(0, len(x), batch):
            idx = order[i:i + batch]
            xb = x[idx].to(device, non_blocking=True).float().div_(255.0)
            pb = p[idx].to(device, non_blocking=True)
            mb = m[idx].to(device, non_blocking=True)
            with torch.autocast(device.type, dtype=torch.float16, enabled=amp):
                logits = model(xb)
            logp = masked_log_softmax(torch, logits, mb)
            loss = -(pb * torch.where(mb, logp, torch.zeros_like(logp))).sum(1).mean()
            optimizer.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            schedule.step()
            total += loss.item() * len(idx)
            count += len(idx)
        history.append({'epoch': epoch + 1, 'loss': total / count, 'seconds': time.time() - t0})
        print(json.dumps(history[-1]), flush=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    weights = out / 'weights.pt'
    torch.save({k: v.cpu() for k, v in model.state_dict().items()}, weights)
    meta = {'format': 'neural-policy-imitation-model-v1', 'layout_sha256': layout, 'features': int(x.shape[1]),
            'hidden': list(hidden), 'epochs': epochs, 'batch': batch, 'lr': LR, 'weight_decay': WEIGHT_DECAY,
            'seed': args.seed, 'device': device.type, 'torch': torch.__version__, 'samples': len(x),
            'data': [{'path': str(d), 'sha256': sha_file(d)} for d in args.data], 'history': history,
            'load_seconds': load_seconds, 'seconds': time.time() - start, 'weights_sha256': sha_file(weights)}
    (out / 'model.json').write_text(json.dumps(meta, indent=1) + '\n')
    return meta


def predict(torch, model, device, features, mask, batch=65536):
    out = np.empty((len(features), nps.ACTIONS), dtype=np.float32)
    with torch.no_grad():
        for i in range(0, len(features), batch):
            xb = torch.from_numpy(np.ascontiguousarray(features[i:i + batch])).to(device).float().div_(255.0)
            mb = torch.from_numpy(mask[i:i + batch]).to(device)
            out[i:i + batch] = masked_log_softmax(torch, model(xb), mb).exp().cpu().numpy()
    return out


def tv(a, b):
    return 0.5 * np.abs(a - b).sum(axis=1)


def uniform(mask):
    return mask / mask.sum(axis=1, keepdims=True)


def interval(values, clusters):
    """Mean with a Student-t 95% interval over cluster means (one cluster per hand)."""
    if len(values) == 0:
        return {'n': 0, 'clusters': 0}
    _, inverse = np.unique(clusters, return_inverse=True)
    sums = np.bincount(inverse, weights=values)
    counts = np.bincount(inverse)
    means = sums / counts
    k = len(means)
    mean = float(values.mean())
    if k < 2:
        return {'n': int(len(values)), 'clusters': k, 'mean': mean}
    try:
        from scipy.stats import t
        q = float(t.ppf(0.975, k - 1))
    except ImportError:
        q = 1.96
    se = float(means.std(ddof=1) / math.sqrt(k))
    centre = float(means.mean())
    return {'n': int(len(values)), 'clusters': k, 'mean': mean, 'hand_mean': centre,
            'lower95': centre - q * se, 'upper95': centre + q * se}


def split_of(header):
    job = header['job']['name']
    if job.startswith('wide'):
        return 'wide'
    return 'short-6p' if job.startswith('6p') else 'short-3p4p'


def evaluate(args):
    import torch
    meta = json.loads((Path(args.model) / 'model.json').read_text())
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = network(torch, meta['features'], meta['hidden'])
    model.load_state_dict(torch.load(Path(args.model) / 'weights.pt', map_location='cpu', weights_only=True))
    model.to(device).eval()
    groups = defaultdict(lambda: {'values': [], 'clusters': []})
    agree = defaultdict(lambda: [0, 0])

    def add(key, values, clusters):
        if len(values):
            groups[key]['values'].append(values)
            groups[key]['clusters'].append(clusters)
    for f, path in enumerate(args.data):
        s = nps.load(path, layout_sha256=meta['layout_sha256'])
        split = split_of(s.header)
        mask = s.legal()
        net = predict(torch, model, device, s.records['features'], mask)
        uni = uniform(mask)
        p0, st0 = s.teacher(0)
        others = [s.teacher(t) for t in range(1, len(s.header['teachers']))]
        street = s.records['street']
        players = s.records['players']
        clusters = f * (1 << 32) + s.records['hand'].astype(np.int64)
        positive = np.stack([st == nps.POSITIVE for _, st in others], axis=1)
        rescue = (st0 != nps.POSITIVE) & positive.any(axis=1)
        target = np.zeros_like(p0)
        for k, (pk, _) in enumerate(others):
            target += pk * positive[:, k:k + 1]
        target = target / np.maximum(positive.sum(axis=1, keepdims=True), 1)
        diff = tv(net, target) - tv(uni, target)
        trained = st0 == nps.POSITIVE
        fidelity = tv(net, p0)
        for keys, sel in (((split,), slice(None)),) + tuple(((split, STREETS[i]), street == i) for i in range(4)) \
                + tuple(((split, f'{n}p'), players == n) for n in (3, 4, 5, 6)):
            sel = np.ones(len(s), bool) if isinstance(sel, slice) else sel
            name = '/'.join(keys)
            r = rescue & sel
            add(f'rescue/{name}', diff[r], clusters[r])
            add(f'rescue_net_tv/{name}', tv(net, target)[r], clusters[r])
            add(f'rescue_uniform_tv/{name}', tv(uni, target)[r], clusters[r])
            t = trained & sel
            add(f'fidelity_net/{name}', fidelity[t], clusters[t])
            add(f'fidelity_uniform/{name}', tv(uni, p0)[t], clusters[t])
            for k, (pk, _) in enumerate(others):
                both = t & positive[:, k]
                add(f'seed_noise_t{k + 1}/{name}', tv(pk, p0)[both], clusters[both])
            a = agree[name]
            a[0] += int((net[t].argmax(1) == p0[t].argmax(1)).sum())
            a[1] += int(t.sum())
        if split != 'short-6p':
            add('rescue/primary', diff[rescue], clusters[rescue])
    result = {'format': 'neural-policy-imitation-results-v1', 'model': meta,
              'data': [{'path': str(d), 'sha256': sha_file(d)} for d in args.data], 'measures': {},
              'top_label_agreement': {k: v[0] / v[1] for k, v in agree.items() if v[1]}}
    for key, g in sorted(groups.items()):
        result['measures'][key] = interval(np.concatenate(g['values']), np.concatenate(g['clusters']))
    Path(args.out).write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps({'primary': result['measures'].get('rescue/primary')}))
    return result


def decide(args):
    seeds = []
    for path in args.results:
        r = json.loads(Path(path).read_text())
        p = r['measures']['rescue/primary']
        seeds.append({'seed': r['model']['seed'], 'mean': p['hand_mean'], 'upper95': p['upper95'],
                      'passes': p['upper95'] < MARGIN})
    verdict = {'margin': MARGIN, 'seeds': seeds, 'passes': bool(seeds) and all(s['passes'] for s in seeds)}
    print(json.dumps(verdict, indent=1))
    return verdict


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    t = sub.add_parser('train')
    t.add_argument('--data', nargs='+', required=True)
    t.add_argument('--seed', type=int, required=True)
    t.add_argument('--out', required=True)
    e = sub.add_parser('evaluate')
    e.add_argument('--model', required=True)
    e.add_argument('--data', nargs='+', required=True)
    e.add_argument('--out', required=True)
    d = sub.add_parser('decide')
    d.add_argument('--results', nargs='+', required=True)
    args = parser.parse_args(argv)
    return {'train': train, 'evaluate': evaluate, 'decide': decide}[args.command](args)


if __name__ == '__main__':
    main()
