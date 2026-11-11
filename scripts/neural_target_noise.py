"""How noisy are Deep CFR's advantage targets? (docs/reports/advantage-target-noise/results.md)

`nplayer_deep_cfr noise` probes one traverser decision per deal K times, with independent samples
below it. Its JSON lines hold each deal's K sampled regret vectors. This script splits their spread
into noise (within a deal, across repeats) and signal (across deals, of the per-deal means), in the
fits' units: squared big blinds summed over legal labels.

    python -m scripts.neural_target_noise summary --runs FILE.jsonl [...] --out report.json
"""
import argparse
import gzip
import json
from pathlib import Path

import numpy as np

ACTIONS = 6
STREETS = ('preflop', 'flop', 'turn', 'river')


def regret_match(r, mask):
    """The engine's rule (policy_network::regret_match): positive regrets over the legal labels, or
    the legal label of highest regret when none is positive. `r` is (..., 6), `mask` broadcasts."""
    pos = np.where(mask, np.maximum(r, 0.), 0.)
    total = pos.sum(-1, keepdims=True)
    best = np.where(mask, r, -np.inf).argmax(-1)
    fallback = np.zeros_like(r)
    np.put_along_axis(fallback, best[..., None], 1., -1)
    return np.where(total > 0, pos / np.where(total > 0, total, 1.), fallback)


def read(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rt') as f:
        return [json.loads(line) for line in f if line.strip()]


def stats(rows):
    """Noise and signal over deals. Each row: legal mask and a (K, 6) array of sampled regrets."""
    if not rows:
        return None
    noise, means, tv, sign, nodes = [], [], [], [], []
    for row in rows:
        r = np.asarray(row['regrets'], dtype=np.float64)
        mask = np.array([(row['legal'] >> a) & 1 == 1 for a in range(ACTIONS)])
        k = len(r)
        mean = r.mean(0)
        # Unbiased per-label variance of one sample, summed over legal labels.
        noise.append(float(r.var(0, ddof=1)[mask].sum()))
        means.append(np.where(mask, mean, 0.))
        # How far one sample's regret-matched strategy is from the mean's: the strategy noise.
        tv.append(float(0.5 * np.abs(regret_match(r, mask) - regret_match(mean, mask)).sum(-1).mean()))
        # Does one sample agree with the mean on which legal labels have positive regret?
        sign.append(float(((r > 0) == (mean > 0))[:, mask].all(-1).mean()))
        nodes.append(float(np.mean(row['nodes'])))
        assert k >= 2
    means = np.array(means)
    masks = np.array([[(row['legal'] >> a) & 1 == 1 for a in range(ACTIONS)] for row in rows])
    k = len(rows[0]['regrets'])
    noise = np.array(noise)
    # Spread of the per-deal means around each label's mean over the deals where it's legal, summed
    # over a deal's legal labels as the fits' error is, minus the noise left in a K-sample mean.
    centre = np.where(masks, means, 0.).sum(0) / np.maximum(masks.sum(0), 1)
    spread = float((np.where(masks, means - centre, 0.) ** 2).sum(1).mean() * len(rows) / max(len(rows) - 1, 1))
    signal = spread - float(noise.mean()) / k
    return {'deals': len(rows), 'repeats': k, 'noise_mse': float(noise.mean()),
            'noise_mse_se': float(noise.std(ddof=1) / np.sqrt(len(noise))) if len(noise) > 1 else None,
            'signal_variance': signal, 'noise_share': float(noise.mean() / (noise.mean() + max(signal, 0.))),
            'tv_one_sample_to_mean': float(np.mean(tv)), 'sign_agreement': float(np.mean(sign)),
            'nodes_per_probe': float(np.mean(nodes))}


def summary(args):
    out = []
    for path in args.runs:
        meta_path = Path(str(path).removesuffix('.gz').removesuffix('.jsonl') + '.json')
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        rows = read(path)
        entry = {'run': Path(path).name, 'meta': meta, 'all': stats(rows), 'by_players': {}}
        for n in sorted({r['players'] for r in rows}):
            entry['by_players'][str(n)] = stats([r for r in rows if r['players'] == n])
        out.append(entry)
        a = entry['all'] or {}
        print(json.dumps({'run': entry['run'], **{k: a.get(k) for k in ('deals', 'noise_mse', 'signal_variance', 'noise_share',
                                                                      'tv_one_sample_to_mean', 'nodes_per_probe')}}))
    Path(args.out).write_text(json.dumps({'format': 'neural-target-noise-report-v1', 'runs': out}, indent=1) + '\n')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('summary')
    s.add_argument('--runs', nargs='+', required=True)
    s.add_argument('--out', required=True)
    args = p.parse_args(argv)
    summary(args)


if __name__ == '__main__':
    main()
