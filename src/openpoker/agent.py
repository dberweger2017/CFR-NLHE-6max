"""Routes each Open Poker decision to a native policy and returns the server action.

Routing is by the number of players dealt into the hand. Each count has an ordered list of
routes; a route names a loaded policy, its view (`native`, or `projected` for phantom folds and
other depths, see docs/openpoker-phantom-depth.md) and optionally a depth band. The first route
whose band holds every dealt seat's starting stack plays the hand (docs/openpoker-client.md). A count without a route, an unrepresentable hand or any
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

    def covers(self, stacks_bb) -> bool:
        return self.band_bb is None or all(self.band_bb[0] <= s <= self.band_bb[1] for s in stacks_bb)


class Agent:
    def __init__(self, native, routes: dict[int, tuple[Route, ...]], seed: int):
        self.native, self.routes, self.seed, self.count = native, routes, seed, 0

    def decide(self, hand, turn: dict) -> tuple[dict, dict]:
        """Server action fields and a decision record for the journal."""
        valid = turn.get('valid_actions') or []
        self.count += 1
        record = {'hand_id': hand.hand_id}
        try:
            native = hand.record(turn.get('players'))
            n = len(native['order'])
            depths = [s / native['hand']['bb'] for s in native['hand']['stacks']]
            record.update(players=n, order=native['order'], native_hand=native['hand'], stacks_bb=depths)
            route = next((r for r in self.routes.get(n, ()) if r.covers(depths)), None)
            if route is None:
                raise Unsupported(f'no route for {n} players at {depths} BB')
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


def parse_routes(spec: dict) -> dict[int, tuple[Route, ...]]:
    """{"4": {"agent": "policy:six", "view": "projected"}, "6": [{"agent": "policy:six",
    "view": "projected", "band_bb": [89.4, 111.8]}, {"agent": "policy:mix", "view": "projected"}]}."""
    routes = {}
    for count, entries in spec.items():
        n = int(count)
        entries = entries if isinstance(entries, list) else [entries]
        parsed = []
        for route in entries:
            band = route.get('band_bb')
            if (not 2 <= n <= 6 or route.get('view', 'native') not in ('native', 'projected')
                    or set(route) - {'agent', 'view', 'band_bb'}
                    or band is not None and not (len(band) == 2 and 0 < band[0] <= band[1])):
                raise ValueError(f'route {count}: {route}')
            parsed.append(Route(route['agent'], route.get('view', 'native'), tuple(band) if band else None))
        if not parsed:
            raise ValueError(f'route {count}: empty')
        routes[n] = tuple(parsed)
    return routes


__all__ = ['Agent', 'Route', 'parse_routes', 'SCALE']
