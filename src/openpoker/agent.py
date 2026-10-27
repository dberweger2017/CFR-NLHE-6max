"""Routes each Open Poker decision to a native policy and returns the server action.

Routing is by the number of players dealt into the hand; each route names a loaded policy and
its view (`native`, or `projected` for phantom folds and other depths, see
docs/openpoker-phantom-depth.md). A count without a route, an unrepresentable hand or any
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


class Agent:
    def __init__(self, native, routes: dict[int, Route], seed: int):
        self.native, self.routes, self.seed, self.count = native, routes, seed, 0

    def decide(self, hand, turn: dict) -> tuple[dict, dict]:
        """Server action fields and a decision record for the journal."""
        valid = turn.get('valid_actions') or []
        self.count += 1
        record = {'hand_id': hand.hand_id}
        try:
            native = hand.record(turn.get('players'))
            n = len(native['order'])
            record.update(players=n, order=native['order'], native_hand=native['hand'])
            route = self.routes.get(n)
            if route is None:
                raise Unsupported(f'no route for {n} players')
            expect = {'legal': legal_expectation(valid, native['hero_total'])}
            response = self.native.decide(native['hand'], native['seat'], route.agent, seed=self.seed * 1_000_003 + self.count,
                                          expect=expect, view=route.view)
            stacks = [p[0] for p in response['players']]
            if stacks != native['stacks_now']:
                raise Unsupported(f'stacks {native["stacks_now"]} != native {stacks}')
            action = server_action(response['action'], valid)
            record.update(route=route.agent, view=route.view, native_action=response['action'],
                          trained=response['trained'], status='policy')
            return action, record
        except Unsupported as error:
            record.update(status='fallback', reason=str(error))
        except RuntimeError as error:  # NativeError: engine parity or service failure
            record.update(status='fallback', reason=f'native: {error}')
        return safe_action(valid), record


def parse_routes(spec: dict) -> dict[int, Route]:
    """{"6": {"agent": "policy:six"}, "4": {"agent": "policy:six", "view": "projected"}}."""
    routes = {}
    for count, route in spec.items():
        n = int(count)
        if not 2 <= n <= 6 or route.get('view', 'native') not in ('native', 'projected'):
            raise ValueError(f'route {count}: {route}')
        routes[n] = Route(route['agent'], route.get('view', 'native'))
    return routes


__all__ = ['Agent', 'Route', 'parse_routes', 'SCALE']
