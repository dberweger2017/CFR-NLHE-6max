"""One Open Poker hand as a native dealer record (docs/openpoker-client.md).

Open Poker reports seats, chips and actions; the native engine needs the dealt players in
table order, their starting stacks, the button and every action as fold/check/call/raise-to.
Chips paid by an action come from the most direct field the server sends
(`contribution_delta`, then `stack_before - stack_after`, then the change from the seat's last
known stack), never from `amount`, whose broadcast meaning the documentation leaves open.
Starting stacks are the current stack plus everything contributed this hand. The record is
checked by the native engine, which replays it and must agree with the server's legal actions
and stacks before any policy acts; anything unexpected raises `Unsupported`.

Hidden cards never enter the record: the engine needs a complete deck, so unseen positions are
filled with unused cards in ascending order, and the acting observation shows only the hero's
cards and the dealt board.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.play_api.native_decisions import card_index

# Native chips per Open Poker chip: 10/20 blinds become the trained 50/100.
SCALE = 5
BLINDS = (10, 20)
STREETS = ('preflop', 'flop', 'turn', 'river')
BOARD_SIZES = {'flop': 3, 'turn': 4, 'river': 5}
BLIND_ACTIONS = {'small_blind', 'big_blind', 'post_blind', 'post', 'blind', 'sb', 'bb'}
ACTION_KINDS = {'fold', 'check', 'call', 'raise', 'all_in', 'bet'}
OUT_OF_HAND = {'sitting_out', 'empty', 'away_waiting'}


class Unsupported(ValueError):
    """The hand cannot be represented exactly; the caller plays its safe fallback."""


@dataclass
class Paid:
    seat: int
    kind: str
    chips: int
    street: str
    raw: dict


@dataclass
class Hand:
    hand_id: str
    hero: int
    dealer: int
    hole: list = field(default_factory=list)
    board: list = field(default_factory=list)
    street: str = 'preflop'
    paid: list = field(default_factory=list)
    stacks: dict = field(default_factory=dict)
    seen: set = field(default_factory=set)
    in_hand: dict = field(default_factory=dict)

    @classmethod
    def start(cls, message: dict) -> 'Hand':
        blinds = message.get('blinds') or {}
        if (blinds.get('small_blind'), blinds.get('big_blind')) != BLINDS:
            raise Unsupported(f'blinds {blinds}')
        hand = cls(str(message['hand_id']), int(message['seat']), int(message['dealer_seat']))
        hand.seen.update({hand.hero, hand.dealer})
        return hand

    def hole_cards(self, message: dict):
        cards = [card_index(c) for c in message['cards']]
        if len(cards) != 2 or len(set(cards)) != 2:
            raise Unsupported('hole cards')
        self.hole = cards

    def community_cards(self, message: dict):
        street = message.get('street')
        cards = [card_index(c) for c in message['cards']]
        if street not in BOARD_SIZES:
            raise Unsupported(f'street {street}')
        board = self.board + cards if len(self.board) + len(cards) == BOARD_SIZES[street] else cards
        if len(board) != BOARD_SIZES[street] or len(set(board + self.hole)) != len(board) + len(self.hole):
            raise Unsupported('board')
        self.board, self.street = board, street

    def observe_players(self, players):
        """Latest stacks of seated players, from `your_turn.players` or table snapshots."""
        for p in players or ():
            if 'seat' in p and isinstance(p.get('stack'), int):
                self.stacks[int(p['seat'])] = p['stack']

    def table_state(self, message: dict):
        """Which seats were dealt in, from a mid-hand table snapshot. `your_turn.players` lists
        every seated player, including one who joined during the hand."""
        if message.get('street') not in STREETS:
            return
        seats = {int(s['seat']): s.get('in_hand') for s in message.get('seats') or () if 'seat' in s}
        if any(v is True for v in seats.values()):
            self.in_hand = {seat: v is True for seat, v in seats.items()}

    def player_action(self, message: dict):
        seat, action = int(message['seat']), message.get('action')
        # The server labels an action with the street after it: the call that closes preflop
        # arrives as `flop`, a final fold as `showdown`. The action belongs to the tracked street.
        label = message.get('street') or self.street
        if label not in STREETS + ('showdown',) or (label in STREETS and STREETS.index(label) < STREETS.index(self.street)):
            raise Unsupported(f'action street {label} during {self.street}')
        street = self.street
        self.seen.add(seat)
        if action in BLIND_ACTIONS:
            self._stack_after(seat, message)
            return
        if action not in ACTION_KINDS:
            raise Unsupported(f'action {action}')
        if 'contribution_delta' in message and message['contribution_delta'] is not None:
            chips = message['contribution_delta']
        elif isinstance(message.get('stack_before'), int) and isinstance(message.get('stack_after'), int):
            chips = message['stack_before'] - message['stack_after']
        elif action in ('fold', 'check'):
            chips = 0
        elif seat in self.stacks and isinstance(message.get('stack'), int):
            chips = self.stacks[seat] - message['stack']
        else:
            raise Unsupported(f'chips paid by seat {seat} unknown')
        if type(chips) is not int or chips < 0 or (action in ('fold', 'check') and chips):
            raise Unsupported(f'chips {chips} for {action}')
        self.paid.append(Paid(seat, action, chips, street, message))
        self._stack_after(seat, message)

    def _stack_after(self, seat, message):
        for key in ('stack_after', 'stack'):
            if isinstance(message.get(key), int):
                self.stacks[seat] = message[key]
                return

    def record(self, players) -> dict:
        """The native dealer record at the hero's decision; `players` is `your_turn.players`."""
        self.observe_players(players)
        dealt = set(self.seen)
        if self.in_hand:
            if any(not self.in_hand.get(seat) for seat in self.seen):
                raise Unsupported(f'seats {sorted(self.seen)} acted but the snapshot dealt {self.in_hand}')
            dealt = {seat for seat, dealt_in in self.in_hand.items() if dealt_in}
        else:
            for p in players or ():
                if p.get('in_hand') is False or p.get('status') in OUT_OF_HAND:
                    continue
                dealt.add(int(p['seat']))
        order = sorted(dealt)
        n = len(order)
        if not 2 <= n <= 6 or self.dealer not in dealt or self.hero not in dealt:
            raise Unsupported(f'dealt seats {order}, dealer {self.dealer}, hero {self.hero}')
        if len(self.hole) != 2:
            raise Unsupported('hole cards missing')
        button = order.index(self.dealer)
        native = {seat: i for i, seat in enumerate(order)}
        contributed = {seat: 0 for seat in order}
        sb_seat = order[button] if n == 2 else order[(button + 1) % n]
        bb_seat = order[(order.index(sb_seat) + 1) % n]
        for seat in order:
            if seat not in self.stacks:
                raise Unsupported(f'stack of seat {seat} unknown')
        # Blinds are posted before any action. A blind that may have been all-in posts an amount
        # the messages don't establish.
        for seat, blind in ((sb_seat, BLINDS[0]), (bb_seat, BLINDS[1])):
            if self.stacks[seat] == 0 and not any(p.seat == seat and p.chips for p in self.paid):
                raise Unsupported(f'possible all-in blind at seat {seat}')
            contributed[seat] += blind
        actions, street, bets, wager = [], 'preflop', dict.fromkeys(order, 0), BLINDS[1]
        bets[sb_seat], bets[bb_seat] = BLINDS
        for p in self.paid:
            if p.seat not in native:
                raise Unsupported(f'action by undealt seat {p.seat}')
            if p.street != street:
                if STREETS.index(p.street) < STREETS.index(street):
                    raise Unsupported('streets out of order')
                street, bets, wager = p.street, dict.fromkeys(order, 0), 0
            contributed[p.seat] += p.chips
            total = bets[p.seat] + p.chips
            if p.kind == 'fold':
                actions.append(['fold', 0])
            elif p.chips == 0:
                actions.append(['check', 0])
            elif total > wager:
                actions.append(['raise', total * SCALE])
                wager = total
            else:
                actions.append(['call', 0])
            bets[p.seat] = total
        stacks = [(self.stacks[seat] + contributed[seat]) * SCALE for seat in order]
        hero = native[self.hero]
        return {'hand': {'stacks': stacks, 'sb': BLINDS[0] * SCALE, 'bb': BLINDS[1] * SCALE, 'button': button,
                         'deck': self.deck(n, button, hero), 'actions': actions},
                'seat': hero, 'order': order, 'hero_total': (bets[self.hero] if street == self.street else 0) + self.stacks[self.hero],
                'stacks_now': [self.stacks[seat] * SCALE for seat in order]}

    def deck(self, n, button, hero):
        """Hero's cards in the hero's deal positions, the dealt board in its positions."""
        deck = [None] * 52
        offset = (hero - button - 1) % n
        deck[offset], deck[n + offset] = self.hole
        for i, card in enumerate(self.board):
            deck[2 * n + i] = card
        rest = iter(c for c in range(52) if c not in set(self.hole) | set(self.board))
        return [c if c is not None else next(rest) for c in deck]


