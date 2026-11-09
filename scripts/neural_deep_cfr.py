"""Deep CFR training for the neural-policy track, step 5 (docs/neural-deep-cfr.md).

    init      --hidden H,H,.. --seed S --layout SHA --out DIR [--uniform]
                                                     a constant-output advantage network
    warm      --features NPFEAT.. --regrets NPREG.. --iterations T --per-iteration N
              --advantage-buffer DIR --strategy-buffer DIR --capacity C --seed S
                                                     the table's regrets and strategy as buffer samples
    add       --samples FILE.. --advantage-buffer DIR --strategy-buffer DIR --capacity C --seed S
                                                     one iteration's traversal samples into the reservoirs
    train     --kind advantage|strategy --buffer DIR --init DIR|none --hidden H,.. --steps N
              --seed S --out DIR [--device cuda]     one network from a reservoir
    export    --model DIR --out FILE                 a Rust `policy_network` file

Traversal samples come from `nplayer_deep_cfr traverse` (NPDCF001). Each reservoir keeps a uniform
subsample of every sample it was offered, with a per-sample weight: the iteration for traversal
samples (linear CFR), and for the table's warm-start samples the weight of the first T iterations
spread over them. Advantage networks minimize the weighted squared error of the sampled regrets
over legal labels; strategy networks the weighted cross-entropy to the recorded strategies under a
softmax masked to legal labels. Every step is deterministic given its seed.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ACTIONS = 6
MAGIC = b'NPDCF001'
NET_MAGIC = b'NPNET001'
ADVANTAGE, STRATEGY = 0, 1
LR = 1e-3
WEIGHT_DECAY = 1e-4
BATCH = 8192


def sha_file(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def dtype(features):
    return np.dtype([('kind', 'u1'), ('players', 'u1'), ('street', 'u1'), ('legal', 'u1'), ('iteration', '<u4'),
                     ('targets', '<f4', (ACTIONS,)), ('features', 'u1', (features,))])


def load(path):
    """Header and records (a read-only memmap) of a traversal sample file."""
    with open(path, 'rb') as f:
        if f.read(8) != MAGIC:
            raise ValueError(f'{path}: not a Deep CFR sample file')
        size = int.from_bytes(f.read(8), 'little')
        header = json.loads(f.read(size))
    dt = dtype(header['feature_count'])
    if dt.itemsize != header['record_bytes']:
        raise ValueError(f'{path}: record size')
    return header, np.memmap(path, dtype=dt, mode='r', offset=16 + size)


def legal_mask(legal):
    return (legal[:, None] >> np.arange(ACTIONS)) & 1 == 1


class Reservoir:
    """A fixed-capacity uniform sample of every row offered, with weights, on disk."""

    def __init__(self, folder, features, capacity=None):
        self.folder = Path(folder)
        self.dt = dtype(features)
        state = self.folder / 'state.json'
        if state.exists():
            self.state = json.loads(state.read_text())
            if capacity is not None and capacity != self.state['capacity']:
                raise ValueError('reservoir capacity differs')
        else:
            if capacity is None:
                raise ValueError(f'{folder}: no reservoir')
            self.folder.mkdir(parents=True, exist_ok=True)
            self.state = {'format': 'nplayer-deep-cfr-reservoir-v1', 'capacity': capacity, 'features': features,
                          'filled': 0, 'seen': 0, 'batches': 0, 'sources': []}
        cap = self.state['capacity']
        mode = 'r+' if (self.folder / 'rows.u1').exists() else 'w+'
        self.rows = np.memmap(self.folder / 'rows.u1', dtype=self.dt, mode=mode, shape=(cap,))
        self.weights = np.memmap(self.folder / 'weights.f4', dtype='<f4', mode=mode, shape=(cap,))

    def add(self, rows, weights, seed, source):
        """Reservoir sampling over the rows in order; the draws come from (seed, batch number)."""
        n, cap = len(rows), self.state['capacity']
        if n == 0:
            return
        rng = np.random.default_rng([seed, self.state['batches']])
        filled, seen = self.state['filled'], self.state['seen']
        direct = min(n, cap - filled)
        self.rows[filled:filled + direct] = rows[:direct]
        self.weights[filled:filled + direct] = weights[:direct]
        rest = np.arange(direct, n)
        if len(rest):
            # Row k (0-based among all rows ever offered) replaces slot j ~ U[0, k] when j < capacity.
            positions = seen + rest
            slots = rng.integers(0, positions + 1)
            keep = slots < cap
            slots, rest = slots[keep], rest[keep]
            # Later rows win a shared slot, as sequential reservoir sampling would.
            last = len(slots) - 1 - np.unique(slots[::-1], return_index=True)[1]
            order = np.sort(last)
            self.rows[slots[order]] = rows[rest[order]]
            self.weights[slots[order]] = weights[rest[order]]
        self.state['filled'] = filled + direct
        self.state['seen'] = seen + n
        self.state['batches'] += 1
        self.state['sources'].append({'source': source, 'rows': int(n)})
        self.rows.flush()
        self.weights.flush()
        (self.folder / 'state.json').write_text(json.dumps(self.state, indent=1) + '\n')

    def view(self):
        n = self.state['filled']
        return self.rows[:n], self.weights[:n]


def network(torch, features, hidden):
    nn = torch.nn
    layers, width = [], features
    for h in hidden:
        layers += [nn.Linear(width, h), nn.ReLU()]
        width = h
    layers.append(nn.Linear(width, ACTIONS))
    return nn.Sequential(*layers)


def save_model(torch, model, folder, meta):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    torch.save(model.state_dict(), folder / 'weights.pt')
    meta = dict(meta, weights_sha256=sha_file(folder / 'weights.pt'))
    (folder / 'model.json').write_text(json.dumps(meta, indent=1) + '\n')
    return meta


def init(args):
    """A constant-output advantage network. Zero outputs make regret matching play the first legal
    label of highest (zero) regret; `--uniform` sets every output to 1, so regret matching plays
    uniformly over the legal labels, the usual first CFR iterate."""
    import torch
    torch.manual_seed(args.seed)
    hidden = [int(h) for h in args.hidden.split(',')]
    model = network(torch, args.features, hidden)
    with torch.no_grad():
        model[-1].weight.zero_()
        model[-1].bias.fill_(1.0 if args.uniform else 0.0)
    meta = save_model(torch, model, args.out, {'kind': 'advantage', 'output': 'advantage-6', 'features': args.features,
                                               'hidden': hidden, 'layout_sha256': args.layout, 'seed': args.seed, 'steps': 0,
                                               'initial_output': 1.0 if args.uniform else 0.0})
    print(json.dumps({'out': args.out, 'weights_sha256': meta['weights_sha256']}))


def add(args):
    """Each file's advantage and strategy records into their reservoirs, weight = iteration."""
    adv = strat = None
    for k, path in enumerate(args.samples):
        header, rec = load(path)
        if adv is None:
            adv = Reservoir(args.advantage_buffer, header['feature_count'], args.capacity)
            strat = Reservoir(args.strategy_buffer, header['feature_count'], args.capacity)
        for kind, buf in ((ADVANTAGE, adv), (STRATEGY, strat)):
            rows = np.asarray(rec[rec['kind'] == kind])
            buf.add(rows, rows['iteration'].astype('<f4'), args.seed * 1000 + k, {'path': str(path), 'kind': kind,
                    'iteration': header['iteration'], 'sha256': sha_file(path)})
    print(json.dumps({'advantage': adv.state['filled'], 'advantage_seen': adv.state['seen'],
                      'strategy': strat.state['filled'], 'strategy_seen': strat.state['seen']}))


