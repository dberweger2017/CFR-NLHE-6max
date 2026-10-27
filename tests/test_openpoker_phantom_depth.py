import json
from pathlib import Path

from scripts import openpoker_phantom_depth as study


def test_tables_follow_the_protocol():
    tables = {t['table']: t for t in study.tables()}
    assert list(tables) == ['3p', '4p', '5p', '50bb', '100bb', 'unequal']
    for n in (3, 4, 5):
        t = tables[f'{n}p']
        assert (t['players'], t['focals'], t['views']) == (n, [f'p{n}', 'six'], ['native', 'projected'])
        assert list(t['fields'])[0] == 'dedicated'
        assert all(len(o) == n - 1 for o in t['fields'].values())
    assert tables['50bb']['views'] == ['projected', 'native'] and tables['50bb']['fields']['trained'] == ['six50'] * 5
    assert tables['100bb']['views'] == ['native', 'projected'] and tables['100bb']['fields']['trained'] == ['six'] * 5
    unequal = tables['unequal']
    assert unequal['views'] == ['projected', 'projected'] and list(unequal['fields'])[0] == 'mixed'
    assert sorted(unequal['stacks_bb']) == [50, 75, 100, 100, 150, 200]


def test_verdicts_apply_the_margin_and_sign_rules():
    assert study.verdict('phantom', -9.9, 30) == 'phantom adequate'
    assert study.verdict('phantom', -40, -10.1) == 'dedicated needed'
    assert study.verdict('phantom', -12, 5) == 'inconclusive'
    assert study.verdict('depth', 0.1, 9) == '50 BB model better'
    assert study.verdict('depth', -9, -0.1) == '100 BB model better'
    assert study.verdict('depth', -1, 1) == 'no difference shown'


def test_manifests_pin_models_and_never_share_roots(tmp_path, monkeypatch):
    models = {}
    for alias in ('p3', 'p4', 'p5', 'six', 'six50'):
        path = tmp_path / f'{alias}.bin'
        path.write_bytes(alias.encode())
        models[alias] = {'path': str(path), 'sha256': study.sha(path), 'mass': str(tmp_path), 'mass_sha256': '0' * 64}
    spec = tmp_path / 'models.json'
    spec.write_text(json.dumps(models))

    class Args:
        out = tmp_path / 'out'
    Args.models = spec
    study.manifest(Args)
    roots, traces = set(), set()
    for bank in range(study.BANKS):
        m = json.loads((Args.out / f'arena-manifest-b{bank}.json').read_text())
        assert m['models'] == models and len(m['cases']) == 35
        for case in m['cases']:
            assert case['root'] not in roots
            roots.add(case['root'])
            traces.update(case['traces'])
            assert case['blocks'] == study.BLOCKS and len(case['opponents']) == case['players'] - 1
            assert all(o.startswith('bot=') or o in models for o in case['opponents'])
    assert len(traces) == 2 * 35 * study.BANKS
    models['six']['sha256'] = '0' * 64
    spec.write_text(json.dumps(models))
    Args.out = tmp_path / 'other'
    try:
        study.manifest(Args)
    except ValueError as error:
        assert 'six' in str(error)
    else:
        raise AssertionError('changed pin accepted')
