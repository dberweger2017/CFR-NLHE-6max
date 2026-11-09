"""Is the Deep CFR advantage network too small? A capacity sweep on fixed reservoir rows.

Exploration, not a gate (docs/neural-capacity-sweep.md). Every architecture fits the same training
rows with the pilot's loss (scripts/neural_deep_cfr.py: weighted squared error of the sampled
regrets over legal labels), then is scored on the same held-out rows. If held-out error keeps
falling as the network grows, size limits the fit; if it flattens, the noise in the targets does.

    subsample --buffer DIR --rows N --holdout FRACTION --seed S --out DIR
        a uniform, seeded subsample of a reservoir, split into train/ and holdout/ reservoirs
    run --data DIR --arch NAME --steps N --seed S --out DIR [--batch B] [--lr LR] [--device mps]
        [--rows N] [--loss mse|huber --huber-delta BB]
        fits one architecture on DIR/train (or a seeded, nested N-row part of it) and scores it on DIR/holdout
    rescore --data DIR --runs DIR.. [--device mps]
        re-scores saved runs on the holdout (must match) and on a uniform sample of training rows
    report --runs DIR.. --out FILE
        one table over the runs (JSON); also printed as Markdown

Architectures (ARCHS): `mlp-*` are the plain ReLU networks `policy_network` plays today; `res-*` add
residual blocks with layer norm; `cards-*` also learn card embeddings (card, rank and suit, summed
per group as in Brown et al., 2019) in front of a residual trunk. Only `mlp-*` can be exported to
the Rust engine now.
"""
import argparse
import json
import math
import time
from pathlib import Path

import numpy as np

from scripts import neural_deep_cfr as dcfr

ACTIONS = dcfr.ACTIONS
# policy_features layout (native/hu20-trainer/src/policy_features.rs): 4 streets, 5 player counts,
# live share, 6 hero slots, 6 globals, 6 legal, 3 raise sizes, then 52 hole and 52 board cards.
HOLE = 4 + 5 + 1 + 6 + 6 + 6 + 3
BOARD = HOLE + 52
CARDS_END = BOARD + 52

ARCHS = {
    'mlp-0.5m': {'kind': 'mlp', 'hidden': [512, 256, 128]},           # the pilot's advantage network
    'mlp-2m': {'kind': 'mlp', 'hidden': [1024, 1024, 512]},           # the strategy network's shape
    'mlp-13m': {'kind': 'mlp', 'hidden': [1536] * 6},
    'res-15m': {'kind': 'res', 'width': 1536, 'blocks': 3},
    'cards-15m': {'kind': 'cards', 'width': 1536, 'blocks': 3, 'card_dim': 128},
}


