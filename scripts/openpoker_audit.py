"""Audit an Open Poker session journal offline (docs/openpoker-client.md).

Reports decisions by status, fallback reasons and routes, rejected actions, the hero's chip
result per completed hand, and the server message details the documentation leaves open:
which fields `player_action` carries, whether its raise `amount` is a raise-to total (and its
declared `amount_mode`), whether blinds arrive as events and which fields `your_turn.players`
entries have. Streets come from `community_cards`, because the server labels each action with
the street after it.
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def raise_meanings(actions, hero, dealer):
    """Whether each raise's broadcast `amount` is the raise-to total or the chips added. Blind
    seats follow the dealer among the seats seen in the hand; hands that don't fit are skipped.
    `actions` holds the hand's `player_action` messages, with a `{'board': street}` marker
    where each `community_cards` arrived."""
    order = sorted({a['seat'] for a in actions if 'seat' in a} | {hero, dealer})
    if dealer not in order or len(order) < 2:
        return Counter(unresolved=1)
    button = order.index(dealer)
    sb = order[button] if len(order) == 2 else order[(button + 1) % len(order)]
    bets, street, out = defaultdict(int), 'preflop', Counter()
    bets[sb], bets[order[(order.index(sb) + 1) % len(order)]] = 10, 20
    for a in actions:
        if 'board' in a:
            if a['board'] != street:
                street, bets = a['board'], defaultdict(int)
            continue
        delta = a.get('contribution_delta')
        if delta is None and isinstance(a.get('stack_before'), int) and isinstance(a.get('stack_after'), int):
            delta = a['stack_before'] - a['stack_after']
        if delta is None:
            out['unresolved'] += a.get('action') in ('raise', 'all_in', 'bet')
            continue
        total = bets[a['seat']] + delta
        if a.get('action') in ('raise', 'all_in', 'bet') and a.get('amount') is not None:
            out['raise-to total' if a['amount'] == total else 'increment' if a['amount'] == delta else 'other'] += 1
        bets[a['seat']] = total
    return out


def audit(path: Path) -> dict:
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    decisions, reasons, routes = Counter(), Counter(), Counter()
    fields, kinds, player_fields, raise_amounts, modes = Counter(), Counter(), Counter(), Counter(), Counter()
    rejected, hero, dealer, start, results, actions = Counter(), None, None, {}, [], []
    for line in lines:
        kind, p = line['kind'], line['payload']
        if kind == 'decision':
            decisions[p['status']] += 1
            if p['status'] == 'fallback':
                reasons[p['reason'].split(':')[0]] += 1
            else:
                routes[f"{p['players']} players: {p['route']} ({p['view']})"] += 1
        if kind != 'in':
            continue
        t = p.get('type')
        kinds[t] += 1
        if t == 'hand_start':
            hero, dealer, actions = p.get('seat'), p.get('dealer_seat'), []
        elif t == 'your_turn':
            for entry in p.get('players') or ():
                player_fields.update(entry.keys())
                if entry.get('seat') == hero and p.get('hand_id') not in start:
                    start[p.get('hand_id')] = entry.get('stack')
        elif t == 'player_action':
            fields.update(k for k in p if k != 'type')
            modes[f"{p.get('action')}: {p.get('amount_mode')}"] += 1
            actions.append(p)
        elif t == 'community_cards':
            actions.append({'board': p.get('street')})
        elif t == 'hand_result' and hero is not None:
            raise_amounts.update(raise_meanings(actions, hero, dealer))
            final = (p.get('final_stacks') or {}).get(str(hero))
            results.append({'hand_id': p.get('hand_id'), 'final_stack': final})
        elif t == 'action_rejected':
            rejected[p.get('code')] += 1
    return {'journal': str(path), 'hands': len(results), 'decisions': dict(decisions), 'fallback_reasons': dict(reasons),
            'routes': dict(routes), 'rejected': dict(rejected), 'inbound_types': dict(kinds),
            'player_action_fields': dict(fields), 'raise_amount_meaning': dict(raise_amounts), 'amount_modes': dict(modes),
            'blind_events': sum(1 for l in lines if l['kind'] == 'in' and l['payload'].get('type') == 'player_action'
                                and l['payload'].get('action') in ('small_blind', 'big_blind', 'post_blind', 'post', 'blind')),
            'your_turn_player_fields': dict(player_fields),
            'hero_final_stacks': [r['final_stack'] for r in results]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journal', type=Path)
    print(json.dumps(audit(parser.parse_args().journal), indent=1))


if __name__ == '__main__':
    main()
