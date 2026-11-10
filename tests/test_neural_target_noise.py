import json

import numpy as np

from scripts import neural_target_noise as noise


def rows(n_deals, k, signal_sd, noise_sd, seed=0, legal=0b000111):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n_deals):
        mean = np.zeros(6)
        mean[:3] = rng.normal(0, signal_sd, 3)
        r = np.zeros((k, 6))
        r[:, :3] = mean[:3] + rng.normal(0, noise_sd, (k, 3))
        out.append({'deal': i, 'players': 3 + i % 4, 'street': 1, 'legal': legal, 'regrets': r.tolist(), 'nodes': [10] * k})
    return out


def test_noise_and_signal_recover_known_variances():
    s = noise.stats(rows(3000, 8, signal_sd=4.0, noise_sd=10.0))
    # Three legal labels: noise 3 * 100, signal 3 * 16.
    assert abs(s['noise_mse'] - 300) < 15
    assert abs(s['signal_variance'] - 48) < 12
    assert abs(s['noise_share'] - 300 / 348) < 0.03


def test_noiseless_targets_agree_with_their_mean():
    s = noise.stats(rows(200, 4, signal_sd=5.0, noise_sd=0.0))
    assert s['noise_mse'] == 0 and s['tv_one_sample_to_mean'] == 0 and s['sign_agreement'] == 1


def test_regret_matching_matches_the_engine_rule():
    mask = np.array([True, True, True, False, False, False])
    r = np.array([[1., 3., -1., 9., 0., 0.], [-2., -1., -3., 5., 0., 0.]])
    rm = noise.regret_match(r, mask)
    assert np.allclose(rm[0], [0.25, 0.75, 0, 0, 0, 0])
    assert np.allclose(rm[1], [0, 1, 0, 0, 0, 0])


def test_summary_reads_runs_and_their_metadata(tmp_path):
    path = tmp_path / 'late-s1.jsonl'
    path.write_text('\n'.join(json.dumps(r) for r in rows(50, 4, 3.0, 2.0)) + '\n')
    (tmp_path / 'late-s1.json').write_text(json.dumps({'street': 1, 'reached': 50}))
    noise.main(['summary', '--runs', str(path), '--out', str(tmp_path / 'report.json')])
    rep = json.loads((tmp_path / 'report.json').read_text())
    assert rep['runs'][0]['meta']['street'] == 1 and rep['runs'][0]['all']['deals'] == 50
    assert set(rep['runs'][0]['by_players']) == {'3', '4', '5', '6'}