def build(torch, features, spec):
    nn = torch.nn
    if spec['kind'] == 'mlp':
        return dcfr.network(torch, features, spec['hidden'])

    class Block(nn.Module):
        def __init__(self, w):
            super().__init__()
            self.norm, self.fc1, self.fc2 = nn.LayerNorm(w), nn.Linear(w, w), nn.Linear(w, w)

        def forward(self, x):
            return x + self.fc2(torch.relu(self.fc1(self.norm(x))))

    class Res(nn.Module):
        def __init__(self, inputs, w, blocks):
            super().__init__()
            self.inp = nn.Linear(inputs, w)
            self.blocks = nn.Sequential(*[Block(w) for _ in range(blocks)])
            self.out = nn.Sequential(nn.LayerNorm(w), nn.ReLU(), nn.Linear(w, ACTIONS))

        def forward(self, x):
            return self.out(self.blocks(self.inp(x)))

    if spec['kind'] == 'res':
        return Res(features, spec['width'], spec['blocks'])

    class Cards(nn.Module):
        """Hole and board cards (multi-hot over 52) through shared card, rank and suit embeddings,
        summed per group, then a card MLP; the result replaces the raw card inputs."""
        def __init__(self, inputs, w, blocks, d):
            super().__init__()
            card = torch.arange(52)
            self.register_buffer('rank', nn.functional.one_hot(card // 4, 13).float())
            self.register_buffer('suit', nn.functional.one_hot(card % 4, 4).float())
            self.card, self.ranks, self.suits = nn.Linear(52, d, bias=False), nn.Linear(13, d, bias=False), nn.Linear(4, d, bias=False)
            self.mix = nn.Sequential(nn.Linear(2 * d, 2 * d), nn.ReLU(), nn.Linear(2 * d, 2 * d), nn.ReLU())
            self.trunk = Res(inputs - 104 + 2 * d, w, blocks)

        def group(self, x):
            return self.card(x) + self.ranks(x @ self.rank) + self.suits(x @ self.suit)

        def forward(self, x):
            cards = torch.cat([self.group(x[:, HOLE:BOARD]), self.group(x[:, BOARD:CARDS_END])], 1)
            return self.trunk(torch.cat([x[:, :HOLE], self.mix(cards), x[:, CARDS_END:]], 1))

    return Cards(features, spec['width'], spec['blocks'], spec['card_dim'])


def subsample(args):
    """A seeded uniform subsample of a reservoir's filled rows, read in index order (sequential on
    disk), split into train and holdout reservoirs with the same row format and weights."""
    state = json.loads((Path(args.buffer) / 'state.json').read_text())
    src = dcfr.Reservoir(args.buffer, state['features'])
    rows, weights = src.view()
    n = min(args.rows, len(rows))
    rng = np.random.default_rng(args.seed)
    pick = np.sort(rng.choice(len(rows), n, replace=False))
    hold = rng.random(n) < args.holdout
    out = Path(args.out)
    summary = {'source': {'buffer': str(args.buffer), **{k: state[k] for k in ('filled', 'seen', 'batches')}},
               'rows': int(n), 'holdout_fraction': args.holdout, 'seed': args.seed}
    for name, mask in (('train', ~hold), ('holdout', hold)):
        idx = pick[mask]
        buf = dcfr.Reservoir(out / name, state['features'], capacity=len(idx))
        chunk = 1 << 18
        for s in range(0, len(idx), chunk):
            part = idx[s:s + chunk]
            buf.rows[s:s + len(part)] = rows[part]
            buf.weights[s:s + len(part)] = weights[part]
        buf.state.update(filled=len(idx), seen=len(idx), batches=1,
                         sources=[{'source': {'subsample_of': str(args.buffer), 'seed': args.seed, 'part': name}, 'rows': len(idx)}])
        buf.rows.flush()
        buf.weights.flush()
        (out / name / 'state.json').write_text(json.dumps(buf.state, indent=1) + '\n')
        summary[name] = {'rows': int(len(idx)), 'warm_rows': int((np.asarray(buf.rows['iteration']) == 0).sum()),
                         'rows_sha256': dcfr.sha_file(out / name / 'rows.u1')}
    (out / 'subsample.json').write_text(json.dumps(summary, indent=1) + '\n')
    print(json.dumps(summary))


def arrays(folder):
    """A reservoir's filled rows as in-memory arrays (the subsample fits in RAM)."""
    state = json.loads((Path(folder) / 'state.json').read_text())
    rows, weights = dcfr.Reservoir(folder, state['features']).view()
    rows = np.array(rows)
    return {'features': rows['features'], 'targets': np.ascontiguousarray(rows['targets']), 'legal': rows['legal'],
            'street': rows['street'], 'players': rows['players'], 'warm': rows['iteration'] == 0,
            'weights': np.array(weights, np.float32)}, state['features']


def regret_match(adv, mask):
    """Regret matching as `policy_network` plays an advantage-6 output: positive regrets
    normalized, else all mass on the legal label of highest regret."""
    pos = np.where(mask, np.maximum(adv, 0), 0)
    total = pos.sum(1, keepdims=True)
    best = np.where(mask, adv, -np.inf).argmax(1)
    fallback = np.zeros_like(adv)
    fallback[np.arange(len(adv)), best] = 1
    return np.where(total > 0, pos / np.where(total > 0, total, 1), fallback)


def predict(torch, model, data, device, batch=16384):
    model.eval()
    out = []
    with torch.no_grad():
        for s in range(0, len(data['features']), batch):
            x = torch.from_numpy(data['features'][s:s + batch].astype(np.float32) / 255.).to(device)
            out.append(model(x).float().cpu().numpy())
    model.train()
    return np.concatenate(out)


def score(pred, data):
    """Held-out errors: the training loss (weighted), unweighted, and split by source, street and
    player count; plus how far the played strategy is from the targets' own regret matching."""
    mask = dcfr.legal_mask(data['legal'])
    se = np.where(mask, (pred - data['targets']) ** 2, 0).sum(1)
    tv = 0.5 * np.abs(regret_match(pred, mask) - regret_match(data['targets'], mask)).sum(1)
    w = data['weights']

    def part(sel):
        if not sel.any():
            return None
        return {'rows': int(sel.sum()), 'mse': float(se[sel].mean()), 'weighted_mse': float((se[sel] * w[sel]).sum() / w[sel].sum()),
                'tv_to_target_policy': float(tv[sel].mean())}
    out = {'all': part(np.ones(len(se), bool)), 'warm': part(data['warm']), 'deep_cfr': part(~data['warm'])}
    out['by_street'] = {s: part(data['street'] == k) for k, s in enumerate(['preflop', 'flop', 'turn', 'river'])}
    out['by_players'] = {str(p): part(data['players'] == p) for p in range(2, 7) if (data['players'] == p).any()}
    return out


def train_sample(train, k, seed):
    """A seeded uniform sample of training rows, as many as the holdout, to compare with it.
    (Not the first rows: the subsample keeps the reservoir's order, and its first rows are all warm.)"""
    n = len(train['features'])
    idx = np.sort(np.random.default_rng(seed + 1).choice(n, min(n, k), replace=False))
    return {key: v[idx] for key, v in train.items()}


def train_score(s):
    return {'all': s['all'], 'warm': s['warm'], 'deep_cfr': s['deep_cfr'], 'sample': 'seeded uniform, as many rows as the holdout'}


def rescore(args):
    """Re-score saved runs: the holdout again (it must match) and the training sample."""
    import torch
    device = torch.device(args.device)
    train, features = arrays(Path(args.data) / 'train')
    hold, _ = arrays(Path(args.data) / 'holdout')
    for folder in map(Path, args.runs):
        result = json.loads((folder / 'result.json').read_text())
        model = build(torch, features, result['spec'])
        model.load_state_dict(torch.load(folder / 'weights.pt', map_location='cpu'))
        model.to(device)
        h = score(predict(torch, model, hold, device), hold)['all']
        if not math.isclose(h['mse'], result['holdout']['all']['mse'], rel_tol=1e-3):
            raise RuntimeError(f"{folder}: holdout {h['mse']} != recorded {result['holdout']['all']['mse']}")
        part = train_part(train, result.get('train_rows_used'), result['seed'])
        sub = train_sample(part, len(hold['features']), result['seed'])
        result['train_rows_first_rows'] = result.pop('train_rows')
        result['train_rows'] = train_score(score(predict(torch, model, sub, device), sub))
        (folder / 'result.json').write_text(json.dumps(result, indent=1) + '\n')
        print(json.dumps({'arch': result['arch'], 'holdout_mse': h['mse'], 'train': {k: result['train_rows'][k]['mse'] for k in ('all', 'warm', 'deep_cfr')}}), flush=True)


def train_part(train, rows, seed):
    """The first `rows` of one seeded permutation of the training rows, so smaller parts nest in larger ones."""
    n = len(train['features'])
    if not rows or rows >= n:
        return train
    idx = np.sort(np.random.default_rng(seed + 2).permutation(n)[:rows])
    return {key: v[idx] for key, v in train.items()}


def fit_loss(torch, name, delta, out, targets, mask, w):
    """The pilot's loss, or a Huber variant: squared error up to `delta` BB per label, linear beyond.
    Huber is robust to heavy-tailed sampled regrets but estimates a biased mean when their noise is skewed."""
    if name == 'mse':
        return dcfr.loss(torch, 'advantage', out, targets, mask, w)
    err = torch.nn.functional.huber_loss(out.float(), targets, reduction='none', delta=delta) * 2
    err = torch.where(mask, err, torch.zeros_like(targets)).sum(1)
    return (err * w).sum() / w.sum()


def run(args):
    import torch
    device = torch.device(args.device)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    train, features = arrays(Path(args.data) / 'train')
    train = train_part(train, getattr(args, 'rows', None), args.seed)
    loss_name, delta = getattr(args, 'loss', 'mse'), getattr(args, 'huber_delta', 20.0)
    hold, _ = arrays(Path(args.data) / 'holdout')
    spec = ARCHS[args.arch]
    model = build(torch, features, spec).to(device).train()
    params = sum(p.numel() for p in model.parameters())
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=dcfr.WEIGHT_DECAY)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, args.steps)
    n = len(train['features'])
    history, start = [], time.time()
    every = max(1, args.steps // args.evals)
    for step in range(args.steps):
        idx = rng.integers(0, n, args.batch)
        x = torch.from_numpy(train['features'][idx].astype(np.float32) / 255.).to(device)
        t = torch.from_numpy(train['targets'][idx]).to(device)
        m = torch.from_numpy(dcfr.legal_mask(train['legal'][idx])).to(device)
        w = torch.from_numpy(train['weights'][idx]).to(device)
        with torch.autocast(device.type, dtype=torch.float16, enabled=device.type == 'cuda'):
            out = model(x)
        value = fit_loss(torch, loss_name, delta, out, t, m, w)
        if not math.isfinite(float(value)):
            raise RuntimeError(f'{args.arch}: non-finite loss at step {step}')
        opt.zero_grad(set_to_none=True)
        value.backward()
        opt.step()
        sched.step()
        if (step + 1) % every == 0 or step == args.steps - 1:
            h = score(predict(torch, model, hold, device), hold)['all']
            history.append({'step': step + 1, 'train_batch_loss': float(value), 'holdout_weighted_mse': h['weighted_mse'],
                            'holdout_mse': h['mse'], 'seconds': time.time() - start})
            print(json.dumps({'arch': args.arch, **history[-1]}), flush=True)
    seconds = time.time() - start
    sub = train_sample(train, len(hold['features']), args.seed)
    result = {'format': 'neural-capacity-sweep-run-v1', 'arch': args.arch, 'spec': spec, 'parameters': int(params),
              'steps': args.steps, 'train_rows_used': int(n), 'warm_rows_used': int(train['warm'].sum()),
              'loss': loss_name, 'huber_delta': delta if loss_name == 'huber' else None, 'batch': args.batch, 'lr': args.lr, 'seed': args.seed, 'device': str(device),
              'data': json.loads((Path(args.data) / 'subsample.json').read_text()), 'seconds': seconds,
              'holdout': score(predict(torch, model, hold, device), hold),
              'train_rows': train_score(score(predict(torch, model, sub, device), sub)), 'history': history}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    torch.save(model.cpu().state_dict(), out / 'weights.pt')
    result['weights_sha256'] = dcfr.sha_file(out / 'weights.pt')
    (out / 'result.json').write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps({'arch': args.arch, 'parameters': params, 'seconds': seconds, 'holdout': result['holdout']['all']}))


