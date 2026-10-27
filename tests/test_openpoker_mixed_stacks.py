import json

from scripts import openpoker_mixed_stacks as mixed
from scripts import openpoker_phantom_depth as study

GRID = (10, 15, 20, 30, 40, 50, 65, 80, 100, 125, 150, 200, 250)


def test_tables_follow_the_protocol():
    tables = {t['table']: t for t in mixed.tables()}
    assert list(tables) == ['100bb', '50bb', '20bb', '200bb', 'unequal-a', 'unequal-b', 'unequal-4p']
    assert [t['study'] for t in tables.values()] == ['home'] + ['depth'] * 6
    for t in tables.values():
        assert (t['focals'], t['views']) == (['six', 'mix'], ['projected', 'projected'])
        assert all(len(o) == t['players'] - 1 for o in t['fields'].values())
        stacks = t['stacks_bb'] or [t['stack_bb']] * t['players']
        # A mixture field plays natively, so it only sits at tables its grid covers.
        if 'mix' in t['fields']:
            assert t['players'] == 6 and all(s in GRID for s in stacks)
    assert list(tables['100bb']['fields'])[0] == 'trained' and tables['100bb']['fields']['trained'] == ['six'] * 5
    assert list(tables['50bb']['fields'])[0] == 'trained' and tables['50bb']['fields']['trained'] == ['six50'] * 5
    for name in ('20bb', '200bb', 'unequal-a', 'unequal-b', 'unequal-4p'):
        assert list(tables[name]['fields'])[0] == 'mixed'


def test_verdicts_apply_the_margin_and_sign_rules():
    assert mixed.verdict('home', -9.9, 30) == 'mixed adequate at 100 BB'
    assert mixed.verdict('home', -40, -10.1) == 'mixed loses at 100 BB'
    assert mixed.verdict('home', -12, 5) == 'inconclusive'
    assert mixed.verdict('depth', 0.1, 9) == 'mixed better'
    assert mixed.verdict('depth', -9, -0.1) == 'fixed better'
    assert mixed.verdict('depth', -1, 1) == 'no difference shown'


def test_manifests_use_their_own_roots(tmp_path, monkeypatch):
    monkeypatch.setattr(study, 'tables', mixed.tables)
    monkeypatch.setattr(study, 'ROOT', mixed.ROOT)
    models = {}
    for alias in ('six', 'six50', 'mix'):
        path = tmp_path / f'{alias}.bin'
        path.write_bytes(alias.encode())
        models[alias] = {'path': str(path), 'sha256': study.sha(path), 'mass': str(tmp_path), 'mass_sha256': '0' * 64}
    spec = tmp_path / 'models.json'
    spec.write_text(json.dumps(models))

    class Args:
        out = tmp_path / 'out'
        models = spec
    study.manifest(Args)
    cases = sum(len(t['fields']) for t in mixed.tables())
    roots = set()
    for bank in range(study.BANKS):
        m = json.loads((Args.out / f'arena-manifest-b{bank}.json').read_text())
        assert len(m['cases']) == cases
        for case in m['cases']:
            assert case['focal_views'] == ['projected', 'projected']
            roots.add(case['root'])
    assert len(roots) == cases * study.BANKS
    # Disjoint from the phantom/depth study's roots.
    assert min(roots) >= mixed.ROOT and max(roots) < mixed.ROOT + 1000 * study.BANKS
    assert mixed.ROOT >= 20261027300000 + 1000 * study.BANKS
