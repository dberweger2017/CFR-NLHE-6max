"""Exploratory, after the decision (docs/neural-policy-imitation.md): no rule, no claim.

On the rescue spots, splits samples by how far the other teachers' mean strategy is from uniform,
and reports the network's and uniform's TV to that target in each band. A target near uniform
carries little information, which the primary test didn't account for.
"""
import json
import sys
from pathlib import Path

import numpy as np

from scripts import neural_policy_imitation as imitation
from scripts import neural_policy_samples as nps

BANDS = [0, 0.1, 0.2, 0.3, 0.5, 1.01]


def main(model_dir, out, *paths):
    import torch
    meta = json.loads((Path(model_dir) / 'model.json').read_text())
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = imitation.network(torch, meta['features'], meta['hidden'])
    model.load_state_dict(torch.load(Path(model_dir) / 'weights.pt', map_location='cpu', weights_only=True))
    model.to(device).eval()
    rows = {}
    for path in paths:
        s = nps.load(path, layout_sha256=meta['layout_sha256'])
        split = imitation.split_of(s.header)
        mask = s.legal()
        _, st0 = s.teacher(0)
        others = [s.teacher(t) for t in range(1, len(s.header['teachers']))]
        positive = np.stack([st == nps.POSITIVE for _, st in others], axis=1)
        rescue = (st0 != nps.POSITIVE) & positive.any(axis=1)
        if not rescue.any():
            continue
        idx = np.flatnonzero(rescue)
        target = sum(pk[idx] * positive[idx, k:k + 1] for k, (pk, _) in enumerate(others)) / positive[idx].sum(1, keepdims=True)
        uni = imitation.uniform(mask[idx])
        net = imitation.predict(torch, model, device, s.records['features'][idx], mask[idx])
        spread = imitation.tv(target, uni)
        for lo, hi in zip(BANDS, BANDS[1:]):
            sel = (spread >= lo) & (spread < hi)
            r = rows.setdefault(f'{split}/{lo:.1f}-{min(hi, 1):.1f}', [0, 0.0, 0.0])
            r[0] += int(sel.sum())
            r[1] += float(imitation.tv(net[sel], target[sel]).sum())
            r[2] += float(imitation.tv(uni[sel], target[sel]).sum())
    result = {k: {'n': n, 'net_tv': a / n, 'uniform_tv': b / n} for k, (n, a, b) in sorted(rows.items()) if n}
    Path(out).write_text(json.dumps({'model_seed': meta['seed'], 'bands': result}, indent=1) + '\n')
    for k, v in result.items():
        print(f"{k:22s} n={v['n']:6d} net {v['net_tv']:.3f} uniform {v['uniform_tv']:.3f}")


if __name__ == '__main__':
    main(*sys.argv[1:])