def report(args):
    runs = [json.loads((Path(r) / 'result.json').read_text()) for r in args.runs]
    runs.sort(key=lambda r: (r['parameters'], r.get('loss', 'mse'), r.get('train_rows_used', r['data']['train']['rows'])))
    rows = []
    for r in runs:
        h = r['holdout']
        rows.append({'arch': r['arch'], 'parameters': r['parameters'], 'rows': r.get('train_rows_used', r['data']['train']['rows']),
                     'loss': r.get('loss', 'mse'), 'steps': r['steps'], 'minutes': r['seconds'] / 60,
                     'train_mse': r['train_rows']['all']['mse'], 'train_warm_mse': r['train_rows']['warm']['mse'],
                     'train_deep_cfr_mse': r['train_rows']['deep_cfr']['mse'], 'holdout_mse': h['all']['mse'], 'holdout_weighted_mse': h['all']['weighted_mse'],
                     'warm_mse': (h['warm'] or {}).get('mse'), 'deep_cfr_mse': (h['deep_cfr'] or {}).get('mse'),
                     'river_mse': (h['by_street']['river'] or {}).get('mse'), 'tv_to_target_policy': h['all']['tv_to_target_policy']})
    Path(args.out).write_text(json.dumps({'format': 'neural-capacity-sweep-report-v1', 'runs': rows}, indent=1) + '\n')
    cols = list(rows[0]) if rows else []
    fmt = lambda v: f'{v:,}' if isinstance(v, int) else (f'{v:.4g}' if isinstance(v, float) else str(v))
    print('| ' + ' | '.join(cols) + ' |\n|' + '---|' * len(cols))
    for row in rows:
        print('| ' + ' | '.join(fmt(row[c]) for c in cols) + ' |')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('subsample')
    s.add_argument('--buffer', required=True)
    s.add_argument('--rows', type=int, required=True)
    s.add_argument('--holdout', type=float, default=0.1)
    s.add_argument('--seed', type=int, required=True)
    s.add_argument('--out', required=True)
    r = sub.add_parser('run')
    r.add_argument('--data', required=True)
    r.add_argument('--arch', choices=sorted(ARCHS), required=True)
    r.add_argument('--steps', type=int, required=True)
    r.add_argument('--batch', type=int, default=dcfr.BATCH)
    r.add_argument('--lr', type=float, default=dcfr.LR)
    r.add_argument('--evals', type=int, default=10)
    r.add_argument('--seed', type=int, required=True)
    r.add_argument('--device', default='cpu')
    r.add_argument('--rows', type=int, default=None)
    r.add_argument('--loss', choices=['mse', 'huber'], default='mse')
    r.add_argument('--huber-delta', type=float, default=20.0)
    r.add_argument('--out', required=True)
    q = sub.add_parser('rescore')
    q.add_argument('--data', required=True)
    q.add_argument('--runs', nargs='+', required=True)
    q.add_argument('--device', default='cpu')
    t = sub.add_parser('report')
    t.add_argument('--runs', nargs='+', required=True)
    t.add_argument('--out', required=True)
    a = p.parse_args(argv)
    {'subsample': subsample, 'run': run, 'rescore': rescore, 'report': report}[a.command](a)


if __name__ == '__main__':
    main()
