import json

from scripts import neural_policy_everywhere as everywhere
from scripts import nplayer_loss_diagnosis as diagnosis


def test_tables_put_the_live_client_against_the_network_everywhere():
    tables = everywhere.tables(3)
    short = [t for t in tables if t['study'] == 'short']
    assert [t['table'] for t in short] == ['3p-5bb', '3p-short-deep', '3p-unequal', '4p-short-deep', '6p-5bb', '6p-short-deep', '6p-unequal']
    for t in short:
        assert t['focals'] == ['widemix', 'widemix'] and t['views'] == ['projected', 'projected']
        assert t['fallback'] == ['network:net1', 'network-all:net3']
        assert list(t['fields'])[0] == 'mixed'
        assert t['fields'].get('live-copies') == (['live:widemix:net1'] * 5 if t['players'] == 6 else None)
    deep = [t for t in tables if t['study'] == 'deep']
    assert len(deep) == 1 and deep[0]['table'] == '6p-100bb' and deep[0]['stacks_bb'] is None
    assert deep[0]['focals'] == ['six', 'six'] and deep[0]['views'] == ['native', 'native']
    assert deep[0]['fallback'] == ['uniform', 'network-all:net3'] and deep[0]['fields']['trained'] == ['peer'] * 5
    assert list(deep[0]['fields'])[0] == 'trained' and 'check-call' in deep[0]['fields']


def test_verdicts_follow_the_protocol():
    v = everywhere.verdict
    assert v('short', 0.1, 2) == 'network better' and v('short', -2, -0.1) == 'table better' and v('short', -1, 1) == 'no difference shown'
    assert v('deep', -9.9, 5) == 'non-inferior' and v('deep', -30, -10.1) == 'inferior' and v('deep', -12, 3) == 'non-inferiority not shown'


def results(tmp_path, name, short_points, deep_point, deep_verdict='non-inferior', harm=None, check_call_harm=False):
    tables = {}
    for t, (point, verdict) in short_points.items():
        tables[t] = {'study': 'short', 'primary': 'mixed', 'fields': {
            'mixed': {'change': {'adjusted': {'mean_bb100': point}}, 'decision_interval': [point - 1, point + 1], 'verdict': verdict},
            'random': {'harm_flag': harm == t}}}
    tables['6p-100bb'] = {'study': 'deep', 'primary': 'trained', 'fields': {
        'trained': {'change': {'adjusted': {'mean_bb100': deep_point}}, 'decision_interval': [deep_point - 5, deep_point + 5], 'verdict': deep_verdict},
        'check-call': {'harm_flag': check_call_harm}, 'random': {'harm_flag': False}}}
    path = tmp_path / f'{name}.json'
    path.write_text(json.dumps({'tables': tables}))
    return path


def test_gates_need_a_replicated_win_no_loss_and_no_harm(tmp_path):
    win = {'a': (2, 'network better'), 'b': (0.5, 'no difference shown')}
    r1 = results(tmp_path, 'r1', win, -3, check_call_harm=True)
    r2 = results(tmp_path, 'r2', {'a': (1, ''), 'b': (-1, '')}, -8)
    r3 = results(tmp_path, 'r3', {'a': (0.2, ''), 'b': (0, '')}, -2)
    d = everywhere.decide([r1, r2, r3])
    assert d['gate_s']['passed'] and d['gate_s']['tables']['a']['replicates'] and not d['gate_s']['tables']['b']['replicates']
    assert d['gate_d']['passed'] and d['gate_d']['check_call_harm_flag'], 'check-call is exempt at 100 BB'
    r3 = results(tmp_path, 'r3b', {'a': (-0.1, ''), 'b': (0, '')}, -11)
    d = everywhere.decide([r1, r2, r3])
    assert not d['gate_s']['passed'] and not d['gate_d']['passed']
    lose = results(tmp_path, 'r1c', {'a': (2, 'network better'), 'b': (-3, 'table better')}, -3, harm='a')
    d = everywhere.decide([lose, r2, results(tmp_path, 'r3c', {'a': (1, ''), 'b': (0, '')}, -2)])
    assert not d['gate_s']['passed'] and d['gate_s']['tables']['a']['harm'] == ['random']


def row(status, action, check, network=None, row_p=None, actor=0, key='network'):
    lookup = {'status': status}
    if network is not None:
        lookup[key] = network
    if row_p is not None:
        lookup['row'] = row_p
    return {'actors': [actor], 'actions': [action], 'states': [{'legal': {'check': check}}], 'lookups': [lookup]}


def test_network_everywhere_records_the_network_at_every_focal_decision():
    mode, p, r = 'network-all:net2', [0, 0.5, 0, 0.5, 0, 0], [0, 1, 0, 0, 0, 0]
    v = diagnosis.fallback_violations
    assert v(row('positive_mass', ['check', 0], True, {'p': p, 'label': 1}, r), 0, mode) == 0
    assert v(row('missing', ['raise', 400], True, {'p': p, 'label': 3}), 0, mode) == 0
    assert v(row('positive_mass', ['check', 0], True, {'p': p, 'label': 1}), 0, mode) == 1, 'trained row unrecorded'
    assert v(row('missing', ['check', 0], True, {'p': p, 'label': 1}, r), 0, mode) == 1, 'row at an untrained row'
    assert v(row('positive_mass', ['check', 0], True, None, r), 0, mode) == 1, 'no network'
    assert v(row('positive_mass', ['check', 0], True, {'p': p, 'label': 1}, r, actor=1), 0, mode) == 2, 'not the focal'


def test_live_copies_play_the_network_only_at_their_untrained_rows():
    p = [0, 0.5, 0, 0.5, 0, 0]
    v = diagnosis.fallback_violations
    for mode in ('network:net1', 'network-all:net1', 'uniform'):
        assert v(row('missing', ['check', 0], True, {'p': p, 'label': 1}, actor=1, key='copy_network'), 0, mode) == 0
        assert v(row('positive_mass', ['check', 0], True, {'p': p, 'label': 1}, actor=1, key='copy_network'), 0, mode) == 1
        assert v(row('missing', ['call', 0], True, {'p': p, 'label': 2}, actor=1, key='copy_network'), 0, mode) == 1
