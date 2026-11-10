import json

import numpy as np
import pytest

from scripts import neural_deep_cfr as dcfr
from scripts import neural_policy_samples as nps

F = 16


def samples_file(path, rows, iteration=3):
    header = json.dumps({'format': 'nplayer-deep-cfr-samples-v1', 'feature_count': F, 'record_bytes': dcfr.dtype(F).itemsize,
                         'iteration': iteration}).encode()
    with open(path, 'wb') as f:
        f.write(dcfr.MAGIC + len(header).to_bytes(8, 'little') + header + rows.tobytes())
    return path


def rows(n, kind, iteration=3, seed=0):
    rng = np.random.default_rng(seed)
    r = np.zeros(n, dcfr.dtype(F))
    r['kind'] = kind
    r['legal'] = 0b000111
    r['iteration'] = iteration
    r['features'] = rng.integers(0, 256, (n, F))
    r['targets'][:, :3] = rng.normal(size=(n, 3))
    return r


def test_reservoir_is_deterministic_uniform_and_weighted(tmp_path):
    a = dcfr.Reservoir(tmp_path / 'a', F, capacity=100)
    b = dcfr.Reservoir(tmp_path / 'b', F, capacity=100)
    batches = [rows(80, 0, seed=k) for k in range(10)]
    for k, r in enumerate(batches):
        r['targets'][:, 5] = np.arange(len(r)) + 1000 * k   # tags each row
        for buf in (a, b):
            buf.add(r, np.full(len(r), k + 1, '<f4'), seed=7, source={'k': k})
    ra, wa = a.view()
    rb, wb = b.view()
    assert len(ra) == 100 and a.state['seen'] == 800 and (np.asarray(ra) == np.asarray(rb)).all() and (wa == wb).all()
    tags = np.asarray(ra['targets'][:, 5]).astype(int)
    assert len(set(tags)) == 100, 'no row twice'
    batch = tags // 1000
    # Uniform over all 800 rows offered: each batch holds about 10 slots, and weights follow their batch.
    assert np.bincount(batch, minlength=10).max() <= 25 and (wa == batch + 1).all()
    reopened = dcfr.Reservoir(tmp_path / 'a', F)
    assert reopened.state['seen'] == 800 and (np.asarray(reopened.view()[0]) == np.asarray(ra)).all()
    with pytest.raises(ValueError):
        dcfr.Reservoir(tmp_path / 'a', F, capacity=5)


def test_add_splits_kinds_and_weights_by_iteration(tmp_path):
    s = samples_file(tmp_path / 's.npdcf', np.concatenate([rows(30, dcfr.ADVANTAGE, 4), rows(20, dcfr.STRATEGY, 4)]), 4)
    args = type('A', (), {'samples': [s], 'advantage_buffer': tmp_path / 'adv', 'strategy_buffer': tmp_path / 'str',
                          'capacity': 1000, 'seed': 1})
    dcfr.add(args)
    adv, w = dcfr.Reservoir(tmp_path / 'adv', F).view()
    st, _ = dcfr.Reservoir(tmp_path / 'str', F).view()
    assert len(adv) == 30 and len(st) == 20 and (adv['kind'] == 0).all() and (st['kind'] == 1).all() and (w == 4).all()


def test_training_fits_advantages_and_strategies_then_exports(tmp_path):
    torch = pytest.importorskip('torch')
    buf = dcfr.Reservoir(tmp_path / 'adv', F, capacity=4096)
    r = rows(4096, dcfr.ADVANTAGE)
    # Regret of label 0 is the first feature, a function the network can learn.
    r['targets'][:, 0] = r['features'][:, 0] / 255.
    buf.add(r, np.ones(len(r), '<f4'), seed=1, source='synthetic')
    common = dict(buffer=str(tmp_path / 'adv'), hidden='32,16', layout='ab' * 32, batch=512, lr=3e-3, device='cpu')
    dcfr.train(type('A', (), dict(common, kind='advantage', init='none', steps=300, seed=1, out=str(tmp_path / 'm1')))())
    meta = json.loads((tmp_path / 'm1' / 'model.json').read_text())
    hist = meta['loss_history']
    assert meta['output'] == 'advantage-6' and hist[-1]['loss'] < hist[0]['loss']
    dcfr.train(type('A', (), dict(common, kind='advantage', init=str(tmp_path / 'm1'), steps=10, seed=2, out=str(tmp_path / 'm2')))())
    assert json.loads((tmp_path / 'm2' / 'model.json').read_text())['hidden'] == [32, 16]
    out = tmp_path / 'a.npnet'
    dcfr.export(type('A', (), {'model': str(tmp_path / 'm2'), 'out': str(out)})())
    b = out.read_bytes()
    size = int.from_bytes(b[8:16], 'little')
    header = json.loads(b[16:16 + size])
    assert b[:8] == dcfr.NET_MAGIC and header['output'] == 'advantage-6'
    assert len(b) - 16 - size == 4 * (F * 32 + 32 + 32 * 16 + 16 + 16 * 6 + 6)
    s = dcfr.Reservoir(tmp_path / 'str', F, capacity=512)
    sr = rows(512, dcfr.STRATEGY)
    sr['targets'][:] = 0
    sr['targets'][:, 2] = 1.
    s.add(sr, np.ones(len(sr), '<f4'), seed=1, source='synthetic')
    dcfr.train(type('A', (), dict(common, buffer=str(tmp_path / 'str'), kind='strategy', init='none', steps=100, seed=1,
                                  out=str(tmp_path / 's1')))())
    assert json.loads((tmp_path / 's1' / 'model.json').read_text())['output'] == 'masked-softmax-6'