def warm(args):
    """The table's regrets and strategy, at `nplayer_features` samples where teacher 0 is trained,
    as reservoir rows standing for iterations 1..T: their total weight is that of T iterations of
    `per_iteration` rows each, spread evenly."""
    from scripts import neural_policy_samples as nps
    if len(args.features) != len(args.regrets):
        raise ValueError('one regret sidecar per feature file')
    linear = args.iterations * (args.iterations + 1) / 2
    per = dict(zip((ADVANTAGE, STRATEGY), args.per_iteration))
    parts = {ADVANTAGE: [], STRATEGY: []}
    features = None
    for fpath, rpath in zip(args.features, args.regrets):
        s = nps.load(fpath)
        rh, reg = load_regrets(rpath)
        if rh['features_sha256'] != sha_file(fpath) or len(reg) != len(s):
            raise ValueError(f'{rpath}: not the sidecar of {fpath}')
        p, status = s.teacher(0)
        features = s.records['features'].shape[1]
        keep = np.flatnonzero((status == nps.POSITIVE) & (reg['found'] == 1))
        for kind, targets in ((ADVANTAGE, reg['regrets'][keep]), (STRATEGY, p[keep])):
            rows = np.zeros(len(keep), dtype(features))
            rows['kind'] = kind
            rows['players'] = s.records['players'][keep]
            rows['street'] = s.records['street'][keep]
            rows['legal'] = s.records['legal_mask'][keep]
            rows['iteration'] = 0
            rows['targets'] = targets
            rows['features'] = s.records['features'][keep]
            parts[kind].append(rows)
    out = {}
    for kind, folder in ((ADVANTAGE, args.advantage_buffer), (STRATEGY, args.strategy_buffer)):
        rows = np.concatenate(parts[kind])
        buf = Reservoir(folder, features, args.capacity)
        if buf.state['seen']:
            raise ValueError(f'{folder}: warm start goes into an empty reservoir')
        w = np.full(len(rows), per[kind] * linear / len(rows), '<f4')
        buf.add(rows, w, args.seed, {'warm': True, 'iterations': args.iterations, 'per_iteration': args.per_iteration,
                                     'features': [str(f) for f in args.features], 'regrets': [str(r) for r in args.regrets]})
        out['advantage' if kind == ADVANTAGE else 'strategy'] = {'rows': len(rows), 'weight_each': float(w[0])}
    print(json.dumps(out))


