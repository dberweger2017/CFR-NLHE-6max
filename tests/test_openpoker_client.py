import asyncio
import json
from collections import Counter

import pytest

from src.openpoker.agent import Agent, Route, parse_routes
from src.openpoker.sandbox import Table, native_action, valid_actions
from src.openpoker.tracker import Hand, Unsupported, legal_expectation, server_action
from src.play_api.native_decisions import BINARY, NativeDecisions

native_only = pytest.mark.skipif(not BINARY.is_file(), reason='needs the release nplayer_serve example')
ALLOWED_FALLBACKS = ('possible all-in blind',)
TOKEN = 'sandbox-secret-7f3a91'


@pytest.fixture(scope='module')
def native():
    service = NativeDecisions()
    yield service
    service.close()


def scripted_routes(agent='script:random'):
    return {n: Route(agent) for n in range(2, 7)}


async def play(table, agent, hands):
    """Feeds the sandbox's messages to a tracker exactly as the client does."""
    records, state = [], {}

    async def send(message):
        kind = message['type']
        if kind == 'hand_start':
            state['hand'] = Hand.start(message)
        elif kind == 'hole_cards':
            state['hand'].hole_cards(message)
        elif kind == 'community_cards':
            state['hand'].community_cards(message)
        elif kind == 'player_action':
            state['hand'].player_action(message)

    async def act(turn):
        action, record = agent.decide(state['hand'], turn)
        records.append(record)
        return action

    for _ in range(hands):
        if not await table.hand(send, act):
            break
    return records


@native_only
def test_sandbox_hands_reconstruct_exactly_for_every_table_shape(native):
    shapes = [
        {0: ['script:check-call', 2000], 2: ['bot', 2000]},
        {1: ['script:pot-pressure', 1500], 3: ['bot', 2600], 4: ['script:random', 900]},
        {0: ['script:tight-aggressive', 2000], 2: ['bot', 2000], 3: ['script:pot-pressure', 1200], 5: ['script:check-call', 5000]},
        {0: ['script:random', 1000], 1: ['bot', 2000], 2: ['script:pot-pressure', 3000], 4: ['script:check-call', 400],
         5: ['script:random', 2500]},
        {s: [('bot' if s == 4 else 'script:random'), 2000 + 300 * s] for s in range(6)},
    ]
    statuses, reasons = Counter(), Counter()
    for k, seats in enumerate(shapes):
        bot = next(s for s, v in seats.items() if v[0] == 'bot')
        table = Table(native, {s: list(v) for s, v in seats.items()}, bot, seed=100 + k)
        agent = Agent(native, scripted_routes(), seed=k)
        records = asyncio.run(play(table, agent, 150))
        assert table.violations == 0
        for r in records:
            statuses[r['status']] += 1
            if r['status'] == 'fallback':
                reasons[r['reason'].split(' at ')[0]] += 1
    assert statuses['policy'] > 500
    assert set(reasons) <= set(ALLOWED_FALLBACKS), reasons


@native_only
def test_unrouted_counts_and_engine_disagreement_fall_back(native):
    table = Table(native, {0: ['script:check-call', 2000], 2: ['bot', 2000], 3: ['script:check-call', 2000]}, 2, seed=5)
    records = asyncio.run(play(table, Agent(native, {}, seed=1), 5))
    assert records and all(r['status'] == 'fallback' and r['reason'] == 'no route for 3 players' for r in records)

    # A legal set the engine doesn't reproduce (here, a raise minimum one chip high) means the
    # record and the server disagree; the decision must not reach a policy.
    corrupted = []

    class Corrupt(Agent):
        def decide(self, hand, turn):
            turn = json.loads(json.dumps(turn))
            for a in turn['valid_actions']:
                if a['action'] == 'raise' and a['min'] < a['max']:
                    a['min'] += 1
                    corrupted.append(True)
                    break
            else:
                corrupted.append(False)
            return super().decide(hand, turn)
    table = Table(native, {0: ['script:check-call', 2000], 2: ['bot', 2000], 3: ['script:check-call', 2000]}, 2, seed=5)
    records = asyncio.run(play(table, Corrupt(native, scripted_routes(), seed=1), 20))
    assert sum(corrupted) > 10
    assert all((r['status'] == 'fallback' and 'engine parity' in r['reason']) == c for r, c in zip(records, corrupted))


