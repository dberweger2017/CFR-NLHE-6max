"""Routes each Open Poker decision to a native policy and returns the server action.

Routing is by the number of players dealt into the hand. Each count has an ordered list of
routes; a route names a loaded policy, its view (`native`, or `projected` for phantom folds and
other depths, see docs/openpoker-phantom-depth.md) and optionally a depth band. The first route
whose band holds every dealt seat's starting stack plays the hand (docs/openpoker-client.md).
Stacks are capped first: chips beyond the largest other seat's can never be won or lost, so
the hand is played as if that seat held only those. A count without a route, an unrepresentable hand or any
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


def cap_stacks(native: dict) -> tuple[dict, list[int]]:
    """The dealer record with every starting stack capped at the largest other seat's, and each
    seat's removed native chips. Only the single deepest seat can lose chips, and it has never
    risked them: a bet past its cap is replayed by the engine and refused, so the decision falls
    back instead of playing a different hand."""
    starts = native['hand']['stacks']
    cap = sorted(starts)[-2]
    excess = [max(0, s - cap) for s in starts]
    if not any(excess):
        return native, excess
    hand = dict(native['hand'], stacks=[s - e for s, e in zip(starts, excess)])
    return dict(native, hand=hand, stacks_now=[s - e for s, e in zip(native['stacks_now'], excess)],
                hero_total=native['hero_total'] - excess[native['seat']] // SCALE), excess


class Agent:
    def __init__(self, native, routes: dict[int, tuple[Route, ...]], seed: int, *, cap: bool = True):
        self.native, self.routes, self.seed, self.count, self.cap = native, routes, seed, 0, cap

    def decide(self, hand, turn: dict) -> tuple[dict, dict]:
        """Server action fields and a decision record for the journal."""
        valid = turn.get('valid_actions') or []
        self.count += 1
        record = {'hand_id': hand.hand_id}
        excess = ()
        try:
            native = hand.record(turn.get('players'))
            n = len(native['order'])
            raw = [s / native['hand']['bb'] for s in native['hand']['stacks']]
            native, excess = cap_stacks(native) if self.cap else (native, [0] * n)
            depths = [s / native['hand']['bb'] for s in native['hand']['stacks']]
            record.update(players=n, order=native['order'], native_hand=native['hand'], stacks_bb=depths)
            if any(excess):
                record['raw_stacks_bb'] = raw
            route = next((r for r in self.routes.get(n, ()) if r.covers(depths)), None)
            if route is None:
                raise Unsupported(f'no route for {n} players at {depths} BB')
            legal = legal_expectation(valid, native['hero_total'])
            if excess[native['seat']] and legal['raise_to']:
                # The server offers raises up to the hero's whole stack; the capped hand stops at the cap.
                top = native['hero_total'] * SCALE
                legal['raise_to'] = [min(legal['raise_to'][0], top), min(legal['raise_to'][1], top)]
            expect = {'legal': legal}
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
            # With a capped stack, the likely cause is a bet past the cap: the capped hand differs.
            record.update(status='fallback', reason=f"{'capped' if any(excess) else 'native'}: {error}")
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


__all__ = ['Agent', 'Route', 'cap_stacks', 'parse_routes', 'SCALE']