def load_regrets(path):
    """An `nplayer_features` regret sidecar: header, then per sample found u8 and six f32 average
    regrets by menu label (big blinds per traversal)."""
    with open(path, 'rb') as f:
        if f.read(8) != b'NPREG001':
            raise ValueError(f'{path}: not a regret sidecar')
        size = int.from_bytes(f.read(8), 'little')
        header = json.loads(f.read(size))
    dt = np.dtype([('found', 'u1'), ('regrets', '<f4', (ACTIONS,))])
    return header, np.memmap(path, dtype=dt, mode='r', offset=16 + size)


def loss(torch, kind, out, targets, mask, w):
    if kind == 'advantage':
        err = torch.where(mask, (out.float() - targets) ** 2, torch.zeros_like(targets)).sum(1)
    else:
        logp = torch.log_softmax(out.float().masked_fill(~mask, float('-inf')), dim=1)
        err = -torch.where(mask, targets * logp, torch.zeros_like(targets)).sum(1)
    return (err * w).sum() / w.sum()


def train(args):
    import torch
    device = torch.device(args.device)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    state = json.loads((Path(args.buffer) / 'state.json').read_text())
    buf = Reservoir(args.buffer, state['features'])
    rows, weights = buf.view()
    if args.init != 'none':
        meta = json.loads((Path(args.init) / 'model.json').read_text())
        hidden = meta['hidden']
        model = network(torch, state['features'], hidden)
        model.load_state_dict(torch.load(Path(args.init) / 'weights.pt', map_location='cpu', weights_only=True))
        layout = meta['layout_sha256']
    else:
        hidden = [int(h) for h in args.hidden.split(',')]
        model = network(torch, state['features'], hidden)
        layout = args.layout
    model.to(device).train()
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=WEIGHT_DECAY)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, args.steps)
    n = len(rows)
    if n == 0:
        raise ValueError('empty reservoir')
    # Weights are normalized per batch, so their scale doesn't change the step size.
    history = []
    for step in range(args.steps):
        idx = np.sort(rng.integers(0, n, min(args.batch, n)))
        b = np.asarray(rows[idx])
        x = torch.from_numpy(b['features'].astype(np.float32) / 255.).to(device)
        t = torch.from_numpy(np.ascontiguousarray(b['targets'])).to(device)
        m = torch.from_numpy(legal_mask(b['legal'])).to(device)
        w = torch.from_numpy(np.asarray(weights[idx], np.float32)).to(device)
        with torch.autocast(device.type, dtype=torch.float16, enabled=device.type == 'cuda'):
            out = model(x)
        value = loss(torch, args.kind, out, t, m, w)
        opt.zero_grad(set_to_none=True)
        value.backward()
        opt.step()
        sched.step()
        if step % max(1, args.steps // 20) == 0 or step == args.steps - 1:
            history.append({'step': step, 'loss': float(value)})
    model.cpu()
    output = 'advantage-6' if args.kind == 'advantage' else 'masked-softmax-6'
    meta = save_model(torch, model, args.out, {'kind': args.kind, 'output': output, 'features': state['features'],
                                               'hidden': hidden, 'layout_sha256': layout, 'seed': args.seed, 'steps': args.steps,
                                               'batch': args.batch, 'lr': args.lr, 'buffer': {'path': str(args.buffer), **{k: state[k] for k in ('filled', 'seen', 'batches')}},
                                               'init': args.init, 'loss_history': history})
    print(json.dumps({'out': args.out, 'weights_sha256': meta['weights_sha256'], 'final_loss': history[-1]['loss']}))


def export(args):
    import torch
    meta = json.loads((Path(args.model) / 'model.json').read_text())
    state = torch.load(Path(args.model) / 'weights.pt', map_location='cpu', weights_only=True)
    linear = sorted({k.split('.')[0] for k in state}, key=int)
    dims = [meta['features']] + list(meta['hidden']) + [ACTIONS]
    header = {'format': 'nplayer-policy-network-v1', 'layout_sha256': meta['layout_sha256'], 'features': meta['features'],
              'layers': [{'in': a, 'out': b} for a, b in zip(dims, dims[1:])], 'activation': 'relu',
              'output': meta.get('output', 'masked-softmax-6'), 'source_weights_sha256': meta['weights_sha256'], 'seed': meta['seed']}
    h = json.dumps(header, separators=(',', ':')).encode()
    with open(args.out, 'xb') as f:
        f.write(NET_MAGIC + len(h).to_bytes(8, 'little') + h)
        for k, (a, b) in zip(linear, zip(dims, dims[1:])):
            w, bias = state[f'{k}.weight'], state[f'{k}.bias']
            if tuple(w.shape) != (b, a) or tuple(bias.shape) != (b,):
                raise ValueError(f'layer {k}: shape {tuple(w.shape)}')
            f.write(w.numpy().astype('<f4').tobytes() + bias.numpy().astype('<f4').tobytes())
    print(json.dumps({'out': str(args.out), 'sha256': sha_file(args.out)}))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    i = sub.add_parser('init')
    i.add_argument('--hidden', required=True)
    i.add_argument('--features', type=int, default=612)
    i.add_argument('--layout', required=True)
    i.add_argument('--seed', type=int, required=True)
    i.add_argument('--out', required=True)
    i.add_argument('--uniform', action='store_true')
    for name in ('warm', 'add'):
        a = sub.add_parser(name)
        a.add_argument('--advantage-buffer', required=True)
        a.add_argument('--strategy-buffer', required=True)
        a.add_argument('--capacity', type=int, required=True)
        a.add_argument('--seed', type=int, required=True)
        if name == 'add':
            a.add_argument('--samples', nargs='+', required=True)
        else:
            a.add_argument('--features', nargs='+', required=True)
            a.add_argument('--regrets', nargs='+', required=True)
            a.add_argument('--iterations', type=int, required=True)
            a.add_argument('--per-iteration', type=float, nargs=2, required=True, metavar=('ADVANTAGE', 'STRATEGY'),
                           help='rows per iteration of each kind, measured on the first iterations')
    t = sub.add_parser('train')
    t.add_argument('--kind', choices=('advantage', 'strategy'), required=True)
    t.add_argument('--buffer', required=True)
    t.add_argument('--init', required=True)
    t.add_argument('--hidden', default='512,256,128')
    t.add_argument('--layout', default=None)
    t.add_argument('--steps', type=int, required=True)
    t.add_argument('--batch', type=int, default=BATCH)
    t.add_argument('--lr', type=float, default=LR)
    t.add_argument('--seed', type=int, required=True)
    t.add_argument('--device', default='cpu')
    t.add_argument('--out', required=True)
    e = sub.add_parser('export')
    e.add_argument('--model', required=True)
    e.add_argument('--out', required=True)
    args = p.parse_args(argv)
    if args.command == 'train' and args.init == 'none' and not args.layout:
        p.error('--layout is required without --init')
    {'init': init, 'warm': warm, 'add': add, 'train': train, 'export': export}[args.command](args)


if __name__ == '__main__':
    main()
