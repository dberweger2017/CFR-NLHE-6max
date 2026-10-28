import json

from scripts import openpoker_phantom_depth as study
from scripts import openpoker_short_mixed as short

GRID = (10, 15, 20, 30, 40, 50, 65, 80, 100, 125, 150, 200, 250)


def test_tables_follow_the_protocol():
    tables = {t['table']: t for t in short.tables()}
    assert list(tables) == [f'{n}p-{k}' for n in (3, 4, 5) for k in ('100bb', '50bb', '20bb', '200bb', 'unequal')]
    for n in (3, 4, 5):
        home = tables[f'{n}p-100bb']
        assert (home['study'], home['focals'], home['stacks_bb']) == ('home', [f'p{n}', f'p{n}mix'], None)
        assert list(home['fields']) == ['dedicated', 'mixed', 'pot-pressure', 'mixed-copies']
        assert home['fields']['dedicated'] == [f'p{n}'] * (n - 1)
        for k in ('50bb', '20bb', '200bb', 'unequal'):
            t = tables[f'{n}p-{k}']
            assert (t['study'], t['focals']) == ('depth', ['mix', f'p{n}mix'])
            assert list(t['fields']) == ['mixed', 'pot-pressure', 'tight-aggressive', 'mixed-copies']
    for t in tables.values():
        assert t['views'] == ['projected', 'projected']
        assert all(len(o) == t['players'] - 1 for o in t['fields'].values())
        # Mixture copies play natively, so every stack must be on the trained grid.
        assert all(s in GRID for s in (t['stacks_bb'] or [t['stack_bb']] * t['players']))


def test_verdicts_follow_the_rules():
    assert short.verdict('home', -9.9, 30) == 'mixed adequate at 100 BB'
    assert short.verdict('home', -40, -10.1) == 'mixed loses at 100 BB'
    assert short.verdict('home', -12, 5) == 'inconclusive'
    assert short.verdict('depth', 0.1, 9) == 'dedicated mixed better'
    assert short.verdict('depth', -9, -0.1) == 'six-player mixed better'
    assert short.verdict('depth', -1, 1) == 'no difference shown'


def test_manifests_use_their_own_roots(tmp_path, monkeypatch):
    monkeypatch.setattr(study, 'tables', short.tables)
    monkeypatch.setattr(study, 'ROOT', short.ROOT)
    models = {}
    for alias in ('mix', 'p3', 'p4', 'p5', 'p3mix', 'p4mix', 'p5mix'):
        path = tmp_path / f'{alias}.bin'
        path.write_bytes(alias.encode())
        models[alias] = {'path': str(path), 'sha256': study.sha(path), 'mass': str(tmp_path), 'mass_sha256': '0' * 64}
    spec = tmp_path / 'models.json'
    spec.write_text(json.dumps(models))

    class Args:
        out = tmp_path / 'out'
        models = spec
    study.manifest(Args)
    cases = sum(len(t['fields']) for t in short.tables())
    roots = set()
    for bank in range(study.BANKS):
        m = json.loads((Args.out / f'arena-manifest-b{bank}.json').read_text())
        assert len(m['cases']) == cases
        roots.update(c['root'] for c in m['cases'])
    assert len(roots) == cases * study.BANKS
