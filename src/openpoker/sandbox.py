"""A local stand-in for Open Poker's table protocol, dealt by the native engine.

It follows the documented message shapes (docs/openpoker-client.md): seats with gaps, a
rotating dealer, unequal stacks and scripted opponents. It encodes this repository's reading of
the documentation, so it tests the client's plumbing and exact chip handling, not the server's
real behavior; undocumented server details (blind events, broadcast `amount`) are chosen here.
"""
from __future__ import annotations

import asyncio
import itertools
import json
import random

from src.openpoker.tracker import BLINDS, SCALE
from src.play_api.native_decisions import card_name

STREET_OF_BOARD = {3: 'flop', 4: 'turn', 5: 'river'}


def valid_actions(legal) -> list:
    out = [{'action': 'check'}] if legal['check'] else [{'action': 'fold'}, {'action': 'call', 'amount': legal['call'] // SCALE}]
    if legal['raise_to']:
        low, high = (v // SCALE for v in legal['raise_to'])
        out.append({'action': 'raise', 'min': low, 'max': high} if low < high else {'action': 'all_in', 'amount': high})
    return out


def native_action(fields, legal) -> list:
    """The bot's server action as a native action; invalid actions raise ValueError."""
    kinds = {a['action']: a for a in valid_actions(legal)}
    kind = fields.get('action')
    if kind not in kinds:
        raise ValueError(f'{kind} not offered')
    if kind == 'raise':
        amount = fields.get('amount')
        if type(amount) is not int or not kinds['raise']['min'] <= amount <= kinds['raise']['max']:
            raise ValueError(f'raise amount {amount}')
        return ['raise', amount * SCALE]
    if kind == 'all_in':
        return ['raise', legal['raise_to'][1]]
    return [kind, 0]


class Table:
    """One sandbox table; `seats` maps server seat -> [agent, stack in server chips]."""

    def __init__(self, native, seats: dict, bot_seat: int, seed: int):
        self.native, self.seats, self.bot = native, seats, bot_seat
        self.rng = random.Random(seed)
        self.dealer = None
        self.ids = itertools.count()
        self.violations = 0

    async def hand(self, send, act):
        order = sorted(s for s, (_, stack) in self.seats.items() if stack > 0)
        if self.bot not in order or len(order) < 2:
            return False
        later = [s for s in order if self.dealer is None or s > self.dealer]
        self.dealer = (later or order)[0]
        n, button = len(order), order.index(self.dealer)
        deck = list(range(52))
        self.rng.shuffle(deck)
        record = {'stacks': [self.seats[s][1] * SCALE for s in order], 'sb': BLINDS[0] * SCALE, 'bb': BLINDS[1] * SCALE,
                  'button': button, 'deck': deck, 'actions': []}
        hand_id = f'sandbox-{next(self.ids)}'
        hero = order.index(self.bot)
        offset = (hero - button - 1) % n
        await send({'type': 'hand_start', 'hand_id': hand_id, 'seat': self.bot, 'dealer_seat': self.dealer,
                    'blinds': {'small_blind': BLINDS[0], 'big_blind': BLINDS[1]}})
        await send({'type': 'hole_cards', 'cards': [card_name(deck[offset]), card_name(deck[n + offset])]})
        state, board, history = self.native.state(record), 0, []
        while not state['finished']:
            actor = state['actor']
            seat = order[actor]
            if seat == self.bot:
                turn = {'type': 'your_turn', 'hand_id': hand_id, 'valid_actions': valid_actions(state['legal']),
                        'pot': sum(p[2] for p in state['players']) // SCALE,
                        'community_cards': [card_name(c) for c in state['board']], 'turn_token': f'{hand_id}-{len(record["actions"])}',
                        'players': [{'seat': s, 'name': f'p{s}', 'stack': p[0] // SCALE, 'bet': p[1] // SCALE, 'folded': p[3],
                                     'in_hand': True} for s, p in zip(order, state['players'])]}
                try:
                    action = native_action(await act(turn), state['legal'])
                except ValueError:
                    self.violations += 1
                    action = ['check', 0] if state['legal']['check'] else ['fold', 0]
            else:
                agent = self.seats[seat][0]
                action = self.native.decide(record, actor, agent, seed=self.rng.randrange(2**63))['action']
            before = state['players'][actor]
            record['actions'].append(action)
            after = self.native.state(record)
            paid_total = (self.native.settle(record)['contributions'][actor] if after['finished'] else after['players'][actor][2])
            paid = (paid_total - before[2]) // SCALE
            kind = action[0]
            if kind == 'raise' and action[1] == before[0] + before[1]:
                kind = 'all_in'
            stack_after = before[0] // SCALE - paid
            message = {'type': 'player_action', 'seat': seat, 'name': f'p{seat}', 'action': kind,
                       'amount': action[1] // SCALE if action[0] == 'raise' else (paid or None),
                       'street': state['street'], 'stack': stack_after, 'stack_before': before[0] // SCALE,
                       'stack_after': stack_after, 'contribution_delta': paid,
                       'pot': (sum(p[2] for p in after['players']) if not after['finished'] else 0) // SCALE}
            history.append({'seat': seat, 'action': kind, 'amount': message['amount'], 'street': state['street']})
            await send(message)
            if not after['finished'] and len(after['board']) > board:
                cards = after['board'][board:]
                board = len(after['board'])
                await send({'type': 'community_cards', 'cards': [card_name(c) for c in cards], 'street': STREET_OF_BOARD[board]})
            state = after
        settled = self.native.settle(record)
        final = {}
        for s, start, reward in zip(order, record['stacks'], settled['rewards']):
            self.seats[s][1] = (start + reward) // SCALE
            final[str(s)] = self.seats[s][1]
        await send({'type': 'hand_result', 'hand_id': hand_id, 'final_stacks': final, 'actions': history,
                    'payouts': [{'seat': s, 'amount': (r + c) // SCALE} for s, r, c in
                                zip(order, settled['rewards'], settled['contributions']) if r + c > 0],
                    'pot': sum(settled['contributions']) // SCALE})
        return True


async def serve(native, *, host='127.0.0.1', port=0, token='sandbox', seats=None, bot_seat=2, hands=50, seed=1,
                started=None, results=None):
    """Serves one bot connection for `hands` hands, then closes the table."""
    import websockets

    seats = seats or {0: ['script:tight-aggressive', 2000], 2: ['bot', 2000], 3: ['script:pot-pressure', 1500],
                      5: ['script:check-call', 3000]}
    table = Table(native, {s: list(v) for s, v in seats.items()}, bot_seat, seed)

    async def handler(ws):
        if ws.request.headers.get('Authorization') != f'Bearer {token}':
            await ws.send(json.dumps({'type': 'error', 'code': 'auth_failed'}))
            await ws.close(4001)
            return
        inbox = asyncio.Queue()

        async def send(message):
            await ws.send(json.dumps(message))

        async def reader():
            async for raw in ws:
                await inbox.put(json.loads(raw))

        task = asyncio.create_task(reader())
        await send({'type': 'connected', 'agent_id': 'sandbox-agent', 'name': 'sandbox'})
        first = await inbox.get()
        if first.get('type') != 'join_lobby':
            raise RuntimeError(f'expected join_lobby, got {first}')
        table.seats[bot_seat][1] = first.get('buy_in', 2000)
        await send({'type': 'lobby_joined', 'position': 0, 'estimated_wait': '0s'})
        await send({'type': 'table_joined', 'table_id': 'sandbox-table', 'seat': bot_seat,
                    'players': [{'seat': s, 'name': f'p{s}', 'stack': v[1]} for s, v in table.seats.items()]})

        async def act(turn):
            await send(turn)
            while True:
                message = await inbox.get()
                if message.get('type') == 'leave_table':
                    raise ConnectionAbortedError
                if message.get('type') == 'set_auto_rebuy':
                    await send({'type': 'auto_rebuy_set', 'enabled': bool(message.get('enabled'))})
                if message.get('type') == 'action' and message.get('turn_token') == turn['turn_token']:
                    await send({'type': 'action_ack', 'client_action_id': message.get('client_action_id'), 'status': 'accepted'})
                    return message

        played, left = 0, False
        try:
            while played < hands and await table.hand(send, act):
                played += 1
                if not inbox.empty() and inbox._queue[0].get('type') == 'leave_table':
                    left = True
                    break
            if not left:
                await send({'type': 'table_closed', 'reason': 'sandbox_finished'})
        except ConnectionAbortedError:
            left = True
        if left:
            await send({'type': 'player_left', 'seat': bot_seat, 'name': 'sandbox', 'reason': 'left'})
        else:
            try:
                while (await asyncio.wait_for(inbox.get(), 5)).get('type') != 'leave_table':
                    pass
                await send({'type': 'action_rejected', 'code': 'not_at_table'})
            except asyncio.TimeoutError:
                pass
        if results is not None:
            results.update(hands=played, violations=table.violations, stacks={s: v[1] for s, v in table.seats.items()})
        # Like the server, keep the socket open and let the client close it.
        try:
            await asyncio.wait_for(ws.wait_closed(), 5)
        except asyncio.TimeoutError:
            pass
        task.cancel()
        await ws.close()

    async with websockets.serve(handler, host, port) as server:
        if started is not None:
            started.set_result(server.sockets[0].getsockname()[1])
        await asyncio.Event().wait()
