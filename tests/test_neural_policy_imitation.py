import json
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import neural_policy_imitation as imitation
from scripts import neural_policy_samples as nps

FEATURES = 8


def write(path, job, n, rng, rescue_share=0.0):
    """Synthetic samples: feature 0 decides which of two legal labels teacher 0 prefers."""
    d = nps.dtype(2, FEATURES)
    header = {'format': nps.FORMAT, 'layout_sha256': 'ab' * 32, 'feature_count': FEATURES, 'record_bytes': d.itemsize,
              'teachers': [{'alias': 't0'}, {'alias': 't1'}], 'job': {'name': job}}
    r = np.zeros(n, d)
    r['hand'] = np.arange(n) // 2
    r['players'] = 6
    r['street'] = rng.integers(0, 4, n)
    r['legal_mask'] = 0b000110  # check and call
    bit = rng.integers(0, 2, n)
    r['features'][:, 0] = bit * 255
    r['features'][:, 1:] = rng.integers(0, 256, (n, FEATURES - 1))
    prefer = np.where(bit[:, None] == 1, [0, 0.9, 0.1, 0, 0, 0], [0, 0.1, 0.9, 0, 0, 0])
    q = (prefer * 65535).round().astype(np.uint16)
    rescue = rng.random(n) < rescue_share
    r['t0_status'] = np.where(rescue, nps.MISSING, nps.POSITIVE)
    r['t0_p'] = np.where(rescue[:, None], 0, q)
    r['t1_status'] = nps.POSITIVE
    r['t1_p'] = q
    h = json.dumps(header).encode()
    with open(path, 'wb') as f:
        f.write(nps.MAGIC + len(h).to_bytes(8, 'little') + h + r.tobytes())


def test_tv_uniform_and_cluster_interval():
    mask = np.array([[False, True, True, False, False, False]])
    assert imitation.uniform(mask).tolist() == [[0, 0.5, 0.5, 0, 0, 0]]
    assert imitation.tv(np.array([[0, 1.0, 0, 0, 0, 0]]), imitation.uniform(mask))[0] == pytest.approx(0.5)
    values = np.array([1.0, 3.0, 2.0, 2.0])
    r = imitation.interval(values, np.array([0, 0, 1, 1]))
    assert r['clusters'] == 2 and r['hand_mean'] == pytest.approx(2.0) and r['lower95'] <= 2.0 <= r['upper95']


def test_a_tiny_network_learns_and_beats_uniform_on_rescued_spots(tmp_path):
    pytest.importorskip('torch')
    rng = np.random.default_rng(0)
    write(tmp_path / 'train.npfeat', 'wide-6p-self', 4000, rng)
    write(tmp_path / 'test.npfeat', 'wide-6p-self', 2000, rng, rescue_share=0.5)
    out = tmp_path / 'model'
    meta = imitation.train(SimpleNamespace(data=[str(tmp_path / 'train.npfeat')], seed=1, out=str(out)),
                           hidden=(16,), epochs=40, batch=64)
    assert meta['samples'] == 4000 and meta['history'][-1]['loss'] < meta['history'][0]['loss']
    results = tmp_path / 'r.json'
    r = imitation.evaluate(SimpleNamespace(model=str(out), data=[str(tmp_path / 'test.npfeat')], out=str(results)))
    primary = r['measures']['rescue/primary']
    # Uniform is 0.4 TV from the 0.9/0.1 target; a network that learned the bit is near 0.
    assert primary['upper95'] < imitation.MARGIN
    assert r['measures']['fidelity_net/wide']['mean'] < 0.1
    verdict = imitation.decide(SimpleNamespace(results=[str(results)]))
    assert verdict['passes']
