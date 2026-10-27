import json

from scripts import openpoker_heads_up as hu
from scripts import openpoker_phantom_depth as study


def test_tables_follow_the_protocol():
    tables = {t['table']: t for t in hu.tables()}
    assert list(tables) == ['100bb', '50bb', '20bb', '200bb', 'unequal-a', 'unequal-b']
    assert [t['study'] for t in tables.values()] == ['home'] + ['depth'] * 5
    assert tables['100bb']['fields']['trained'] == ['hu100']
    for name, t in tables.items():
        assert (t['players'], t['focals'], t['views']) == (2, ['hu100', 'humix'], ['projected', 'projected'])
        assert list(t['fields'])[0] == 'trained' and all(len(o) == 1 for o in t['fields'].values())
        # The fixed model plays natively only at its own 100 BB, so it is a field only there.
        if name != '100bb':
            assert t['fields']['trained'] == ['humix'] and 'hu100' not in t['fields']
    assert list(tables['100bb']['fields'])[:2] == ['trained', 'humix']
    assert sorted(tables['unequal-b']['stacks_bb']) == [100, 250]


def test_manifests_use_their_own_roots(tmp_path, monkeypatch):
    monkeypatch.setattr(study, 'tables', hu.tables)
    monkeypatch.setattr(study, 'ROOT', hu.ROOT)
    models = {}
    for alias in ('hu100', 'humix'):
        path = tmp_path / f'{alias}.bin'
        path.write_bytes(alias.encode())
        models[alias] = {'path': str(path), 'sha256': study.sha(path), 'mass': str(tmp_path), 'mass_sha256': '0' * 64}
    spec = tmp_path / 'models.json'
    spec.write_text(json.dumps(models))

    class Args:
        out = tmp_path / 'out'
        models = spec
    study.manifest(Args)
    cases = sum(len(t['fields']) for t in hu.tables())
    roots = set()
    for bank in range(study.BANKS):
        m = json.loads((Args.out / f'arena-manifest-b{bank}.json').read_text())
        assert len(m['cases']) == cases and all(c['players'] == 2 for c in m['cases'])
        roots.update(c['root'] for c in m['cases'])
    assert len(roots) == cases * study.BANKS
    assert min(roots) >= hu.ROOT and hu.ROOT >= 20261027700000 + 1000 * study.BANKS
