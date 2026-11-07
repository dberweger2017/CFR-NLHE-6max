import json
from pathlib import Path

from scripts import openpoker_short_coverage as cov


def test_tables_follow_the_protocol():
    tables = {t['table']: t for t in cov.tables(['ctrl', 'eff'])}
    assert list(tables) == ['3p-5bb', '3p-short-deep', '3p-unequal', '4p-short-deep', '6p-5bb', '6p-short-deep', '6p-unequal']
    for t in tables.values():
        assert list(t['fields'])[0] == 'mixed' and t['focals'] == ['ctrl', 'eff']
        assert all(len(o) == t['players'] - 1 for o in t['fields'].values())
        assert ('live-copies' in t['fields']) == (t['players'] == 6)
    assert cov.verdict('coverage', 0.1, 5) == 'candidate better'
    assert cov.verdict('coverage', -5, -0.1) == 'widemix better'
    assert cov.verdict('coverage', -1, 1) == 'no difference shown'


def write_screen(root: Path, candidate, untrained):
    """Receipts where each arm's postflop decisions at a table are 100, `untrained[arm][table]` of them untrained."""
    receipts = root / candidate / 'out' / 'receipts'
    receipts.mkdir(parents=True)
    for t in cov.tables(['ctrl', candidate]):
        for field in t['fields']:
            for arm in ('a0', 'a1'):
                bad = untrained[arm].get(t['table'], 0) if field == 'mixed' else 0
                decisions = {'preflop|missing|x': [50, 0], 'flop|positive|x': [100 - bad, 0], 'flop|missing|x': [bad, 0]}
                (receipts / f"{arm}-{t['table']}-b0--{field}.json").write_text(json.dumps(
                    {'label': f"{arm}-{t['table']}-b0", 'field': field, 'decisions': decisions, 'fallback_violations': 0}))


def test_coverage_rule_needs_ten_points_and_every_six_player_table(tmp_path):
    six = ('6p-5bb', '6p-short-deep', '6p-unequal')
    ctrl = {t: 60 for t in six}
    # eff: 12 points better on the mixed field = 12/6 fields = 2 points pooled -> doesn't qualify.
    write_screen(tmp_path, 'eff', {'a0': ctrl, 'a1': {t: 48 for t in six}})
    # short: 60 points on mixed at each six-player table = 10 points pooled, exactly the bar -> qualifies.
    write_screen(tmp_path, 'short', {'a0': ctrl, 'a1': {t: 0 for t in six}})
    # effshort: better pooled but worse at one six-player table -> doesn't qualify.
    write_screen(tmp_path, 'effshort', {'a0': {**ctrl, '6p-unequal': 0}, 'a1': {'6p-5bb': 0, '6p-short-deep': 0, '6p-unequal': 1}})
    out = tmp_path / 'screen.json'

    class Args:
        screens, command = tmp_path, 'coverage'
    Args.out = out
    cov.coverage(Args)
    r = json.loads(out.read_text())
    assert [r['candidates'][c]['qualifies'] for c in cov.CANDIDATES] == [False, True, False]
    assert r['advance'] == 'short'
    assert r['candidates']['eff']['tables']['6p-5bb']['a0']['preflop'] == 100.0
