"""Offline policy representation pilot. No production encoder or regret targets are changed."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import time

import numpy as np

from scripts import neural_policy_samples as samples
from scripts import neural_policy_imitation as imitation

FEATURES = 612
HOLE, BOARD, CARDS_END = 31, 83, 135
LAYOUT = '33d180c77adfd1d322afa313949cb5b7bade2469a92b86022458635d650adb8b'
SEED = 20261111860001
FIT_SEEDS = (20261111860011, 20261111860012, 20261111860013)
PERMUTATIONS = tuple(itertools.permutations(range(4)))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def canonicalize(x):
    """Sort joint hole/board suit signatures; equal signatures have identical channels."""
    if x.ndim != 2 or x.shape[1] != FEATURES or x.dtype != np.uint8:
        raise ValueError('expected quantized 612-feature rows')
    hole = x[:, HOLE:BOARD].reshape(-1, 13, 4)
    board = x[:, BOARD:CARDS_END].reshape(-1, 13, 4)
    if not np.isin(hole, [0, 255]).all() or not np.isin(board, [0, 255]).all():
        raise ValueError('card channels must be binary')
    powers = (1 << np.arange(13, dtype=np.uint32))[None, :, None]
    hs = ((hole // 255).astype(np.uint32) * powers).sum(1, dtype=np.uint32)
    bs = ((board // 255).astype(np.uint32) * powers).sum(1, dtype=np.uint32)
    order = np.argsort((hs << 13) | bs, axis=1, kind='stable')[:, ::-1]
    out = x.copy()
    out[:, HOLE:BOARD] = np.take_along_axis(hole, order[:, None, :], axis=2).reshape(-1, 52)
    out[:, BOARD:CARDS_END] = np.take_along_axis(board, order[:, None, :], axis=2).reshape(-1, 52)
    return out


def permute(x, permutation):
    if sorted(permutation) != list(range(4)):
        raise ValueError('not a suit permutation')
    inverse = np.argsort(permutation)
    out = x.copy()
    for start in (HOLE, BOARD):
        out[:, start:start + 52] = x[:, start:start + 52].reshape(-1, 13, 4)[:, :, inverse].reshape(-1, 52)
    return out


def orbit_keys(x):
    return [hashlib.sha256(row.tobytes()).digest() for row in canonicalize(x)]


def validate_rows(x, legal, street, target):
    if x.shape[1] != FEATURES or x.dtype != np.uint8:
        raise ValueError('feature schema')
    hole, board = x[:, HOLE:BOARD], x[:, BOARD:CARDS_END]
    if not np.isin(hole, [0, 255]).all() or not np.isin(board, [0, 255]).all():
        raise ValueError('nonbinary cards')
    if (np.count_nonzero(hole, axis=1) != 2).any() or (hole.astype(np.uint16) + board > 255).any():
        raise ValueError('invalid/overlapping hole and board cards')
    if not np.isin(street, [1, 2, 3]).all() or (np.count_nonzero(board, axis=1) != street + 2).any():
        raise ValueError('board/street disagreement')
    mask = (legal[:, None] >> np.arange(6)) & 1 == 1
    if (legal == 0).any() or (legal > 63).any() or not np.array_equal(mask, x[:, 22:28] == 255):
        raise ValueError('legal feature/mask disagreement')
    if not np.isfinite(target).all() or (target < 0).any() or (target[~mask] != 0).any():
        raise ValueError('invalid teacher probabilities')
    total = target.sum(1, keepdims=True)
    if (total <= 0).any() or (np.abs(total - 1) > .001).any():
        raise ValueError('teacher probability mass')
    return target / total


def prepare(args):
    """Select before any fitting; purge observable-state suit orbits across original splits."""
    root, out = Path(args.data), Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    expected = json.loads(Path(args.reference_eval).read_text())
    pins = {str(Path(x['path']).relative_to('/home/dberweger/neural-policy-imitation-20261108/data')): x['sha256']
            for x in [*expected['model']['data'], *expected['data']]}
    rng = np.random.default_rng(SEED)
    training_orbits = set()
    report = {'format': 'suit-symmetry-data-v1', 'seed': SEED, 'layout': LAYOUT,
              'source_pins': {}, 'source_jobs': {}, 'cells': []}
    roots = set()
    for split, count in [('train', 8192), ('test-wide', 1024)]:
        chunks = []
        for players in range(3, 7):
            relative = f'{split}/wide-{players}p-mixed.npfeat'
            path = root / relative
            digest = sha(path)
            if pins.get(relative) != digest:
                raise ValueError('source SHA256 mismatch: ' + relative)
            report['source_pins'][relative] = digest
            src = samples.load(path, LAYOUT)
            if src.header['feature_count'] != FEATURES:
                raise ValueError('unexpected feature count')
            job = src.header['job']
            if job['root'] in roots:
                raise ValueError('source jobs reuse the same random-stream root')
            roots.add(job['root'])
            report['source_jobs'][relative] = job
            r = src.records
            for street in (1, 2, 3):
                eligible = np.flatnonzero((r['t0_status'] == 0) & (r['street'] == street) & (r['players'] == players))
                # Shuffle indices, not outcomes; deterministic prefix after orbit purging.
                pick = rng.permutation(eligible)
                purged = 0
                if split == 'test-wide':
                    keep = []
                    for first in range(0, len(pick), 8192):
                        part = pick[first:first + 8192]
                        keys = orbit_keys(np.asarray(r['features'][part]))
                        for idx, key in zip(part, keys):
                            if key in training_orbits:
                                purged += 1
                            else:
                                keep.append(idx)
                    pick = np.asarray(keep, dtype=np.int64)
                pick = pick[:count]
                x = np.asarray(r['features'][pick]).copy()
                legal = np.asarray(r['legal_mask'][pick]).copy()
                st = np.asarray(r['street'][pick]).copy()
                target = np.asarray(r['t0_p'][pick]).astype(np.float32) / 65535
                target = validate_rows(x, legal, st, target)
                hand = np.asarray(r['hand'][pick]).astype(np.uint64) + np.uint64(players) * np.uint64(1 << 40)
                min_rows, min_hands = (1024, 512) if split == 'train' else (128, 64)
                distinct = int(len(np.unique(hand)))
                cell = dict(split=split, players=players, street=street, eligible=len(eligible), purged=purged,
                            selected=len(pick), hands=distinct)
                report['cells'].append(cell)
                if len(pick) < min_rows or distinct < min_hands:
                    write(out / 'insufficient.json', report)
                    raise ValueError('insufficient fixed cell: ' + str(cell))
                if split == 'train':
                    training_orbits.update(orbit_keys(x))
                chunks.append(dict(x=x, target=target, legal=legal, street=st,
                                   players=np.full(len(pick), players, np.uint8), hand=hand, source_row=pick))
        folder = out / ('train' if split == 'train' else 'test')
        folder.mkdir()
        for key in chunks[0]:
            np.save(folder / (key + '.npy'), np.concatenate([c[key] for c in chunks]), allow_pickle=False)
    report['files'] = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*.npy'))}
    write(out / 'data.json', report)
    print(json.dumps(report, indent=2))


def load_data(root, split):
    return {key: np.load(Path(root) / split / (key + '.npy'), allow_pickle=False)
            for key in ('x', 'target', 'legal', 'street', 'players', 'hand')}


def predict(torch, model, x, legal, device, batch=8192):
    out = []
    model.eval()
    with torch.no_grad():
        for start in range(0, len(x), batch):
            xx = torch.from_numpy(np.ascontiguousarray(x[start:start + batch])).to(device).float() / 255
            mask = torch.from_numpy(((legal[start:start + batch, None] >> np.arange(6)) & 1).astype(bool)).to(device)
            out.append(model(xx).masked_fill(~mask, float('-inf')).softmax(1).cpu().numpy())
    return np.concatenate(out)


def audit(torch, data, reference, device, out):
    meta = json.loads((reference / 'model.json').read_text())
    if sha(reference / 'weights.pt') != meta['weights_sha256'] or meta['layout_sha256'] != LAYOUT:
        raise ValueError('reference model pin')
    model = imitation.network(torch, FEATURES, meta['hidden']).to(device)
    model.load_state_dict(torch.load(reference / 'weights.pt', map_location='cpu', weights_only=True))
    idx = np.concatenate([np.flatnonzero((data['players'] == p) & (data['street'] == s))[:256]
                          for p in range(3, 7) for s in (1, 2, 3)])
    x, legal = data['x'][idx], data['legal'][idx]
    original = predict(torch, model, x, legal, device)
    canonical = canonicalize(x)
    max_tv = np.zeros(len(x))
    for permutation in PERMUTATIONS:
        transformed = permute(x, permutation)
        if not np.array_equal(canonicalize(transformed), canonical):
            raise ValueError('canonical orbit identity failed')
        p = predict(torch, model, transformed, legal, device)
        max_tv = np.maximum(max_tv, .5 * np.abs(p - original).sum(1))
    result = {'rows': len(x), 'permutations': 24, 'mean_max_tv': float(max_tv.mean()),
              'p99_max_tv': float(np.quantile(max_tv, .99)), 'canonical_identity': True,
              'reference_weights_sha256': meta['weights_sha256']}
    result['fit_admitted'] = result['mean_max_tv'] > .005 or result['p99_max_tv'] > .05
    write(out / 'audit.json', result)
    del model
    torch.cuda.empty_cache()
    return result


def fit(torch, data, canonical, seed, device, out):
    out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    torch.manual_seed(seed)
    model = imitation.network(torch, FEATURES).to(device)
    initial_sha = hashlib.sha256(b''.join(v.detach().cpu().numpy().tobytes()
                                        for v in model.state_dict().values())).hexdigest()
    opt = torch.optim.AdamW(model.parameters(), lr=.001, weight_decay=.0001)
    xx = canonicalize(data['x']) if canonical else data['x']
    x = torch.from_numpy(xx).to(device).float() / 255
    y = torch.from_numpy(data['target']).to(device)
    legal = torch.from_numpy(((data['legal'][:, None] >> np.arange(6)) & 1).astype(bool)).to(device)
    generator = torch.Generator(device=device).manual_seed(seed)
    history = []
    torch.cuda.synchronize()
    fit_start = time.monotonic()
    for step in range(1000):
        idx = torch.randint(len(x), (4096,), generator=generator, device=device)
        opt.zero_grad(set_to_none=True)
        logp = model(x[idx]).masked_fill(~legal[idx], float('-inf')).log_softmax(1)
        loss = -(y[idx] * torch.where(legal[idx], logp, 0.)).sum(1).mean()
        if not torch.isfinite(loss):
            raise ValueError('nonfinite fit')
        loss.backward()
        opt.step()
        if step % 100 == 0 or step == 999:
            row = {'step': step + 1, 'loss': float(loss.detach().cpu())}
            history.append(row)
            print(json.dumps(dict(seed=seed, canonical=canonical, **row)), flush=True)
    torch.cuda.synchronize()
    fit_seconds = time.monotonic() - fit_start
    state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
    torch.save(state, out / 'weights.pt')
    info = {'format': 'suit-symmetry-fit-v1', 'seed': seed, 'canonical': canonical, 'steps': 1000,
            'initial_state_sha256': initial_sha, 'batch_generator_seed': seed,
            'rows': len(x), 'fit_seconds': fit_seconds, 'seconds': time.monotonic() - start,
            'history': history, 'weights_sha256': sha(out / 'weights.pt')}
    write(out / 'fit.json', info)
    del x, y, legal
    return model, info


def hand_means(values, hand):
    ids, inverse = np.unique(hand, return_inverse=True)
    return ids, np.bincount(inverse, weights=values) / np.bincount(inverse)


def interval(values, hand, alpha=.05):
    ids, means = hand_means(values, hand)
    if len(ids) < 2:
        raise ValueError('insufficient independent hands')
    rng = np.random.default_rng(20261111860002)
    boot = np.asarray([means[rng.integers(len(means), size=len(means))].mean() for _ in range(2000)])
    return {'hands': len(ids), 'mean': float(means.mean()),
            'lower': float(np.quantile(boot, alpha)), 'upper': float(np.quantile(boot, 1 - alpha))}


def latency(torch, model, data, canonical):
    cpu = imitation.network(torch, FEATURES)
    cpu.load_state_dict({k: v.detach().cpu() for k, v in model.state_dict().items()})
    cpu.eval()
    # Include quantization conversion, transformation and legal softmax, not model loading.
    timings = []
    indices = np.linspace(0, len(data['x']) - 1, min(256, len(data['x'])), dtype=int)
    with torch.no_grad():
        for repeat in range(5):
            for i in indices:
                start = time.perf_counter_ns()
                x = data['x'][i:i + 1]
                if canonical:
                    x = canonicalize(x)
                p = cpu(torch.from_numpy(x.copy()).float() / 255)
                mask = torch.from_numpy(((data['legal'][i:i + 1, None] >> np.arange(6)) & 1).astype(bool))
                p = p.masked_fill(~mask, float('-inf')).softmax(1)
                if repeat:
                    timings.append((time.perf_counter_ns() - start) / 1000)
    return {'median_us': float(np.median(timings)), 'p95_us': float(np.quantile(timings, .95)),
            'samples': len(timings), 'timings_us': timings, 'row_indices': indices.tolist()}


def run(args):
    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
    import torch
    if not torch.cuda.is_available():
        raise ValueError('CUDA required; no CPU fallback')
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    device = torch.device('cuda')
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    data_pin = json.loads((Path(args.data) / 'data.json').read_text())
    for name, digest in data_pin['files'].items():
        if sha(Path(args.data) / name) != digest:
            raise ValueError('selected input changed: ' + name)
    preprocess_start = time.monotonic()
    test = load_data(args.data, 'test')
    result = {'format': 'suit-symmetry-result-v1', 'torch': torch.__version__,
              'gpu': torch.cuda.get_device_name(0), 'data_sha256': sha(Path(args.data) / 'data.json')}
    result['audit'] = audit(torch, test, Path(args.reference), device, out)
    if not result['audit']['fit_admitted']:
        result['verdict'] = 'stop: little measured suit sensitivity'
        write(out / 'results.json', result)
        return
    train = load_data(args.data, 'train')
    contrasts, seed_means, latency_ratios, per_seed_errors = [], [], [], []
    preprocessing = {}
    for split, rows in [('train', train['x']), ('test', test['x'])]:
        start = time.monotonic()
        canonicalize(rows)
        preprocessing[split] = {'rows': len(rows), 'canonical_seconds': time.monotonic() - start}
    result['preprocessing'] = preprocessing
    all_fits = []
    for index, seed in enumerate(FIT_SEEDS):
        errors, times = {}, {}
        for canonical in ([False, True] if index % 2 == 0 else [True, False]):
            name = ('canonical' if canonical else 'raw') + '-' + str(seed)
            model, info = fit(torch, train, canonical, seed, device, out / name)
            prediction = predict(torch, model, canonicalize(test['x']) if canonical else test['x'], test['legal'], device)
            errors[canonical] = .5 * np.abs(prediction - test['target']).sum(1)
            times[canonical] = latency(torch, model, test, canonical)
            write(out / name / 'latency.json', times[canonical])
            all_fits.append(info)
            del model
            torch.cuda.empty_cache()
        contrast = errors[True] - errors[False]
        per_seed_errors.append(np.stack([errors[False], errors[True]]))
        contrasts.append(contrast)
        _, hm = hand_means(contrast, test['hand'])
        seed_means.append(float(hm.mean()))
        latency_ratios.append(times[True]['median_us'] / times[False]['median_us'])
        paired = [f for f in all_fits if f['seed'] == seed]
        if len({f['initial_state_sha256'] for f in paired}) != 1:
            raise ValueError('paired initialization differs')
    differences = np.stack(contrasts)
    np.save(out / 'paired_tv.npy', differences, allow_pickle=False)
    np.save(out / 'raw_canonical_tv.npy', np.stack(per_seed_errors), allow_pickle=False)
    mean = differences.mean(0)
    primary = interval(mean, test['hand'])
    groups = {}
    for key, codes in [('street', (1, 2, 3)), ('players', (3, 4, 5, 6))]:
        for code in codes:
            selected = test[key] == code
            groups[f'{key}-{code}'] = interval(mean[selected], test['hand'][selected], alpha=.05 / 7)
    harmful = any(g['lower'] > .01 for g in groups.values())
    advance = (primary['mean'] <= -.01 and primary['upper'] < -.005 and all(m < 0 for m in seed_means)
               and not harmful and float(np.median(latency_ratios)) <= 1.25)
    result.update(primary=primary, safeguards=groups, seed_means=seed_means,
                  latency_ratios=latency_ratios, fits=all_fits,
                  hand_mean_tv={name: [float(hand_means(e[arm], test['hand'])[1].mean())
                                       for e in per_seed_errors]
                                for arm, name in enumerate(['raw', 'canonical'])},
                  analysis_seconds=time.monotonic() - preprocess_start,
                  error_array_axes=['fixed seed', 'raw then canonical', 'original held-out row'])
    if harmful:
        result['verdict'] = 'reject: established subgroup regression'
    elif advance:
        result['verdict'] = 'advance to a separately approved playing test'
    elif np.median(latency_ratios) > 1.25:
        result['verdict'] = 'reject: CPU decision-latency limit'
    elif primary['lower'] >= -.005:
        result['verdict'] = 'reject: required imitation gain not established'
    else:
        result['verdict'] = 'inconclusive'
    write(out / 'results.json', result)
    print(json.dumps(result, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--data', required=True)
    prep.add_argument('--reference-eval', required=True)
    prep.add_argument('--out', required=True)
    job = sub.add_parser('run')
    job.add_argument('--data', required=True)
    job.add_argument('--reference', required=True)
    job.add_argument('--out', required=True)
    args = parser.parse_args()
    {'prepare': prepare, 'run': run}[args.command](args)


if __name__ == '__main__':
    main()
