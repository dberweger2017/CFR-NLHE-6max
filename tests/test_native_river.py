"""Prepared native/reference semantics; these are not live search matches."""
from copy import deepcopy
import json
import numpy as np
import pytest

from scripts.benchmark_native_river import fixture, qualify
from src.blueprint.native_river import BINARY, NativeRiver, prepared_request, profiles
from src.blueprint.river_cfr import RiverCFR, profile_quality

native = pytest.mark.skipif(not BINARY.is_file(), reason='build --example river_prepared')


def test_first_divergent_row_has_exactly_zero_rational_regrets():
    from scripts.diagnose_river_numerics import exact_first_sweep_row
    game,ranges=fixture(2)
    assert exact_first_sweep_row(game,ranges,9,2)==['0','0']


def test_adapter_refuses_correlated_law_even_when_label_is_unchanged():
    game, ranges = fixture()
    original = game.joint.copy()
    supported = np.argwhere(original > 0)
    a, b = supported[0], supported[-1]
    delta = min(original[tuple(a)], original[tuple(b)])/2
    game.joint[tuple(a)] -= delta; game.joint[tuple(b)] += delta
    with pytest.raises(ValueError, match='product-compatible'):
        prepared_request(game, ranges, 1)


@native
def test_native_dense_values_accumulators_quality_and_fixed_work():
    game, ranges = fixture()
    with NativeRiver() as worker:
        receipt = qualify(worker, game, ranges, [1,16,64])
    assert receipt['leaf_max_absolute_error_bb'] < 1e-10
    assert all(r['deterministic_repetitions']==3 for r in receipt['records'])


@native
def test_fixed_policy_matches_reference_and_normalized_average():
    game, ranges = fixture(1)
    fixed = {}
    for node in game.nodes:
        if node.actor is not None:
            row = np.zeros((len(game.holdings[game.seats.index(node.actor)]), len(node.menu)))
            row[:,0] = 1
            fixed[node.id] = row
            break
    with NativeRiver() as worker:
        result = worker.solve(prepared_request(game,ranges,2,fixed_profile=fixed))
    reference = RiverCFR(game,fixed_profile=fixed)
    expected = reference.solve(max_sweeps=2)
    for node,p in profiles(game,result['average']).items():
        np.testing.assert_allclose(p,expected.average[node],atol=1e-10,rtol=1e-10)
    assert result['quality']['exploitability_bb']==pytest.approx(profile_quality(game,expected.average)['exploitability_bb'],abs=1e-10)


@native
def test_scalar_review_control_agrees_under_identical_supplied_profiles():
    game, ranges = fixture(2)
    reference = RiverCFR(game).solve(max_sweeps=16)
    request = prepared_request(game,ranges,2,fixed_profile=reference.average)
    with NativeRiver() as worker:
        linear = worker.solve(request)
        scalar = worker.solve(dict(request,scalar_control=True))
    assert scalar['leaf_evaluation_mode'] == 'scalar-review-control'
    for field in ('last_deltas','average_numer','average_denom'):
        for a,b in zip(linear[field],scalar[field]):
            np.testing.assert_allclose(a,b,rtol=1e-10,atol=1e-10)
    assert scalar['quality']['exploitability_bb'] == pytest.approx(linear['quality']['exploitability_bb'],abs=1e-10)


@native
def test_error_response_does_not_corrupt_persistent_worker():
    game,ranges=fixture();request=prepared_request(game,ranges,1)
    with NativeRiver() as worker:
        pid=worker.process.pid
        bad=deepcopy(request);bad['opponent_actual_cards']=[1,2]
        with pytest.raises(ValueError,match='unexpected field'):
            worker.solve(bad)
        worker.process.stdin.write('{broken json}\n');worker.process.stdin.flush()
        assert json.loads(worker.process.stdout.readline())['status']=='error'
        first=worker.solve(request);second=worker.solve(request)
        assert worker.process.pid==pid
        assert first['average']==second['average']
        assert first['regrets']==second['regrets']


@native
@pytest.mark.parametrize('mutation', ['board','range','weight','cycle','actor','sweeps','fixed'])
def test_invalid_prepared_request_is_refused(mutation):
    game,ranges=fixture();request=prepared_request(game,ranges,1)
    if mutation=='board':request['game']['board'][1]=request['game']['board'][0]
    if mutation=='range':request['game']['ranges'][0].append(request['game']['ranges'][0][0])
    if mutation=='weight':request['game']['ranges'][0][0][2]=-1
    if mutation=='cycle':request['game']['nodes'][0]['children'][0]=0
    if mutation=='actor':request['game']['nodes'][0]['actor']=2
    if mutation=='sweeps':request['sweeps']=0
    if mutation=='fixed':request['fixed']={'0':[0.2]}
    with NativeRiver() as worker:
        with pytest.raises(ValueError):worker.solve(request)


@pytest.mark.parametrize('case',[0,1,4,5])
def test_prepared_terminal_ledgers_match_independent_native_settlement(case):
    from src.arena.endgame_quality import _world
    from src.game.observation import ActionTaken, HandFinished
    from src.game.showdown import hand_value
    game,ranges=fixture(case,dead_money=True)
    root=game.nodes[0].history
    first,second=game.seats
    for node in game.nodes:
        if node.terminal is None:continue
        for a in game.holdings[0]:
            for b in game.holdings[1]:
                if set(a)&set(b):continue
                hand=_world(root,game.board,{first:a,second:b})
                for event in node.history[len(root):]:
                    if isinstance(event,ActionTaken):hand=hand.apply(event.action)
                finish=next(e for e in hand.events if isinstance(e,HandFinished))
                expected=(finish.stacks[first]-game.root_stacks[first]-game.root_pot/2)/game.big_blind
                ra,rb=hand_value(a+game.board),hand_value(b+game.board)
                t=node.terminal
                actual=t.base+t.win0*(ra>rb)+t.tie0*(ra==rb)
                assert actual==pytest.approx(expected,abs=1e-11)