def test_translation_is_exact_and_refuses_unoffered_or_fractional_raises():
    valid = [{'action': 'fold'}, {'action': 'call', 'amount': 40}, {'action': 'raise', 'min': 100, 'max': 1980}]
    assert legal_expectation(valid) == {'check': False, 'call': 200, 'raise_to': [500, 9900]}
    assert server_action(['raise', 1500], valid) == {'action': 'raise', 'amount': 300}
    assert server_action(['call', 0], valid) == {'action': 'call'}
    for bad in (['raise', 1501], ['raise', 400], ['check', 0]):
        with pytest.raises(Unsupported):
            server_action(bad, valid)
    short = [{'action': 'fold'}, {'action': 'call', 'amount': 40}, {'action': 'all_in', 'amount': 55}]
    assert legal_expectation(short, hero_total=55) == {'check': False, 'call': 200, 'raise_to': [275, 275]}
    assert server_action(['raise', 275], short) == {'action': 'all_in'}
    legal = {'check': False, 'call': 200, 'raise_to': [500, 9900]}
    assert native_action({'action': 'raise', 'amount': 300}, legal) == ['raise', 1500]
    assert valid_actions(legal) == valid


def test_hand_messages_outside_the_contract_are_unsupported():
    with pytest.raises(Unsupported):
        Hand.start({'hand_id': 'h', 'seat': 1, 'dealer_seat': 0, 'blinds': {'small_blind': 25, 'big_blind': 50}})
    hand = Hand.start({'hand_id': 'h', 'seat': 1, 'dealer_seat': 0, 'blinds': {'small_blind': 10, 'big_blind': 20}})
    with pytest.raises(Unsupported):
        hand.player_action({'seat': 3, 'action': 'raise', 'amount': 60, 'street': 'preflop'})
    with pytest.raises(Unsupported):
        hand.player_action({'seat': 3, 'action': 'straddle', 'street': 'preflop', 'contribution_delta': 40})
    assert parse_routes({'6': {'agent': 'policy:six'}, '4': {'agent': 'policy:six', 'view': 'projected'}})[4] == Route('policy:six', 'projected')
    with pytest.raises(ValueError):
        parse_routes({'7': {'agent': 'policy:six'}})


@native_only
def test_websocket_session_plays_a_bounded_sandbox_session(native, tmp_path):
    pytest.importorskip('websockets')
    from src.openpoker import sandbox
    from src.openpoker.client import Journal, Session

    async def main():
        started, results = asyncio.get_running_loop().create_future(), {}
        server = asyncio.create_task(sandbox.serve(native, token=TOKEN, hands=40, started=started, results=results))
        port = await started
        journal = Journal(tmp_path / 'journal.jsonl')
        session = Session(Agent(native, scripted_routes('script:check-call'), seed=3), journal, buy_in=2000, max_hands=12)
        await asyncio.wait_for(session.run(f'ws://127.0.0.1:{port}', TOKEN), 60)
        journal.close()
        await asyncio.sleep(0.2)
        server.cancel()
        return session, results

    session, results = asyncio.run(main())
    assert session.hands == 12 and session.done
    assert session.stats['fallback'] == 0 and session.stats['policy'] > 0 and session.stats['rejected'] == 0
    assert results['violations'] == 0 and results['hands'] == 12
    lines = [json.loads(line) for line in (tmp_path / 'journal.jsonl').read_text().splitlines()]
    sent = [l['payload'] for l in lines if l['kind'] == 'out']
    assert sent[0] == {'type': 'join_lobby', 'buy_in': 2000} and sent[-1] == {'type': 'leave_table'}
    assert TOKEN not in (tmp_path / 'journal.jsonl').read_text()
