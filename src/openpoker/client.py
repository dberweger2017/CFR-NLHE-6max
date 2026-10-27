"""Open Poker WebSocket client: one bot, one table, a bounded session (docs/openpoker-client.md).

Every inbound and outbound message and every decision record goes to a new JSONL journal, so a
session can be audited offline. The API key travels only in the Authorization header and is
never written. The session stops after `max_hands` completed hands, when `stop_file` exists, on
`busted`, or when the server closes the table and `rejoin` is off. It turns auto-rebuy off after
joining, and on stopping sends `leave_table` and keeps the socket open until the server confirms
the leave (`player_left` for its seat, or `not_at_table`), as the bot lifecycle documentation asks.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path

from src.openpoker.tracker import Hand, Unsupported, safe_action

RECONNECT_WINDOW = 110.0
DECISION_SECONDS = 30.0
LEAVE_SECONDS = 60.0


class Journal:
    def __init__(self, path: Path):
        self.file = Path(path).open('x')

    def write(self, kind: str, payload: dict):
        self.file.write(json.dumps({'t': time.time(), 'kind': kind, 'payload': payload}, separators=(',', ':')) + '\n')
        self.file.flush()

    def close(self):
        self.file.close()


class Session:
    def __init__(self, agent, journal: Journal, *, buy_in: int = 2000, max_hands: int = 100, stop_file: Path | None = None,
                 rejoin: bool = False):
        if not 1000 <= buy_in <= 5000:
            raise ValueError('buy-in must be 1000..5000 chips')
        self.agent, self.journal, self.buy_in, self.max_hands = agent, journal, buy_in, max_hands
        self.stop_file, self.rejoin = stop_file, rejoin
        self.hand = None
        self.broken = None
        self.hands = 0
        self.table_id = None
        self.seat = None
        self.leaving = None
        self.table_seq = 0
        self.pending = {}
        self.done = False
        self.stats = {'policy': 0, 'fallback': 0, 'rejected': 0}

    async def send(self, ws, message: dict):
        self.journal.write('out', message)
        await ws.send(json.dumps(message))

    async def leave(self, ws):
        await self.send(ws, {'type': 'leave_table'})
        self.leaving = self.leaving or time.monotonic() + LEAVE_SECONDS

    def stopping(self) -> bool:
        return self.hands >= self.max_hands or (self.stop_file is not None and self.stop_file.exists())

    async def act(self, ws, turn: dict):
        if self.hand is not None and self.broken is None and str(turn.get('hand_id')) == self.hand.hand_id:
            loop = asyncio.get_running_loop()
            try:
                action, record = await asyncio.wait_for(loop.run_in_executor(None, self.agent.decide, self.hand, turn), DECISION_SECONDS)
            except asyncio.TimeoutError:
                action, record = safe_action(turn.get('valid_actions') or []), {'status': 'fallback', 'reason': 'decision timeout'}
        else:
            action = safe_action(turn.get('valid_actions') or [])
            record = {'hand_id': turn.get('hand_id'), 'status': 'fallback', 'reason': self.broken or 'no tracked hand'}
        self.stats[record['status']] += 1
        self.journal.write('decision', record)
        message = {'type': 'action', 'hand_id': turn.get('hand_id'), 'client_action_id': str(uuid.uuid4()),
                   'turn_token': turn.get('turn_token'), **action}
        self.pending[message['client_action_id']] = turn
        await self.send(ws, message)

    def track(self, method, message):
        if self.hand is None or self.broken is not None:
            return
        try:
            method(message)
        except (Unsupported, KeyError, ValueError, TypeError) as error:
            self.broken = f'{type(error).__name__}: {error}'

    async def handle(self, ws, message: dict, *, replay: bool = False):
        kind = message.get('type')
        if isinstance(message.get('table_seq'), int):
            self.table_seq = max(self.table_seq, message['table_seq'])
        if kind == 'connected' and not replay:
            if self.table_id is None:
                await self.send(ws, {'type': 'join_lobby', 'buy_in': self.buy_in})
                await self.send(ws, {'type': 'set_auto_rebuy', 'enabled': False})
            else:
                await self.send(ws, {'type': 'resync_request', 'table_id': self.table_id, 'last_table_seq': self.table_seq})
        elif kind == 'table_joined':
            self.table_id, self.seat = message.get('table_id'), message.get('seat')
        elif kind == 'player_left' and self.seat is not None and message.get('seat') == self.seat and not replay:
            self.done = True
        elif kind == 'hand_start':
            self.hand, self.broken = None, None
            try:
                self.hand = Hand.start(message)
            except (Unsupported, KeyError, ValueError, TypeError) as error:
                self.broken = f'{type(error).__name__}: {error}'
        elif kind == 'hole_cards':
            self.track(self.hand.hole_cards if self.hand else None, message)
        elif kind == 'community_cards':
            self.track(self.hand.community_cards if self.hand else None, message)
        elif kind == 'player_action':
            self.track(self.hand.player_action if self.hand else None, message)
        elif kind == 'table_state' and self.hand is not None and str(message.get('hand_id')) == self.hand.hand_id:
            self.track(self.hand.table_state, message)
        elif kind == 'your_turn' and not replay:
            await self.act(ws, message)
        elif kind == 'action_rejected' and message.get('code') == 'not_at_table' and self.leaving and not replay:
            self.done = True
        elif kind == 'action_rejected' and not replay:
            self.stats['rejected'] += 1
            turn = self.pending.pop((message.get('details') or {}).get('client_action_id') or message.get('client_action_id'), None)
            if turn is not None and message.get('code') != 'stale_turn_token':
                fallback = {'type': 'action', 'hand_id': turn.get('hand_id'), 'client_action_id': str(uuid.uuid4()),
                            'turn_token': turn.get('turn_token'), **safe_action(turn.get('valid_actions') or [])}
                self.broken = f'rejected: {message.get("code")}'
                await self.send(ws, fallback)
        elif kind == 'hand_result':
            self.hands += 1
            self.hand = None
            if self.stopping() and self.leaving is None and not replay:
                await self.leave(ws)
        elif kind in ('table_closed', 'season_ended') and not replay:
            self.table_id, self.hand = None, None
            if self.rejoin and not self.stopping() and self.leaving is None:
                await self.send(ws, {'type': 'join_lobby', 'buy_in': self.buy_in})
            else:
                # A closing table can briefly requeue the bot; one more leave_table answered by
                # not_at_table is the clean exit.
                await self.leave(ws)
        elif kind == 'busted' and not replay:
            await self.leave(ws)
        elif kind == 'resync_response':
            for event in message.get('replayed_events') or ():
                await self.handle(ws, event, replay=True)
            hero = (message.get('snapshot') or {}).get('hero') or {}
            if hero.get('turn_token') and hero.get('valid_actions'):
                snapshot = message['snapshot']
                await self.act(ws, {'hand_id': snapshot.get('hand_id', self.hand.hand_id if self.hand else None),
                                    'valid_actions': hero['valid_actions'], 'turn_token': hero['turn_token'],
                                    'players': snapshot.get('seats')})
        elif kind == 'error' and message.get('code') in ('auth_failed', 'flood_kick'):
            raise PermissionError(message.get('code'))

    async def run(self, url: str, api_key: str):
        import websockets

        deadline = None
        while not self.done:
            try:
                async with websockets.connect(url, additional_headers={'Authorization': f'Bearer {api_key}'}) as ws:
                    deadline = None
                    while True:
                        wait = None if self.leaving is None else self.leaving - time.monotonic()
                        try:
                            raw = await asyncio.wait_for(ws.recv(), wait)
                        except asyncio.TimeoutError:
                            self.journal.write('leave_timeout', {'hands': self.hands})
                            return
                        message = json.loads(raw)
                        self.journal.write('in', message)
                        await self.handle(ws, message)
                        if self.done:
                            break
                return
            except websockets.ConnectionClosedOK:
                # A normal close by the server ends the session.
                self.journal.write('closed', {'hands': self.hands})
                return
            except (OSError, websockets.ConnectionClosedError) as error:
                self.journal.write('disconnect', {'error': f'{type(error).__name__}: {error}'})
                if self.leaving is not None:
                    return
                deadline = deadline or time.monotonic() + RECONNECT_WINDOW
                if self.table_id is None or time.monotonic() > deadline:
                    raise
                await asyncio.sleep(2)
