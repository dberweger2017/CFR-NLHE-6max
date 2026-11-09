import json

import numpy as np
import pytest

from scripts import neural_capacity_sweep as sweep
from scripts import neural_deep_cfr as dcfr

F = 612


def reservoir(path, n=3000, seed=0):
    rng = np.random.default_rng(seed)
    r = np.zeros(n, dcfr.dtype(F))
    r['legal'] = 0b011110
    r['street'] = rng.integers(0, 4, n)
    r['players'] = rng.integers(3, 7, n)
    r['iteration'] = np.where(np.arange(n) < n // 3, 0, 101 + np.arange(n) % 20)
    r['features'] = rng.integers(0, 2, (n, F)) * 255
    # A learnable target: regrets are a fixed function of a few features.
    r['targets'][:, 1:5] = (r['features'][:, :4] / 255.) - 0.5
    buf = dcfr.Reservoir(path, F, capacity=n)
    buf.add(r, np.where(r['iteration'] == 0, 50., r['iteration']).astype('<f4'), seed=1, source={'test': True})
    return r


def args(**kw):
    return type('A', (), kw)()


def test_subsample_is_seeded_disjoint_and_keeps_rows_and_weights(tmp_path):
    src = reservoir(tmp_path / 'src')
    for name in ('a', 'b'):
        sweep.subsample(args(buffer=str(tmp_path / 'src'), rows=2000, holdout=0.2, seed=5, out=str(tmp_path / name)))
    a = json.loads((tmp_path / 'a' / 'subsample.json').read_text())
    b = json.loads((tmp_path / 'b' / 'subsample.json').read_text())
    assert a['train']['rows_sha256'] == b['train']['rows_sha256'] and a['train']['rows'] + a['holdout']['rows'] == 2000
    train, _ = sweep.arrays(tmp_path / 'a' / 'train')
    hold, _ = sweep.arrays(tmp_path / 'a' / 'holdout')
    key = lambda d: {bytes(f) + bytes(t) for f, t in zip(d['features'], d['targets'])}
    assert not key(train) & key(hold)
    assert key(train) | key(hold) <= key({'features': src['features'], 'targets': src['targets']})
    assert set(np.unique(train['weights'][train['warm']])) == {50.}


def test_card_offsets_match_the_feature_layout():
    # policy_features: hole.0 is feature 31, board.0 is 83, board.51 is 134 (checked on a real export header).
    assert (sweep.HOLE, sweep.BOARD, sweep.CARDS_END) == (31, 83, 135)


def test_every_architecture_builds_with_six_outputs():
    torch = pytest.importorskip('torch')
    x = torch.rand(3, F)
    for name, spec in sweep.ARCHS.items():
        model = sweep.build(torch, F, spec)
        assert model(x).shape == (3, 6), name
    assert sum(p.numel() for p in sweep.build(torch, F, sweep.ARCHS['mlp-0.5m']).parameters()) < 600_000


def test_regret_matching_matches_the_engine_rule():
    mask = np.array([[True, True, True, False, False, False]] * 2)
    adv = np.array([[1., 3., -1., 9., 0., 0.], [-2., -1., -3., 5., 0., 0.]])
    rm = sweep.regret_match(adv, mask)
    assert np.allclose(rm[0], [0.25, 0.75, 0, 0, 0, 0])
    assert np.allclose(rm[1], [0, 1, 0, 0, 0, 0])   # no positive regret: the legal label of highest regret


def test_run_and_report_end_to_end(tmp_path, monkeypatch):
    pytest.importorskip('torch')
    reservoir(tmp_path / 'src')
    sweep.subsample(args(buffer=str(tmp_path / 'src'), rows=3000, holdout=0.2, seed=5, out=str(tmp_path / 'data')))
    monkeypatch.setitem(sweep.ARCHS, 'tiny-mlp', {'kind': 'mlp', 'hidden': [16]})
    monkeypatch.setitem(sweep.ARCHS, 'tiny-cards', {'kind': 'cards', 'width': 32, 'blocks': 1, 'card_dim': 8})
    runs = []
    for arch in ('tiny-mlp', 'tiny-cards'):
        out = tmp_path / arch
        sweep.run(args(data=str(tmp_path / 'data'), arch=arch, steps=60, batch=256, lr=3e-3, evals=3, seed=1, device='cpu', out=str(out)))
        r = json.loads((out / 'result.json').read_text())
        assert r['history'][-1]['holdout_mse'] < r['history'][0]['holdout_mse'] * 1.5
        assert set(r['holdout']['by_street']) == {'preflop', 'flop', 'turn', 'river'}
        assert r['holdout']['warm']['rows'] + r['holdout']['deep_cfr']['rows'] == r['holdout']['all']['rows']
        runs.append(str(out))
        assert r['train_rows']['warm']['rows'] + r['train_rows']['deep_cfr']['rows'] == r['train_rows']['all']['rows']
    before = json.loads((tmp_path / 'tiny-mlp' / 'result.json').read_text())
    sweep.rescore(args(data=str(tmp_path / 'data'), runs=runs, device='cpu'))
    after = json.loads((tmp_path / 'tiny-mlp' / 'result.json').read_text())
    assert after['train_rows'] == before['train_rows'] and after['holdout'] == before['holdout']
    sweep.report(args(runs=runs, out=str(tmp_path / 'report.json')))
    rep = json.loads((tmp_path / 'report.json').read_text())
    assert [r['arch'] for r in rep['runs']] == ['tiny-mlp', 'tiny-cards']