def test_warm_start_spreads_the_first_iterations_weight(tmp_path):
    n = 10
    d = nps.dtype(1, F)
    rec = np.zeros(n, d)
    rec['players'], rec['street'], rec['legal_mask'] = 6, 1, 0b000111
    rec['t0_status'] = [0] * 8 + [2] * 2
    rec['t0_p'][:, 1] = 65535
    rec['features'] = 7
    header = json.dumps({'format': nps.FORMAT, 'layout_sha256': 'ab' * 32, 'teachers': [{}], 'feature_count': F,
                         'record_bytes': d.itemsize}).encode()
    feat = tmp_path / 'x.npfeat'
    feat.write_bytes(nps.MAGIC + len(header).to_bytes(8, 'little') + header + rec.tobytes())
    reg = np.zeros(n, np.dtype([('found', 'u1'), ('regrets', '<f4', (6,))]))
    reg['found'] = [1] * 7 + [0] * 3
    reg['regrets'][:, 2] = 0.5
    rh = json.dumps({'format': 'nplayer-regret-sidecar-v1', 'features_sha256': dcfr.sha_file(feat)}).encode()
    regp = tmp_path / 'x.npreg'
    regp.write_bytes(b'NPREG001' + len(rh).to_bytes(8, 'little') + rh + reg.tobytes())
    args = type('A', (), {'features': [feat], 'regrets': [regp], 'iterations': 4, 'per_iteration': [100., 50.],
                          'advantage_buffer': tmp_path / 'adv', 'strategy_buffer': tmp_path / 'str', 'capacity': 100, 'seed': 3})
    dcfr.warm(args)
    adv, aw = dcfr.Reservoir(tmp_path / 'adv', F).view()
    st, sw = dcfr.Reservoir(tmp_path / 'str', F).view()
    # Trained by teacher 0 and found in the checkpoint: 7 rows; each carries 1/7 of 100 rows x (1+2+3+4).
    assert len(adv) == len(st) == 7 and np.allclose(aw, 1000 / 7) and np.allclose(sw, 500 / 7)
    assert np.allclose(adv['targets'][:, 2], 0.5) and np.allclose(st['targets'][:, 1], 1.)


def test_the_pilot_evaluation_plays_both_networks_everywhere_on_step_4s_tables():
    from scripts import neural_deep_cfr_eval as ev
    from scripts import neural_policy_everywhere as everywhere
    tables = ev.tables()
    assert [t['table'] for t in tables] == [t['table'] for t in everywhere.tables(1)]
    assert all(t['fallback'] == ['network-all:start', 'network-all:dcfr'] for t in tables)
    assert {t['study'] for t in tables} == {'pilot-short', 'pilot-deep'}
    assert ev.verdict('pilot-short', 0.1, 1) == 'deep cfr better' and ev.verdict('pilot-deep', -2, -0.1) == 'start better'


@pytest.mark.parametrize('uniform', [False, True])
def test_init_sets_constant_outputs_for_the_first_iterate(tmp_path, uniform):
    torch = pytest.importorskip('torch')
    args = type('A', (), dict(hidden='8,4', features=F, layout='ab' * 32, seed=1, out=str(tmp_path / 'm'), uniform=uniform))()
    dcfr.init(args)
    meta = json.loads((tmp_path / 'm' / 'model.json').read_text())
    model = dcfr.network(torch, F, [8, 4])
    model.load_state_dict(torch.load(tmp_path / 'm' / 'weights.pt', weights_only=True))
    out = model(torch.rand(5, F))
    # Equal positive regrets on every label: regret matching is uniform over the legal labels.
    assert torch.equal(out, torch.full_like(out, 1.0 if uniform else 0.0))
    assert meta['initial_output'] == (1.0 if uniform else 0.0)


@pytest.mark.parametrize('name,root,blocks', [('e1', 20261109500000, 4096), ('e2', 20261110500000, 4096),
                                              ('e3', 20261111500000, 4096), ('e4', 20261111600000, 4096),
                                              ('monitor-25', 20261110602500, 512)])
def test_scratch_evaluations_pick_their_roots_size_and_fields(monkeypatch, name, root, blocks):
    from scripts import neural_deep_cfr_scratch_eval as ev
    from scripts import neural_policy_everywhere as everywhere
    from scripts import openpoker_phantom_depth as study
    for attr in ('tables', 'verdict', 'ROOT', 'BANKS', 'BLOCKS', 'HARM_STUDIES', 'FORMAT', '__doc__'):
        monkeypatch.setattr(study, attr, getattr(study, attr))
    monkeypatch.setenv('DCFR_SCRATCH_EVAL', name)
    ev.configure()
    assert (study.ROOT, study.BANKS, study.BLOCKS) == (root, 1, blocks)
    tables = study.tables()
    full = everywhere.tables(1)
    assert [t['table'] for t in tables] == [t['table'] for t in full]
    assert all(t['fallback'] == ['network-all:start', 'network-all:dcfr'] for t in tables)
    for t, f in zip(tables, full):
        if name.startswith('monitor'):
            # The primary field stays first, so the report reads it as the primary.
            assert list(t['fields'])[0] == list(f['fields'])[0] and len(t['fields']) == 2
        else:
            assert t['fields'] == f['fields']
    better, worse = ('run 2 better', 'run 1 better') if name in ('e3', 'e4') else ('scratch better', 'start better')
    assert ev.verdict('scratch-short', 0.1, 1) == better and ev.verdict('scratch-deep', -2, -0.1) == worse
    assert ev.verdict('scratch-deep', -1, 1) == 'no difference shown'


def test_scratch_evaluation_refuses_an_unknown_mode(monkeypatch):
    from scripts import neural_deep_cfr_scratch_eval as ev
    monkeypatch.setenv('DCFR_SCRATCH_EVAL', 'monitor-x')
    with pytest.raises(SystemExit):
        ev.mode()
