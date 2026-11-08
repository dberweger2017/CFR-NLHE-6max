"""Routes each Open Poker decision to a native policy and returns the server action.

Routing is by the number of players dealt into the hand. Each count has an ordered list of
routes; a route names a loaded policy, its view (`native`, or `projected` for phantom folds and
other depths, see docs/openpoker-phantom-depth.md), optionally a depth band and optionally a short
threshold, and optionally a `fallback`: `network:NAME` plays that pinned network wherever the
policy has no positive-mass row (docs/neural-policy-fallback.md). Stacks are capped first: chips beyond the largest other seat's can never be won or lost,
so the hand is played as if that seat held only those (`Hand.record`). The first route whose band
holds every dealt seat's capped starting stack, and, with a threshold, where some dealt seat starts
below it, plays the hand (docs/openpoker-client.md). A count without a route, an unrepresentable hand or any
disagreement between the server and the native engine plays the safe fallback, check else
fold, and is recorded with its reason.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.openpoker.tracker import SCALE, Unsupported, legal_expectation, safe_action, server_action


@dataclass(frozen=True)
class Route:
    agent: str
    view: str = 'native'
    band_bb: tuple[float, float] | None = None
    short_bb: float | None = None
    fallback: str | None = None

    def covers(self, stacks_bb) -> bool:
        return ((self.band_bb is None or all(self.band_bb[0] <= s <= self.band_bb[1] for s in stacks_bb))
                and (self.short_bb is None or min(stacks_bb) < self.short_bb))


class Agent:
    def __init__(self, native, routes: dict[int, tuple[Route, ...]], seed: int, *, cap: bool = True):
        self.native, self.routes, self.seed, self.count, self.cap = native, routes, seed, 0, cap

    def decide(self, hand, turn: dict) -> tuple[dict, dict]:
        """Server action fields and a decision record for the journal."""
        valid = turn.get('valid_actions') or []
        self.count += 1
        record = {'hand_id': hand.hand_id}
        try:
            native = hand.record(turn.get('players'), cap=self.cap)
            n = len(native['order'])
            excess = native['excess']
            depths = [s / native['hand']['bb'] for s in native['hand']['stacks']]
            record.update(players=n, order=native['order'], native_hand=native['hand'], stacks_bb=depths)
            if any(excess):
                record['excess_bb'] = [e / native['hand']['bb'] for e in excess]
            route = next((r for r in self.routes.get(n, ()) if r.covers(depths)), None)
            if route is None:
                raise Unsupported(f'no route for {n} players at {depths} BB')
            legal = legal_expectation(valid, native['hero_total'])
            deep = excess[native['seat']] > 0 and legal['raise_to'] is not None
            if deep:
                # The server offers raises up to the hero's whole stack; the capped hand stops at the
                # cap, and has no raise when calling already puts the capped stack in.
                top = native['hero_total'] * SCALE
                after_call = native['stacks_now'][native['seat']] - legal['call']
                legal['raise_to'] = [min(legal['raise_to'][0], top), min(legal['raise_to'][1], top)] if after_call > 0 else None
            expect = {'legal': legal}
            response = self.native.decide(native['hand'], native['seat'], route.agent, seed=self.seed * 1_000_003 + self.count,
                                          expect=expect, view=route.view, fallback=route.fallback)
            stacks = [p[0] for p in response['players']]
            if stacks != native['stacks_now']:
                raise Unsupported(f'stacks {native["stacks_now"]} != native {stacks}')
            native_action = response['action']
            offered = next((a for a in valid if a['action'] == 'raise'), None)
            if deep and native_action[0] == 'raise' and offered:
                # Nobody can match past the cap, so any legal raise at or above it plays the same hand.
                native_action = ['raise', max(native_action[1], offered['min'] * SCALE)]
            action = server_action(native_action, valid)
            record.update(route=route.agent, view=route.view, native_action=response['action'],
                          trained=response['trained'], status='policy')
            if route.fallback:
                record.update(fallback=route.fallback, row_status=response['status'])
                if 'network' in response:
                    record['network'] = response['network']
            return action, record
        except Unsupported as error:
            record.update(status='fallback', reason=str(error))
        except RuntimeError as error:  # NativeError: engine parity or service failure
            record.update(status='fallback', reason=f'native: {error}')
        return safe_action(valid), record


def parse_routes(spec: dict) -> dict[int, tuple[Route, ...]]:
    """{"4": {"agent": "policy:six", "view": "projected"}, "6": [{"agent": "policy:six",
    "view": "projected", "band_bb": [89.4, 111.8]}, {"agent": "policy:mix", "view": "projected"}]};
    a route may also carry "short_bb": 10, matching only hands where some dealt seat starts below it,
    and "fallback": "network:NAME" for a policy route."""
    routes = {}
    for count, entries in spec.items():
        n = int(count)
        entries = entries if isinstance(entries, list) else [entries]
        parsed = []
        for route in entries:
            band, short, fallback = route.get('band_bb'), route.get('short_bb'), route.get('fallback')
            if (not 2 <= n <= 6 or route.get('view', 'native') not in ('native', 'projected')
                    or set(route) - {'agent', 'view', 'band_bb', 'short_bb', 'fallback'}
                    or fallback is not None and not (isinstance(fallback, str) and fallback.startswith('network:')
                                                     and len(fallback) > 8 and route['agent'].startswith('policy:'))
                    or band is not None and not (len(band) == 2 and 0 < band[0] <= band[1])
                    or short is not None and not (isinstance(short, (int, float)) and short > 0)):
                raise ValueError(f'route {count}: {route}')
            parsed.append(Route(route['agent'], route.get('view', 'native'), tuple(band) if band else None,
                                float(short) if short is not None else None, fallback))
        if not parsed:
            raise ValueError(f'route {count}: empty')
        routes[n] = tuple(parsed)
    return routes


__all__ = ['Agent', 'Route', 'parse_routes', 'SCALE']
