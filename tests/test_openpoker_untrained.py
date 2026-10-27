import json

from scripts import openpoker_phantom_depth as study
from scripts import openpoker_untrained as untrained

GRID = (10, 15, 20, 30, 40, 50, 65, 80, 100, 125, 150, 200, 250)


def test_tables_follow_the_protocol():
    tables = {t['table']: t for t in untrained.tables()}
    names = ['100bb', '50bb', 'unequal', 'deep-outlier']
    assert list(tables) == [f'{n}-{c}' for c in ('no-all-in', 'no-raise') for n in names]
    for t in tables.values():
        assert (t['players'], t['focals'], t['views']) == (6, ['mix', 'mix'], ['projected', 'projected'])
        assert t['fallback'] == ['uniform', t['study']] and t['study'] in untrained.CANDIDATES
        assert list(t['fields'])[0] == 'mixed' and all(len(o) == 5 for o in t['fields'].values())
        # Mixture copies play natively, so only where every stack is on the trained grid.
        assert ('mix' in t['fields']) == all(s in GRID for s in t['stacks_bb'])
    assert tables['deep-outlier-no-raise']['stacks_bb'] == [100, 2000, 100, 125, 150, 80]


def test_verdicts_follow_the_sign_rule():
    assert untrained.verdict('no-all-in', 0.1, 9) == 'candidate better'
    assert untrained.verdict('no-raise', -9, -0.1) == 'uniform better'
    assert untrained.verdict('no-all-in', -1, 1) == 'no difference shown'


def test_manifests_declare_each_arms_fallback_on_their_own_roots(tmp_path, monkeypatch):
    monkeypatch.setattr(study, 'tables', untrained.tables)
    monkeypatch.setattr(study, 'ROOT', untrained.ROOT)
    path = tmp_path / 'mix.bin'
    path.write_bytes(b'mix')
    spec = tmp_path / 'models.json'
    spec.write_text(json.dumps({'mix': {'path': str(path), 'sha256': study.sha(path), 'mass': str(tmp_path), 'mass_sha256': '0' * 64}}))

    class Args:
        out = tmp_path / 'out'
        models = spec
    study.manifest(Args)
    cases = sum(len(t['fields']) for t in untrained.tables())
    roots = set()
    for bank in range(study.BANKS):
        m = json.loads((Args.out / f'arena-manifest-b{bank}.json').read_text())
        assert len(m['cases']) == cases
        assert {tuple(c['focal_untrained_fallback']) for c in m['cases']} == {('uniform', 'no-all-in'), ('uniform', 'no-raise')}
        roots.update(c['root'] for c in m['cases'])
    assert len(roots) == cases * study.BANKS