def legal_expectation(valid_actions, hero_total: int | None = None) -> dict:
    """Open Poker's legal actions in native chips. A lone `all_in` is a raise to everything."""
    kinds = {a['action']: a for a in valid_actions}
    call = kinds.get('call', {}).get('amount', 0)
    if 'raise' in kinds:
        raise_to = [kinds['raise']['min'] * SCALE, kinds['raise']['max'] * SCALE]
    elif 'all_in' in kinds and hero_total is not None:
        raise_to = [hero_total * SCALE, hero_total * SCALE]
    else:
        raise_to = None
    return {'check': 'check' in kinds, 'call': call * SCALE, 'raise_to': raise_to}


def server_action(native_action, valid_actions) -> dict:
    """A native fold/check/call/raise-to as Open Poker's action fields; raises must be exact."""
    kind, raise_to = native_action
    kinds = {a['action']: a for a in valid_actions}
    if kind in ('fold', 'check', 'call'):
        if kind not in kinds:
            raise Unsupported(f'{kind} not offered')
        return {'action': kind}
    if raise_to % SCALE:
        raise Unsupported(f'raise to {raise_to} native chips is not a whole server chip')
    amount = raise_to // SCALE
    if 'raise' in kinds and kinds['raise']['min'] <= amount <= kinds['raise']['max']:
        return {'action': 'raise', 'amount': amount}
    if 'all_in' in kinds and 'raise' not in kinds:
        return {'action': 'all_in'}
    raise Unsupported(f'raise to {amount} outside the offered range')


def safe_action(valid_actions) -> dict:
    """Check when free, otherwise fold: never commits chips on an unrepresented state."""
    kinds = {a['action'] for a in valid_actions}
    return {'action': 'check'} if 'check' in kinds else {'action': 'fold'}
