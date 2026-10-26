"""Check statistical units and failure boundaries of the saved-trace diagnosis."""
import hashlib
import importlib.util
import json
from pathlib import Path
import pytest

SPEC = importlib.util.spec_from_file_location('bb100_diagnosis', Path(__file__).parents[1]/'docs/reports/nplayer-bb100-diagnosis/analyze.py')
d = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(d)


def fixture_trace(path, mutate=None):
    header = dict(policies=[dict(sha256=d.BASELINE)]+[dict(script='random', version='nplayer-scripts-v1')]*2,
                  seed=99, identity=dict(stacks=[10000]*3, big_blind=100,
                  schema='nplayer-button-live-actor-history-equity-k50-v1'), hands=12, blocks=2)
    rows = []
    for b in range(2):
        for p, ids in enumerate(d.PERMUTATIONS):
            seat = ids.index(0)
            rewards = [-50, -50, -50]
            rewards[seat] = 100
            state = dict(actor=seat, legal=dict(check=True, call=0, raise_to=None),
                         players=[[10000, 0, 0, False]]*3, street='preflop')
            row = dict(hand=b*6+p, block=b, permutation=p, identities=ids, button=b,
                       bb=100, rewards=rewards, deck=list(range(52)), states=[state, dict(players=state['players'])],
                       actions=[['check', 0]], actors=[seat], history=[['preflop', seat, 'check', 0, 0]],
                       settlement=dict(pots=[[150, 7]]))
            if mutate:
                mutate(row)
            rows.append(row)
    path.write_text('\n'.join(json.dumps(x) for x in [header]+rows)+'\n')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_duplicate_blocks_and_singleton_seat_mapping(tmp_path):
    path=tmp_path/'trace.jsonl'; sha=fixture_trace(path)
    r=d.scan(path, sha, 'random', 99)
    assert r['blocks']==[100, 100]
    assert r['seats']==[[100, 100]]*3
    assert r['positions']==[[100, 100]]*3
    assert sum(g['sum_bb100'] for k,g in r['groups'].items() if k.startswith('path|'))==1200
    assert r['decisions']==[12, 0, 0, 0]
    assert r['off_menu_actions']==0


@pytest.mark.parametrize('mutate', [
    lambda r:r.update(rewards=[0, 0, 1]),
    lambda r:r.update(permutation=5),
    lambda r:r.update(identities=[0, 1, 2]),
    lambda r:r.update(deck=list(reversed(range(52)))) if r['permutation']==1 else None,
    lambda r:r.update(actions=[]),
])
def test_corrupt_accounting_or_duplicate_refuses(tmp_path, mutate):
    path=tmp_path/'trace.jsonl'; sha=fixture_trace(path, mutate)
    with pytest.raises(ValueError):d.scan(path, sha, 'random', 99)


def test_wrong_checksum_refuses(tmp_path):
    path=tmp_path/'trace.jsonl';fixture_trace(path)
    with pytest.raises(ValueError, match='checksum'):d.scan(path, '0'*64, 'random', 99)


def test_menu_uses_raise_to_and_conditional_jam():
    s=dict(actor=0, legal=dict(check=False, call=100, raise_to=[200, 10000]),
           players=[[10000, 0, 0, False], [9950, 50, 50, False], [9900, 100, 100, False]])
    assert d.allowed_actions(s)=={('fold',0), ('call',0), ('raise',200), ('raise',350)}
    s['legal']['raise_to']=[200, 500]
    assert ('raise',500) in d.allowed_actions(s)


def test_block_interval_and_family_width():
    pytest.importorskip('scipy')
    r=d.interval([1, 2, 3, 4]); f=d.interval([1, 2, 3, 4], 4)
    assert r['mean_bb100']==2.5 and r['blocks']==4
    assert f['lower']<r['lower']<2.5<r['upper']<f['upper']


def test_truncated_trace_refuses_even_with_matching_new_checksum(tmp_path):
    path=tmp_path/'trace.jsonl';fixture_trace(path)
    path.write_text('\n'.join(path.read_text().splitlines()[:-1])+'\n')
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match='incomplete trace'):d.scan(path, sha, 'random', 99)


def test_wrong_model_identity_refuses(tmp_path):
    path=tmp_path/'trace.jsonl';fixture_trace(path)
    lines=path.read_text().splitlines();header=json.loads(lines[0]);header['policies'][0]['sha256']='0'*64
    lines[0]=json.dumps(header);path.write_text('\n'.join(lines)+'\n')
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match='identity mismatch'):d.scan(path, sha, 'random', 99)
