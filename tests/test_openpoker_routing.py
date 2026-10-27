import json

from scripts import openpoker_phantom_depth as study
from scripts import openpoker_routing as routing

GRID = (10, 15, 20, 30, 40, 50, 65, 80, 100, 125, 150, 200, 250)


def test_tables_follow_the_protocol():
    tables = {t['table']: t for t in routing.tables()}
    band = ['65bb', '80bb', '125bb', '150bb', 'near-100']
    short = [f'{n}p-{k}' for n in (3, 4, 5) for k in ('100bb', '50bb', 'unequal')]
    assert list(tables) == band + short
    for name in band:
        t = tables[name]
        assert (t['study'], t['players'], t['focals']) == ('band', 6, ['six', 'mix'])
        assert list(t['fields']) == ['mixed', 'mix', 'pot-pressure', 'tight-aggressive']
    for n in (3, 4, 5):
        home = tables[f'{n}p-100bb']
        assert (home['study'], home['players'], home['focals'], home['stacks_bb']) == ('short', n, [f'p{n}', 'mix'], None)
        assert list(home['fields'])[0] == 'dedicated' and home['fields']['dedicated'] == [f'p{n}'] * (n - 1)
        assert tables[f'{n}p-50bb']['stacks_bb'] == [50] * n
        assert list(tables[f'{n}p-unequal']['fields'])[0] == 'mixed'
    for t in tables.values():
        assert t['views'] == ['projected', 'projected']
        assert all(len(o) == t['players'] - 1 for o in t['fields'].values())
        stacks = t['stacks_bb'] or [t['stack_bb']] * t['players']
        assert all(s in GRID for s in stacks)
        # Mixture fields play natively, so only at six-player tables.
        assert 'mix' not in t['fields'] or t['players'] == 6


def test_verdicts_follow_the_sign_rule():
    assert routing.verdict('band', 0.1, 9) == 'mixed better'
    assert routing.verdict('short', -9, -0.1) == 'fixed better'
    assert routing.verdict('band', -1, 1) == 'no difference shown'


def test_manifests_use_their_own_roots(tmp_path, monkeypatch):
    monkeypatch.setattr(study, 'tables', routing.tables)
    monkeypatch.setattr(study, 'ROOT', routing.ROOT)
    models = {}
    for alias in ('six', 'mix', 'p3', 'p4', 'p5'):
        path = tmp_path / f'{alias}.bin'
        path.write_bytes(alias.encode())
        models[alias] = {'path': str(path), 'sha256': study.sha(path), 'mass': str(tmp_path), 'mass_sha256': '0' * 64}
    spec = tmp_path / 'models.json'
    spec.write_text(json.dumps(models))

    class Args:
        out = tmp_path / 'out'
        models = spec
    study.manifest(Args)
    cases = sum(len(t['fields']) for t in routing.tables())
    roots = set()
    for bank in range(study.BANKS):
        m = json.loads((Args.out / f'arena-manifest-b{bank}.json').read_text())
        assert len(m['cases']) == cases
        roots.update(c['root'] for c in m['cases'])
    assert len(roots) == cases * study.BANKS
    # Disjoint from the phantom/depth (…300000) and mixed-stack (…600000) studies' roots.
    assert min(roots) >= routing.ROOT and max(roots) < routing.ROOT + 1000 * study.BANKS
    assert routing.ROOT >= 20261027600000 + 1000 * study.BANKS
